import io
import uuid
import csv
from fiscallizeon.exports.models import ExportExams 

import pyexcel
import pandas as pd

from django.conf import settings
from django.shortcuts import get_object_or_404, reverse, redirect
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Subquery, OuterRef, Case, When, Value, DecimalField, CharField, Q
from django.db.models.functions import Coalesce
from django.views.generic import FormView, TemplateView
from django.views.generic.detail import DetailView
from django.http import HttpResponse

from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.exams.models import Exam, ExamQuestion
from fiscallizeon.classes.models import SchoolClass, Stage, Grade
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.clients.models import Unity
from fiscallizeon.subjects.models import Subject
from fiscallizeon.answers.models import OptionAnswer, FileAnswer, TextualAnswer
from fiscallizeon.corrections.models import CorrectionTextualAnswer, CorrectionFileAnswer
from fiscallizeon.exports.forms import ExamExportAnswerForm, ExamsExportErpForm, ExamsExportAnswerForm, ExamsSimpleExportForm
from fiscallizeon.exports.tasks.export_exams_erp import export_exams_erp
from fiscallizeon.exports.tasks.export_exams_answers import export_exams_answers
from fiscallizeon.exports.tasks.export_exams_simple import export_exams_simple
from fiscallizeon.omrnps.tasks.results.export_results import export_application_results
from fiscallizeon.omrnps.models import NPSApplication


class ExamExportDetailView(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, settings.TEACHER ]
    template_name = 'dashboard/exports/exam_export.html'
    model = Exam

    def get_subjects(self):
        exam_questions = self.object.questions.all()
        if self.object.is_abstract:
            exam_subjects = Subject.objects.filter(question__in=exam_questions.all()).distinct()
        else:
            exam_subjects = Subject.objects.filter(pk__in=self.object.teacher_subjects.all().values_list('subject__pk', flat=True)).distinct()

        user = self.request.user
        if user.user_type == settings.TEACHER:
            return user.inspector.subjects.all().intersection(exam_subjects)

        return exam_subjects

    def get_context_data(self, **kwargs):
        user_coordinations = self.request.user.get_coordinations_cache()
        application_students_exam = ApplicationStudent.objects.filter(
            application__exam=self.get_object(),
            student__user__is_active=True,
            student__classes__coordination__in=user_coordinations
        )
        school_classes = SchoolClass.objects.none()

        if application_students_exam.exists():
            school_classes = SchoolClass.objects.filter(
                coordination__in=user_coordinations,
                students__applicationstudent__in=application_students_exam,
                school_year=application_students_exam.first().application.date.year
            ).distinct()

        unities = Unity.objects.filter(
            coordinations__in=user_coordinations
        )

        context = super(ExamExportDetailView, self).get_context_data(**kwargs)
        context['exam_subjects'] = self.get_subjects()
        context['school_classes'] = school_classes
        context['unities'] = unities
        return context


