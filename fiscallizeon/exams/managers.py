import random
from datetime import datetime
from django.utils import timezone
from decimal import Decimal

from django.db import models
from django.db.models import Q, F, Exists, Count, DateTimeField, Subquery, OuterRef, Case, When, IntegerField, Value, Sum, DecimalField, BooleanField, CharField
from django.db.models.functions import Coalesce
from django.apps import apps


class ExamQueryset(models.QuerySet):
    def annotate_total_weight(self):
        ExamQuestion = apps.get_model('exams', 'ExamQuestion')
        exam_questions_subquery = Subquery(
                ExamQuestion.objects.filter(
                    exam=OuterRef('pk'),
                ).values('weight').annotate(
                    total=Sum('weight')
                ).values('total')[:1]
            )
        
        return self.annotate(
            total_weight=Coalesce(
                exam_questions_subquery,
                Value(0.0, output_field=DecimalField())
            )
        )
    
    def applieds(self):
        Application = apps.get_model('applications', 'Application')
        
        return self.annotate(
            has_application_finished=Exists(
                Application.objects.filter(exam=OuterRef('pk')).annotate(
                    finish_datetime=Case(
                        When(
                            Q(category=Application.HOMEWORK), then=F('date_end') + F('end')
                        ),
                        default=F('date') + F('end'), 
                        output_field=DateTimeField()
                    )
                ).filter(finish_datetime__lt=timezone.now().astimezone())
            )
        ).filter(has_application_finished=True)

    def generate_external_code(self, exam, client):
        external_code = random.randint(100000, 999999)
        exams = self.filter(
            coordinations__unity__client=client,
            created_at__year=datetime.now().year,
            external_code=external_code,
        ).distinct()

        if not exams:
            exam.external_code = external_code
            exam.save()
            return

        self.generate_external_code(exam, client)

class ExamTeacherSubjectQuerySet(models.QuerySet):

    def detailed_status(self):
        """
            Aberto: no prazo sem questão
            Atrasada: fora do prazo && ((sem questão) || (Menos questão do que o solicitado) || (com sugerir correção)) 
            Análise: Qualquer momento que a quantidade de questões >= solicitado
            Elaborando: no prazo && qualquer qtd de questão
        """
        
        StatusQuestion = apps.get_model('exams', 'StatusQuestion')

        return self.annotate(
            count_total_questions=Count('examquestion', filter=Q(
                Q(      
                    Q(
                        Q(examquestion__statusquestion__active=True),
                        ~Q(examquestion__statusquestion__status__in=StatusQuestion.get_unavailables_status()),
                    ) |
                    Q(
                        Q(examquestion__statusquestion__isnull=True),
                    )
                )
            ),  distinct=True),
            count_approved_questions=Count(
                'examquestion__statusquestion__exam_question', 
                distinct=True, 
                filter=(Q(
                    examquestion__statusquestion__status=StatusQuestion.APPROVED, 
                    examquestion__statusquestion__active=True
                ))
            ),
            count_reproved_questions=Count(
                'examquestion__statusquestion__exam_question', 
                distinct=True, 
                filter=(Q(
                    examquestion__statusquestion__status=StatusQuestion.REPROVED, 
                    examquestion__statusquestion__active=True
                ))
            ),
            count_peding_questions=Count(
                'examquestion__statusquestion__exam_question', 
                distinct=True, 
                filter=(Q(
                    examquestion__statusquestion__status=StatusQuestion.CORRECTION_PENDING, 
                    examquestion__statusquestion__active=True
                ))
            ),
            count_corrected_questions=Count(
                'examquestion__statusquestion__exam_question', 
                distinct=True, 
                filter=(Q(
                    examquestion__statusquestion__status=StatusQuestion.CORRECTED, 
                    examquestion__statusquestion__active=True
                ))
            ),
            is_late=Case(
                When(
                    Q(
                        Q(exam__elaboration_deadline__lt=timezone.now().date()),
                        Q(
                            Q(count_peding_questions__gt=0) |
                            Q(count_total_questions__lt=F('quantity')) |
                            Q(count_total_questions=0)
                        ),
                    ),
                    then=Value(True)
                ),
                default=Value(False),
                output_field=BooleanField()
            ),
            status=Case(
                When(
                    count_peding_questions__gt=0,
                    then=Value('Aguardando correção')
                ),
                When(
                    is_late=True,
                    then=Value('Atrasada')
                ),
                When(
                    count_total_questions__gte=F('quantity'),
                    then=Value('Análise')
                ),
                When(
                    is_late=False, count_total_questions__gt=0,
                    then=Value('Elaborando')
                ),
                When(
                    is_late=False, count_total_questions=0,
                    then=Value('Aberto')
                ),
                default=Value('Aberto'),
                output_field=CharField()
            ),
            count_opened_questions=F('count_total_questions') - (F('count_approved_questions') + F('count_reproved_questions') + F ('count_peding_questions') + F('count_corrected_questions')),
        )

    def teacher_detailed_status(self, user):
        StatusQuestion = apps.get_model('exams', 'StatusQuestion')
        Question = apps.get_model('questions', 'Question')
        
        return self.annotate(
            count=Count('examquestion', distinct=True),
            count_reviewed_questions=Count(
                'examquestion',
                filter=Q(
                    examquestion__statusquestion__user=user,
                ),
                distinct=True
            ),
            count_seen_questions=Count(
                'examquestion',
                filter=Q(
                    examquestion__statusquestion__user=user,
                    examquestion__statusquestion__status=StatusQuestion.SEEN,
                ),
                distinct=True
            ),
            count_approved_questions=Count(
                'examquestion',
                filter=Q(
                    examquestion__statusquestion__user=user,
                    examquestion__statusquestion__status=StatusQuestion.APPROVED,
                ),
                distinct=True
            ),
            count_reproved_questions=Count(
                'examquestion',
                filter=Q(
                    examquestion__statusquestion__user=user,
                    examquestion__statusquestion__status=StatusQuestion.REPROVED,
                ),
                distinct=True
            ),
            count_correction_pending_questions=Count(
                'examquestion',
                filter=Q(
                    examquestion__statusquestion__user=user,
                    examquestion__statusquestion__status=StatusQuestion.CORRECTION_PENDING,
                ),
                distinct=True
            ),
            count_question_choices=Count(
                'examquestion',
                filter=Q(
                    examquestion__question__category=Question.CHOICE
                ),
                distinct=True
            ),
        )
