import re
import io
import uuid
import zipfile

import pandas as pd

from django.utils import timezone
from django.db.models import Value

from fiscallizeon.celery import app
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.exams.models import Exam, ExamTeacherSubject
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.accounts.models import User
from fiscallizeon.subjects.models import Subject

@app.task(bind=True)
def export_exams_simple(
        self, user_id, exam_pks, file_format, students_filter, separate_subjects=False, extra_fields=False, add_teacher_name=False
    ):

    exams = Exam.objects.filter(pk__in=exam_pks)
    user = User.objects.get(pk=user_id)

    self.update_state(state='PROGRESS', meta={'done': 0, 'total': exams.count()})

    zip_filename = f'/tmp/{str(uuid.uuid4())[:6]}.zip'
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for i, exam in enumerate(exams):

            if students_filter == 'presentes':
                application_students_exam = ApplicationStudent.objects.get_unique_set(
                    exam=exam, 
                    present=True, 
                )
            elif students_filter == 'ausentes':
                application_students_exam = ApplicationStudent.objects.get_unique_set(
                    exam=exam, 
                    vacant=True, 
                )
            else:
                application_students_exam = ApplicationStudent.objects.get_unique_set(
                    exam=exam, 
                )

            application_students_exam = application_students_exam.filter(
                student__user__is_active=True,
                student__classes__coordination__in=user.get_coordinations_cache(),
            )

            queryset_columns = [
                'student__name', 'student__enrollment_number', 
                'total_correct_answers', 'total_incorrect_answers', 
                'total_partial_answers'
            ]

            if extra_fields:
                application_students_exam = application_students_exam.get_last_school_class(use_application_date=True)
                queryset_columns.insert(2, 'school_class_name')
                queryset_columns.insert(3, 'school_class_unity')

            if separate_subjects:
                exam_subjects = exam.get_subjects()
                application_students_exam_subjects = ApplicationStudent.objects.none()

                for subject in exam_subjects:
                    if add_teacher_name:
                        application_students_exam_subjects = application_students_exam_subjects.union(
                            application_students_exam.get_annotation_subject_count(
                                subject=subject,
                                exclude_annuleds=True,
                            ).annotate(
                                subject_name=Value(subject.name),
                                teacher_name=Value("|".join(set(exam.examteachersubject_set.filter(
                                    teacher_subject__subject=subject
                                ).values_list(
                                    "teacher_subject__teacher__name", flat=True
                                ).distinct())))
                            )
                        )
                    else:
                        application_students_exam_subjects = application_students_exam_subjects.union(
                            application_students_exam.get_annotation_subject_count(
                                subject=subject,
                                exclude_annuleds=True,
                            ).annotate(
                                subject_name=Value(subject.name)
                            )
                        )
                
                queryset_columns.append('subject_name')

                if add_teacher_name:
                    queryset_columns.append('teacher_name')

                application_students = application_students_exam_subjects.values(*queryset_columns)
            else:
                application_students = application_students_exam.get_annotation_count_answers(
                    only_total_answers=True,
                    exclude_annuleds=True,
                ).values(
                    *queryset_columns
                )

                if add_teacher_name:
                    application_students = application_students.annotate(
                        teacher_name=Value("|".join(set(exam.examteachersubject_set.all().values_list(
                            "teacher_subject__teacher__name", flat=True
                        ).distinct())))
                    )

            df = pd.DataFrame(application_students)
            df = df.sort_values(by='student__name')

            subjects_dict = []

            if exam.is_abstract:
                questions = exam.questions.availables(exam=exam)
                for subject in Subject.objects.filter(question__in=questions).distinct():
                    subjects_dict.append({
                        'subject_name': subject.name,
                        'total_questions': questions.filter(subject=subject).count()
                    })

            else:

                for ets in ExamTeacherSubject.objects.filter(exam=exam):
                    subjects_dict.append({
                        'subject_name': ets.teacher_subject.subject.name,
                        'total_questions': ets.examquestion_set.availables().count()
                    })

            subjects_df = pd.DataFrame(subjects_dict)

            if separate_subjects:
                df = df.merge(subjects_df, on='subject_name', how='left')
            else:
                df['total_questions'] = int(subjects_df['total_questions'].sum())

            df.rename(columns={
                    "student__name": "Aluno", 
                    "student__enrollment_number": "Matrícula", 
                    "school_class_name": "Turma", 
                    "school_class_unity": "Unidade", 
                    "exam_name": "Caderno",
                    "total_correct_answers": "Acertos",
                    "total_incorrect_answers": "Erros",
                    "total_partial_answers": "Parciais",
                    "subject_name": "Disciplina",
                    "teacher_name": "Professores",
                    "total_questions": 'Total de questões'
                }, inplace=True)
            
            exam_name = exam.name.replace('/', '')

            if file_format == 'csv':
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                zip_file.writestr(f'{exam_name}.csv', csv_buffer.getvalue())
            else:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Resultados')

                buffer.seek(0)
                zip_file.writestr(f'{exam_name}.xlsx', buffer.getvalue())

            self.update_state(state='PROGRESS', meta={'done': i, 'total': exams.count()})

    if exams:
        fs = PrivateMediaStorage()
        now = timezone.localtime(timezone.now())
        task_id = re.sub('\D', '', self.request.id)

        with open(zip_filename, 'rb') as file:
            filename = fs.save(f'devolutivas/resultados/{task_id}_{now:%Y%m%d-%H%M%S}.zip', file)
        self.update_state(state='SUCCESS', meta=fs.url(filename))
        return fs.url(filename)

    self.update_state(state='SUCCESS', meta=0)