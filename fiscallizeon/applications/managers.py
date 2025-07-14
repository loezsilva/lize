from decimal import Decimal
from django.apps import apps
from django.db import models
from django.utils import timezone
from fiscallizeon.classes.models import SchoolClass
from django.db.models import FloatField, Q, F, Count, Sum, Avg, Max, ExpressionWrapper, DateTimeField, BooleanField, OuterRef, Subquery, Value, When, Case, DurationField, Exists
from django.db.models.functions import Coalesce, Cast, JSONObject
from django.contrib.postgres.expressions import ArraySubquery
from django.db.models.functions import NullIf
from fiscallizeon.core.utils import round_half_up



class ApplicationQuerySet(models.QuerySet):
    def is_online(self):
        Application = apps.get_model('applications', 'Application')
        return self.exclude(
            category=Application.PRESENTIAL,
        )

    def annotate_date_end(self):
        Application = apps.get_model('applications', 'Application')
        return self.annotate(
            datetime_end=Case(
                When(
                    Q(category=Application.HOMEWORK), then=F('date_end') + F('end')
                ),
                default=F('date') + F('end'),
                output_field=DateTimeField()
            )
        )

    def annotate_date_start(self):
        return self.annotate(
            date_start=ExpressionWrapper(
                F('date') + F('start'),
                output_field=DateTimeField()
            )
        )

    def applieds(self):
        Application = apps.get_model('applications', 'Application')

        return self.annotate(
            finish_datetime=Case(
                When(
                    Q(category=Application.HOMEWORK), then=F('date_end') + F('end')
                ),
                default=F('date') + F('end'),
                output_field=DateTimeField()
            )
        ).filter(finish_datetime__lt=timezone.localtime(timezone.now()))

