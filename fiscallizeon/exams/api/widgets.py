from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from fiscallizeon.answers.models import FileAnswer, OptionAnswer, TextualAnswer 
from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication
from django.db.models import Q, Subquery, F, Count, Sum, OuterRef

from fiscallizeon.exams.models import Exam, ExamQuestion


def get_exam(request):
    exam_pk = request.GET.get('exam_pk')
    if not exam_pk:
        return Response('Caderno não informado', status=status.HTTP_400_BAD_REQUEST)
    try:
        return Exam.objects.get(pk=exam_pk)
    except Exam.DoesNotExist:
        return Response('Caderno não encontrado', status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(repr(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WidgetObjectiveAnswers(APIView):
    permission_classes = []
    authentication_classes = (CsrfExemptSessionAuthentication,)
    
    
    def get_exam_questions(self, exam):
        exam = exam
        exam_questions = exam.examquestion_set.availables()

        user = self.request.user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if exam.correction_by_subject:
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all()) |
                    Q(question__subject__in=teacher.subjects.all())
                ).distinct()
            else:
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__teacher=teacher) |
                    Q(question__subject__in=teacher.subjects.all())
                ).distinct()

        return exam_questions.order_by('exam_teacher_subject__order', 'order')
    
    def get(self, request):
        exam = get_exam(request)
        user = self.request.user
        coordinations = user.get_coordinations_cache()

        data: dict = {
            "total_objective_answers": 0,
            "total_correct_objective_answers": 0,
            "total_incorrect_objective_answers": 0,
        }
        q_subjects = self.request.GET.getlist('q_subjects', None)
        
        applications_student = exam.get_application_students(coordinations=coordinations).filter(
            Q(option_answers__question_option__question__examquestion__in=self.get_exam_questions(exam)),
            Q(application__in=self.request.GET.getlist('q_applications')) if self.request.GET.get('q_applications') else Q(),    
            Q(student__name__icontains=self.request.GET.get('q_student_name')) if self.request.GET.get('q_student_name') else Q(),
            Q(student__classes__in=self.request.GET.getlist('q_school_classes')) if self.request.GET.getlist('q_school_classes') else Q(),
            Q(
                Q(is_omr=True) | Q(start_time__isnull=False)
            ) if self.request.GET.get('q_application_start') else Q(),
        )
        
        applications_student_aggregations = applications_student.aggregate(
            total_option_answers=Count('option_answers', filter=Q(
                Q(option_answers__question_option__question__subject__in=q_subjects) if q_subjects else Q(), 
                Q(option_answers__question_option__question__examquestion__in=self.get_exam_questions(exam))
            ), distinct=True),
            total_correct_objective_answers=Count('option_answers', filter=Q(
                Q(option_answers__status=OptionAnswer.ACTIVE), 
                Q(option_answers__question_option__is_correct=True), 
                Q(option_answers__question_option__question__subject__in=q_subjects) if q_subjects else Q(), 
                Q(option_answers__question_option__question__examquestion__in=self.get_exam_questions(exam))
            ), distinct=True),
        )
        data['total_objective_answers'] = applications_student_aggregations.get('total_option_answers', 0)
        data['total_correct_objective_answers'] = applications_student_aggregations.get('total_correct_objective_answers', 0)
        data['total_incorrect_objective_answers'] = data['total_objective_answers'] - data['total_correct_objective_answers']
        
        return Response(data=data, status=status.HTTP_200_OK)
    
