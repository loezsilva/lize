import re

from django.db import IntegrityError
from django.db.models import Q, Value, F
from django.db.models.functions import Concat
from django.utils import timezone

from djangorestframework_camel_case.parser import CamelCaseMultiPartParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.exams.models import Exam
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.students.models import Student

from .serializers import FeedbackOnboardingSerializer


def get_nested_attr(obj, attr_string, default=None):
    attrs = attr_string.split('.')
    result = obj

    for attr in attrs:
        try:
            result = getattr(result, attr)
        except AttributeError:
            return default

    return result


class SearchView(APIView):
    def normalize_query(
        self,
        query_string,
        findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
        normspace=re.compile(r'\s{2,}').sub,
    ):
        return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)]

    def get_query(self, query_string, search_fields):
        query = None
        terms = self.normalize_query(query_string)
        for term in terms:
            or_query = None
            for field_name in search_fields:
                q = Q(**{"%s__icontains" % field_name: term})
                if or_query is None:
                    or_query = q
                else:
                    or_query = or_query | q
            if query is None:
                query = or_query
            else:
                query = query & or_query
        return query

    def get_results(self, queryset, attr):
        id_ = queryset.model.__name__.lower()
        name = queryset.model._meta.verbose_name_plural

        if id_ == 'inspector':
            id_ = 'teacher'
            name = 'Professores'
        elif id_ == 'applicationstudent':
            id_ = 'application'
            name = 'Provas'

        return {
            'id': id_,
            'name': name,
            'results': [{ 'pk': item.id, 'name': get_nested_attr(item, attr) } for item in queryset],
        }

    def get(self, request, format=None):
        items = []
        params_string = request.GET.get('q', None)
        if not params_string:
            return Response(items)

        user = self.request.user
        client = user.client
        clients = user.get_clients_cache()
        coordinations = user.get_coordinations_cache()
        name_query = self.get_query(params_string, ['name'])
        exam_name_query = self.get_query(params_string, ['exam__name'])
        application_exam_name_query = self.get_query(params_string, ['application__exam__name'])

        today = timezone.localtime(timezone.now())

        if request.user.user_type == 'teacher':
            inspector = user.inspector
            
            if inspector.can_correct_questions_other_teachers:
                query = Q(examteachersubject__teacher_subject__subject__in=inspector.subjects.all())
            else:
                query = Q(examteachersubject__teacher_subject__teacher__user=user)

            exam_qs = Exam.objects.filter(
                Q(
                    Q(release_elaboration_teacher__lte=timezone.now()) | Q(release_elaboration_teacher__isnull=True)
                ),
                Q(
                    Q(
                        Q(correction_by_subject=True),
                        Q(coordinations__unity__client__in=user.get_clients_cache()), 
                        Q(examteachersubject__teacher_subject__subject__in=inspector.subjects.all())
                    )
                    | Q(
                        Q(coordinations__unity__client__in=user.get_clients_cache()), 
                        query,
                    )
                    | Q(created_by=user)
                ),
                name_query,
                created_at__year__gte=today.year,
            ).distinct()
            queries = []
            
            if user.has_perm('exams.view_exam'):
                queries.append([
                    exam_qs.distinct()[0:5],
                    'name'
                ])
                
            queries.append([
                SchoolClass.objects.filter(
                    name_query,
                    pk__in=inspector.get_classes(),
                    coordination__in=coordinations,
                    school_year__gte=today.year,
                )
                .order_by('coordination__unity__name', 'name')
                .annotate(
                    full_name=Concat(
                        F('name'),
                        Value(' - '),
                        F('coordination__unity__name'),
                    )
                ).distinct()[0:5],
                'full_name'
            ])
                
        elif request.user.user_type == 'student':
            queries = [
                [
                    ApplicationStudent.objects.filter(
                        application_exam_name_query,
                        student=user.student,
                        application__exam__isnull=False,
                    ).filter(
                        Q(application__date__year__gte=today.year),
                        Q(Q(application__duplicate_application=False) | Q(is_omr=True)),
                        Q(
                            Q(application__show_result_only_for_started_application=True),
                            Q(
                                Q(option_answers__isnull=False)
                                | Q(textual_answers__isnull=False)
                                | Q(file_answers__isnull=False)
                            ),
                        )
                        | Q(application__show_result_only_for_started_application=False),
                    ).exclude(application__category=Application.HOMEWORK).order_by(
                        '-created_at'
                    ).select_related('application__exam').distinct()[0:5],
                    'application.exam.name'
                ],
            ]
        
        elif request.user.user_type == 'coordination':
            application_qs = Application.objects.filter(
                exam_name_query,
                date__year__gte=today.year,
                exam__coordinations__in=coordinations,
            )
            if not user.client_has_exam_elaboration:
                application_qs = application_qs.filter(category=Application.PRESENTIAL)
            queries = []
            if user.has_perm('exams.view_exam'):
                queries.append([
                    Exam.objects.filter(
                        name_query,
                        coordinations__in=coordinations,
                        is_abstract=False,
                        created_at__year__gte=today.year,
                    ).exclude(
                        application__automatic_creation=True,
                    ).distinct()[0:5],
                    'name'
                ])
            if user.has_perm('students.view_student'):
                queries.append([
                    Student.objects.filter(
                        Q(
                            name_query,
                            client=client,
                        ),
                        Q(
                            Q(classes__coordination__in=coordinations) |
                            Q(classes__isnull=True)
                        )
                    ).distinct()[0:5],
                    'name'
                ])
            if user.has_perm('inspectors.view_teacher') or user.has_perm('inspectors.view_inspector'):
                queries.append([
                    Inspector.objects.filter(
                        name_query,
                        inspector_type=Inspector.TEACHER,
                        coordinations__in=coordinations,
                        user__is_active=True,
                    ).order_by('-created_at').distinct()[0:5],
                    'name'
                ])
            if user.has_perm('applications.view_application'):
                queries.append([
                    application_qs.exclude(
                        automatic_creation=True,
                    ).select_related('exam').order_by('-created_at').distinct()[0:5],
                    'exam.name'
                ])
            if user.has_perm('classes.view_schoolclass'):
                queries.append([
                    SchoolClass.objects.filter(
                        name_query,
                        coordination__in=coordinations,
                        school_year__gte=today.year,
                    )
                    .order_by('coordination__unity__name', 'name')
                    .annotate(
                        full_name=Concat(
                            F('name'),
                            Value(' - '),
                            F('coordination__unity__name'),
                        )
                    ).distinct()[0:5],
                    'full_name'
                ])
        
        for query, attr in queries:
            if query:
                items.append(self.get_results(query, attr))

        return Response(items)


class FeedbackOnboardingAPIView(APIView):
    parser_classes = (CamelCaseMultiPartParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, format=None):
        serializer = FeedbackOnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save(user=request.user)
        except IntegrityError:
            return Response({'detail': 'Você já avaliou esta notificação!'}, status=status.HTTP_200_OK)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
