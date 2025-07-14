import uuid
from datetime import datetime

from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework import status

from django.conf import settings
from django.db.models import Q, Value, Exists, Avg, F, Subquery, OuterRef, Count, Sum, Case, When, DateTimeField
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin

from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.analytics.models import ClassSubjectApplicationLevel
from fiscallizeon.analytics.api.serializers.widgets import ExamQuestionsSumarySerializer
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.core.utils import CheckHasPermission, SimpleAPIPagination
from fiscallizeon.exams.models import Exam, ExamQuestion, ExamTeacherSubject, StatusQuestion
from fiscallizeon.inspectors.models import Inspector, TeacherSubject
from fiscallizeon.subjects.models import Subject
from fiscallizeon.exams.serializers.exams import TagsCountSerializer
from fiscallizeon.clients.models import QuestionTag
from fiscallizeon.students.models import Student
from fiscallizeon.omr.models import  OMRStudents, OMRDiscursiveScan
from fiscallizeon.analytics.tasks import export_admin_dashboard

def get_applications(request):
    application_pks = list(ClassSubjectApplicationLevel.objects.filter_request(
            request=request
        ).values_list(
            'application__pk', flat=True
        ).order_by(
            'application__date', 'application__start'
        ).distinct()
    )

    queryset = Application.objects.filter(
        pk__in=application_pks
    )

    return queryset.distinct()


class CoordinationWidgetsSummaryAPIWiew(LoginRequiredMixin, CheckHasPermission, APIView):
    renderer_classes = [JSONRenderer]
    required_permissions = ['coordination']
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get(self, request, *args, **kwargs):

        queryset = get_applications(request)

        result = ClassSubjectApplicationLevel.objects.all().get_performance(
            request=request
        )

        application_student = ApplicationStudent.objects.filter(
            Q(application__in=list(queryset)),
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
        ).distinct()

        school_classes = request.GET.getlist("q_classes")
        stage = request.GET.get("q_stage", None)
        unitys = request.GET.getlist('q_unitys')
        grades = request.GET.getlist('q_grades')
        subjects = request.GET.getlist('q_subjects')
        stage = request.GET.getlist('q_stage')

        if school_classes and not school_classes[0] == '':
            application_student = application_student.filter(
                student__classes__in=school_classes
            )

        if stage and not stage[0] == '' or stage == 0 :
            application_student = application_student.filter(
                student__classes__grade__level=int(stage[0])
            )

        if unitys and not unitys[0] == '':
            application_student = application_student.filter(
                student__classes__coordination__unity__in=unitys
            )

        if grades and not grades[0] == '':
            application_student = application_student.filter(
                student__classes__grade__in=grades
            )

        all_exam_questions = set(list(queryset.values_list('exam__examquestion__pk', flat=True)))
            
        exam_questions = ExamQuestion.objects.filter(
            pk__in=all_exam_questions
        ).availables()  

        if subjects and not subjects[0] == '':
            exam_questions = exam_questions.filter(
                exam_teacher_subject__teacher_subject__subject__in=subjects
            )

        return Response(status=status.HTTP_200_OK, 
            data= {
                "applications_count": queryset.count(),
                "questions_count": exam_questions.count(),
                "students_count": application_student.count(),
                "applications_avarage": 
                    ClassSubjectApplicationLevel.objects.all().get_performance(
                        request=request
                    ),
            }, content_type="application/json")
        