class ExamQuestionQueryset(models.QuerySet):
    def get_max_grade(self):
        return self.aggregate(
            max_grade=Sum('weight'),
        ).get('max_grade', 0)

    def get_application_students_report(self, application_students):
        Question = apps.get_model('questions', 'Question')
        OptionAnswer = apps.get_model('answers', 'OptionAnswer')
        FileAnswer = apps.get_model('answers', 'FileAnswer')
        TextualAnswer = apps.get_model('answers', 'TextualAnswer') 
        SumAnswer = apps.get_model('answers', 'SumAnswer') 
        
        application_students = list(application_students)

        active_choice_answers = OptionAnswer.objects.filter(
            question_option__question=OuterRef('question'),
            status=OptionAnswer.ACTIVE,
            student_application__in=application_students
        )

        file_answers = FileAnswer.objects.filter(
            question__pk=OuterRef('question__pk'),
            student_application__in=application_students,
        )

        textual_answers = TextualAnswer.objects.filter(
            question__pk=OuterRef('question__pk'),
            student_application__in=application_students,
        )

        sum_answers = SumAnswer.objects.filter(
            question=OuterRef('question'),
            student_application__in=application_students
        )

        corrected_file_answers = file_answers.filter(
            teacher_grade__isnull=False,
        )

        corrected_textual_answers = textual_answers.filter(
            teacher_grade__isnull=False,
        )

        correct_choice_answers = active_choice_answers.filter(
            question_option__is_correct=True,
        )

        correct_file_answers = corrected_file_answers.filter(
            grade=Value(1.0),
        )

        correct_textual_answers = corrected_textual_answers.filter(
            grade=Value(1.0),
        )

        correct_sum_answers = sum_answers.filter(
            grade=Value(1.0),
        )

        incorrect_choice_answers = active_choice_answers.filter(
            question_option__is_correct=False,
        )

        incorrect_file_answers = corrected_file_answers.filter(
            teacher_grade=Value(0),
        )

        incorrect_textual_answers = corrected_textual_answers.filter(
            teacher_grade=Value(0),
        )

        incorrect_sum_answers = sum_answers.filter(
            grade=Value(0),
        )

        partial_file_answers = corrected_file_answers.filter(
            grade__gt=Value(0),
            grade__lt=Value(1.0),
        )

        partial_textual_answers = corrected_textual_answers.filter(
            grade__gt=Value(0),
            grade__lt=Value(1.0),
        )

        partial_sum_answers = sum_answers.filter(
            grade__gt=Value(0),
            grade__lt=Value(1.0),
        )
        
        return self.filter(
            exam__application__applicationstudent__in=application_students,
        ).annotate(
            answers=Case(
                When(
                    question__category=Question.CHOICE, 
                    then=active_choice_answers
                    .values('question_option__question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                When(
                    question__category=Question.FILE, 
                    then=file_answers
                    .values('question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                When(
                    question__category=Question.TEXTUAL, 
                    then=textual_answers
                    .values('question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                When(
                    question__category=Question.SUM_QUESTION, 
                    then=sum_answers
                    .values('question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                default=Value(0),
                output_field=IntegerField(),
            ),  
            correct_answers=Case(
                When(
                    question__category=Question.CHOICE, 
                    then=correct_choice_answers
                    .values('question_option__question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                When(
                    question__category=Question.FILE, 
                    then=correct_file_answers
                    .values('question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                When(
                    question__category=Question.TEXTUAL, 
                    then=correct_textual_answers
                    .values('question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                When(
                    question__category=Question.SUM_QUESTION, 
                    then=correct_sum_answers
                    .values('question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                default=Value(0),
                output_field=IntegerField(),
            ),
            incorrect_answers=Case(
                When(
                    question__category=Question.CHOICE, 
                    then=incorrect_choice_answers
                    .values('question_option__question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                When(
                    question__category=Question.FILE, 
                    then=incorrect_file_answers
                    .values('question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                When(
                    question__category=Question.TEXTUAL, 
                    then=incorrect_textual_answers
                    .values('question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                When(
                    question__category=Question.SUM_QUESTION, 
                    then=incorrect_sum_answers
                    .values('question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                default=Value(0),
                output_field=IntegerField(),
            ),
            partial_answers=Case(
                When(
                    question__category=Question.FILE, 
                    then=partial_file_answers
                    .values('question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                When(
                    question__category=Question.TEXTUAL, 
                    then=partial_textual_answers
                    .values('question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                When(
                    question__category=Question.SUM_QUESTION, 
                    then=partial_sum_answers
                    .values('question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                default=Value(0),
                output_field=IntegerField(),
            ),
            corrected_answers=Case(
                When(
                    question__category=Question.CHOICE,
                    then=F('answers')
                ),
                When(
                    question__category=Question.FILE, 
                    then=corrected_file_answers
                    .values('question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                When(
                    question__category=Question.TEXTUAL, 
                    then=corrected_textual_answers
                    .values('question')
                    .annotate(count=Count('pk'))
                    .values('count')[:1]
                ),
                default=Value(0),
                output_field=IntegerField(),
            ),
        ).order_by(

        ).distinct()

    def availables_without_distinct(self, exclude_annuleds=False, exclude_use_later=True, exclude_correction_pending=False):
        StatusQuestion = apps.get_model('exams', 'StatusQuestion')
        status_list = [StatusQuestion.REPROVED, StatusQuestion.DRAFT]

        if exclude_annuleds:
            status_list.append(StatusQuestion.ANNULLED)
        
        if exclude_use_later:
            status_list.append(StatusQuestion.USE_LATER)
        
        if exclude_correction_pending:
            status_list.append(StatusQuestion.CORRECTION_PENDING)
            
        return self.annotate(
            annuled=Case(
                When(
                    Q(
                        pk=F('pk'),
                        statusquestion__active=True,
                        statusquestion__status=StatusQuestion.ANNULLED,
                    ), then=Value(True)
                ), default=Value(False)
            )
        ).exclude(
            pk__in=Subquery(
                StatusQuestion.objects.filter(
                    exam_question__pk=OuterRef('pk'),
                    active=True,
                    status__in=status_list,
                ).values('exam_question__pk')[:1]
            )
        )

    def availables(self, exclude_annuleds=False, exclude_use_later=True, exclude_correction_pending=False, include_give_score=False):
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
                    active=True,
                    status=StatusQuestion.ANNULLED,
                ).values('exam_question__pk').annotate(
                    count=Count('pk')
                ).values('count'), output_field=IntegerField()),
            annuled=Case(
                When(annuled_count__gt=0, then=Value(True)), 
                default=Value(False), 
                output_field=BooleanField()
            )
        ).exclude(
            pk__in=Subquery(
                StatusQuestion.objects.filter(
                    Q(
                        exam_question__pk=OuterRef('pk'),
                        active=True,
                        status__in=status_list
                    ),
                    Q(annuled_give_score=False) if include_give_score else Q(),
                ).distinct().values('exam_question__pk')[:1]
            )
        ).distinct()
        
    def get_ordered_pks(self, pk_ids):
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(pk_ids)])
        return self.filter(pk__in=pk_ids).order_by(preserved)

ExamTeacherSubjectManager = models.Manager.from_queryset(ExamTeacherSubjectQuerySet)
ExamQuestionManager = models.Manager.from_queryset(ExamQuestionQueryset)
ExamManager = models.Manager.from_queryset(ExamQueryset)