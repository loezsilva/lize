import re
import io
import csv
import zipfile
from fiscallizeon.classes.models import SchoolClass, Stage
from fiscallizeon.clients.models import Unity
from fiscallizeon.core.utils import round_half_up
import pyexcel
from decimal import Decimal

from django.utils import timezone

from fiscallizeon.celery import app
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.exams.models import Exam
from fiscallizeon.accounts.models import User
from fiscallizeon.students.models import Student
from fiscallizeon.subjects.models import Subject
from fiscallizeon.exports.models import ExportExams
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.integrations.models import SubjectCode

def get_application_student_queryset(exam, students_filter, school_class=None, unity=None, start_date=None, end_date=None):
    get_present = students_filter == ExportExams.PRESENT_STUDENTS
    get_vacant = students_filter == ExportExams.ABSENT_STUDENTS

    application_students_exam = ApplicationStudent.objects.get_unique_set(
        exam=exam, 
        present=get_present, 
        vacant=get_vacant
    )

    if start_date and end_date:
        application_students_exam = application_students_exam.filter(
            application__date__gte=start_date,
            application__date__lte=end_date
        )

    if school_class:
        application_students_exam = application_students_exam.filter(
            student__in=school_class.students.all()
        ).distinct()

    elif unity:
        application_students_exam = application_students_exam.filter(
            student__classes__coordination__unity=unity
        ).distinct()
    
    return application_students_exam

def get_application_student_grades(exam, application_students, extra_columns=False, subjects=None, add_exam_name=False):
    
    if exam.is_abstract:
        local_subjects = Subject.objects.filter(question__in=exam.questions.all()).distinct()
    else:
        local_subjects = Subject.objects.filter(pk__in=exam.teacher_subjects.all().values_list('subject__pk', flat=True)).distinct()

    subjects = subjects or local_subjects
    queryset = application_students.get_annotation_count_answers(subjects=subjects, exclude_annuleds=True, include_give_score=True)

    columns_names = [
        'student__id', 
        'student__name', 
        'student__client__id_erp', 
        'student__enrollment_number',
        'start_time',
        'choice_grade_sum',
        'textual_grade_sum',
        'file_grade_sum',
        'sum_questions_grade_sum',
        'total_grade',
        'is_omr',
        'is_present',
        'application__date',
        'application__start'
    ]

    if extra_columns:
        columns_names.extend(['school_class_name', 'school_class_unity'])
        queryset = queryset.get_last_school_class(use_application_date=True)

    if add_exam_name:
        columns_names.extend(['application__exam__name'])

    return queryset.values(*columns_names)

def get_application_student_subjects_grades(exam, application_students, subjects=[]):
    subject_grades_columns = {}
    
    if exam.is_abstract:
        exam_subjects = Subject.objects.filter(question__in=exam.questions.all()).distinct()
    else:
        exam_subjects = Subject.objects.filter(pk__in=exam.teacher_subjects.all().values_list('subject__pk', flat=True)).distinct()


    if subjects:
        exam_subjects.filter(pk__in=subjects)

    for subject in exam_subjects:
        _application_students = []
        for result in application_students.get_annotation_subject_grade(subject=subject, exclude_annuleds=True):
            if result.total_subject_grade:
                _application_students.append(result.total_subject_grade)
            else:
                _application_students.append(Decimal(0.0))
                
        subject_grades_columns[subject.name] = _application_students

    return subject_grades_columns