class ExamsWidgetsSummaryAPIWiew(LoginRequiredMixin, CheckHasPermission, APIView):
    renderer_classes = [JSONRenderer]
    required_permissions = [settings.COORDINATION]
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get(self, request, *args, **kwargs):
        user = self.request.user
        
        # Filters
        teachers = request.GET.getlist("q_teachers")
        subjects = request.GET.getlist('q_subjects')
        teaching_stages = request.GET.getlist('q_teaching_stages')
        education_systems = request.GET.getlist('q_education_systems')
        year = request.GET.get('year', None)
        segments = request.GET.getlist('q_segments')
        initial_date = request.GET.get('q_initial_date', None)
        final_date = request.GET.get('q_final_date', None)

        exams = Exam.objects.filter(
            Q(coordinations__in=user.get_coordinations_cache()),
            Q(teacher_subjects__subject__in=subjects) if subjects else Q(),
            Q(teacher_subjects__teacher__in=teachers) if teachers else Q(),
            Q(teaching_stage__in=teaching_stages) if teaching_stages else Q(),
            Q(education_system__in=education_systems) if education_systems else Q(),
            Q(examteachersubject__grade__level__in=segments) if segments else Q(),
            Q(created_at__gte=initial_date) if initial_date else Q(),
            Q(created_at__lte=final_date) if final_date else Q(),
        ).exclude(is_abstract=True).distinct()
        
        
        if self.request.GET.get('get_tme'):
            
            exam_questions_subquery = ExamQuestion.objects.filter(
                Q(exam__pk=OuterRef('pk')),
                Q(exam_teacher_subject__teacher_subject__subject__in=subjects) if subjects else Q(),
                Q(exam_teacher_subject__teacher_subject__teacher__in=teachers) if teachers else Q(),
            )
            
            exams_aggregations = exams.filter(Q(created_at__year=year) if year else Q()).annotate(
                tme_start_time=Subquery(exam_questions_subquery.order_by('created_at').values('created_at')[:1]),
                tmt_start_time=Case(
                    When(
                        Q(release_elaboration_teacher__isnull=False),
                        then=F('release_elaboration_teacher')
                    ),
                    default=Subquery(exam_questions_subquery.order_by('created_at').values('created_at')[:1]),
                    output_field=DateTimeField()
                ),
                end_time=Subquery(exam_questions_subquery.order_by('-created_at').values('created_at')[:1]),
            ).aggregate(
                tme=Avg(F('end_time') - F('tme_start_time')),
                tmt=Avg(F('end_time') - F('tmt_start_time'))
            )
            return Response(status=status.HTTP_200_OK, data={
                    "tme": exams_aggregations.get('tme') or 0,
                    "tmt": exams_aggregations.get('tmt') or 0,
                }, 
                content_type="application/json"
            )
            
        exam_questions = ExamQuestion.objects.filter(
            Q(exam__in=exams),
            Q(exam_teacher_subject__teacher_subject__subject__in=subjects) if subjects else Q(),
            Q(exam_teacher_subject__teacher_subject__teacher__in=teachers) if teachers else Q(),
            Q(exam_teacher_subject__grade__level__in=segments) if segments else Q(),
        ).exclude(is_abstract=True).distinct()
        
        common_filters_statusquestion = Q(
            Q(statusquestion__created_at__year=year) if year else Q(),
            Q(statusquestion__active=True),
        )
        
        exam_questions_aggregations = exam_questions.annotate(
            approveds=Count('pk', filter=Q(common_filters_statusquestion, statusquestion__status=StatusQuestion.APPROVED), distinct=True),
            reproveds=Count('pk', filter=Q(common_filters_statusquestion, statusquestion__status=StatusQuestion.REPROVED), distinct=True),
            correcteds=Count('pk', filter=Q(common_filters_statusquestion, statusquestion__status=StatusQuestion.CORRECTED), distinct=True),
            annuleds=Count('pk', filter=Q(common_filters_statusquestion, statusquestion__status=StatusQuestion.ANNULLED), distinct=True),
            correction_pendings=Count('pk', filter=Q(Q(statusquestion__created_at__year=year) if year else Q(), Q(statusquestion__status=StatusQuestion.CORRECTION_PENDING)), distinct=True),
            use_later=Count('pk', filter=Q(common_filters_statusquestion, statusquestion__status=StatusQuestion.USE_LATER), distinct=True),
            lates=Count('pk', filter=Q(Q(created_at__year=year) if year else Q(), Q(is_late=True)), distinct=True),
        ).aggregate(
            Sum('approveds'),
            Sum('reproveds'),
            Sum('correcteds'),
            Sum('annuleds'),
            Sum('correction_pendings'),
            Sum('use_later'),
            Sum('lates'),
        )
        
        # Filtrar os exams e examquestions do ano atual
        exam_questions = exam_questions.filter(
            Q(created_at__year=year) if year else Q()
        )
        exams = exams.filter(
            Q(created_at__year=year) if year else Q()
        )
        
        data = {
            "exams": {
                "count": exams.count(),
                "elaborating": exams.filter(status=Exam.ELABORATING).exclude(application__isnull=False).count(),
                "opened": exams.filter(status=Exam.OPENED).exclude(application__isnull=False).count(),
                "closed": exams.filter(Q(status=Exam.CLOSED) | Q(application__isnull=False)).count(),
                "send_review": exams.filter(status=Exam.SEND_REVIEW).exclude(application__isnull=False).count(),
                "text_review": exams.filter(status=Exam.TEXT_REVIEW).count(),
                "is_printed_count": exams.filter(is_printed=True).exclude(application__isnull=False).count(),
                "late": exams.filter(status=Exam.ELABORATING, elaboration_deadline__lt=timezone.now()).exclude(application__isnull=False).count(),
            },
            "questions": {
                "count": exam_questions.count(),
                "approved": exam_questions_aggregations.get('approveds__sum') or 0,
                "reproved": exam_questions_aggregations.get('reproveds__sum') or 0,
                "correction_pending": exam_questions_aggregations.get('correction_pendings__sum') or 0,
                "use_later": exam_questions_aggregations.get('use_later__sum') or 0,
                "annuled": exam_questions_aggregations.get('annuleds__sum') or 0,
                "lates": exam_questions_aggregations.get('lates__sum') or 0,
            }
        }

        data['questions']['opened'] = data['questions']['count'] - (data['questions']['approved'] + data['questions']['reproved'] + data['questions']['correction_pending'] + data['questions']['use_later'] + data['questions']['annuled'])
        
        return Response(status=status.HTTP_200_OK, data=data, content_type="application/json")