class ExamExportReportView(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, settings.TEACHER ]
    template_name = 'dashboard/exports/exam_export.html'
    model = Exam
    unity = None
    school_class = None
    export_format = None
    extra_columns = False
    show_exam_name = False
    show_teacher_name = False
    subject_grades_columns = {}
    subject_grades_rows = False
    subjects = []

    def clean_params(self):
        self.unity = None
        self.school_class = None
        self.export_format = None
        self.extra_columns = False
        self.show_exam_name = False
        self.show_teacher_name = False
        self.subject_grades_columns = {}
        self.subject_grades_rows = False
        
        self.subjects = []
        
    def get_application_student_details(self):
        user = self.request.user
        self.object = self.get_object()

        school_class_pk = self.request.GET.get('turma', '')
        unity_pk = self.request.GET.get('unidade', '')
        students_filter = self.request.GET.get('alunos', '')
        self.export_format = self.request.GET.get('formato', '')
        self.extra_columns = bool(self.request.GET.get('colunas-extras', False))
        self.show_exam_name = bool(self.request.GET.get('show_exam_name', False))    
        self.show_teacher_name = bool(self.request.GET.get('show_teacher_name', False))        

        if students_filter == 'presentes':
            application_students_exam = ApplicationStudent.objects.get_unique_set(
                exam=self.object, 
                present=True, 
            ).filter(
                student__user__is_active=True
            )
        elif students_filter == 'ausentes':
            application_students_exam = ApplicationStudent.objects.get_unique_set(
                exam=self.object, 
                vacant=True, 
            ).filter(
                student__user__is_active=True
            )
        else:
            application_students_exam = ApplicationStudent.objects.get_unique_set(
                exam=self.object, 
            ).filter(
                student__user__is_active=True
            )

        if not application_students_exam:
            return ApplicationStudent.objects.none()
        
        application_students_exam = application_students_exam.filter(
            Q(
                Q(student__classes__coordination__in=self.request.user.get_coordinations_cache()) |
                Q(student__classes__isnull=True)
            )
        )

        application_students_exam = application_students_exam.filter(
            created_at__year=application_students_exam.order_by('created_at').last().application.date.year
        )

        application_students_exam = (
            application_students_exam
            .annotate_is_present_with_subquery()
            .has_answer_and_last_applicationstudent()
        )

        if school_class_pk:
            self.school_class = get_object_or_404(SchoolClass, pk=school_class_pk)
            class_students = self.school_class.students.all()
            application_students_exam = application_students_exam.filter(
                student__in=class_students
            ).distinct()
        elif unity_pk:
            self.unity = get_object_or_404(Unity, pk=unity_pk)
            application_students_exam = application_students_exam.filter(
                student__classes__coordination__unity=self.unity
            ).distinct()

        subjects_request = self.request.GET.get('disciplinas-detalhadas', False)
        detailed_subjects_columns = subjects_request == 'colunas'
        self.subject_grades_rows = subjects_request == 'linhas'

        subject_pks = self.request.GET.getlist('disciplinas', [])
        subjects_filter = Subject.objects.filter(pk__in=subject_pks) if subject_pks else []
        self.subjects = subjects_filter.values_list('name', flat=True) if subject_pks else []

        detailed_subjects = detailed_subjects_columns or self.subject_grades_rows
        if detailed_subjects:
            if self.object.is_abstract:
                exam_subjects = Subject.objects.filter(question__in=self.object.questions.all()).distinct()
            else:
                exam_subjects = Subject.objects.filter(pk__in=self.object.teacher_subjects.all().values_list('subject__pk', flat=True)).distinct()

            if subjects_filter:
                exam_subjects = subjects_filter

            for subject in exam_subjects:
                list_grades = []

                for a in application_students_exam.get_annotation_subject_grade(subject=subject, exclude_annuleds=True).distinct():
                    if a.has_answer or a.last_application_student_id == a.id:
                        list_grades.append(a.total_subject_grade)

                self.subject_grades_columns[subject.name] = list_grades


        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if self.object.correction_by_subject:  
                subjects = teacher.subjects.all()
                queryset = application_students_exam.get_annotation_count_answers_filter_subjects(subjects=subjects_filter or subjects, exclude_annuleds=True)
            else:          
                queryset = application_students_exam.get_annotation_count_answers_filter_teacher(teacher=teacher, subjects=subjects_filter, exclude_annuleds=True)
        else:
            queryset = application_students_exam.get_annotation_count_answers(subjects=subjects_filter, exclude_annuleds=True)
            
        fields = [
            'student__name',
            'student__enrollment_number', 
            'start_time', 
            'choice_grade_sum', 
            'textual_grade_sum', 
            'file_grade_sum',
            'sum_questions_grade_sum',
            'total_grade', 
            'is_omr', 
            'is_present'
        ]
        
        if self.show_exam_name:
            fields.append('exam_name')
            queryset = queryset.annotate_exam_name()

        if self.extra_columns:
            fields.extend(['school_class_name','school_class_unity'])
            queryset = queryset.get_last_school_class(use_application_date=True)

        return queryset.values(*fields)


    def get(self, request, *args, **kwargs):
        self.clean_params()

        buffer = io.StringIO()  
        wr = csv.writer(buffer, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)

        application_students = self.get_application_student_details()

        csv_header = ['Aluno', 'Matrícula']  
        subjects_header = self.subject_grades_columns.keys()
        subjects_summed = self.request.GET.get('disciplinas-detalhadas', '') == 'somadas'

        if self.show_exam_name:
            csv_header.extend(['Caderno'])

        if self.extra_columns:
            csv_header.extend(['Turma', 'Unidade'])

        if self.subject_grades_rows:
            csv_header.extend(['Disciplina', 'Nota'])

        elif subjects_summed:
            csv_header.extend(['Nota objetivas', 'Nota discursivas', 'Nota somatórias', 'Nota'])

        else:
            csv_header.extend(subjects_header)

        if (self.subject_grades_rows or subjects_summed) and self.show_teacher_name and not self.get_object().is_abstract:
            csv_header.extend(['Professores'])
        
        wr.writerow(csv_header)

        for index, application_student in enumerate(application_students):
            if not application_student['is_present']: 
                student_row = [
                    application_student.get('student__name', ''),
                    application_student.get('student__enrollment_number', ''),                        
                ]

                if self.show_exam_name:
                    student_row.extend([
                        application_student.get('exam_name', '-'),
                    ])   

                if self.extra_columns:
                    student_row.extend([
                        application_student.get('school_class_name', '-'), 
                        application_student.get('school_class_unity', '-')
                    ])                        

                if self.subject_grades_rows:
                    for subject in self.subject_grades_columns:
                        student_row.extend([subject, 'Ausente'])
                elif subjects_summed:
                    student_row.extend(['', '', '', 'Ausente'])

                else:
                    student_row.extend(['Ausente' for _ in subjects_header])

                wr.writerow(student_row)
                continue
            
            student_row = [
                application_student.get('student__name', 'Aluno'),
                application_student.get('student__enrollment_number', ''),
            ]

            if self.show_exam_name:
                student_row.insert(2, application_student.get('exam_name', '-'))

            if self.extra_columns:
                student_row.insert(3 if self.show_exam_name else 2, application_student.get('school_class_name', '-'))
                student_row.insert(4 if self.show_exam_name else 3, application_student.get('school_class_unity', '-'))   

            if self.subject_grades_rows:
                for subject in self.subject_grades_columns:
                    _student_row = student_row.copy()
                    _student_row.extend([
                        subject, 
                            self.subject_grades_columns[subject][index],
                        ]
                    )
                    if self.show_teacher_name:
                        _student_row.extend([
                            f"{'|'.join(self.get_object().examteachersubject_set.filter(teacher_subject__subject__name=subject).values_list('teacher_subject__teacher__name', flat=True).distinct())}"
                        ])
                    wr.writerow(_student_row)
                continue        

            elif self.subject_grades_columns:
                try:
                    student_row.extend([grades[index] for s, grades in self.subject_grades_columns.items()])
                except Exception as e:
                    student_row.append('')

            else:
                student_row.extend([
                    f"{application_student.get('choice_grade_sum', 0):.5f}",
                    f"{application_student.get('textual_grade_sum', 0) + application_student.get('file_grade_sum', 0):.5f}",
                    f"{application_student.get('sum_questions_grade_sum', 0):.5f}",
                    f"{application_student.get('total_grade', '0'):.5f}",
                ])

                if self.show_teacher_name:
                    student_row.extend([
                        f"{'|'.join(self.get_object().examteachersubject_set.all().values_list('teacher_subject__teacher__name', flat=True).distinct())}"
                    ])

            wr.writerow(student_row)

        buffer.seek(0)
        sheet = pyexcel.load_from_memory("csv", buffer.getvalue())

        if self.export_format == 'csv':
            response = HttpResponse(sheet.csv, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{self.get_object().name}.csv"'        
        else:
            response = HttpResponse(sheet.xlsx, content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = f'attachment; filename="{self.get_object().name}.xlsx"'
        
        return response

class ExamExportReportAnswersView(LoginRequiredMixin, CheckHasPermission, FormView):
    required_permissions = [settings.COORDINATION, settings.TEACHER ]
    template_name = 'dashboard/exports/exam_export.html'
    form_class = ExamExportAnswerForm

    def get_success_url(self):
        base_url = reverse('exports:exam_export_report_answers', kwargs={'pk': self.kwargs['pk']})
        return f'{base_url}?export_id={self.export_id}'

    def form_valid(self, form):
        exams = Exam.objects.filter(pk=self.kwargs.get('pk'))

        export_kwargs = {
            'user_id': str(self.request.user.id),
            'exam_pks': [str(exam.pk) for exam in exams],
            'file_format': form.cleaned_data.get('file_format'),
            'add_topic': form.cleaned_data.get('add_topic'),
            'add_bncc': form.cleaned_data.get('add_bncc'),
            'only_correct_wrong': form.cleaned_data.get('only_correct_wrong'),
            'add_teacher_name': form.cleaned_data.get('add_teacher_name'),
            'export_disposition': form.cleaned_data.get('export_disposition'),
            'start_date': form.cleaned_data['start_date'].strftime('%Y-%m-%d') if form.cleaned_data['start_date'] else None,
            'end_date': form.cleaned_data['end_date'].strftime('%Y-%m-%d') if form.cleaned_data['end_date'] else None,
        }

        self.export_id = uuid.uuid4()
        export_exams_answers.apply_async(
            kwargs=export_kwargs,
            task_id=f'EXAMS_EXPORT_RESULTS_{self.export_id}'
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        print('################# INVALID')
        print(form.errors)
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['export_id'] = self.request.GET.get('export_id', '')
        context['object'] = Exam.objects.get(pk=self.kwargs.get('pk'))
        return context

class ExamExportSimpleReportView(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, settings.TEACHER ]
    template_name = 'dashboard/exports/exam_export.html'
    model = Exam

    def get_application_student_details(
            self, students_filter, separate_subjects=False, extra_columns=False, add_exam_name=False, school_class=None, unity=None, add_teacher_name=False):

        self.object = self.get_object()

        if students_filter == 'presentes':
            application_students_exam = ApplicationStudent.objects.get_unique_set(
                exam=self.object, 
                present=True, 
            )
        elif students_filter == 'ausentes':
            application_students_exam = ApplicationStudent.objects.get_unique_set(
                exam=self.object, 
                vacant=True, 
            )
        else:
            application_students_exam = ApplicationStudent.objects.get_unique_set(
                exam=self.object, 
            )

        application_students_exam = application_students_exam.filter(student__user__is_active=True)

        queryset_columns = [
            'student__name', 'student__enrollment_number', 
            'total_correct_answers', 'total_incorrect_answers', 
            'total_partial_answers'
        ]

        if school_class:
            class_students = school_class.students.all()
            application_students_exam = application_students_exam.filter(
                student__in=class_students
            ).distinct()
        elif unity:
            application_students_exam = application_students_exam.filter(
                student__classes__coordination__unity=unity
            ).distinct()

        if extra_columns:
            application_students_exam = application_students_exam.get_last_school_class(use_application_date=True)
            queryset_columns.insert(2, 'school_class_name')
            queryset_columns.insert(3, 'school_class_unity')

        if add_exam_name:
            application_students_exam = application_students_exam.annotate(exam_name=Value(self.object.name))
            queryset_columns.insert(0, 'exam_name')

        if separate_subjects:
            exam_subjects = self.object.get_subjects()
            application_students_exam_subjects = ApplicationStudent.objects.none()

            for subject in exam_subjects:
                if add_teacher_name:
                    application_students_exam_subjects = application_students_exam_subjects.union(
                        application_students_exam.get_annotation_subject_count(
                            subject=subject
                        ).annotate(
                            subject_name=Value(subject.name),
                            teacher_name=Value("|".join(set(self.object.examteachersubject_set.filter(
                                teacher_subject__subject=subject
                            ).values_list(
                                "teacher_subject__teacher__name", flat=True
                            ).distinct())))
                        )
                    )
                else:
                    application_students_exam_subjects = application_students_exam_subjects.union(
                        application_students_exam.get_annotation_subject_count(
                            subject=subject
                        ).annotate(
                            subject_name=Value(subject.name)
                        )
                    )
            
            queryset_columns.append('subject_name')
            if add_teacher_name:
                queryset_columns.append('teacher_name')
            return application_students_exam_subjects.values(*queryset_columns)

        application_students_exam = application_students_exam.get_annotation_count_answers(
            only_total_answers=True
        ).values(
            *queryset_columns
        )

        if add_teacher_name:
            return application_students_exam.annotate(
                teacher_name=Value("|".join(set(self.object.examteachersubject_set.all().values_list(
                    "teacher_subject__teacher__name", flat=True
                ).distinct())))
            )
        
        return application_students_exam

    def get(self, request, *args, **kwargs):
        export_format = self.request.GET.get('formato', '')
        students_filter = self.request.GET.get('alunos', '')
        school_class_pk = self.request.GET.get('turma', '')
        unity_pk = self.request.GET.get('unidade', '')

        try:
            separate_subjects = bool(self.request.GET.get('separar-disciplinas', 0))
            extra_columns = bool(self.request.GET.get('colunas-extras', 0))
            add_exam_name = bool(self.request.GET.get('adicionar-nome-caderno', 0))
            add_teacher_name = bool(self.request.GET.get('adicionar-nome-professor', 0))
        except:
            separate_subjects = self.request.GET.get('separar-disciplinas', False)
            extra_columns = self.request.GET.get('colunas-extras', False)
            add_exam_name = self.request.GET.get('adicionar-nome-caderno', False)
            add_teacher_name = self.request.GET.get('adicionar-nome-professor', False)

        school_class, unity = None, None
        if school_class_pk:
            school_class = get_object_or_404(SchoolClass, pk=school_class_pk)
        elif unity_pk:
            unity = get_object_or_404(Unity, pk=unity_pk)

        application_students = self.get_application_student_details(
            students_filter, separate_subjects, extra_columns, add_exam_name, school_class, unity, add_teacher_name
        )
        df = pd.DataFrame(application_students)
        df = df.sort_values(by='student__name')
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
                "teacher_name": "Professores"
            }, inplace=True)

        if export_format == 'csv':
            buffer = io.StringIO()
            df.to_csv(buffer, index=False)
            csv_content = buffer.getvalue()
            buffer.close()

            response = HttpResponse(csv_content, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{self.object.name}.csv"'
        else:
            buffer = io.BytesIO()

            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Resultados')
            
            xlsx_content = buffer.getvalue()
            buffer.close()

            response = HttpResponse(xlsx_content, content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = f'attachment; filename="{self.object.name}.xlsx"'
        
        return response

class ExamExporCorrectionsReportView(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, settings.TEACHER ]
    template_name = 'dashboard/exports/exam_export.html'
    model = Exam

    def dispatch(self, request, *args, **kwargs):

        if not self.get_object().has_text_correction_questions:
            messages.warning(
                self.request, 
                'Nenhuma questão com correção por critério.'
            )
            return redirect(reverse('core:redirect_dashboard')) 

        return super().dispatch(request, *args, **kwargs)

    def get_application_student_queryset(
            self, students_filter, extra_columns=False, add_exam_name=False, school_class=None, unity=None):

       
        application_students_exam = ApplicationStudent.objects.get_unique_set(
            exam=self.object,
        ).filter(
            student__user__is_active=True
        )

        queryset_columns = [
            'application_student_id', 'student__name', 'student__enrollment_number', 
        ]

        if school_class:
            class_students = school_class.students.all()
            application_students_exam = application_students_exam.filter(
                student__in=class_students
            ).distinct()
        elif unity:
            application_students_exam = application_students_exam.filter(
                student__classes__coordination__unity=unity,
                student__classes__school_year=timezone.now().year
            ).distinct()

        if extra_columns:
            application_students_exam = application_students_exam.get_last_school_class(use_application_date=True)
            queryset_columns.append('school_class_name')
            queryset_columns.append('school_class_unity')

        if add_exam_name:
            application_students_exam = application_students_exam.annotate(exam_name=Value(self.object.name))
            queryset_columns.insert(0, 'exam_name')

        application_students_exam = application_students_exam.get_annotation_count_answers(
            only_total_answers=True
        ).annotate(
            application_student_id=F('id')
        ).values(
            *queryset_columns
        )

        return application_students_exam

    def get_corrections_queryset(self, add_teacher_name=False):
        queryset_values = [
            'application_student_id',
            'question_id',
            'criterion_name',
            'criterion_order',
            'grade',
        ]

        if add_teacher_name:
            queryset_values.append('teacher_name')

        textual_corrections = CorrectionTextualAnswer.objects.filter(
            textual_answer__student_application__application__exam=self.object
        ).annotate(
            application_student_id=F('textual_answer__student_application_id'),
            question_id=F('textual_answer__question_id'),
            criterion_name=F('correction_criterion__name'),
            criterion_order=F('correction_criterion__order'),
            grade=F('point'),
            teacher_name=F('textual_answer__who_corrected__name'),
        ).values(
            *queryset_values
        )

        file_corrections = CorrectionFileAnswer.objects.filter(
            file_answer__student_application__application__exam=self.object
        ).annotate(
            application_student_id=F('file_answer__student_application_id'),
            question_id=F('file_answer__question_id'),
            criterion_name=F('correction_criterion__name'),
            criterion_order=F('correction_criterion__order'),
            grade=F('point'),
            teacher_name=F('file_answer__who_corrected__name'),
        ).values(
            *queryset_values
        )

        return textual_corrections.union(file_corrections)

    def get(self, request, *args, **kwargs):
        export_format = self.request.GET.get('formato', '')
        students_filter = self.request.GET.get('alunos', '')
        school_class_pk = self.request.GET.get('turma', '')
        unity_pk = self.request.GET.get('unidade', '')

        self.object = self.get_object()

        try:
            extra_columns = bool(self.request.GET.get('colunas-extras', 0))
            add_exam_name = bool(self.request.GET.get('adicionar-nome-caderno', 0))
            add_teacher_name = bool(self.request.GET.get('adicionar-nome-professor', 0))
        except:
            extra_columns = self.request.GET.get('colunas-extras', False)
            add_exam_name = self.request.GET.get('adicionar-nome-caderno', False)
            add_teacher_name = self.request.GET.get('adicionar-nome-professor', False)

        school_class, unity = None, None
        if school_class_pk:
            school_class = get_object_or_404(SchoolClass, pk=school_class_pk)
        elif unity_pk:
            unity = get_object_or_404(Unity, pk=unity_pk)

        questions = self.object.get_ordered_questions().filter(
            text_correction__isnull=False
        )

        questions_orders = [
            {'question_id': q.id, 'number': self.object.number_print_question(q)}
            for q in questions
        ]

        application_students = self.get_application_student_queryset(
            students_filter, extra_columns, add_exam_name, school_class, unity
        )

        corrections = self.get_corrections_queryset(add_teacher_name)

        questions_df = pd.DataFrame(questions_orders)
        students_df = pd.DataFrame(application_students)
        corrections_df = pd.DataFrame(corrections)

        print(students_df.columns)

        corrections_questions_df = pd.merge(questions_df, corrections_df, on='question_id')
        final_df = pd.merge(students_df, corrections_questions_df, on='application_student_id')
        final_df = final_df.sort_values(by=['student__name', 'criterion_order', 'number'])

        final_df.drop(columns=['application_student_id', 'question_id', 'criterion_order'], inplace=True)

        final_df.rename(columns={
                "student__name": "Aluno", 
                "student__enrollment_number": "Matrícula", 
                "school_class_name": "Turma", 
                "school_class_unity": "Unidade", 
                "exam_name": "Caderno",
                "teacher_name": "Professor",
                "grade": "Nota",
                "number": "Questão",
                "criterion_name": "Critério",
            }, inplace=True)

        if export_format == 'csv':
            buffer = io.StringIO()
            final_df.to_csv(buffer, index=False)
            csv_content = buffer.getvalue()
            buffer.close()

            response = HttpResponse(csv_content, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{self.object.name}.csv"'
        else:
            buffer = io.BytesIO()

            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                final_df.to_excel(writer, index=False, sheet_name='Resultados')
            
            xlsx_content = buffer.getvalue()
            buffer.close()

            response = HttpResponse(xlsx_content, content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = f'attachment; filename="{self.object.name}.xlsx"'
        
        return response

class ExamsExportErp(LoginRequiredMixin, CheckHasPermission, FormView):
    required_permissions = [settings.COORDINATION, settings.TEACHER ]
    template_name = 'dashboard/exports/exams_export_erp.html'
    form_class = ExamsExportErpForm
    
    def get_success_url(self):
        from urllib.parse import urlparse, parse_qs, urlencode
        base_url = reverse('exports:exams_export_erp')
        url = f'{base_url}?export_id={self.export_id}'
        query_string = urlparse(self.request.META['HTTP_REFERER']).query
        params_dict = parse_qs(query_string)
        query_params = urlencode(params_dict, doseq=True)
        return f'{url}&{query_params}' 

    def get_form_kwargs(self):
        kwargs = super(ExamsExportErp, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        exam_pks = [str(exam.pk) for exam in form.cleaned_data.get('exams', [])]
        subject_pks = [str(subject.pk) for subject in form.cleaned_data['subjects']]
        
        start_date = form.cleaned_data.get('start_date', None)
        end_date = form.cleaned_data.get('end_date', None)

        start_date = form.cleaned_data.get('start_date', None) 
        end_date  = form.cleaned_data.get('end_date', None) 

        add_exam_name  = form.cleaned_data.get('add_exam_name', None) 

        if start_date and end_date:
            exam_pks = Exam.objects.filter(
                application__date__gte=start_date,
                application__date__lte=end_date,
                coordinations__in=self.request.user.get_coordinations(),
            ).distinct().values_list('pk', flat=True)
        
        export_kwargs = {
            'user_id': str(self.request.user.id),
            'exam_pks': list(exam_pks),
            'subjects_pks': subject_pks,
            'extra_columns': form.cleaned_data.get('extra_columns', False),
            'students_filter': form.cleaned_data.get('students', None),
            'subjects_format': form.cleaned_data.get('subjects_format', 'all'),
            'start_date': start_date.strftime('%Y-%m-%d')  if start_date else None,
            'end_date': end_date.strftime('%Y-%m-%d') if end_date else None,
            'add_exam_name': add_exam_name,
            'export_standard': form.cleaned_data.get('export_standard'),
            'unique_file': form.cleaned_data.get('unique_file', False),
            'get_abstracts': form.cleaned_data.get('get_abstracts', False),
        }

        if unity := form.cleaned_data.get('unity', None):
            export_kwargs['unity_pk'] = unity.pk
        elif school_class := form.cleaned_data.get('school_class', None):
            export_kwargs['school_class_pk'] = school_class.pk

        if form.cleaned_data.get('export_format', None) == 'xlsx':
            export_kwargs['file_format'] = ExportExams.FORMAT_XLS

        if form.cleaned_data.get('application_category', None) == 'online':
            export_kwargs['application_category'] = Application.MONITORIN_EXAM
            
        elif form.cleaned_data.get('application_category', None) == 'presencial':
            export_kwargs['application_category'] = Application.PRESENTIAL
        self.export_id = uuid.uuid4()
        export_exams_erp.apply_async(
            kwargs=export_kwargs,
            task_id=f'EXAMS_EXPORT_RESULTS_{self.export_id}'
        )
        return super(ExamsExportErp, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(ExamsExportErp, self).get_context_data(**kwargs)
        context['export_id'] = self.request.GET.get('export_id', '')

        if exam_id := self.request.GET.get('q_exam_id', None):
            try:
                context['selected_exam'] = Exam.objects.get(id=exam_id)
            except:
                pass
        
        context['get_abstracts'] = self.request.GET.get('get_abstracts', False)
        
        return context

class ExamsExportAnswers(LoginRequiredMixin, CheckHasPermission, FormView):
    required_permissions = [settings.COORDINATION, settings.TEACHER ]
    template_name = 'dashboard/exports/exams_export_answers.html'
    form_class = ExamsExportAnswerForm

    def get_success_url(self):
        from urllib.parse import urlparse, parse_qs, urlencode
        base_url = reverse('exports:exams_export_answers')
        url = f'{base_url}?export_id={self.export_id}'
        query_string = urlparse(self.request.META['HTTP_REFERER']).query
        params_dict = parse_qs(query_string)
        query_params = urlencode(params_dict, doseq=True)
        return f'{url}&{query_params}' 
   
    def form_valid(self, form):
        exams = Exam.objects.filter(
            application__date__gte=form.cleaned_data['start_date'],
            application__date__lte=form.cleaned_data['end_date'],
            coordinations__in=self.request.user.get_coordinations(),
        ).distinct()

        if not exams:
            messages.warning(
                self.request, 
                'Nenhuma prova encontrada para o período informado. Selecione um novo período e tente novamente.'
            )
            return super().form_invalid(form)

        export_kwargs = {
            'user_id': str(self.request.user.id),
            'exam_pks': [str(exam.pk) for exam in exams],
            'start_date': form.cleaned_data['start_date'].strftime('%Y-%m-%d'),
            'end_date': form.cleaned_data['end_date'].strftime('%Y-%m-%d'),
            'add_topic': form.cleaned_data.get('add_topic'),
            'add_bncc': form.cleaned_data.get('add_bncc'),
            'file_format': form.cleaned_data.get('export_format', None)
        }

        self.export_id = uuid.uuid4()
        export_exams_answers.apply_async(
            kwargs=export_kwargs,
            task_id=f'EXAMS_EXPORT_RESULTS_{self.export_id}'
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['export_id'] = self.request.GET.get('export_id', '')
        if exam_id := self.request.GET.get('q_exam_id', None):
            try:
                context['selected_exam'] = Exam.objects.get(id=exam_id)
            except:
                pass
        
        context['get_abstracts'] = self.request.GET.get('get_abstracts', False)

        return context

class ExamsSimpleExportView(LoginRequiredMixin, CheckHasPermission, FormView):
    required_permissions = [settings.COORDINATION, settings.TEACHER ]
    template_name = 'dashboard/exports/exams_export_simple.html'
    form_class = ExamsSimpleExportForm

    def get_success_url(self):
        from urllib.parse import urlparse, parse_qs, urlencode
        base_url = reverse('exports:exams_export_simple_report')
        url = f'{base_url}?export_id={self.export_id}'
        query_string = urlparse(self.request.META['HTTP_REFERER']).query
        params_dict = parse_qs(query_string)
        query_params = urlencode(params_dict, doseq=True)
        return f'{url}&{query_params}' 

    def form_valid(self, form):
        exams_pks = list(form.cleaned_data.get('exams', []).values_list('pk', flat=True))
        start_date = form.cleaned_data.get('start_date', None)
        end_date = form.cleaned_data.get('end_date', None)

        if start_date and end_date:
            exams_pks = list(
                Exam.objects.filter(
                    application__date__gte=start_date,
                    application__date__lte=end_date,
                    coordinations__in=self.request.user.get_coordinations(),
                ).distinct().values_list('pk', flat=True)
            )

        if not exams_pks:
            messages.warning(
                self.request, 
                'Nenhuma prova encontrada para o período informado. Selecione um novo período e tente novamente.'
            )
            return super().form_invalid(form)

        export_kwargs = {
            'user_id': str(self.request.user.id),
            'exam_pks': exams_pks,
            'students_filter': form.cleaned_data.get('students_filter', None),
            'file_format': form.cleaned_data.get('export_format', None),
            'separate_subjects': form.cleaned_data.get('separate_subjects', False),
            'extra_fields': form.cleaned_data.get('extra_fields', False),
            'add_teacher_name': form.cleaned_data.get('add_teacher_name', False),
        }

        self.export_id = uuid.uuid4()

        export_exams_simple.apply_async(
            kwargs=export_kwargs,
            task_id=f'EXAMS_EXPORT_RESULTS_{self.export_id}'
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['export_id'] = self.request.GET.get('export_id', '')
        if exam_id := self.request.GET.get('q_exam_id', None):
            try:
                context['selected_exam'] = Exam.objects.get(id=exam_id)
            except:
                pass
        
        context['get_abstracts'] = self.request.GET.get('get_abstracts', False)

        return context  
    


class NPSApplicationExport(LoginRequiredMixin, CheckHasPermission, TemplateView):
    required_permissions = [settings.COORDINATION]
    template_name = 'dashboard/exports/nps_applications_export.html'
    export_id = None
    has_error = False

    
    def dispatch(self, request, *args, **kwargs):
        
        if self.request.GET.get('export_data'):
            
            user = self.request.user
            queryset = NPSApplication.objects.filter(
                client__in=user.get_clients_cache()
            )
            
            if self.request.GET.get('year'):
                queryset = queryset.filter(
                    date__year=self.request.GET.get('year'),
                )
            else:
                queryset = queryset.filter(
                    date__year=timezone.now().year,
                )
            
            if q_name := self.request.GET.get('q_name'):
                queryset = queryset.filter(
                    name__unaccent__icontains=q_name
                )
            
            if q_unity := self.request.GET.getlist('q_unity'):
                queryset = queryset.filter(
                    school_classes__coordination__unity__in=q_unity
                )
                
            if q_school_class := self.request.GET.getlist('q_school_class'):
                queryset = queryset.filter(
                    school_classes__in=q_school_class
                )
                
            if q_grade := self.request.GET.getlist('q_grade'):
                queryset = queryset.filter(
                    school_classes__grade__in=q_grade
                )
            
            if queryset.exists():
                self.export_id = uuid.uuid4()
                export_application_results.apply_async(
                    kwargs={
                        'nps_applications_ids': list(map(lambda x: str(x), queryset.distinct().values_list('id', flat=True)))
                    },
                    task_id=f'EXPORT_NPS_APPLICATION_DATA_{self.export_id}'
                )
            else:
                self.has_error = True
            
        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user

        filter_condition = Q()
        if user.has_high_school_coordinations:
            filter_condition |= Q(level=Grade.HIGHT_SCHOOL)

        if user.has_elementary_school_only_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL)

        if user.has_elementary_school2_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL_2)
        
        context["grades"] = Grade.objects.filter(filter_condition)
        context["unities"] = Unity.objects.filter(client=user.client)
        context['school_classes'] = SchoolClass.objects.filter(
            Q(
				Q(coordination__unity__client=user.client)
			)
        ).distinct('created_at', 'pk').order_by('-created_at').values('pk', 'name', 'coordination__unity__name',  'school_year')
        
        if year := self.request.GET.get('year'):
            context['year'] = year
        else:
            context['year'] = timezone.now().year
        
        if year := self.request.GET.get('year'):
            context['year'] = year
        else:
            context['year'] = timezone.now().year
        
        if q_name := self.request.GET.get('q_name'):
            context['q_name'] = q_name
        
        if q_unity := self.request.GET.getlist('q_unity'):
            context['q_unity'] = q_unity
            
        if q_school_class := self.request.GET.getlist('q_school_class'):
            context['q_school_class'] = q_school_class
            
        if q_grade := self.request.GET.getlist('q_grade'):
            context['q_grade'] = q_grade
        
        context['export_id'] = self.export_id
        context['has_error'] = self.has_error
            
        return context

class ExamExportEssayDetailView(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, settings.TEACHER ]
    template_name = 'dashboard/exports/exam_export_essay.html'
    model = Exam

    def dispatch(self, request, *args, **kwargs):
        if not self.get_object().has_text_correction_questions:
            messages.warning(
                self.request, 
                'Essa prova não possui questões de redação.'
            )
            return redirect(reverse('core:redirect_dashboard'))
        
        return super().dispatch(request, *args, **kwargs)

    def get_subjects(self):
        
        exam_subjects = self.object.get_subjects()

        user = self.request.user
        if user.user_type == settings.TEACHER:
            return user.inspector.subjects.all().intersection(exam_subjects)

        return exam_subjects

    def get_context_data(self, **kwargs):
        user_coordinations = self.request.user.get_coordinations_cache()
        application_students_exam = ApplicationStudent.objects.filter(
            application__exam=self.get_object(),
            student__user__is_active=True,
            student__classes__coordination__in=user_coordinations
        )
        school_classes = SchoolClass.objects.none()

        if application_students_exam.exists():
            school_classes = SchoolClass.objects.filter(
                coordination__in=user_coordinations,
                students__applicationstudent__in=application_students_exam,
                school_year=application_students_exam.first().application.date.year
            ).distinct()

        unities = Unity.objects.filter(
            coordinations__in=user_coordinations
        )

        context = super().get_context_data(**kwargs)
        context['exam_subjects'] = self.get_subjects()
        context['school_classes'] = school_classes
        context['unities'] = unities
        return context

exam_export = ExamExportDetailView.as_view()
exam_export_report = ExamExportReportView.as_view()
exam_export_report_answers = ExamExportReportAnswersView.as_view()

exams_export_erp = ExamsExportErp.as_view()
exams_export_answers = ExamsExportAnswers.as_view()