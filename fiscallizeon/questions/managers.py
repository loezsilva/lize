from datetime import datetime

from django.db import models
from django.db.models import Q, F, Count, Sum, Subquery, OuterRef, Value, IntegerField, Case, When, Value, CharField, DecimalField, BooleanField, UUIDField
from django.apps import apps
from django.db.models.functions import Coalesce
from django.db.models.fields import DateTimeField
from django.contrib.postgres.aggregates import ArrayAgg

class QuestionQuerySet(models.QuerySet):

    def availables(self, exam, exclude_annuleds=False, exclude_use_later=True, exclude_correction_pending=False):
        StatusQuestion = apps.get_model('exams', 'StatusQuestion')
        status_list = [StatusQuestion.REPROVED, StatusQuestion.DRAFT]
        
        if exclude_annuleds:
            status_list.append(StatusQuestion.ANNULLED)
            
        if exclude_use_later:
            status_list.append(StatusQuestion.USE_LATER)
        
        if exclude_correction_pending:
            status_list.append(StatusQuestion.CORRECTION_PENDING)
        
        return self.annotate(
            annuled_count=Subquery(StatusQuestion.objects.filter(
                    exam_question__pk=OuterRef('pk'),
                    exam_question__exam=exam,
                    active=True,
                    status=StatusQuestion.ANNULLED,
                ).values('exam_question__pk').annotate(
                    count=Count('exam_question__pk')
                ).values('count'), output_field=IntegerField()
            ),
            annuled=Case(
                When(annuled_count__gt=0, then=Value(True)), 
                default=Value(False), 
                output_field=BooleanField()
                
            )
        ).exclude(
            pk__in=Subquery(
                StatusQuestion.objects.filter(
                    exam_question__question__pk=OuterRef('pk'),
                    exam_question__exam=exam,
                    active=True,
                    status__in=status_list,
                ).distinct().values('exam_question__question__pk')[:1]
            )
        ).distinct()
    
    
    def get_application_student_report(self, application_student, only_answers=False):
        Question = apps.get_model('questions', 'Question')
        ExamQuestion = apps.get_model('exams', 'ExamQuestion')
        OptionAnswer = apps.get_model('answers', 'OptionAnswer')
        FileAnswer = apps.get_model('answers', 'FileAnswer')
        TextualAnswer = apps.get_model('answers', 'TextualAnswer') 
        SumAnswer = apps.get_model('answers', 'SumAnswer') 

        answers = OptionAnswer.objects.filter(
            question_option__question__pk=OuterRef('pk'),
            student_application=application_student
        )

        active_answers = answers.filter(
            status=OptionAnswer.ACTIVE
        ).order_by('-created_at')

        exam_question = ExamQuestion.objects.filter(
            question__pk=OuterRef('pk'),
            exam=application_student.application.exam,
        )

        file_answer = FileAnswer.objects.filter(
            question__pk=OuterRef('pk'),
            student_application=application_student,
        ).order_by('-created_at')

        textual_answer = TextualAnswer.objects.filter(
            question__pk=OuterRef('pk'),
            student_application=application_student,
        ).order_by('-created_at')
        
        sum_answers = SumAnswer.objects.filter(
            question__pk=OuterRef('pk'),
            student_application=application_student,
        )

        if only_answers:
            return self.filter(
                exams__application__applicationstudent=application_student,
            ).annotate(
                is_correct_choice=Subquery(active_answers.values('question_option__is_correct')[:1]),
                question_weight=Subquery(exam_question.values('weight')[:1]),
                percent_grade=Case(
                    When(category=Question.TEXTUAL, then=Subquery(textual_answer.values('grade')[:1])),
                    When(category=Question.FILE, then=Subquery(file_answer.values('grade')[:1])),
                    When(category=Question.SUM_QUESTION, then=Subquery(sum_answers.values('grade')[:1])),
                    When(category=Question.CHOICE, is_correct_choice=True, then=Value(1.0)),
                    default=Value(0.0),
                    output_field=DecimalField(),
                ),
                teacher_grade=Case(
                    When(category=Question.TEXTUAL, then=Subquery(textual_answer.values('grade')[:1]) * F('question_weight')),
                    When(category=Question.FILE, then=Subquery(file_answer.values('grade')[:1]) * F('question_weight')),
                    When(category=Question.SUM_QUESTION, then=Subquery(sum_answers.values('grade')[:1])),
                    When(category=Question.CHOICE, is_correct_choice=True, then=F('question_weight')),
                    default=Value(0.0),
                    output_field=DecimalField(),
                ),
                is_correct=Case(
                    When(category=Question.CHOICE, then=F('is_correct_choice')),
                    When(category=Question.FILE, teacher_grade__gte=F('question_weight'), then=Value(True)),
                    When(category=Question.TEXTUAL, teacher_grade__gte=F('question_weight'), then=Value(True)),
                    When(category=Question.SUM_QUESTION, teacher_grade=Value(1.0), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                is_incorrect=Case(
                    When(category=Question.CHOICE, is_correct_choice=Value(False), then=Value(True)),
                    When(category=Question.FILE, teacher_grade=Value(0.0), then=Value(True)),
                    When(category=Question.TEXTUAL, teacher_grade=Value(0.0), then=Value(True)),
                    When(category=Question.SUM_QUESTION, teacher_grade=Value(0.0), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                is_partial=Case(
                    When(
                        category=Question.FILE, 
                        teacher_grade__gt=Value(0.0), 
                        teacher_grade__lt=F('question_weight'), 
                        then=Value(True)
                    ),
                    When(
                        category=Question.TEXTUAL, 
                        teacher_grade__gt=Value(0.0), 
                        teacher_grade__lt=F('question_weight'), 
                        then=Value(True)
                    ),
                    When(
                        category=Question.SUM_QUESTION, 
                        teacher_grade__gt=Value(0.0), 
                        teacher_grade__lt=Value(1.0), 
                        then=Value(True)
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
        
        return self.filter(
            exams__application__applicationstudent=application_student,
        ).annotate(
            option_answer=Subquery(active_answers.values('pk')[:1]),
            answer=Subquery(active_answers.values('question_option__pk')[:1]),
            answer_created_by_id=Case(
                When(category=Question.SUM_QUESTION, then=Subquery(sum_answers.values('created_by__pk')[:1])),
                When(category=Question.CHOICE, then=Subquery(active_answers.values('created_by__pk')[:1])),
                default=Value(None),
                output_field=UUIDField(),
            ),
            answer_created_by_name=Case(
                When(category=Question.SUM_QUESTION, then=Subquery(sum_answers.values('created_by__name')[:1])),
                When(category=Question.CHOICE, then=Subquery(active_answers.values('created_by__name')[:1])),
                default=Value(''),
                output_field=CharField(),
            ),
            answer_created_at=Subquery(active_answers.values('created_at')[:1]),
            file_answer=Case(
                When(category=Question.FILE, then=Subquery(file_answer.values('pk')[:1])),
                default=None
            ),
            textual_answer=Case(
                When(category=Question.TEXTUAL, then=Subquery(textual_answer.values('pk')[:1])),
                default=None
            ),
            textual_answer_content=Case(
                When(category=Question.TEXTUAL, then=Subquery(textual_answer.values('content')[:1])),
                default=None
            ),
            sum_question_sum_value=Coalesce(
                Subquery(
                    sum_answers.values('value')[:1]
                ), Value(0)
            ),
            sum_question_checked_answers=Coalesce(
                Subquery(
                    sum_answers.annotate(checked_ids=ArrayAgg(
                        'sumanswerquestionoption__question_option', 
                        filter=Q(sumanswerquestionoption__checked=True),
                        default=Value([]),
                    )).values('checked_ids')
                ), Value([])
            ),
            corrected_but_no_answer=Case(
                When(category=Question.FILE, then=file_answer.values('corrected_but_no_answer')[:1]),
                When(category=Question.TEXTUAL, then=textual_answer.values('corrected_but_no_answer')[:1]),
                default=False,
                output_field=BooleanField()
            ),
            is_correct_choice=Subquery(active_answers.values('question_option__is_correct')[:1]),
            question_weight=Subquery(exam_question.values('weight')[:1]),
            duration=Subquery(active_answers.values('duration')[:1]),
            last_modified=Case(
                When(category=Question.TEXTUAL, then=Subquery(textual_answer.values('updated_at')[:1])),
                When(category=Question.FILE, then=Subquery(file_answer.values('updated_at')[:1])),
                When(category=Question.CHOICE, then=Subquery(active_answers.values('updated_at')[:1])),
                default=None,
                output_field=DateTimeField(),
            ),         
            teacher_feedback=Case(
                When(category=Question.TEXTUAL, then=Subquery(textual_answer.values('teacher_feedback')[:1])),
                When(category=Question.FILE, then=Subquery(file_answer.values('teacher_feedback')[:1])),
                default=Value(''),
                output_field=CharField(),
            ),
            textual_answer_teacher_grade=Case(
                When(category=Question.TEXTUAL, then=Subquery(textual_answer.values('grade')[:1]) * F('question_weight')),
                default=None
            ),
            file_answer_teacher_grade=Case(
                When(category=Question.FILE, then=Subquery(file_answer.values('grade')[:1]) * F('question_weight')),
                default=None
            ),
            awaiting_correction=Case(
                When(category=Question.TEXTUAL, textual_answer_teacher_grade__isnull=True, then=Value(True)),
                When(category=Question.FILE, file_answer_teacher_grade__isnull=True, then=Value(True)),
                default=False,
                output_field=BooleanField(),
            ),
            percent_grade=Case(
                When(category=Question.TEXTUAL, then=Subquery(textual_answer.values('grade')[:1])),
                When(category=Question.FILE, then=Subquery(file_answer.values('grade')[:1])),
                When(category=Question.SUM_QUESTION, then=Subquery(sum_answers.values('grade')[:1])),
                When(category=Question.CHOICE, is_correct_choice=True, then=Value(1.0)),
                default=Value(0.0),
                output_field=DecimalField(),
            ),
            teacher_grade=Case(
                When(category=Question.TEXTUAL, then=Subquery(textual_answer.values('grade')[:1]) * F('question_weight')),
                When(category=Question.FILE, then=Subquery(file_answer.values('grade')[:1]) * F('question_weight')),
                When(category=Question.SUM_QUESTION, then=Subquery(sum_answers.values('grade')[:1])),
                When(category=Question.CHOICE, is_correct_choice=True, then=F('question_weight')),
                default=Value(0.0),
                output_field=DecimalField(),
            ),
            is_correct=Case(
                When(category=Question.CHOICE, then=F('is_correct_choice')),
                When(category=Question.FILE, teacher_grade__gte=F('question_weight'), then=Value(True)),
                When(category=Question.TEXTUAL, teacher_grade__gte=F('question_weight'), then=Value(True)),
                When(category=Question.SUM_QUESTION, teacher_grade=Value(1.0), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
            is_incorrect=Case(
                When(category=Question.CHOICE, is_correct_choice=Value(False), then=Value(True)),
                When(category=Question.FILE, teacher_grade=Value(0.0), then=Value(True)),
                When(category=Question.TEXTUAL, teacher_grade=Value(0.0), then=Value(True)),
                When(category=Question.SUM_QUESTION, teacher_grade=Value(0.0), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
            is_none=Case(
                When(
                    category=Question.CHOICE,
                    answer__isnull=True,
                    then=Value(True)
                ),
                When(
                    category=Question.FILE, 
                    file_answer__isnull=True,
                    then=Value(True)
                ),
                When(
                    category=Question.TEXTUAL, 
                    textual_answer__isnull=True,
                    then=Value(True)
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
            is_partial=Case(
                When(
                    category=Question.FILE, 
                    teacher_grade__gt=Value(0.0), 
                    teacher_grade__lt=F('question_weight'), 
                    then=Value(True)
                ),
                When(
                    category=Question.TEXTUAL, 
                    teacher_grade__gt=Value(0.0), 
                    teacher_grade__lt=F('question_weight'), 
                    then=Value(True)
                ),
                When(
                    category=Question.SUM_QUESTION, 
                    teacher_grade__gt=Value(0.0), 
                    teacher_grade__lt=Value(1.0), 
                    then=Value(True)
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
            total_answers=Subquery(
                answers.values('question_option__question').annotate(
                    count=Count('pk')
                ).values('count')
            ),
            empty=Case(
                When(category=Question.FILE, then=Coalesce(Subquery(file_answer.values('empty')[:1]), Value(False))),
                When(category=Question.TEXTUAL, then=Coalesce(Subquery(textual_answer.values('empty')[:1]), Value(False))),
                default=False
            )
        ).order_by(
            'created_at'
        ).distinct()

    def get_application_students_report(self, application_students):
        Question = apps.get_model('questions', 'Question')
        OptionAnswer = apps.get_model('answers', 'OptionAnswer')

        answers = OptionAnswer.objects.filter(
            question_option__question__pk=OuterRef('pk'),
            student_application__in=application_students,
            question_option__is_correct=True,
            status=OptionAnswer.ACTIVE
        ).distinct()

        return self.filter(
            exams__application__applicationstudent__in=application_students,
        ).annotate(
            answers=Value(application_students.filter(start_time__isnull=False).count(), output_field=IntegerField()),
            correct_answers=Subquery(
                answers.values('question_option__question').annotate(c=Count('pk', distinct=True)).values('c')[:1]
            )
        ).order_by(
            'created_at'
        ).distinct()

    def get_application_student_report_aggregation(self):
        self.aggregate(
            total_grade=Sum('teacher_grade'),
        )

    def get_public_boards(self):
        return [
            "", "ACAFE", "Aeronáutica", "AFA", "BIO-RIO", "CEC", "CECIERJ", "CEPERJ", "Cesgranrio", "CESPE", 
            "CETRO", "CEV-URCA", "CN", "Comperve", "COMVEST - UNICAMP", "CONSULPLAN", "COPEPS", "COPERVE - UFSC", 
            "COPESE - UFT", "COPEVE-UFAL", "COSEAC", "CPCON", "CS-UFG", "EDUCA", "EEAR", "EFOMM", "EN", "ENEM", 
            "EPCAR", "ESA", "ESPCEX", "EXATUS", "Exército", "FAPERP", "FATEC", "FAURGS", "FCC", "FCM", "FDC", 
            "FEPESE", "FGV", "FUMARC", "FUNCAB", "FUNDATEC", "FUNDEP (Gestão de Concursos)", "FUNIVERSA", "FUNRIO", 
            "Fuvest", "IADES", "IBADE", "IBAM", "IBEG", "IBFC", "IBGP", "IDECAN", "IESES", "IFB", "IF-BA", "IFC", "IF-ES", 
            "IF-MT", "IF-SP", "IF-TO", "IME", "INAZ do Pará", "Inep", "INSPER", "INSTITUTO AOCP", "ITA", "Jota Consultoria", 
            "LEGALLE Concursos", "MACK", "Marinha", "MS CONCURSOS", "NC-UFPR", "Nosso Rumo", "NUCEPE", "OBMEP", "PM-SC", "PR-4 UFRJ", 
            "Prefeitura de Betim - MG", "Prefeitura de Fortaleza - CE", "Prefeitura do Rio de Janeiro - RJ", "PUC - Campinas", 
            "PUC - GO", "PUC-MINAS", "PUC-PR", "PUC - RJ", "PUC-RJ", "PUC - RS", "PUC-RS", "PUC - SP", "PUC-SP", "Quadrix", 
            "REIS & REIS", "SENAC-SP", "SIGMA RH", "UCS", "UDESC", "UECE-CEV", "UEG", "UEL", "UEM", "UERJ", "UFAC", "UFAM ", 
            "UFCG", "UFF", "UFGD", "UFLA", "UFMG", "UFMT", "UFPR", "UFRGS", "UFRN-PRH", "UFSCar", "UFU-MG", "UNB", "UNEMAT", 
            "UNESP", "UNESPAR", "UNICAMP", "UNICENTRO", "UniCEUB", "UNIFAL-MG", "UNIFESP", "UNIFOR", "Unimontes-MG", "UNITINS", 
            "USP", "UTFPR", "VUNESP"
        ]

QuestionManager = models.Manager.from_queryset(QuestionQuerySet)