class TeachersSummaryAPIWiew(LoginRequiredMixin, CheckHasPermission, APIView):
    renderer_classes = [JSONRenderer]
    required_permissions = [settings.COORDINATION]
    authentication_classes = (CsrfExemptSessionAuthentication, )        
    
    def get(self, request, *args, **kwargs):
        user = self.request.user
        
        # Filters
        teachers = request.GET.getlist("q_teachers")
        subjects = request.GET.getlist('q_subjects')
        teaching_stages = request.GET.getlist('q_teaching_stages')
        education_systems = request.GET.getlist('q_education_systems')
        year = request.GET.get('year', None)
        segments = request.GET.getlist('q_segments')
        order_by = request.GET.get('order_by', None)
        desc = request.GET.get('desc', None)
        initial_date = request.GET.get('q_initial_date', None)
        final_date = request.GET.get('q_final_date', None)
        
        exam_questions = ExamQuestion.objects.filter(
            Q(exam_teacher_subject__teacher_subject__subject__in=subjects) if subjects else Q(),
            Q(exam_teacher_subject__teacher_subject__teacher__in=teachers) if teachers else Q(),
            Q(created_at__year=year) if year else Q(),
            Q(exam_teacher_subject__created_at__gte=initial_date) if initial_date else Q(),
            Q(exam_teacher_subject__created_at__lte=final_date) if final_date else Q(),
            Q(exam_teacher_subject__grade__level__in=segments) if segments else Q(),
        ).exclude(is_abstract=True).distinct()

        teachers_queryset = Inspector.objects.filter(
            Q(coordinations__in=user.get_coordinations_cache()),
            Q(pk__in=teachers) if teachers else Q(),
            Q(teachersubject__subject__in=subjects) if subjects else Q(),
            Q(teachersubject__examteachersubject__grade__level__in=segments) if segments else Q(),
        ).annotate(
            questions_count=Count('teachersubject__examteachersubject__examquestion', filter=Q(
                Q(teachersubject__examteachersubject__examquestion__is_abstract=False),
                Q(teachersubject__examteachersubject__examquestion__created_at__year=year) if year else Q(),
                Q(teachersubject__examteachersubject__examquestion__exam_teacher_subject__grade__level__in=segments) if segments else Q(),
                Q(teachersubject__examteachersubject__examquestion__exam_teacher_subject__teacher_subject__subject__in=subjects) if subjects else Q(),
            ), distinct=True)
        ).order_by('-questions_count', 'name').distinct()
        
        if order_by:
            questions_common_filters = Q(
                Q(teachersubject__examteachersubject__examquestion__statusquestion__active=True),
                Q(teachersubject__examteachersubject__examquestion__created_at__year=year) if year else Q(),
                Q(teachersubject__examteachersubject__examquestion__statusquestion__created_at__gte=initial_date) if initial_date else Q(),
                Q(teachersubject__examteachersubject__examquestion__statusquestion__created_at__lte=final_date) if final_date else Q(),
            )
            exams_common_filters = Q(
                Q(teachersubject__examteachersubject__exam__teaching_stage__in=teaching_stages) if teaching_stages else Q(),
                Q(teachersubject__examteachersubject__exam__education_system__in=education_systems) if education_systems else Q(),
                Q(teachersubject__examteachersubject__exam__created_at__year=year) if year else Q(),
                Q(teachersubject__examteachersubject__exam__created_at__gte=initial_date) if initial_date else Q(),
                Q(teachersubject__examteachersubject__exam__created_at__lte=final_date) if final_date else Q(),
                Q(teachersubject__examteachersubject__grade__level__in=segments) if segments else Q(),
            )
            
            # Questions annotations
            teachers_queryset = teachers_queryset.annotate(
                teacher_questions_seens=Count('teachersubject__examteachersubject__examquestion', filter=Q(
                    Q(teachersubject__examteachersubject__examquestion__created_at__year=year) if year else Q(),
                    Q(teachersubject__examteachersubject__examquestion__statusquestion__status=StatusQuestion.SEEN)
                ), distinct=True),
                teacher_questions_approveds=Count('teachersubject__examteachersubject__examquestion', filter=Q(
                    Q(teachersubject__examteachersubject__examquestion__statusquestion__status=StatusQuestion.APPROVED), 
                    questions_common_filters
                ), distinct=True),
                teacher_questions_reproveds=Count('teachersubject__examteachersubject__examquestion', filter=Q(
                    Q(teachersubject__examteachersubject__examquestion__statusquestion__status=StatusQuestion.REPROVED), 
                    questions_common_filters
                ), distinct=True),
                teacher_questions_lates=Count('teachersubject__examteachersubject__examquestion', filter=Q(Q(teachersubject__examteachersubject__examquestion__is_late=True), Q(created_at__year=year) if year else Q()), distinct=True),
                teacher_questions_annuleds=Count('teachersubject__examteachersubject__examquestion', filter=Q(Q(teachersubject__examteachersubject__examquestion__statusquestion__status=StatusQuestion.ANNULLED), questions_common_filters), distinct=True),
                teacher_questions_use_later=Count('teachersubject__examteachersubject__examquestion', filter=Q(Q(teachersubject__examteachersubject__examquestion__statusquestion__status=StatusQuestion.USE_LATER), questions_common_filters), distinct=True),
                teacher_questions_correction_pending=Count('teachersubject__examteachersubject__examquestion', filter=Q(
                    Q(teachersubject__examteachersubject__examquestion__statusquestion__status=StatusQuestion.CORRECTION_PENDING), 
                    questions_common_filters
                ), distinct=True)
            )
            
            # Exams annotations
            teachers_queryset = teachers_queryset.annotate(
                teacher_exams_elaborating=Count('teachersubject__examteachersubject__exam', filter=Q(
                    Q(teachersubject__examteachersubject__exam__status=Exam.ELABORATING, teachersubject__examteachersubject__exam__application__isnull=True),
                    Q(exams_common_filters)
                ), distinct=True) if order_by == 'teacher_exams_elaborating' else Value(0),
                teacher_exams_opened=Count('teachersubject__examteachersubject__exam', filter=Q(
                    Q(teachersubject__examteachersubject__exam__status=Exam.OPENED, teachersubject__examteachersubject__exam__application__isnull=True),
                    Q(exams_common_filters)
                ), distinct=True) if order_by == 'teacher_exams_opened' else Value(0),
                teacher_exams_send_review=Count('teachersubject__examteachersubject__exam', filter=Q(
                    Q(teachersubject__examteachersubject__exam__status=Exam.SEND_REVIEW, teachersubject__examteachersubject__exam__application__isnull=True),
                    Q(exams_common_filters)
                ), distinct=True) if order_by == 'teacher_exams_send_review' else Value(0),
                teacher_exams_closed=Count('teachersubject__examteachersubject__exam', filter=Q(
                    Q(teachersubject__examteachersubject__exam__status=Exam.CLOSED),
                    Q(exams_common_filters)
                ), distinct=True) if order_by == 'teacher_exams_closed' else Value(0),
                teacher_exams_is_printed=Count('teachersubject__examteachersubject__exam', filter=Q(
                    Q(teachersubject__examteachersubject__exam__is_printed=True),
                    Q(exams_common_filters)
                ), distinct=True) if order_by == 'teacher_exams_is_printed' else Value(0),
                teacher_exams_lates=Count('teachersubject__examteachersubject__exam', filter=Q(
                    Q(teachersubject__examteachersubject__exam__examquestion__is_late=True),
                    Q(exams_common_filters)
                ), distinct=True) if order_by == 'teacher_exams_lates' else Value(0),
            )
            

            teachers_queryset = teachers_queryset.order_by(f'{"-" if desc else ""}{order_by}')
            
        else:
            teachers_queryset = teachers_queryset.annotate(
                questions_count=Count('teachersubject__examteachersubject__examquestion', distinct=True)
            ).order_by('-questions_count', 'name').distinct()
        
        paginator = SimpleAPIPagination()
        instances = paginator.paginate_queryset(teachers_queryset, request)
        
        teachers_data = []
        
        if self.request.GET.get('get_questions'):
            
            for teacher in instances:
                
                exam_teacher_subjects = ExamTeacherSubject.objects.filter(teacher_subject__teacher=teacher).distinct()
                
                exam_questions = ExamQuestion.objects.filter(
                    Q(exam_teacher_subject__in=exam_teacher_subjects),
                    Q(exam__teaching_stage__in=teaching_stages) if teaching_stages else Q(),
                    Q(exam__education_system__in=education_systems) if education_systems else Q(),
                    Q(exam_teacher_subject__grade__level__in=segments) if segments else Q(),
                    Q(statusquestion__created_at__gte=initial_date) if initial_date else Q(),
                    Q(statusquestion__created_at__lte=final_date) if final_date else Q(),
                ).exclude(is_abstract=True).distinct()
                
                common_filters_statusquestion = Q(
                    Q(statusquestion__created_at__year=year) if year else Q(),
                    Q(statusquestion__active=True),
                )
                
                data = {
                    "name": teacher.__str__(),
                    "id": teacher.pk,
                    "questions": {
                        "count": exam_questions.filter(Q(created_at__year=year) if year else Q()).count(),
                        "approved": exam_questions.filter(common_filters_statusquestion, Q(statusquestion__status=StatusQuestion.APPROVED)).distinct().count(),
                        "reproved": exam_questions.filter(common_filters_statusquestion, Q(statusquestion__status=StatusQuestion.REPROVED)).distinct().count(),
                        "correction_pending": exam_questions.filter(common_filters_statusquestion, Q(statusquestion__status=StatusQuestion.CORRECTION_PENDING)).distinct().count(),
                        "use_later": exam_questions.filter(common_filters_statusquestion, Q(statusquestion__status=StatusQuestion.USE_LATER)).distinct().count(),
                        "corrected": exam_questions.filter(common_filters_statusquestion, Q(statusquestion__status=StatusQuestion.CORRECTED)).distinct().count(),
                        "annuled": exam_questions.filter(common_filters_statusquestion, Q(statusquestion__status=StatusQuestion.ANNULLED)).distinct().count(),
                        "seen": exam_questions.filter(Q(statusquestion__created_at__year=year) if year else Q(), Q(statusquestion__status=StatusQuestion.SEEN)).distinct().count(),
                        "lates": exam_questions.filter(Q(created_at__year=year) if year else Q(), Q(is_late=True)).distinct().count(),
                    }
                }
                teachers_data.append(data)
        
        if self.request.GET.get('get_exams'):
            
            for teacher in instances:
                
                exams = Exam.objects.filter(
                    Q(teacher_subjects__in=teacher.teachersubject_set.filter(Q(subject__in=subjects) if subjects else Q())),
                    Q(teaching_stage__in=teaching_stages) if teaching_stages else Q(),
                    Q(education_system__in=education_systems) if education_systems else Q(),
                    Q(created_at__year=year) if year else Q(),
                    Q(created_at__gte=initial_date) if initial_date else Q(),
                    Q(created_at__lte=final_date) if final_date else Q(),
                    Q(examteachersubject__grade__level__in=segments) if segments else Q(),
                ).annotate(
                    tme_start_time=Subquery(ExamQuestion.objects.filter(exam__pk=OuterRef('pk'), exam_teacher_subject__teacher_subject__in=teacher.teachersubject_set.all()).order_by('created_at').values('created_at')[:1]),
                    tmt_start_time=Case(
                        When(
                            Q(release_elaboration_teacher__isnull=False),
                            then=F('release_elaboration_teacher')
                        ),
                        default=Subquery(ExamQuestion.objects.filter(exam__pk=OuterRef('pk'), exam_teacher_subject__teacher_subject__in=teacher.teachersubject_set.all()).order_by('created_at').values('created_at')[:1]),
                        output_field=DateTimeField()
                    ),
                    end_time=Subquery(ExamQuestion.objects.filter(exam__pk=OuterRef('pk'), exam_teacher_subject__teacher_subject__in=teacher.teachersubject_set.all()).order_by('-created_at').values('created_at')[:1]),
                ).exclude(is_abstract=True).distinct()
                
                data = {
                    "name": teacher.__str__(),
                    "id": teacher.pk,
                    "exams": {
                        "count": exams.count(),
                        "elaborating": exams.filter(status=Exam.ELABORATING).exclude(application__isnull=False).count(),
                        "opened": exams.filter(status=Exam.OPENED).exclude(application__isnull=False).count(),
                        "closed": exams.filter(Q(status=Exam.CLOSED) | Q(application__isnull=False)).count(),
                        "send_review": exams.filter(status=Exam.SEND_REVIEW).exclude(application__isnull=False).count(),
                        "lates": exams.filter(examquestion__created_at__gt=F('elaboration_deadline')).distinct().count(),
                        "is_printed": exams.filter(is_printed=True).distinct().count(),
                        "tme": exams.aggregate(tme=Avg(F('end_time') - F('tme_start_time'))).get('tme') or 0,
                        "tmt": exams.aggregate(tmt=Avg(F('end_time') - F('tmt_start_time'))).get('tmt') or 0,
                    },
                }
                
                teachers_data.append(data)
                
        return paginator.get_paginated_response(teachers_data)