class WidgetDiscursiveAnswers(APIView):
    permission_classes = []
    authentication_classes = (CsrfExemptSessionAuthentication,)
    
    def get_exam_questions(self, exam):
        exam = exam
        exam_questions = exam.examquestion_set.availables()

        user = self.request.user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if exam.correction_by_subject:
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all()) |
                    Q(question__subject__in=teacher.subjects.all())
                ).distinct()
            else:
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__teacher=teacher) |
                    Q(question__subject__in=teacher.subjects.all())
                ).distinct()

        return exam_questions.order_by('exam_teacher_subject__order', 'order')
    
    def get(self, request):
        exam = get_exam(request)
        data = {}
        q_subjects = self.request.GET.getlist('q_subjects', None)
        user = self.request.user
        coordinations = user.get_coordinations_cache()

        applications_student = exam.get_application_students(coordinations=coordinations).filter(
            Q(application__in=self.request.GET.getlist('q_applications')) if self.request.GET.get('q_applications') else Q(),    
            Q(student__name__icontains=self.request.GET.get('q_student_name')) if self.request.GET.get('q_student_name') else Q(),
            Q(student__classes__in=self.request.GET.getlist('q_school_classes')) if self.request.GET.getlist('q_school_classes') else Q(),
            Q(
                Q(is_omr=True) | Q(start_time__isnull=False)
            ) if self.request.GET.get('q_application_start') else Q(),
        )
        
        applications_student_aggregations = applications_student.aggregate(
            total_file_answers=Count('file_answers', filter=Q(
                Q(file_answers__question__examquestion__in=self.get_exam_questions(exam)),
                Q(file_answers__arquivo__isnull=False),
                Q(file_answers__question__subject__in=q_subjects) if q_subjects else Q(),
            ), distinct=True),
            total_textual_answers=Count('textual_answers', filter=Q(
                Q(textual_answers__question__examquestion__in=self.get_exam_questions(exam)),
                Q(textual_answers__content__isnull=False),
                Q(textual_answers__question__subject__in=q_subjects) if q_subjects else Q(),
            ), distinct=True),
        )
        
        corrects_file_answers = FileAnswer.objects.filter(
            Q(question__examquestion__in=self.get_exam_questions(exam)),
            Q(student_application__in=applications_student),
            Q(teacher_grade__gte=Subquery(ExamQuestion.objects.filter(question=OuterRef(F'question'), exam=exam).values('weight')[:1])),
            Q(question__subject__in=q_subjects) if q_subjects else Q(),
        )
        corrects_textual_answers = TextualAnswer.objects.filter(
            Q(question__examquestion__in=self.get_exam_questions(exam)),
            Q(student_application__in=applications_student),
            Q(teacher_grade__gte=Subquery(ExamQuestion.objects.filter(question=OuterRef(F'question'), exam=exam).values('weight')[:1])),
            Q(question__subject__in=q_subjects) if q_subjects else Q(),
        )
        partial_correct_file_answers = FileAnswer.objects.filter(
            Q(question__examquestion__in=self.get_exam_questions(exam)),
            Q(student_application__in=applications_student),
            Q(teacher_grade__gt=0), 
            Q(teacher_grade__lt=Subquery(ExamQuestion.objects.filter(question=OuterRef(F'question'), exam=exam).values('weight')[:1])), 
            Q(question__subject__in=q_subjects) if q_subjects else Q(),
        )
        partial_correct_textual_answers = TextualAnswer.objects.filter(
            Q(question__examquestion__in=self.get_exam_questions(exam)),
            Q(student_application__in=applications_student),
            Q(teacher_grade__gt=0), 
            Q(teacher_grade__lt=Subquery(ExamQuestion.objects.filter(question=OuterRef(F'question'), exam=exam).values('weight')[:1])), 
            Q(question__subject__in=q_subjects) if q_subjects else Q(),
        )
        
        data['total_file_answers'] = applications_student_aggregations.get('total_file_answers', 0)
        data['total_textual_answers'] = applications_student_aggregations.get('total_textual_answers', 0)
        data['total_discursive_answers'] = data['total_file_answers'] + data['total_textual_answers']
        data['total_correct_discursive_answers'] = corrects_file_answers.count() + corrects_textual_answers.count()
        data['total_partial_correct_discursive_answers'] = partial_correct_file_answers.count() + partial_correct_textual_answers.count()
        
        return Response(data=data, status=status.HTTP_200_OK)
    