@app.task(bind=True)
def export_exams_erp(
        self, exam_pks=[], school_class_pk=None, 
        unity_pk=None, students_filter=None, application_category=None,
        subjects_pks=[], subjects_format=ExportExams.SUBJECT_GRADES_SUMMED,
        extra_columns=False, file_format=ExportExams.FORMAT_CSV,
        start_date=None, end_date=None, add_exam_name=False,
        export_standard='fiscallize', unique_file=False, get_abstracts=False):

    exam_pks = ['56038e05-87cf-4956-bf90-7d582718812d']
    exams = Exam.objects.filter(pk__in=exam_pks)

    subjects = Subject.objects.filter(pk__in=subjects_pks)
    school_class = SchoolClass.objects.filter(pk=school_class_pk).first()
    unity = Unity.objects.filter(pk=unity_pk).first()

    self.update_state(state='PROGRESS', meta={'done': 0, 'total': exams.count()})

    zip_buffer = io.BytesIO()

    if unique_file:
        
        add_exam_name = True
        buffer = io.StringIO()  
        wr = csv.writer(buffer, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        
        if export_standard == 'fiscallize':
            # Inicia e ajusta o header da planilha
            subjects_grades = {}
            csv_header = ['Aluno', 'Matrícula']

            if extra_columns:
                csv_header.extend(['Turma', 'Unidade'])

            subjects_summed = subjects_format == ExportExams.SUBJECT_GRADES_SUMMED
            subjects_grades_rows = subjects_format == ExportExams.SUBJECT_GRADES_ROWS
            subjects_grades_columns = subjects_format == ExportExams.SUBJECT_GRADES_COLUMNS
            subjects_header = subjects_grades.keys()

            if subjects_grades_rows:
                csv_header.extend(['Disciplina', 'Nota'])
            elif subjects_summed:
                csv_header.extend(['Nota objetivas', 'Nota discursivas', 'Nota somatórias', 'Nota'])
            else:
                csv_header.extend(subjects_header)
                
            if add_exam_name:
                csv_header.extend(['Nome do caderno', ])

            csv_header.extend(['Data', 'Hora'])
        
        elif export_standard == 'totvs':
            csv_header = [
                'COD. COLIGADA', 
                'COD. CURSO', 
                'COD. HABILITACAO', 
                'COD. GRADE', 
                'TURNO', 
                'COD. FILIAL', 
                'COD. TIPO CURSO', 
                'RA', 
                'COD. TURMA', 
                'COD. PER. LETIVO', 
                'COD. DISCIPLINA', 
                'COD. ETAPA', 
                'TIPO ETAPA', 
                'COD. PROVA', 
                'CAMPO 1', 
                'VALOR', 
                'CAMPO 2',
            ]
        
        wr.writerow(csv_header)
        
        for i, exam in enumerate(exams, start=1):

            application_students = get_application_student_queryset(
                exam, students_filter, school_class, unity, start_date, end_date
            )

            application_students = application_students.annotate_is_present()

            if application_category:
                application_students = application_students.filter(
                    application__category=application_category
                )

            if export_standard == 'fiscallize':
                application_student_grades = get_application_student_grades(
                    exam, application_students, extra_columns, subjects, add_exam_name
                )

                if subjects_format is not ExportExams.SUBJECT_GRADES_SUMMED:
                    subjects_grades = get_application_student_subjects_grades(
                        exam, application_students, subjects
                    )

                for index, application_student in enumerate(application_student_grades):
                    student_row = [
                        application_student.get('student__name', 'Aluno'),
                        application_student.get('student__enrollment_number', '-'),
                    ]

                    if not application_student['is_present']:  
                        if subjects_grades_rows:
                            for subject in subjects_grades:
                                _student_row = student_row.copy()
                                _student_row.extend([subject, 'Ausente'])
                                
                                if extra_columns:
                                    _student_row.insert(2, application_student.get('school_class_name', '-'))
                                    _student_row.insert(3, application_student.get('school_class_unity', '-'))

                                if add_exam_name:
                                    _student_row.extend([application_student.get('application__exam__name', '-'), ])
                                wr.writerow(_student_row)
                            continue

                        elif subjects_summed:
                            student_row.extend(['', '', '', 'Ausente'])
                        else:
                            student_row.extend(['Ausente' for _ in subjects_header])

                        if extra_columns:
                            student_row.insert(2, application_student.get('school_class_name', '-'))
                            student_row.insert(3, application_student.get('school_class_unity', '-'))

                        if add_exam_name:
                            student_row.extend([application_student.get('application__exam__name', '-'), ])

                        wr.writerow(student_row)
                        continue

                    if extra_columns:
                        student_row.insert(2, application_student.get('school_class_name', '-'))
                        student_row.insert(3, application_student.get('school_class_unity', '-'))

                    if subjects_grades_rows:
                        for subject in subjects_grades:
                            _student_row = student_row.copy()
                            try:
                                _student_row.extend([subject, subjects_grades[subject][index]])
                                if add_exam_name:
                                    _student_row.extend([application_student.get('application__exam__name', '-'), ])
                                wr.writerow(_student_row)
                            except IndexError:
                                _student_row.extend([subject, 'Ausente'])
                                if add_exam_name:
                                    _student_row.extend([application_student.get('application__exam__name', '-'), ])
                                wr.writerow(_student_row)
                        continue

                    elif subjects_grades_columns:
                        try:
                            student_row.extend([grades[index] for s, grades in subjects_grades.items()])
                        except Exception as e:
                            student_row.append('')

                    else:
                        student_row.extend([
                            application_student.get('choice_grade_sum', 0),
                            application_student.get('textual_grade_sum', 0) + application_student.get('file_grade_sum', 0),
                            application_student.get('sum_questions_grade_sum', 0),
                            application_student.get('total_grade', '0'),
                        ])

                    if add_exam_name:
                        student_row.extend([application_student.get('application__exam__name', '-'), ])
                    
                    student_row.extend([application_student.get('application__date', '-'), application_student.get('application__start', '-')])
                    
                    wr.writerow(student_row)
            
            elif export_standard == 'totvs':

                application_students_with_grades = application_students.get_annotation_json_subjects_grades(subjects_pks=subjects_pks)

                for application_student in application_students_with_grades:
                    last_school_class = Student.objects.get(pk=application_student.student.pk).get_last_class()

                    for subject_json in application_student.exam_subjects_json:
                        student_row = [
                            application_student.student.client.id_erp or '',
                            last_school_class.course.id_erp if last_school_class and last_school_class.course else '',
                            last_school_class.name[:3] if last_school_class else '',
                            last_school_class.school_year if last_school_class else '',
                            last_school_class.get_turn_display() if last_school_class and last_school_class.get_turn_display() else '',
                            last_school_class.coordination.unity.id_erp if last_school_class else '',
                            last_school_class.course.course_type.id_erp if last_school_class and last_school_class.course else '',
                            application_student.student.enrollment_number or '',
                            last_school_class.name if last_school_class else '',
                            last_school_class.school_year if last_school_class else '',
                            subject_json.get('code', ''),
                            Stage.objects.all().first().id_erp if Stage.objects.all().first() else '',
                            Stage.objects.all().first().get_stage_type_display() if Stage.objects.all().first() else '',
                            exam.name,
                            '',
                            round_half_up(subject_json.get('grade', '0'), 1),
                            '',
                        ]
                        
                        wr.writerow(student_row)

        buffer.seek(0)
        sheet = pyexcel.load_from_memory("csv", buffer.getvalue())

        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:            
            exam_name = 'cadernos'
            if file_format == ExportExams.FORMAT_CSV:
                zip_file.writestr(f'{exam_name}.csv', sheet.csv.encode('utf-8'))
            else:
                zip_file.writestr(f'{exam_name}.xlsx', sheet.xlsx)

        self.update_state(state='PROGRESS', meta={'done': i, 'total': exams.count()})


        if exams:
            fs = PrivateMediaStorage()
            now = timezone.localtime(timezone.now())
            task_id = re.sub('\D', '', self.request.id)
            filename = fs.save(f'devolutivas/resultados/{task_id}_{now:%Y%m%d-%H%M%S}.zip', zip_buffer)
            self.update_state(state='SUCCESS', meta=fs.url(filename))
            return fs.url(filename)
        
    else:
        
        for i, exam in enumerate(exams, start=1):
            buffer = io.StringIO()  
            wr = csv.writer(buffer, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)

            subjects_grades = {}
            application_students = get_application_student_queryset(
                exam, students_filter, school_class, unity, start_date, end_date
            )

            application_students = application_students.annotate_is_present()

            if application_category:
                application_students = application_students.filter(
                    application__category=application_category
                )

            if export_standard == 'fiscallize':
                application_student_grades = get_application_student_grades(
                    exam, application_students, extra_columns, subjects, add_exam_name
                )

                if subjects_format is not ExportExams.SUBJECT_GRADES_SUMMED:
                    subjects_grades = get_application_student_subjects_grades(
                        exam, application_students, subjects
                    )

                csv_header = ['Aluno', 'Matrícula']

                if extra_columns:
                    csv_header.extend(['Turma', 'Unidade'])

                subjects_summed = subjects_format == ExportExams.SUBJECT_GRADES_SUMMED
                subjects_grades_rows = subjects_format == ExportExams.SUBJECT_GRADES_ROWS
                subjects_grades_columns = subjects_format == ExportExams.SUBJECT_GRADES_COLUMNS
                subjects_header = subjects_grades.keys()

                if subjects_grades_rows:
                    csv_header.extend(['Disciplina', 'Nota'])
                elif subjects_summed:
                    csv_header.extend(['Nota objetivas', 'Nota discursivas', 'Nota somatórias', 'Nota'])
                else:
                    csv_header.extend(subjects_header)
                    
                if add_exam_name:
                    csv_header.extend(['Nome do caderno', ])
                
                wr.writerow(csv_header)
    
                for index, application_student in enumerate(application_student_grades):
                    student_row = [
                        application_student.get('student__name', 'Aluno'),
                        application_student.get('student__enrollment_number', '-'),
                    ]            
                    
                    if not application_student['is_present']:  
                        if subjects_grades_rows:
                            for subject in subjects_grades:
                                _student_row = student_row.copy()
                                _student_row.extend([subject, 'Ausente'])
                                
                                if extra_columns:
                                    _student_row.insert(2, application_student.get('school_class_name', '-'))
                                    _student_row.insert(3, application_student.get('school_class_unity', '-'))

                                if add_exam_name:
                                    _student_row.extend([application_student.get('application__exam__name', '-'), ])
                                wr.writerow(_student_row)
                            continue

                        elif subjects_summed:
                            student_row.extend(['', '', '', 'Ausente'])
                        else:
                            student_row.extend(['Ausente' for _ in subjects_header])

                        if extra_columns:
                            student_row.insert(2, application_student.get('school_class_name', '-'))
                            student_row.insert(3, application_student.get('school_class_unity', '-'))

                        if add_exam_name:
                            student_row.extend([application_student.get('application__exam__name', '-'), ])

                        wr.writerow(student_row)
                        continue

                    if extra_columns:
                        student_row.insert(2, application_student.get('school_class_name', '-'))
                        student_row.insert(3, application_student.get('school_class_unity', '-'))

                    if subjects_grades_rows:
                        for subject in subjects_grades:
                            _student_row = student_row.copy()
                            try:
                                _student_row.extend([subject, subjects_grades[subject][index]])
                                if add_exam_name:
                                    _student_row.extend([application_student.get('application__exam__name', '-'), ])
                                wr.writerow(_student_row)
                            except IndexError:
                                _student_row.extend([subject, 'Ausente'])
                                if add_exam_name:
                                    _student_row.extend([application_student.get('application__exam__name', '-'), ])
                                wr.writerow(_student_row)
                        continue

                    elif subjects_grades_columns:
                        try:
                            student_row.extend([grades[index] for s, grades in subjects_grades.items()])
                        except Exception as e:
                            student_row.append('')

                    else:
                        student_row.extend([
                            application_student.get('choice_grade_sum', 0),
                            application_student.get('textual_grade_sum', 0) + application_student.get('file_grade_sum', 0),
                            application_student.get('sum_questions_grade_sum', 0),
                            application_student.get('total_grade', '0'),
                        ])

                    if add_exam_name:
                        student_row.extend([application_student.get('application__exam__name', '-'), ])

                    wr.writerow(student_row)
            
            elif export_standard == 'totvs':

                csv_header = [
                    'COD. COLIGADA', 
                    'COD. CURSO', 
                    'COD. HABILITACAO', 
                    'COD. GRADE', 
                    'TURNO', 
                    'COD. FILIAL', 
                    'COD. TIPO CURSO', 
                    'RA', 
                    'COD. TURMA', 
                    'COD. PER. LETIVO', 
                    'COD. DISCIPLINA', 
                    'COD. ETAPA', 
                    'TIPO ETAPA', 
                    'COD. PROVA', 
                    'CAMPO 1', 
                    'VALOR', 
                    'CAMPO 2'
                ]
                
                wr.writerow(csv_header)

                application_students_with_grades = application_students.get_annotation_json_subjects_grades(subjects_pks=subjects_pks, get_abstracts=get_abstracts)

                for application_student in application_students_with_grades:
                    last_school_class = Student.objects.get(pk=application_student.student.pk).get_last_class()

                    for subject_json in application_student.exam_subjects_json:
                        student_row = [
                            application_student.student.client.id_erp or '',
                            last_school_class.course.id_erp if last_school_class and last_school_class.course else '',
                            last_school_class.name[:3] if last_school_class else '',
                            last_school_class.school_year if last_school_class else '',
                            last_school_class.get_turn_display() if last_school_class and last_school_class.get_turn_display() else '',
                            last_school_class.coordination.unity.id_erp if last_school_class else '',
                            last_school_class.course.course_type.id_erp if last_school_class and last_school_class.course else '',
                            application_student.student.enrollment_number or '',
                            last_school_class.name if last_school_class else '',
                            last_school_class.school_year if last_school_class else '',
                            subject_json.get('code', ''),
                            Stage.objects.all().first().id_erp if Stage.objects.all().first() else '',
                            Stage.objects.all().first().get_stage_type_display() if Stage.objects.all().first() else '',
                            exam.name,
                            '',
                            round_half_up(subject_json.get('grade', '0'), 1),
                            '',
                        ]
                        
                        wr.writerow(student_row)


            buffer.seek(0)
            sheet = pyexcel.load_from_memory("csv", buffer.getvalue())

            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                exam_name = re.sub(r'[^a-zA-Z0-9_]+', '', exam.name)
                if file_format == ExportExams.FORMAT_CSV:
                    zip_file.writestr(f'{exam_name}.csv', sheet.csv.encode('utf-8'))
                else:
                    zip_file.writestr(f'{exam_name}.xlsx', sheet.xlsx)

            self.update_state(state='PROGRESS', meta={'done': i, 'total': exams.count()})


        if exams:
            fs = PrivateMediaStorage()
            now = timezone.localtime(timezone.now())
            task_id = re.sub('\D', '', self.request.id)
            filename = fs.save(f'devolutivas/resultados/{task_id}_{now:%Y%m%d-%H%M%S}.zip', zip_buffer)
            self.update_state(state='SUCCESS', meta=fs.url(filename))
            return fs.url(filename)

    self.update_state(state='SUCCESS', meta=0)