class SubjectsSummaryAPIWiew(LoginRequiredMixin, CheckHasPermission, APIView):
    renderer_classes = [JSONRenderer]
    required_permissions = [settings.COORDINATION]
    authentication_classes = (CsrfExemptSessionAuthentication, )        
    
    def get(self, request, *args, **kwargs):
        """ 
            Ao passar o parametro (subject_id e only_lates) 
            a API deve retornar apenas os cadernos que estão atrasados de cada disciplina 
        """
        
        user = self.request.user
        
        # Filters
        teachers = request.GET.getlist("q_teachers")
        subjects = request.GET.getlist('q_subjects')
        teaching_stages = request.GET.getlist('q_teaching_stages')
        education_systems = request.GET.getlist('q_education_systems')
        year = request.GET.get('year', None)
        segments = request.GET.getlist('q_segments')
        order_by = request.GET.get('order_by', None)
        desc = request.GET.get('desc', None)
        initial_date = request.GET.get('q_initial_date', None)
        final_date = request.GET.get('q_final_date', None)
        
        exams = Exam.objects.filter(
            Q(coordinations__in=user.get_coordinations_cache()),
            Q(teaching_stage__in=teaching_stages) if teaching_stages else Q(),
            Q(education_system__in=education_systems) if education_systems else Q(),
            Q(created_at__year=year) if year else Q(),
            Q(created_at__gte=initial_date) if initial_date else Q(),
            Q(created_at__lte=final_date) if final_date else Q(),
            Q(examteachersubject__grade__level__in=segments) if segments else Q(),
        ).annotate(
            tmt_start_time=Case(
                When(
                    Q(release_elaboration_teacher__isnull=False),
                    then=F('release_elaboration_teacher')
                ),
                default=Subquery(ExamQuestion.objects.filter(exam__pk=OuterRef('pk')).order_by('created_at').values('created_at')[:1]),
                output_field=DateTimeField()
            ),
            end_time=Subquery(ExamQuestion.objects.filter(exam__pk=OuterRef('pk')).order_by('-created_at').values('created_at')[:1]),
        ).exclude(is_abstract=True).distinct()
        
        teacher_subjects = TeacherSubject.objects.filter(
            Q(examteachersubject__exam__in=exams),
            Q(teacher__in=teachers) if teachers else Q(),
            Q(subject__in=subjects) if subjects else Q(),
            # Q(school_year=year) if year else Q(),
            Q(examteachersubject__grade__level__in=segments) if segments else Q(),
        ).distinct()
        
        if self.request.GET.get('only_lates'): 
            subject_id = self.request.GET.get('subject_id')
            if not subject_id:
                return Response('É necessário indicar qual a disciplina através do parametro: subject_id', status=status.HTTP_400_BAD_REQUEST)
            
            try:
                filtred_exams = exams.filter(
                    Q(teacher_subjects__subject__id=subject_id),
                    Q(teacher_subjects__in=teacher_subjects),
                ).annotate(
                    lates=Exists(
                        ExamQuestion.objects.filter(
                            exam_teacher_subject__teacher_subject__subject=subject_id,
                            exam__pk=OuterRef('pk'), 
                            created_at__gt=OuterRef('elaboration_deadline')
                        ).distinct().exclude(is_abstract=True)
                    ),
                ).distinct()
                
            except Exception as e:
                return Response('Não foi possível encontrar a disciplina informada', status=status.HTTP_400_BAD_REQUEST)
            
            return Response(filtred_exams.filter(lates=True).count())
        
        subjects_queryset = Subject.objects.filter(
            Q(teachersubject__examteachersubject__exam__in=exams),
            Q(teachersubject__subject__in=subjects) if subjects else Q(),
            Q(teachersubject__in=teacher_subjects),
        ).annotate(
            questions_count=Count('teachersubject__examteachersubject__exam__examquestion', distinct=True),
        ).order_by('-questions_count').distinct()
        
        if order_by:
            questions_common_filters = Q(
                Q(teachersubject__examteachersubject__examquestion__statusquestion__active=True),
                Q(teachersubject__examteachersubject__examquestion__created_at__year=year) if year else Q(),
            )
            exams_common_filters = Q(
                Q(teachersubject__examteachersubject__exam__teaching_stage__in=teaching_stages) if teaching_stages else Q(),
                Q(teachersubject__examteachersubject__exam__education_system__in=education_systems) if education_systems else Q(),
                Q(teachersubject__examteachersubject__exam__created_at__year=year) if year else Q(),
                Q(teachersubject__examteachersubject__grade__level__in=segments) if segments else Q(),
            )
            
            # Questions annotations
            subjects_queryset = subjects_queryset.annotate(
                subject_teacher_questions_approveds=Count('teachersubject__examteachersubject__examquestion', filter=Q(Q(teachersubject__examteachersubject__examquestion__statusquestion__status=StatusQuestion.APPROVED), questions_common_filters), distinct=True) if order_by == 'subject_teacher_questions_approveds' else Value(0),
                subject_teacher_questions_reproveds=Count('teachersubject__examteachersubject__examquestion', filter=Q(Q(teachersubject__examteachersubject__examquestion__statusquestion__status=StatusQuestion.REPROVED), questions_common_filters), distinct=True) if order_by == 'subject_teacher_questions_reproveds' else Value(0),
                subject_teacher_questions_lates=Count('teachersubject__examteachersubject__examquestion', filter=Q(
                        Q(teachersubject__examteachersubject__examquestion__created_at__gt=F('teachersubject__examteachersubject__examquestion__exam__elaboration_deadline')),
                        Q(teachersubject__examteachersubject__examquestion__created_at__year=year) if year else Q()
                    ), distinct=True
                ) if order_by == 'subject_teacher_questions_lates' else Value(0),
                subject_teacher_questions_annuleds=Count('teachersubject__examteachersubject__examquestion', filter=Q(Q(teachersubject__examteachersubject__examquestion__statusquestion__status=StatusQuestion.ANNULLED), questions_common_filters), distinct=True) if order_by == 'subject_teacher_questions_annuleds' else Value(0),
                subject_teacher_questions_correction_pending=Count('teachersubject__examteachersubject__examquestion', filter=Q(
                    Q(teachersubject__examteachersubject__examquestion__statusquestion__status=StatusQuestion.CORRECTION_PENDING), 
                    questions_common_filters
                ), distinct=True) if order_by == 'subject_teacher_questions_correction_pending' else Value(0)
            )
            
            # Exams annotations
            subjects_queryset = subjects_queryset.annotate(
                subject_exams_elaborating=Count('teachersubject__examteachersubject__exam', filter=Q(
                    Q(teachersubject__examteachersubject__exam__status=Exam.ELABORATING, teachersubject__examteachersubject__exam__application__isnull=True),
                    Q(exams_common_filters)
                ), distinct=True) if order_by == 'subject_exams_elaborating' else Value(0),
                subject_exams_opened=Count('teachersubject__examteachersubject__exam', filter=Q(
                    Q(teachersubject__examteachersubject__exam__status=Exam.OPENED, teachersubject__examteachersubject__exam__application__isnull=True),
                    Q(exams_common_filters)
                ), distinct=True) if order_by == 'subject_exams_opened' else Value(0),
                subject_exams_send_review=Count('teachersubject__examteachersubject__exam', filter=Q(
                    Q(teachersubject__examteachersubject__exam__status=Exam.SEND_REVIEW, teachersubject__examteachersubject__exam__application__isnull=True),
                    Q(exams_common_filters)
                ), distinct=True) if order_by == 'subject_exams_send_review' else Value(0),
                subject_exams_closed=Count('teachersubject__examteachersubject__exam', filter=Q(
                    Q(teachersubject__examteachersubject__exam__status=Exam.CLOSED),
                    Q(exams_common_filters)
                ), distinct=True) if order_by == 'subject_exams_closed' else Value(0),
                subject_exams_lates=Count('teachersubject__examteachersubject__exam', filter=Q(
                    Q(
                        teachersubject__examteachersubject__exam__examquestion__is_abstract=False, 
                        teachersubject__examteachersubject__exam__examquestion__created_at__gt=F('teachersubject__examteachersubject__exam__elaboration_deadline')
                    ),
                    Q(exams_common_filters)
                ), distinct=True) if order_by == 'subject_exams_lates' else Value(0),
                subject_exams_is_printed=Count('teachersubject__examteachersubject__exam', filter=Q(
                    Q(teachersubject__examteachersubject__exam__is_printed=True),
                    Q(exams_common_filters)
                ), distinct=True) if order_by == 'subject_exams_is_printed' else Value(0),
            )
            subjects_queryset = subjects_queryset.order_by(f'{"-" if desc else ""}{order_by}')
        
        paginator = SimpleAPIPagination()
        instances = paginator.paginate_queryset(subjects_queryset, request)
        
        subjects_data = []
        
        for subject in instances:
            
            if self.request.GET.get('get_questions'):
                
                exam_questions = ExamQuestion.objects.filter(
                    Q(exam__in=exams),
                    Q(exam_teacher_subject__teacher_subject__subject=subject),
                    Q(exam_teacher_subject__teacher_subject__in=teacher_subjects),
                    Q(exam_teacher_subject__grade__level__in=segments) if segments else Q(),
                    Q(created_at__year=year) if year else Q()
                ).exclude(is_abstract=True).distinct()
                
                exam_questions_aggregations = exam_questions.annotate(
                    approveds=Count(
                        Subquery(
                            StatusQuestion.objects
                            .filter(
                                Q(created_at__gte=initial_date) if initial_date else Q(),
                                Q(created_at__lte=final_date) if final_date else Q(),
                                exam_question__pk=OuterRef('pk'),
                                status=StatusQuestion.APPROVED,
                                active=True
                            )
                            .order_by('-updated_at')
                            .values('pk')[:1]
                        ),
                        distinct=True
                    ),
                    reproveds=Count(
                        Subquery(
                            StatusQuestion.objects
                            .filter(
                                Q(updated_at__gte=initial_date) if initial_date else Q(),
                                Q(updated_at__lte=final_date) if final_date else Q(),
                                exam_question__pk=OuterRef('pk'),
                                status=StatusQuestion.REPROVED,
                                active=True
                            )
                            .order_by('-updated_at')
                            .values('pk')[:1]
                        ),
                        distinct=True
                    ),
                    correction_pendings=Count(
                        Subquery(
                            StatusQuestion.objects
                            .filter(
                                Q(updated_at__gte=initial_date) if initial_date else Q(),
                                Q(updated_at__lte=final_date) if final_date else Q(),
                                exam_question__pk=OuterRef('pk'),
                                status=StatusQuestion.CORRECTION_PENDING,
                                active=True
                            )
                            .order_by('-updated_at')
                            .values('pk')[:1]
                        ),
                        distinct=True
                    ),
                    correcteds=Count(
                        Subquery(
                            StatusQuestion.objects
                            .filter(
                                Q(updated_at__gte=initial_date) if initial_date else Q(),
                                Q(updated_at__lte=final_date) if final_date else Q(),
                                exam_question__pk=OuterRef('pk'),
                                status=StatusQuestion.CORRECTED,
                                active=True
                            )
                            .order_by('-updated_at')
                            .values('pk')[:1]
                        ),
                        distinct=True
                    ),
                    annuleds=Count(
                        Subquery(
                            StatusQuestion.objects
                            .filter(
                                Q(updated_at__gte=initial_date) if initial_date else Q(),
                                Q(updated_at__lte=final_date) if final_date else Q(),
                                exam_question__pk=OuterRef('pk'),
                                status=StatusQuestion.ANNULLED,
                                active=True
                            )
                            .order_by('-updated_at')
                            .values('pk')[:1]
                        ),
                        distinct=True
                    ),
                ).aggregate(
                    Sum('approveds'),
                    Sum('reproveds'),
                    Sum('correction_pendings'),
                    Sum('correcteds'),
                    Sum('annuleds'),
                )
                
                data = {
                    "name": subject.__str__(),
                    "questions": {
                        "count": exam_questions.count(),
                        "opened": exam_questions.filter(
                            Q(
                                Q(statusquestion__isnull=True) | 
                                Q(statusquestion__status=StatusQuestion.SEEN)
                            )
                        ).count(),
                        "approved": exam_questions_aggregations.get('approveds__sum') or 0,
                        "reproved": exam_questions_aggregations.get('reproveds__sum') or 0,
                        "correction_pending": exam_questions_aggregations.get('correction_pendings__sum') or 0,
                        "corrected": exam_questions_aggregations.get('correcteds__sum') or 0,
                        "annuled": exam_questions_aggregations.get('annuleds__sum') or 0,
                        "lates": exam_questions.filter(created_at__gt=F('exam__elaboration_deadline')).distinct().count(),
                    }
                }
                subjects_data.append(data)
            
            if self.request.GET.get('get_exams'):
                
                filtred_exams = exams.filter(
                    Q(teacher_subjects__in=teacher_subjects),
                    Q(teacher_subjects__subject=subject),
                ).distinct()
                
                data = {
                    "id": str(subject.id),
                    "name": subject.__str__(),
                    "load": {
                        "lates": False,  
                    },
                    "exams": {
                        "count": filtred_exams.count(),
                        "elaborating": filtred_exams.filter(status=Exam.ELABORATING).exclude(application__isnull=False).count(),
                        "opened": filtred_exams.filter(status=Exam.OPENED).exclude(application__isnull=False).count(),
                        "closed": filtred_exams.filter(Q(status=Exam.CLOSED) | Q(application__isnull=False)).count(),
                        "send_review": filtred_exams.filter(status=Exam.SEND_REVIEW).exclude(application__isnull=False).count(),
                        "is_printed": filtred_exams.filter(is_printed=True).distinct().count(), 
                        "tmt": filtred_exams.aggregate(tmt=Avg(F('end_time') - F('tmt_start_time'))).get('tmt') or 0,
                        "lates": 0,
                    },
                }
                
                subjects_data.append(data)
        
        return paginator.get_paginated_response(subjects_data)

class QuestionTagsCountAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    def get(self, request, *args, **kwargs):
        # Filters
        teaching_stages = request.GET.getlist('q_teaching_stages')
        education_systems = request.GET.getlist('q_education_systems')
        subjects = request.GET.getlist('q_subjects')
        year = request.GET.get('year', None)
        segments = request.GET.getlist('q_segments')
        initial_date = request.GET.get('q_initial_date', None)
        final_date = request.GET.get('q_final_date', None)

        teacher = self.request.GET.get('teacher_id', '')
        status = self.request.GET.get('status', '')
        user = self.request.user

        query = QuestionTag.objects.filter(
            Q(questiontagstatusquestion__status__exam_question__exam_teacher_subject__teacher_subject__teacher=teacher) if teacher else Q(),
            Q(
                Q(client__in=user.get_clients_cache()) |
                Q(client__isnull=True)
            ),
            Q(questiontagstatusquestion__status__exam_question__exam_teacher_subject__teacher_subject__subject__in=subjects) if subjects else Q(),
            Q(questiontagstatusquestion__status__exam_question__exam_teacher_subject__exam__teaching_stage__in=teaching_stages) if teaching_stages else Q(),
            Q(questiontagstatusquestion__status__exam_question__exam_teacher_subject__grade__level__in=segments) if segments else Q(),
            Q(questiontagstatusquestion__status__exam_question__exam_teacher_subject__exam__education_system__in=education_systems) if education_systems else Q(),
            Q(questiontagstatusquestion__created_at__year=year) if year else Q(),
            Q(questiontagstatusquestion__created_at__gte=initial_date) if initial_date else Q(),
            Q(questiontagstatusquestion__created_at__lte=final_date) if final_date else Q(),
            Q(questiontagstatusquestion__status__status=status) if status else Q(),
            Q(type=QuestionTag.REVIEW)
        ).values('name').annotate(count=Count('name')).order_by()

        return Response(TagsCountSerializer(query, many=True).data)

