from decimal import Decimal
from django.utils import timezone

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q, Value, Count, Avg, DecimalField, OuterRef, Subquery
from django.db.models.functions import Coalesce, Cast

from fiscallizeon.exams.models import Exam
from fiscallizeon.applications.models import Application

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from fiscallizeon.core.utils import CheckHasPermission
from django.conf import settings
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

def get_text(type, short=False):
    message = ''
    if type == 'elaborações':
        message = 'elaborações de cadernos'
    elif type == 'revisões':
        message = 'revisões de cadernos'
    elif type == 'liberações':
        message = 'liberações para professores'
    elif type == 'resultados':
        message = 'liberação dos resultados para os alunos'
    elif type == 'correções':
        message = 'correções de respostas'
    elif type == 'uploads':
        message = 'upload de cartões'
        
    return message

class CalendarViewSet(LoginRequiredMixin, CheckHasPermission, viewsets.GenericViewSet):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    @action(detail=True, methods=['GET'])
    def get_calendar(self, request, pk=None):
        month = pk
        user = self.request.user
        year = timezone.now().year
        unity_id = self.request.GET.get('unity')
        stage_id = self.request.GET.get('stage')
        
        exams = Exam.objects.filter(
            Q(coordinations__in=user.get_coordinations_cache()),
            Q(coordinations__unity=unity_id) if unity_id else Q(),
            Q(teaching_stage=stage_id) if stage_id else Q(),
            Q(
                Q(elaboration_deadline__month=month, elaboration_deadline__year=year) |
                Q(review_deadline__month=month, review_deadline__year=year) |
                Q(release_elaboration_teacher__month=month, release_elaboration_teacher__year=year)
            )
        ).distinct()
        
        applications = Application.objects.filter(
            Q(exam__coordinations__in=user.get_coordinations_cache()),
            Q(exam__coordinations__unity=unity_id) if unity_id else Q(),
            Q(exam__teaching_stage=stage_id) if stage_id else Q(),
            Q(
                Q(student_stats_permission_date__month=month, student_stats_permission_date__year=year) |
                Q(deadline_for_correction_of_responses__month=month, deadline_for_correction_of_responses__year=year) |
                Q(deadline_for_sending_response_letters__month=month, deadline_for_sending_response_letters__year=year)
            )
        ).distinct()
        
        # Agrupar por prazos e contar a quantidade de cadernos para cada data
        elaboration_group = exams.filter(elaboration_deadline__month=month).values('elaboration_deadline').annotate(
            count=Count('id', distinct=True),
            deadline=F('elaboration_deadline'),
            type=Value('elaborações'),
            text=Value(get_text('elaborações')),
            color=Value('#0C7BDB'),
        ).order_by('elaboration_deadline').values('count', 'deadline', 'type', 'text', 'color')
        
        review_group = exams.filter(review_deadline__month=month).values('review_deadline').annotate(
            count=Count('id', distinct=True),
            deadline=F('review_deadline'),
            type=Value('revisões'),
            text=Value(get_text('revisões')),
            color=Value('#F3B364'),
        ).order_by('review_deadline').values('count', 'deadline', 'type', 'text', 'color')
        
        release_group = exams.filter(release_elaboration_teacher__month=month).values('release_elaboration_teacher').annotate(
            count=Count('id', distinct=True),
            deadline=F('release_elaboration_teacher'),
            type=Value('liberações'),
            text=Value(get_text('liberações')),
            color=Value('#41C588'),
        ).order_by('release_elaboration_teacher').values('count', 'deadline', 'type', 'text', 'color')
        
        release_student_result_group = applications.filter(student_stats_permission_date__month=month).values('student_stats_permission_date__date').annotate(
            count=Count('id', distinct=True),
            deadline=F('student_stats_permission_date__date'),
            type=Value('resultados'),
            text=Value(get_text('resultados')),
            color=Value('#2D2A77'),
        ).order_by('student_stats_permission_date__date').values('count', 'deadline', 'type', 'text', 'color')
        
        corrections_group = applications.filter(deadline_for_correction_of_responses__month=month).values('deadline_for_correction_of_responses').annotate(
            count=Count('id', distinct=True),
            deadline=F('deadline_for_correction_of_responses'),
            type=Value('correções'),
            text=Value(get_text('correções')),
            color=Value('#F26F51'),
        ).order_by('deadline_for_correction_of_responses').values('count', 'deadline', 'type', 'text', 'color')
        
        upload_group = applications.filter(deadline_for_sending_response_letters__month=month).values('deadline_for_sending_response_letters').annotate(
            count=Count('id', distinct=True),
            deadline=F('deadline_for_sending_response_letters'),
            type=Value('uploads'),
            text=Value(get_text('uploads')),
            color=Value('#F89724'),
        ).order_by('deadline_for_sending_response_letters').values('count', 'deadline', 'type', 'text', 'color')
        
        items = elaboration_group.union(review_group).union(release_group).union(release_student_result_group).union(corrections_group).union(upload_group)
        
        return Response(items)
    
    @action(detail=True, methods=['GET'])
    def get_teacher_calendar(self, request, pk=None):
        month = pk
        user = self.request.user
        teacher = user.inspector if hasattr(user, 'inspector') else None
        year = timezone.now().year
        unity_id = self.request.GET.get('unity')
            
        stage_id = self.request.GET.get('stage')
        
        def get_text(type, short=False):
            message = ''
            if type == 'elaborações':
                message = 'elaborações de cadernos'
            elif type == 'revisões':
                message = 'revisões de cadernos'
            elif type == 'liberações':
                message = 'liberações de cadernos'
            elif type == 'resultados':
                message = 'liberação dos resultados para os alunos'
            elif type == 'correções':
                message = 'correções de respostas'
                
            return message
        
        exams = Exam.objects.filter(
            Q(coordinations__in=user.get_coordinations_cache()),
            Q(teacher_subjects__teacher=teacher) if teacher else Q(),
            Q(coordinations__unity=unity_id) if unity_id else Q(),
            Q(teaching_stage=stage_id) if stage_id else Q(),
            Q(
                Q(elaboration_deadline__month=month, elaboration_deadline__year=year) |
                Q(review_deadline__month=month, review_deadline__year=year) |
                Q(release_elaboration_teacher__month=month, release_elaboration_teacher__year=year)
            )
        ).distinct()
        
        applications = Application.objects.filter(
            Q(exam__coordinations__in=user.get_coordinations_cache()),
            Q(exam__teacher_subjects__teacher=teacher) if teacher else Q(),
            Q(exam__coordinations__unity=unity_id) if unity_id else Q(),
            Q(exam__teaching_stage=stage_id) if stage_id else Q(),
            Q(
                Q(student_stats_permission_date__month=month, student_stats_permission_date__year=year) |
                Q(deadline_for_correction_of_responses__month=month, deadline_for_correction_of_responses__year=year) |
                Q(deadline_for_sending_response_letters__month=month, deadline_for_sending_response_letters__year=year)
            )
        ).distinct()
        
        if user.user_type == settings.TEACHER:
            exams = exams.filter(teacher_subjects__teacher=user.inspector)
            applications = applications.filter(exam__teacher_subjects__teacher=user.inspector)
        
        # Agrupar por prazos e contar a quantidade de cadernos para cada data
        elaboration_group = exams.filter(elaboration_deadline__month=month).values('elaboration_deadline').annotate(
            count=Count('id', distinct=True),
            deadline=F('elaboration_deadline'),
            type=Value('elaborações'),
            text=Value(get_text('elaborações')),
            color=Value('#0C7BDB'),
        ).order_by('elaboration_deadline').values('count', 'deadline', 'type', 'text', 'color')
        
        review_group = exams.filter(review_deadline__month=month).values('review_deadline').annotate(
            count=Count('id', distinct=True),
            deadline=F('review_deadline'),
            type=Value('revisões'),
            text=Value(get_text('revisões')),
            color=Value('#F3B364'),
        ).order_by('review_deadline').values('count', 'deadline', 'type', 'text', 'color')
        
        release_group = exams.filter(release_elaboration_teacher__month=month).values('release_elaboration_teacher').annotate(
            count=Count('id', distinct=True),
            deadline=F('release_elaboration_teacher'),
            type=Value('liberações'),
            text=Value(get_text('liberações')),
            color=Value('#41C588'),
        ).order_by('release_elaboration_teacher').values('count', 'deadline', 'type', 'text', 'color')
        
        release_student_result_group = applications.filter(student_stats_permission_date__month=month).values('student_stats_permission_date__date').annotate(
            count=Count('id', distinct=True),
            deadline=F('student_stats_permission_date__date'),
            type=Value('resultados'),
            text=Value(get_text('resultados')),
            color=Value('#2D2A77'),
        ).order_by('student_stats_permission_date__date').values('count', 'deadline', 'type', 'text', 'color')
        
        corrections_group = applications.filter(deadline_for_correction_of_responses__month=month).values('deadline_for_correction_of_responses').annotate(
            count=Count('id', distinct=True),
            deadline=F('deadline_for_correction_of_responses'),
            type=Value('correções'),
            text=Value(get_text('correções')),
            color=Value('#F26F51'),
        ).order_by('deadline_for_correction_of_responses').values('count', 'deadline', 'type', 'text', 'color')
        
        items = elaboration_group.union(review_group).union(release_group).union(release_student_result_group).union(corrections_group)
        
        return Response(items)
    
    @action(detail=False, methods=['POST'])
    def get_summary(self, request, pk=None):
        
        user = self.request.user
        event = self.request.data
        year = timezone.now().year
        unity_id = self.request.GET.get('unity')
        stage_id = self.request.GET.get('stage')
        deadline = event.get('deadline')
        teacher = user.inspector if hasattr(user, 'inspector') else None
        type = event.get('type')
        
        if type in ['elaborações', 'revisões', 'liberações']:
            exams = Exam.objects.filter(
                Q(coordinations__in=user.get_coordinations_cache()),
                Q(coordinations__unity=unity_id) if unity_id else Q(),
                Q(teaching_stage=stage_id) if stage_id else Q(),
                Q(
                    Q(elaboration_deadline=deadline) if type == 'elaborações' else Q(),
                    Q(review_deadline=deadline) if type == 'revisões' else Q(),
                    Q(release_elaboration_teacher=deadline) if type == 'liberações' else Q(),
                )
            )
            
            if teacher:
                exams = exams.filter(teacher_subjects__teacher=teacher) if teacher else Q()
                        
            return Response({
                'text': get_text(type),
                'items': exams.annotate(
                    questions_count=Count('questions', distinct=True),
                ).values('id', 'name', 'questions_count').distinct()
            })
            
        if type in ['resultados', 'correções', 'uploads']:
            applications = Application.objects.filter(
                Q(exam__coordinations__in=user.get_coordinations_cache()),
                Q(exam__coordinations__unity=unity_id) if unity_id else Q(),
                Q(exam__teaching_stage=stage_id) if stage_id else Q(),
                Q(
                    Q(student_stats_permission_date__date=deadline) if type == 'resultados' else Q(),
                    Q(deadline_for_correction_of_responses=deadline) if type == 'correções' else Q(),
                    Q(deadline_for_sending_response_letters=deadline) if type == 'uploads' else Q(),
                )
            )
            
            if teacher:
                applications = applications.filter(exam__teacher_subjects__teacher=teacher) if teacher else Q()
        
            return Response({
                'text': get_text(type),
                'items': applications.annotate(
                    name=F('exam__name'),
                    questions_count=Count('exam__questions', distinct=True),
                ).values('id', 'name', 'questions_count').distinct()
            })
            
        return Response(status=status.HTTP_400_BAD_REQUEST)