class ApplicationStudentQuerySet(models.QuerySet):
    def is_online(self):
        Application = apps.get_model('applications', 'Application')
        return self.exclude(
            application__category=Application.PRESENTIAL,
        )

    def filter_by_school_class(self, school_class):
        return self.filter(
            student__classes__in=[school_class],
        ).distinct()

    def filter_by_school_class_year(self, year=None):
        year = year or timezone.now().year
        return self.filter(
            student__classes__school_year=year,
        ).distinct()

    def get_exam_question_subquery(
        self, choice=False, discursive=False, subjects=None, exclude_annuleds=False, include_give_score=False
    ):
        ExamQuestion = apps.get_model('exams', 'ExamQuestion')
        queryset = ExamQuestion.objects.none()

        if choice:
            queryset = ExamQuestion.objects.filter(
                question=OuterRef('question_option__question'),
                exam=OuterRef('student_application__application__exam'),
            ).distinct()
        elif discursive:
            queryset = ExamQuestion.objects.filter(
                pk=OuterRef('exam_question')
            ).distinct()
        else:
            queryset = ExamQuestion.objects.filter(
                question=OuterRef('question'),
                exam=OuterRef('student_application__application__exam'),
            ).distinct()

        if subjects:
            queryset = queryset.filter(
                Q(
                    Q(
                        Q(exam_teacher_subject__isnull=True),
                        Q(question__subject__in=subjects)
                    ) |
                    Q(
                        Q(exam_teacher_subject__isnull=False),
                        Q(exam_teacher_subject__teacher_subject__subject__in=subjects)
                    )
                )
            )

        queryset = queryset.availables(exclude_annuleds=exclude_annuleds, include_give_score=include_give_score)

        return queryset

    def get_exam_question_teacher_subquery(self, teacher, choice=False, discursive=False, subjects=None, exclude_annuleds=False):
        return self.get_exam_question_subquery(choice=choice, discursive=discursive, subjects=subjects, exclude_annuleds=exclude_annuleds).filter(
            exam_teacher_subject__teacher_subject__teacher=teacher
        )

    def get_exam_question_subjects_subquery(self, subjects, choice=False, discursive=False, exclude_annuleds=False):
        return self.get_exam_question_subquery(choice=choice, discursive=discursive, subjects=subjects, exclude_annuleds=exclude_annuleds).filter(
            Q(
                Q(
                    Q(exam_teacher_subject__isnull=True),
                    Q(question__subject__in=subjects)
                ) |
                Q(
                    Q(exam_teacher_subject__isnull=False),
                    Q(exam_teacher_subject__teacher_subject__subject__in=subjects)
                )
            )
        )

    def get_finished_application_student(self):
        today = timezone.localtime(timezone.now())
        Application = apps.get_model('applications', 'Application')

        return self.annotate(
                finish_datetime=Case(
                        When(Q(application__category=Application.HOMEWORK), then=F('application__date_end') + F('application__end')),
                        default=F('application__date') + F('application__end'),
                        output_field=DateTimeField()
                    ),
                release_result_at_end_finished=Case(
                        When(Q(application__release_result_at_end=True, end_time__isnull=False), then=True),
                        default=False,
                        output_field=BooleanField()
                )
            ).filter(
                Q(
                    Q(application__student_stats_permission_date=None) |
                    Q(application__student_stats_permission_date__lte=today)
                ),
                Q(
                    Q(finish_datetime__lt=timezone.now().astimezone()) |
                    Q(release_result_at_end_finished=True)
                )
            ).exclude(
                
            )

    def get_annotation_count_answers(
        self, subjects=None, only_total_grade=False, level=None, exclude_annuleds=False, only_total_answers=None, include_give_score=False, return_performance=False, return_ranking=False
    ):
        OptionAnswer = apps.get_model('answers', 'OptionAnswer')
        TextualAnswer = apps.get_model('answers', 'TextualAnswer')
        FileAnswer = apps.get_model('answers', 'FileAnswer')
        SumAnswer = apps.get_model('answers', 'SumAnswer')
        ExamQuestion = apps.get_model('exams', 'ExamQuestion')
        StatusQuestion = apps.get_model('exams', 'StatusQuestion')

        exam_question_choice_subquery = self.get_exam_question_subquery(
            choice=True, subjects=subjects, exclude_annuleds=exclude_annuleds, include_give_score=include_give_score
        )
        exam_question_discursive_subquery = self.get_exam_question_subquery(
            discursive=True, subjects=subjects, exclude_annuleds=exclude_annuleds, include_give_score=include_give_score
        )
        exam_question_subquery = self.get_exam_question_subquery(
            subjects=subjects, exclude_annuleds=exclude_annuleds, include_give_score=include_give_score
        )

        choice_count = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    status=OptionAnswer.ACTIVE,
                    question_option__question=exam_question_choice_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        textual_count = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    empty=False,
                    question=exam_question_discursive_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        file_count = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    empty=False,
                    question=exam_question_discursive_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        sum_answers_count = Coalesce(
            Subquery(
                SumAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    empty=False,
                    question=exam_question_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        correct_choice_count = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    status=OptionAnswer.ACTIVE,
                    question_option__is_correct=True,
                    question_option__question=exam_question_choice_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        correct_textual_count = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_discursive_subquery.values('question')[:1],
                    grade__gte=Value(1.0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        correct_file_count = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_discursive_subquery.values('question')[:1],
                    grade__gte=Value(1.0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        correct_sum_answer_count = Coalesce(
            Subquery(
                SumAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subquery.values('question')[:1],
                    grade=Value(1.0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        incorrect_choice_count = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    status=OptionAnswer.ACTIVE,
                    question_option__is_correct=False,
                    question_option__question=exam_question_choice_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        incorrect_textual_count = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_discursive_subquery.values('question')[:1],
                    grade=Value(0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        incorrect_file_count = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_discursive_subquery.values('question')[:1],
                    grade=Value(0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        incorrect_sum_answer_count = Coalesce(
            Subquery(
                SumAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subquery.values('question')[:1],
                    grade=Value(0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        corrected_textual_count = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_discursive_subquery.values('question')[:1],
                    grade__isnull=False,
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        corrected_file_count = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_discursive_subquery.values('question')[:1],
                    grade__isnull=False,
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        corrected_sum_answer_count = Coalesce(
            Subquery(
                SumAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subquery.values('question')[:1],
                    grade__isnull=False,
                    empty=False,
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        choice_grade_sum = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    status=1,
                    question_option__is_correct=True,
                    question_option__question=exam_question_choice_subquery.values('question')[:1]
                ).annotate(
                    grade=exam_question_choice_subquery.values('weight')[:1],
                ).values('student_application').annotate(
                    total=Sum('grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        textual_grade_sum = Coalesce(
            Subquery(
                TextualAnswer.objects.annotate(
                    question_pk=exam_question_discursive_subquery.values('question')[:1],
                    question_weight=exam_question_discursive_subquery.values('weight')[:1],
                ).filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=F('question_pk'),
                ).annotate(
                    total_grade=F('grade') * F('question_weight')
                ).values('student_application').annotate(
                    total=Sum('total_grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        file_grade_sum = Coalesce(
            Subquery(
                FileAnswer.objects.annotate(
                    question_pk=exam_question_discursive_subquery.values('question')[:1],
                    question_weight=exam_question_discursive_subquery.values('weight')[:1],
                ).filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=F('question_pk'),
                ).annotate(
                    total_grade=F('grade') * F('question_weight')
                ).values('student_application').annotate(
                    total=Sum('total_grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        sum_questions_grade_sum = Coalesce(
            Subquery(
                SumAnswer.objects.annotate(
                    question_pk=exam_question_subquery.values('question')[:1],
                    question_weight=exam_question_subquery.values('weight')[:1],
                ).filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=F('question_pk'),
                ).annotate(
                    teacher_grade=F('grade') * F('question_weight')
                ).values('student_application').annotate(
                    total=Sum('teacher_grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        questions_give_score_sum=Coalesce(
            Subquery(
                ExamQuestion.objects.annotate(
                    has_give_score=Exists(
                        StatusQuestion.objects.filter(
                            exam_question=OuterRef('pk'),
                            annuled_give_score=True,
                            status=StatusQuestion.ANNULLED,
                            active=True,
                        )
                    )
                ).filter(
                    Q(created_at__year=OuterRef('application__date__year')),
                    Q(exam=OuterRef('application__exam')),
                    Q(has_give_score=True),
                    Q(
                        Q(
                            Q(exam_teacher_subject__isnull=True),
                            Q(question__subject__in=subjects)
                        ) |
                        Q(
                            Q(exam_teacher_subject__isnull=False),
                            Q(exam_teacher_subject__teacher_subject__subject__in=subjects)
                        )
                    ) if subjects else Q(),
                ).values('exam').annotate(Sum('weight')).values('weight__sum')[:1]
            ),
            Decimal(0.0)
        )

        total_grade = choice_grade_sum + textual_grade_sum + file_grade_sum + questions_give_score_sum + sum_questions_grade_sum

        total_correct_answers=correct_choice_count + correct_textual_count + correct_file_count + correct_sum_answer_count
        total_incorrect_answers=incorrect_choice_count + incorrect_textual_count + incorrect_file_count + incorrect_sum_answer_count
        total_partial_answers=corrected_textual_count + corrected_file_count + corrected_sum_answer_count - correct_textual_count - correct_file_count - correct_sum_answer_count - incorrect_textual_count - incorrect_file_count - incorrect_sum_answer_count

        total_answers = choice_count + textual_count + file_count + sum_answers_count

        if return_performance:
            return self.annotate(
                total_correct_answers=total_correct_answers,
                total_answers=total_answers,
            ).distinct().aggregate(
                total=Avg(
                    Case(
                        When(
                            condition=Q(total_answers__gt=0),
                            then=ExpressionWrapper(F('total_correct_answers') * (1.0 / (F('total_answers'))) * 100, output_field=models.DecimalField())
                        ),
                        default=Value(0),
                        output_field=models.DecimalField()
                    )
                )
            ).get('total') or 0

        if return_ranking:
            return self.annotate(
                total_correct_answers=total_correct_answers,
                total_answers=total_answers,
            ).values('student').annotate(
                name=F('student__name'),
                performance=Avg(
                    Case(
                        When(
                            condition=Q(total_answers__gt=0),
                            then=ExpressionWrapper(F('total_correct_answers') * (1.0 / (F('total_answers'))) * 100, output_field=models.DecimalField())
                        ),
                        default=Value(0),
                        output_field=models.DecimalField()
                    )
                )
            ).order_by('-performance').values('name', 'performance')

        if only_total_grade:

            return self.annotate(
                total_grade=total_grade,
            ).distinct()

        if only_total_answers:
            return self.annotate(
                total_correct_answers=total_correct_answers,
                total_incorrect_answers=total_incorrect_answers,
                total_partial_answers=total_partial_answers,
                total_answers=total_answers,
            ).distinct()

        return self.annotate(
            total_answers=total_answers,
            total_corrected_answers=corrected_textual_count + corrected_file_count,
            total_text_file_answers=textual_count + file_count,
            total_correct_answers=total_correct_answers,
            total_incorrect_answers=total_incorrect_answers,
            total_partial_answers=total_partial_answers,
            choice_grade_sum=choice_grade_sum,
            textual_grade_sum=textual_grade_sum,
            file_grade_sum=file_grade_sum,
            sum_questions_grade_sum=sum_questions_grade_sum,
            questions_give_score_sum=questions_give_score_sum,
            total_grade=total_grade,
        ).distinct()

    def get_annotation_count_answers_filter_teacher(self, teacher, subjects=None, exclude_annuleds=False):
        ExamQuestion = apps.get_model('exams', 'ExamQuestion')
        OptionAnswer = apps.get_model('answers', 'OptionAnswer')
        TextualAnswer = apps.get_model('answers', 'TextualAnswer')
        FileAnswer = apps.get_model('answers', 'FileAnswer')
        SumAnswer = apps.get_model('answers', 'SumAnswer')
        StatusQuestion = apps.get_model('exams', 'StatusQuestion')

        exam_question_choice_teacher_subquery = self.get_exam_question_teacher_subquery(teacher, choice=True, subjects=subjects, exclude_annuleds=exclude_annuleds)
        exam_question_discursive_teacher_subquery = self.get_exam_question_teacher_subquery(teacher, discursive=True, subjects=subjects, exclude_annuleds=exclude_annuleds)
        exam_question_teacher_subquery = self.get_exam_question_teacher_subquery(teacher, subjects=subjects, exclude_annuleds=exclude_annuleds)

        choice_count = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    created_at__year=2025,
                    student_application__pk=OuterRef('pk'),
                    status=OptionAnswer.ACTIVE,
                    question_option__question=exam_question_choice_teacher_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        textual_count = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    empty=False,
                    question=exam_question_discursive_teacher_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        file_count = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    empty=False,
                    question=exam_question_discursive_teacher_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        correct_choice_count = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    created_at__year=2025,
                    student_application__pk=OuterRef('pk'),
                    status=OptionAnswer.ACTIVE,
                    question_option__is_correct=True,
                    question_option__question=exam_question_choice_teacher_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        correct_textual_count = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_discursive_teacher_subquery.values('question')[:1],
                    grade=Value(1.0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        correct_file_count = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_discursive_teacher_subquery.values('question')[:1],
                    grade=Value(1.0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        incorrect_choice_count = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    created_at__year=2025,
                    student_application__pk=OuterRef('pk'),
                    status=OptionAnswer.ACTIVE,
                    question_option__is_correct=False,
                    question_option__question=exam_question_choice_teacher_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        incorrect_textual_count = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_discursive_teacher_subquery.values('question')[:1],
                    teacher_grade=Value(0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        incorrect_file_count = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_teacher_subquery.values('question')[:1],
                    teacher_grade=Value(0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        corrected_textual_count = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_teacher_subquery.values('question')[:1],
                    grade__isnull=False,
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        corrected_file_count = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_teacher_subquery.values('question')[:1],
                    grade__isnull=False,
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        choice_grade_sum = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    created_at__year=2025,
                    student_application__pk=OuterRef('pk'),
                    status=1,
                    question_option__is_correct=True,
                    question_option__question=exam_question_choice_teacher_subquery.values('question')[:1]
                ).annotate(
                    grade=exam_question_choice_teacher_subquery.values('weight')[:1]
                ).values('student_application').annotate(
                    total=Sum('grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        textual_grade_sum = Coalesce(
            Subquery(
                TextualAnswer.objects.annotate(
                    question_pk=exam_question_discursive_teacher_subquery.values('question')[:1],
                    question_weight=exam_question_discursive_teacher_subquery.values('weight')[:1],
                ).filter(
                    student_application__pk=OuterRef('pk'),
                    question=F('question_pk'),
                ).annotate(
                    total_grade=F('grade') * F('question_weight')
                ).values('student_application').annotate(
                    total=Sum('total_grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        file_grade_sum = Coalesce(
            Subquery(
                FileAnswer.objects.annotate(
                    question_pk=exam_question_discursive_teacher_subquery.values('question')[:1],
                    question_weight=exam_question_discursive_teacher_subquery.values('weight')[:1],
                ).filter(
                    student_application__pk=OuterRef('pk'),
                    question=F('question_pk'),
                ).annotate(
                    total_grade=F('grade') * F('question_weight')
                ).values('student_application').annotate(
                    total=Sum('total_grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        sum_questions_grade_sum = Coalesce(
            SumAnswer.objects.annotate(
                    question_pk=exam_question_teacher_subquery.values('question')[:1],
                    question_weight=exam_question_teacher_subquery.values('weight')[:1],
                ).filter(
                    student_application__pk=OuterRef('pk'),
                    question=F('question_pk'),
                ).annotate(
                    teacher_grade=F('grade') * F('question_weight'),
                ).values('student_application').annotate(
                    total=Sum('teacher_grade')
                ).values('total')[:1],
            Decimal(0.0)
        )

        questions_give_score_sum=Coalesce(
            Subquery(
                ExamQuestion.objects.annotate(
                    has_give_score=Exists(
                        StatusQuestion.objects.filter(
                            exam_question=OuterRef('pk'),
                            annuled_give_score=True,
                            status=StatusQuestion.ANNULLED,
                            active=True,
                        )
                    )
                ).filter(
                    Q(exam=OuterRef('application__exam')),
                    Q(has_give_score=True),
                    Q(
                        Q(
                            Q(exam_teacher_subject__isnull=True),
                            Q(question__subject__in=subjects)
                        ) |
                        Q(
                            Q(exam_teacher_subject__isnull=False),
                            Q(exam_teacher_subject__teacher_subject__subject__in=subjects)
                        )
                    ) if subjects else Q(),
                ).values('exam').annotate(Sum('weight')).values('weight__sum')[:1]
            ),
            Decimal(0.0)
        )

        return self.annotate(
            total_answers=choice_count + textual_count + file_count,
            total_corrected_answers=corrected_textual_count + corrected_file_count,
            total_text_file_answers=textual_count + file_count,
            total_correct_answers=correct_choice_count + correct_textual_count + correct_file_count,
            total_incorrect_answers=incorrect_choice_count + incorrect_textual_count + incorrect_file_count,
            total_partial_answers=corrected_textual_count + corrected_file_count - correct_textual_count - correct_file_count - incorrect_textual_count - incorrect_file_count,
            choice_grade_sum=choice_grade_sum,
            textual_grade_sum=textual_grade_sum,
            file_grade_sum=file_grade_sum,
            sum_questions_grade_sum=sum_questions_grade_sum,
            questions_give_score_sum=questions_give_score_sum,
            total_grade=choice_grade_sum + textual_grade_sum + file_grade_sum + questions_give_score_sum + sum_questions_grade_sum,
        ).distinct()

    def get_annotation_count_answers_filter_subjects(
            self, subjects, only_total_grade=False, exclude_annuleds=False, only_total_answers=None):
        OptionAnswer = apps.get_model('answers', 'OptionAnswer')
        TextualAnswer = apps.get_model('answers', 'TextualAnswer')
        FileAnswer = apps.get_model('answers', 'FileAnswer')
        ExamQuestion = apps.get_model('exams', 'ExamQuestion')
        SumAnswer = apps.get_model('answers', 'SumAnswer')
        StatusQuestion = apps.get_model('exams', 'StatusQuestion')

        exam_question_choice_subjects_subquery = self.get_exam_question_subjects_subquery(subjects, choice=True, exclude_annuleds=exclude_annuleds)
        exam_question_discursive_subjects_subquery = self.get_exam_question_subjects_subquery(subjects, discursive=True, exclude_annuleds=exclude_annuleds)
        exam_question_subjects_subquery = self.get_exam_question_subjects_subquery(subjects, exclude_annuleds=exclude_annuleds)

        choice_count = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    status=OptionAnswer.ACTIVE,
                    question_option__question=exam_question_choice_subjects_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        textual_count = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    empty=False,
                    question=exam_question_discursive_subjects_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        file_count = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    empty=False,
                    question=exam_question_discursive_subjects_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        correct_choice_count = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    status=OptionAnswer.ACTIVE,
                    question_option__is_correct=True,
                    question_option__question=exam_question_choice_subjects_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        correct_textual_count = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subjects_subquery.values('question')[:1],
                    grade=Value(1.0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        correct_file_count = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subjects_subquery.values('question')[:1],
                    grade=Value(1.0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        correct_sum_answer_count = Coalesce(
            Subquery(
                SumAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subjects_subquery.values('question')[:1],
                    grade=Value(1.0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        incorrect_choice_count = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    status=OptionAnswer.ACTIVE,
                    question_option__is_correct=False,
                    question_option__question=exam_question_choice_subjects_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        incorrect_textual_count = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subjects_subquery.values('question')[:1],
                    grade=Value(0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        incorrect_file_count = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subjects_subquery.values('question')[:1],
                    grade=Value(0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        incorrect_sum_answer_count = Coalesce(
            Subquery(
                SumAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subjects_subquery.values('question')[:1],
                    grade=Value(0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        corrected_textual_count = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subjects_subquery.values('question')[:1],
                    grade__isnull=False,
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        corrected_file_count = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subjects_subquery.values('question')[:1],
                    grade__isnull=False,
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        corrected_sum_answer_count = Coalesce(
            Subquery(
                SumAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subjects_subquery.values('question')[:1],
                    grade__isnull=False,
                    empty=False,
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        choice_grade_sum = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    status=1,
                    question_option__is_correct=True,
                    question_option__question=exam_question_choice_subjects_subquery.values('question')[:1]
                ).annotate(
                    grade=exam_question_choice_subjects_subquery.values('weight')[:1]
                ).values('student_application').annotate(
                    total=Sum('grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        textual_grade_sum = Coalesce(
            Subquery(
                TextualAnswer.objects.annotate(
                    question_pk=exam_question_discursive_subjects_subquery.values('question')[:1],
                    question_weight=exam_question_discursive_subjects_subquery.values('weight')[:1],
                ).filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=F('question_pk'),
                ).annotate(
                    total_grade=F('grade') * F('question_weight')
                ).values('student_application').annotate(
                    total=Sum('total_grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        file_grade_sum = Coalesce(
            Subquery(
                FileAnswer.objects.annotate(
                    question_pk=exam_question_discursive_subjects_subquery.values('question')[:1],
                    question_weight=exam_question_discursive_subjects_subquery.values('weight')[:1],
                ).filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=F('question_pk'),
                ).annotate(
                    total_grade=F('grade') * F('question_weight')
                ).values('student_application').annotate(
                    total=Sum('total_grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        sum_questions_grade_sum = Coalesce(
            Subquery(
                SumAnswer.objects.annotate(
                    question_pk=exam_question_subjects_subquery.values('question')[:1],
                    question_weight=exam_question_subjects_subquery.values('weight')[:1],
                ).filter(
                    created_at__year=OuterRef('application__date__year'),
                    student_application__pk=OuterRef('pk'),
                    question=F('question_pk'),
                ).annotate(
                    teacher_grade=F('grade') * F('question_weight')
                ).values('student_application').annotate(
                    total=Sum('teacher_grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        questions_give_score_sum=Coalesce(
            Subquery(
                ExamQuestion.objects.annotate(
                    has_give_score=Exists(
                        StatusQuestion.objects.filter(
                            exam_question=OuterRef('pk'),
                            annuled_give_score=True,
                            status=StatusQuestion.ANNULLED,
                            active=True,
                        )
                    )
                ).filter(
                    Q(exam=OuterRef('application__exam')),
                    Q(has_give_score=True),
                    Q(
                        Q(
                            Q(exam_teacher_subject__isnull=True),
                            Q(question__subject__in=subjects)
                        ) |
                        Q(
                            Q(exam_teacher_subject__isnull=False),
                            Q(exam_teacher_subject__teacher_subject__subject__in=subjects)
                        )
                    ) if subjects else Q(),
                ).values('exam').annotate(Sum('weight')).values('weight__sum')[:1]
            ),
            Decimal(0.0)
        )

        if only_total_grade:
            return self.annotate(
                total_grade=choice_grade_sum + textual_grade_sum + file_grade_sum + questions_give_score_sum + sum_questions_grade_sum
            ).distinct()

        if only_total_answers:
            return self.annotate(
                total_correct_answers=correct_choice_count + correct_textual_count + correct_file_count + correct_sum_answer_count,
                total_incorrect_answers=incorrect_choice_count + incorrect_textual_count + incorrect_file_count + incorrect_sum_answer_count,
                total_partial_answers=corrected_textual_count + corrected_file_count + corrected_sum_answer_count - correct_textual_count - correct_file_count - correct_sum_answer_count - incorrect_textual_count - incorrect_file_count - incorrect_sum_answer_count,
            ).distinct()

        return self.annotate(
            total_answers=choice_count + textual_count + file_count,
            total_corrected_answers=corrected_textual_count + corrected_file_count,
            total_text_file_answers=textual_count + file_count,
            total_correct_answers=correct_choice_count + correct_textual_count + correct_file_count + correct_sum_answer_count,
            total_incorrect_answers=incorrect_choice_count + incorrect_textual_count + incorrect_file_count + incorrect_sum_answer_count,
            total_partial_answers=corrected_textual_count + corrected_file_count + corrected_sum_answer_count - correct_textual_count - correct_file_count - correct_sum_answer_count - incorrect_textual_count - incorrect_file_count - incorrect_sum_answer_count,
            choice_grade_sum=choice_grade_sum,
            textual_grade_sum=textual_grade_sum,
            file_grade_sum=file_grade_sum,
            questions_give_score_sum=questions_give_score_sum,
            sum_questions_grade_sum=sum_questions_grade_sum,
            total_grade=choice_grade_sum + textual_grade_sum + file_grade_sum + questions_give_score_sum + sum_questions_grade_sum,
        ).distinct()

    def get_annotation_subject_grade(self, subject, exclude_annuleds=True):
        OptionAnswer = apps.get_model('answers', 'OptionAnswer')
        TextualAnswer = apps.get_model('answers', 'TextualAnswer')
        FileAnswer = apps.get_model('answers', 'FileAnswer')
        SumAnswer = apps.get_model('answers', 'SumAnswer')
        ExamQuestion = apps.get_model('exams', 'ExamQuestion')
        StatusQuestion = apps.get_model('exams', 'StatusQuestion')


        exam_question_choice_subjects_subquery = self.get_exam_question_subjects_subquery([subject], choice=True, exclude_annuleds=exclude_annuleds)
        exam_question_discursive_subjects_subquery = self.get_exam_question_subjects_subquery([subject], discursive=True, exclude_annuleds=exclude_annuleds)
        exam_question_subjects_subquery = self.get_exam_question_subjects_subquery([subject], exclude_annuleds=exclude_annuleds)

        choice_grade_sum = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    status=1,
                    question_option__is_correct=True,
                    question_option__question=exam_question_choice_subjects_subquery.values('question')[:1]
                ).annotate(
                    grade=exam_question_choice_subjects_subquery.values('weight')[:1]
                ).values('student_application').annotate(
                    total=Sum('grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        textual_grade_sum = Coalesce(
            Subquery(
                TextualAnswer.objects.annotate(
                    question_pk=exam_question_discursive_subjects_subquery.values('question')[:1],
                    question_weight=exam_question_discursive_subjects_subquery.values('weight')[:1],
                ).filter(
                    student_application__pk=OuterRef('pk'),
                    question=F('question_pk'),
                ).annotate(
                    total_grade=F('grade') * F('question_weight')
                ).values('student_application').annotate(
                    total=Sum('total_grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        file_grade_sum = Coalesce(
            Subquery(
                FileAnswer.objects.annotate(
                    question_pk=exam_question_discursive_subjects_subquery.values('question')[:1],
                    question_weight=exam_question_discursive_subjects_subquery.values('weight')[:1],
                ).filter(
                    student_application__pk=OuterRef('pk'),
                    question=F('question_pk'),
                ).annotate(
                    total_grade=F('grade') * F('question_weight')
                ).values('student_application').annotate(
                    total=Sum('total_grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        sum_questions_grade_sum = Coalesce(
            Subquery(
                SumAnswer.objects.annotate(
                    question_pk=exam_question_subjects_subquery.values('question')[:1],
                    question_weight=exam_question_subjects_subquery.values('weight')[:1],
                ).filter(
                    student_application__pk=OuterRef('pk'),
                    question=F('question_pk'),
                ).annotate(
                    teacher_grade=F('grade') * F('question_weight')
                ).values('student_application').annotate(
                    total=Sum('teacher_grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        questions_give_score_sum=Coalesce(
            Subquery(
                ExamQuestion.objects.annotate(
                    has_give_score=Exists(
                        StatusQuestion.objects.filter(
                            exam_question=OuterRef('pk'),
                            annuled_give_score=True,
                            status=StatusQuestion.ANNULLED,
                            active=True,
                        )
                    )
                ).filter(
                    Q(exam=OuterRef('application__exam')),
                    Q(has_give_score=True),
                    Q(
                        Q(
                            Q(exam_teacher_subject__isnull=True),
                            Q(question__subject=subject)
                        ) |
                        Q(
                            Q(exam_teacher_subject__isnull=False),
                            Q(exam_teacher_subject__teacher_subject__subject=subject)
                        )
                    ),
                ).values('exam').annotate(Sum('weight')).values('weight__sum')[:1]
            ),
            Decimal(0.0)
        )

        result = self.annotate(
            total_subject_grade=choice_grade_sum + textual_grade_sum + file_grade_sum + sum_questions_grade_sum + questions_give_score_sum,
        ).distinct()

        return result

    def get_annotation_subject_count(self, subject, exclude_annuleds=False):
        OptionAnswer = apps.get_model('answers', 'OptionAnswer')
        TextualAnswer = apps.get_model('answers', 'TextualAnswer')
        FileAnswer = apps.get_model('answers', 'FileAnswer')
        SumAnswer = apps.get_model('answers', 'SumAnswer')

        exam_question_choice_subjects_subquery = self.get_exam_question_subjects_subquery([subject], choice=True, exclude_annuleds=exclude_annuleds)
        exam_question_discursive_subjects_subquery = self.get_exam_question_subjects_subquery([subject], discursive=True, exclude_annuleds=exclude_annuleds)
        exam_question_subjects_subquery = self.get_exam_question_subjects_subquery([subject], exclude_annuleds=exclude_annuleds)

        correct_choice_count = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    status=OptionAnswer.ACTIVE,
                    question_option__is_correct=True,
                    question_option__question=exam_question_choice_subjects_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        correct_textual_count = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_discursive_subjects_subquery.values('question')[:1],
                    grade__gte=Value(1.0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        correct_file_count = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_discursive_subjects_subquery.values('question')[:1],
                    grade__gte=Value(1.0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        correct_sum_answer_count = Coalesce(
            Subquery(
                SumAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subjects_subquery.values('question')[:1],
                    grade=Value(1.0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        incorrect_choice_count = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    status=OptionAnswer.ACTIVE,
                    question_option__is_correct=False,
                    question_option__question=exam_question_choice_subjects_subquery.values('question')[:1],
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        incorrect_textual_count = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_discursive_subjects_subquery.values('question')[:1],
                    grade=Value(0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        incorrect_file_count = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_discursive_subjects_subquery.values('question')[:1],
                    grade=Value(0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        incorrect_sum_answer_count = Coalesce(
            Subquery(
                SumAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subjects_subquery.values('question')[:1],
                    grade=Value(0),
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        corrected_textual_count = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subjects_subquery.values('question')[:1],
                    grade__isnull=False,
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        corrected_file_count = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subjects_subquery.values('question')[:1],
                    grade__isnull=False,
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        corrected_sum_answer_count = Coalesce(
            Subquery(
                SumAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_subjects_subquery.values('question')[:1],
                    grade__isnull=False,
                    empty=False,
                ).values('student_application').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ), 0
        )

        return self.annotate(
            total_correct_answers=correct_choice_count + correct_textual_count + correct_file_count + correct_sum_answer_count,
            total_incorrect_answers=incorrect_choice_count + incorrect_textual_count + incorrect_file_count + incorrect_sum_answer_count,
            total_partial_answers=corrected_textual_count + corrected_file_count + corrected_sum_answer_count - correct_textual_count - correct_file_count - correct_sum_answer_count - incorrect_textual_count - incorrect_file_count - incorrect_sum_answer_count,
        ).distinct()

    def annotate_exam_name(self):
        return self.annotate(
            exam_name=F('application__exam__name')
        ).distinct()

    def get_last_school_class(self, use_application_date=False):
        if use_application_date:
            year = OuterRef('application__date__year')
        else:
            year = timezone.now().year

        school_class_subquery = SchoolClass.objects.filter(
            students=OuterRef('student'),
            school_year=year,
            temporary_class=False,
        )
        return self.annotate(
            school_class=Subquery(
                school_class_subquery.values('pk')[:1]
            ),
            school_class_name=Subquery(
                school_class_subquery.values('name')[:1]
            ),
            school_class_unity=Subquery(
                school_class_subquery.values('coordination__unity__name')[:1]
            )
        )

    def annotate_is_present(self):
        return self.annotate(
            is_present=Case(
                When(
                    Q(
                        Q(is_omr=True) |
                        Q(start_time__isnull=False) |
                        Q(option_answers__isnull=False) |
                        Q(file_answers__grade__isnull=False) |
                        Q(textual_answers__grade__isnull=False)
                    ),
                    then=Value(True)
                ),
                When(
                    Q(
                        Q(missed=True)
                    ),
                    then=Value(False)
                ),
                default=Value(False)
            )
        ).distinct()
    
    def annotate_is_present_with_subquery(self):

        OptionAnswer = apps.get_model('answers', 'OptionAnswer')
        FileAnswer = apps.get_model('answers', 'FileAnswer')
        TextualAnswer = apps.get_model('answers', 'TextualAnswer')

        return self.annotate(
            is_present=Case(
                When(
                    Q(is_omr=True) |
                    Q(start_time__isnull=False) |
                    Exists(OptionAnswer.objects.filter(student_application=OuterRef('pk'))) |
                    Exists(FileAnswer.objects.filter(student_application=OuterRef('pk'), grade__isnull=False)) |
                    Exists(TextualAnswer.objects.filter(student_application=OuterRef('pk'), grade__isnull=False)),
                    then=Value(True)
                ),
                When(
                    missed=True, 
                    then=Value(False)
                ),
                default=Value(False),
            )
        ).distinct()

    def has_answer_and_last_applicationstudent(self):
        ApplicationStudent = apps.get_model('applications', 'ApplicationStudent')
        return self.annotate(
            has_answer=Case(
                When(
                    Q(
                        Q(option_answers__isnull=False) |
                        Q(file_answers__isnull=False) |
                        Q(textual_answers__isnull=False)
                    ),
                    then=True
                ),
                default=Value(False)
            ),
            last_application_student_id=Subquery(
                ApplicationStudent.objects.filter(
                    student=OuterRef('student'),
                    application__exam=OuterRef('application__exam'),
                ).order_by('-created_at').values('pk')[:1]
            )
        ).distinct()

    def presents(self):
        Application = apps.get_model('applications', 'Application')
        ApplicationStudent = apps.get_model('applications', 'ApplicationStudent')

        pks = set(list(self.filter(
            Q(
                Q(
                    Q(application__category=Application.MONITORIN_EXAM),
                    Q(start_time__isnull=False)
                ) |
                Q(
                    Q(application__category=Application.PRESENTIAL),
                    Q(is_omr=True)
                ) |
                Q(
                    Q(application__category=Application.HOMEWORK),
                    Q(
                        Q(option_answers__isnull=False) |
                        Q(textual_answers__isnull=False) |
                        Q(file_answers__isnull=False)
                    )
                )
            )
        ).distinct().values_list("pk", flat=True)))

        return self.filter(
            pk__in=pks
        )

    def get_aggregation_answers(self):

        return self.presents().aggregate(
            total_correct=Sum('total_correct_answers'),
            total_partial=Sum('total_partial_answers'),
            total_incorrect=Sum('total_incorrect_answers'),
            duration_average=Avg(F('end_time') - F('start_time')),
            grade_average=Avg('total_grade')
        )

    def get_unique_set(self, exam, present=False, vacant=False):
        # Student = apps.get_model('students', 'Student')

        application_students_exam = (
            self.filter(
                application__exam=exam
            )
            .annotate_is_present_with_subquery()
            .order_by('student__name')
        )

        if present:
            application_students_exam = application_students_exam.filter(is_present=True)
        elif vacant:
            application_students_exam = application_students_exam.filter(is_present=False)

        return application_students_exam

        # A LÓGICA FOI SUBSTITUÍDA EM 25/06/2025 POR LUIZ 
        # Adicionei o annotate_is_present_with_subquery() para centralizar a lógica
        # que faz a anotação do is_present

        # application_students_exam_presential = application_students_exam.filter(
        #     is_omr=True,
        #     missed=False
        # )

        # application_students_exam_online = application_students_exam.filter(
        #     Q(is_omr=False),
        #     Q(missed=False),
        #     Q(
        #         Q(start_time__isnull=False) |
        #         Q(
        #             Q(file_answers__grade__isnull=False) |
        #             Q(textual_answers__grade__isnull=False)
        #         )
        #     )
        # )

        # application_students_present = application_students_exam_presential | application_students_exam_online

        # application_students_exam_vacant = application_students_exam.exclude(
        #     is_omr=True
        # ).exclude(
        #     start_time__isnull=False
        # ).exclude(
        #     student__in=Student.objects.filter(
        #         pk__in=application_students_present.values('student__pk')
        #     )
        # )

        # if not present and not vacant:
        #     return application_students_present | application_students_exam_vacant
        # elif present:
        #     return application_students_present
        # elif vacant:
        #     return application_students_exam_vacant

    def get_annotation_json_subjects_grades(self, subjects_pks=[], get_abstracts=False):
        Subject = apps.get_model('subjects', 'Subject')
        SubjectCode = apps.get_model('integrations', 'SubjectCode')
        ExamQuestion = apps.get_model('exams', 'ExamQuestion')
        ExamTeacherSubject = apps.get_model('exams', 'ExamTeacherSubject')
        OptionAnswer = apps.get_model('answers', 'OptionAnswer')
        TextualAnswer = apps.get_model('answers', 'TextualAnswer')
        FileAnswer = apps.get_model('answers', 'FileAnswer')

        exam_question_discursive_subquery = self.get_exam_question_subquery(
            discursive=True, subjects=subjects_pks
        )

        choice_grade_sum = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    student_application__pk=OuterRef(OuterRef('pk')),
                    status=1,
                    question_option__is_correct=True,
                ).annotate(
                    grade=Subquery(
                        ExamQuestion.objects.filter(
                            question=OuterRef('question_option__question'),
                            exam=OuterRef('student_application__application__exam'),
                            exam_teacher_subject__teacher_subject__subject=OuterRef(OuterRef('pk'))
                        ).values('weight')[:1]
                    )
                ).values('student_application').annotate(
                    total=Sum('grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        textual_grade_sum = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    student_application__pk=OuterRef(OuterRef('pk')),
                    question=Subquery(
                        ExamQuestion.objects.filter(
                            question=OuterRef('question'),
                            exam=OuterRef('student_application__application__exam'),
                            exam_teacher_subject__teacher_subject__subject=OuterRef(OuterRef('pk'))
                        ).values('question')[:1]
                    ),
                    question_weight=exam_question_discursive_subquery.values('weight')[:1]
                ).annotate(
                    teacher_grade=F('grade') * F('question_weight')
                ).values('student_application').annotate(
                    total=Sum('teacher_grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        file_grade_sum = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    student_application__pk=OuterRef(OuterRef('pk')),
                    question=Subquery(
                        ExamQuestion.objects.filter(
                            question=OuterRef('question'),
                            exam=OuterRef('student_application__application__exam'),
                            exam_teacher_subject__teacher_subject__subject=OuterRef(OuterRef('pk'))
                        ).values('question')[:1]
                    ),
                    question_weight=exam_question_discursive_subquery.values('weight')[:1]
                ).annotate(
                    teacher_grade=F('grade') * F('question_weight')
                ).values('student_application').annotate(
                    total=Sum('teacher_grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        subject_subquery = Subject.objects.filter(
                Q(pk__in=Subquery(
                    ExamTeacherSubject.objects.filter(
                        exam=OuterRef(OuterRef('application__exam'))
                    ).values('teacher_subject__subject')
                )) |
                Q(pk__in=Subquery(
                    ExamQuestion.objects.filter(
                        exam=OuterRef(OuterRef('application__exam')),
                        exam__is_abstract=True
                    ).values('question__subject')
                )) if get_abstracts else Q()
            ).annotate(
                grade=choice_grade_sum + textual_grade_sum + file_grade_sum,
                code=Coalesce(
                    Subquery(
                        SubjectCode.objects.filter(
                            subject=OuterRef('pk'),
                            client=OuterRef(OuterRef('student__client')),
                        ).values('code')[:1]
                    ),
                    Subquery(
                        SubjectCode.objects.filter(
                            subject=OuterRef('parent_subject__pk'),
                            client=OuterRef(OuterRef('student__client')),
                        ).values('code')[:1]
                    )
                )
            )

        if subjects_pks:
            subject_subquery =  subject_subquery.filter(
                pk__in=subjects_pks
            )

        exam_subjects = Subquery(
            subject_subquery.values(
                json=JSONObject(name='name', code='code', grade=F('grade'), pk='pk')
            )
        )

        return self.annotate(
            exam_subjects_json=ArraySubquery(exam_subjects),
        )

    # AQUI COMEÇA OS MANAGERS PARA IMPORTAÇÃO DAS PERFORMANCES'

    def annotate_performance(self, level, teacher_subject):
        ExamQuestion = apps.get_model('exams', 'ExamQuestion')
        Application = apps.get_model('applications', 'Application')

        from sql_util.utils import SubqueryAggregate

        try:
            # exam_questions = ExamQuestion.objects.filter(
            #     question__level=level,
            #     exam_teacher_subject__teacher_subject=teacher_subject,
            #     exam=OuterRef('application__exam')
            # ).order_by().distinct()

            queryset = self.filter(
                Q(
                   Q(
                        Q(application__category=Application.MONITORIN_EXAM),
                        Q(start_time__isnull=False),
                        Q(end_time__isnull=False)
                   ) |
                   Q(
                       Q(application__category=Application.PRESENTIAL),
                       Q(is_omr=True)
                    ) |
                    Q(
                        Q(application__category=Application.HOMEWORK),
                        Q(
                            Q(option_answers__isnull=False) |
                            Q(textual_answers__isnull=False) |
                            Q(file_answers__isnull=False)
                        )
                    )
                ),
                Q(
                    application__exam__isnull=False
                )
            ).get_annotation_count_answers_filter_teacher_subject(
                teacher_subject=teacher_subject,
                level=level
            )

            # queryset = queryset.annotate(
            #     exam_max_grade=Subquery(
            #         exam_questions.values("weight").annotate(
            #             total_grade=Sum('weight')
            #         ).values('total_grade')[:1]
            #     )
            # )

            queryset = queryset.annotate(
                exam_max_grade=SubqueryAggregate(
                    'application__exam__examteachersubject__examquestion__weight',
                    # 'application__exam__examquestion__weight',
                    filter=Q(
                        Q(question__level=level),
                        Q(exam_teacher_subject__teacher_subject=teacher_subject)
                    ),
                    aggregate=Sum
                )
            )

            queryset = queryset.annotate(
                performance=Cast(
                    F('total_grade'), FloatField()
                ) /
                Cast(
                    F('exam_max_grade'), FloatField()
                )
            ).distinct()

        except Exception as e:
            print("### - Erro @@@", e)

        return queryset

    def get_average_grade(self, level, teacher_subject):
        result = self.annotate_performance(
            teacher_subject=teacher_subject,
            level=level
        )

        result = result.aggregate(
            avarage_grade=Avg('performance')
        ).get("avarage_grade", 0)

        return round_half_up((result * 100), 2) if result else 0

    def get_exam_question_subquery_level(self, level, choice=False, exclude_annuleds=False):
        ExamQuestion = apps.get_model('exams', 'ExamQuestion')
        queryset = ExamQuestion.objects.none()

        if choice:
            queryset = ExamQuestion.objects.filter(
                question=OuterRef('question_option__question'),
                question__level=level,
                exam=OuterRef('student_application__application__exam'),
            )
        else:
            queryset = ExamQuestion.objects.filter(
                    question=OuterRef('question'),
                    question__level=level,
                    exam=OuterRef('student_application__application__exam'),
                )
        if exclude_annuleds:
            queryset = queryset.availables(exclude_annuleds=exclude_annuleds)

        return queryset

    def get_exam_question_teacher_subject_subquery(self, teacher_subject, level, choice=False, exclude_annuleds=False):
        return self.get_exam_question_subquery_level(choice=choice, level=level, exclude_annuleds=exclude_annuleds).filter(
            exam_teacher_subject__teacher_subject=teacher_subject
        )

    def get_annotation_count_answers_filter_teacher_subject(self, teacher_subject, level, exclude_annuleds=False):
        OptionAnswer = apps.get_model('answers', 'OptionAnswer')
        TextualAnswer = apps.get_model('answers', 'TextualAnswer')
        FileAnswer = apps.get_model('answers', 'FileAnswer')

        exam_question_choice_teacher_subject_subquery = self.get_exam_question_teacher_subject_subquery(teacher_subject=teacher_subject, level=level, choice=True, exclude_annuleds=exclude_annuleds)

        exam_question_teacher_subject_subquery = self.get_exam_question_teacher_subject_subquery(teacher_subject=teacher_subject, level=level, exclude_annuleds=exclude_annuleds)

        choice_grade_sum = Coalesce(
            Subquery(
                OptionAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    status=1,
                    question_option__is_correct=True,
                    question_option__question__level=level,
                    question_option__question=exam_question_choice_teacher_subject_subquery.values('question')[:1]
                ).annotate(
                    grade=exam_question_choice_teacher_subject_subquery.values('weight')[:1]
                ).values('student_application').annotate(
                    total=Sum('grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        textual_grade_sum = Coalesce(
            Subquery(
                TextualAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_teacher_subject_subquery.values('question')[:1],
                    question__level=level
                ).annotate(
                    teacher_grade=F('grade') * F('question_weight')
                ).values('student_application').annotate(
                    total=Sum('teacher_grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        file_grade_sum = Coalesce(
            Subquery(
                FileAnswer.objects.filter(
                    student_application__pk=OuterRef('pk'),
                    question=exam_question_teacher_subject_subquery.values('question')[:1],
                    question__level=level
                ).annotate(
                    teacher_grade=F('grade') * F('question_weight')
                ).values('student_application').annotate(
                    total=Sum('teacher_grade')
                ).values('total')[:1]
            ), Decimal(0.0)
        )

        return self.annotate(
            total_grade=choice_grade_sum + textual_grade_sum + file_grade_sum,
        ).distinct()

    def only_scheduled(self):
        Application = apps.get_model('applications', 'Application')
        from datetime import timedelta
        today = timezone.localtime(timezone.now())
        return self.annotate(
            exam_datetime_end = ExpressionWrapper(F('application__date') + F('application__end') + timedelta(hours=3), output_field=DateTimeField()),
            homework_datetime_end = ExpressionWrapper(F('application__date_end') + F('application__end') + timedelta(hours=3), output_field=DateTimeField())
        ).filter(
            Q(
                Q(application__release_result_at_end=True, end_time__isnull=True),
                Q(
                    Q(application__category=Application.HOMEWORK, homework_datetime_end__gt=today) |
                    Q(application__category=Application.MONITORIN_EXAM, exam_datetime_end__gt=today)
                )
            ) |
            Q(
                application__release_result_at_end=False,
                application__student_stats_permission_date__gt=today,
            )
        ).exclude(
            application__student_stats_permission_date__isnull=True
        )

    def availables_today(self):
        Application = apps.get_model('applications', 'Application')
        from datetime import timedelta

        application_date_start = ExpressionWrapper(F('application__date') + F('application__start'), output_field=DurationField())
        application_date_end = ExpressionWrapper(F('application__date') + F('application__end'), output_field=DurationField())
        application_date_end_homework = ExpressionWrapper((F('application__date_end') + F('application__end')) + timedelta(hours=3), output_field=DurationField())

        today = timezone.localtime(timezone.now()).today()
        now = timezone.localtime(timezone.now()).now()

        return self.annotate(
            application_date_start=application_date_start,
            application_date_end=Case(
                When(application__category=Application.HOMEWORK, then=application_date_end_homework),
                default=application_date_end,
                output_field=DurationField()
            )
        ).filter(
            Q(
                Q(end_time__isnull=True),
                Q(application__date=today),
                Q(application_date_start__lte=now),
                Q(application_date_end__gt=now),
                Q(
                    Q(application__duplicate_application=False) |
                    Q(is_omr=True)
                ),
                ~Q(application__category=Application.HOMEWORK)
            ) |
            Q(
                Q(application_date_end__gte=now),
                Q(application_date_start__lte=now),
                Q(application__category=Application.HOMEWORK),
                Q(
                    Q(application__duplicate_application=False) |
                    Q(is_omr=True)
                )
            )
        ).exclude(
            Q(
                Q(application__allow_student_redo_list=False),
                Q(end_time__isnull=False)
            )
        ).order_by('application__exam__name').distinct()

    def recently_released_results(self, return_all=False):
        Application = apps.get_model('applications', 'Application')
        from datetime import timedelta
        now = timezone.localtime(timezone.now())
        seven_days_ago = now - timedelta(days=7)

        applications_student = self.annotate(
            datetime_end=Case(
                When(
                    application__student_stats_permission_date__lt=F('application__date_end') + F('application__end'),
                    then=F('application__student_stats_permission_date')
                ),
                default=F('application__date_end') + F('application__end'),
                output_field=DateTimeField()
            ),
            can_see=Case(
                When(
                    application__category=Application.MONITORIN_EXAM,
                    end_time__isnull=False,
                    then=Value(True)
                ),
                When(
                    application__category=Application.PRESENTIAL,
                    is_omr=True,
                    then=Value(True)
                ),
                When(
                    application__category=Application.HOMEWORK,
                    datetime_end__lt=now,
                    then=Value(True)
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
        ).filter(
            # Q(performances__isnull=False), # TODO: Removi por que ta pesando muito e não faz diferença deixar esse filtro aqui pois a performance foi aprimorada
            Q(application__student_stats_permission_date__gt=seven_days_ago),
            Q(application__student_stats_permission_date__lte=now),
            Q(can_see=True),
            Q(
                Q(application__duplicate_application=False) |
                Q(is_omr=True)
            )
        ).order_by('end_time', '-application__student_stats_permission_date')

        return applications_student if return_all else applications_student[:5]

class RandomizationVersionQuerySet(models.QuerySet):

    def add_new_application_student(self, application_student, exam_json):
        total_count = self.filter(application_student=application_student).count()
        randomization_version = self.create(
            application_student=application_student,
            exam_json=exam_json,
            version_number=total_count + 1
        )

        return randomization_version

class ApplicationRandomizationVersionQuerySet(models.QuerySet):

    def get_last_versions(self, application):
        max_version = self.using('default').filter(application=application).aggregate(max_version=Max('version_number')).get('max_version', 0)
        return self.using('default').filter(
                application=application,
                version_number=max_version
            ).order_by('created_at', 'sequential')


ApplicationManager = models.Manager.from_queryset(ApplicationQuerySet)
ApplicationStudentManager = models.Manager.from_queryset(ApplicationStudentQuerySet)
RandomizationVersionManager = models.Manager.from_queryset(RandomizationVersionQuerySet)
ApplicationRandomizationVersionManager = models.Manager.from_queryset(ApplicationRandomizationVersionQuerySet)