class ExamStudentsGradeRetrieveAPIView(LoginRequiredMixin, CheckHasPermission, RetrieveAPIView):
    queryset = Exam.objects.all()
    
    def get(self, request, *args, **kwargs):
        students_db = Student.objects.filter(
            Q(user__is_active=True),
            Q(
                applicationstudent__application__created_at__year=timezone.now().year,
                applicationstudent__application__exam=self.get_object()
            ),
            Q(classes=self.request.GET.get('classe_id')) if self.request.GET.get('classe_id') else Q()
        ).distinct()


        exam = self.get_object()
        has_questions_choices =  exam.count_choice_and_sum_questions()
        has_questions_discursives = exam.count_file_and_textual_questions()
        students = []
        for student in students_db:
            application_student = student.applicationstudent_set.filter(application__exam=exam).order_by('created_at').first()

            has_upload_choice = False
            has_upload_discursive = False
            is_ok = False
            count_pendence_choice = 0
            count_pendence_discursive = 0

            if application_student:
                total_grade = student.applicationstudent_set.filter(application__exam=exam).order_by('created_at').get_annotation_count_answers(
                    only_total_grade=True,
                    exclude_annuleds=True,
                )[0].total_grade
                
                missed = False
                if application_student.missed:
                    missed = True

                is_checked = OMRStudents.objects.filter(
                    application_student=application_student,
                    checked=True
                ).exists()
                if is_checked:
                    is_ok = True
                    
                if not (missed or is_checked):
                    if has_questions_choices:
                        has_upload_choice = OMRStudents.objects.filter(
                            application_student=application_student
                        ).exists()

                        if has_upload_choice:
                            count_pendence_choice = exam.total_choice_pendence(application_student)

                    if has_questions_discursives:

                        has_upload_discursive = OMRDiscursiveScan.objects.filter(
                            omr_student__application_student=application_student
                        ).exists()

                        if has_upload_discursive:
                            count_pendence_discursive = exam.total_discursive_pendence(application_student)
                    
                    is_ok = (count_pendence_choice + count_pendence_discursive <= 0) and has_upload_choice and has_upload_discursive


                student_data = {
                    "nome": student.name,
                    "id": student.id,
                    "application_student": application_student.id,
                    "grade": total_grade,
                    "missed": missed,
                    "has_upload_choice": has_upload_choice,
                    "has_upload_discursive": has_upload_discursive,""
                    "count_pendence_choice": count_pendence_choice,
                    "has_questions_discursives": has_questions_discursives,
                    "has_questions_choices": has_questions_choices,
                    "count_pendence_discursive": count_pendence_discursive,
                    "is_ok": is_ok,
                }

                students.append(student_data)

        return Response(students)

class ExamsExportSheetAPIWiew(LoginRequiredMixin, CheckHasPermission, APIView):
    renderer_classes = [JSONRenderer]
    required_permissions = [settings.COORDINATION]

    def post(self, request, format=None):
        serializer = ExamQuestionsSumarySerializer(data=request.data)
        if serializer.is_valid():
            args = {
                'user_pk': self.request.user.pk,
                'questions': serializer.data['questions'],
                'exams': serializer.data['exams'],
                'teachers': self.request.GET.getlist("q_teachers"),
                'subjects': self.request.GET.getlist('q_subjects'),
                'teaching_stages': self.request.GET.getlist('q_teaching_stages'),
                'education_systems': self.request.GET.getlist('q_education_systems'),
                'year': self.request.GET.get('year', datetime.now().year),
                'segments': self.request.GET.getlist('q_segments'),
                'initial_date': self.request.GET.get('q_initial_date', None),
                'final_date': self.request.GET.get('q_final_date', None),
            }
            task_id = f'EXPORT_ADMIN_DASH_{str(uuid.uuid4())[:8]}'
            export_admin_dashboard.apply_async(kwargs=args, task_id=task_id)
            return Response({'task_id': task_id}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

coordination_widgets = CoordinationWidgetsSummaryAPIWiew.as_view()
