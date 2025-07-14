from rest_framework import serializers

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer

from django.db.models import Q
from django.utils import timezone

from fiscallizeon.exams.models import Exam
from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.integrations.models import Integration
from fiscallizeon.core.utils import CheckHasPermissionAPI
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

class ExamsGradeListAPIView(CheckHasPermissionAPI, APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    
    class OutputSerializer(serializers.ModelSerializer):
        score_loaded = serializers.BooleanField(default=False)
        replace_notes = serializers.BooleanField(default=False)
        replace_confirmed_notes = serializers.BooleanField(default=False)
        in_sync = serializers.BooleanField(default=False)
        students_loaded = serializers.BooleanField(default=False)
        loading_compositions = serializers.BooleanField(default=False)
        classes = serializers.SerializerMethodField()
        selected_classes = serializers.SerializerMethodField()
        subjects_relation = serializers.SerializerMethodField()
        phases = serializers.SerializerMethodField()
        logs = serializers.SerializerMethodField()
        students = serializers.SerializerMethodField()
        nc = serializers.SerializerMethodField()
        subjects = serializers.SerializerMethodField()
        selected_phase = serializers.SerializerMethodField()
        subjects_activesoft = serializers.SerializerMethodField()
        subjects_ischolar = serializers.SerializerMethodField()
        subjects_athenaweb = serializers.SerializerMethodField()
        ncs = serializers.SerializerMethodField()
        avaliation = serializers.SerializerMethodField()
        avaliations = serializers.SerializerMethodField()
        division = serializers.SerializerMethodField()
        divisions = serializers.SerializerMethodField()
        errors = serializers.SerializerMethodField()
        itinerary_only = serializers.BooleanField(default=False)
        applications = serializers.SerializerMethodField()
        period = serializers.SerializerMethodField()
        selected_application = serializers.SerializerMethodField()
        
        class Meta:
            model = Exam
            fields = [
                'id',
                'name',
                'score_loaded',
                'replace_notes',
                'replace_confirmed_notes',
                'classes',
                'selected_classes',
                'subjects_relation',
                'phases',
                'selected_phase',
                'nc',
                'in_sync',
                'logs',
                'loading_compositions',
                'students',
                'subjects',
                'students_loaded',
                'subjects_activesoft',
                'subjects_ischolar',
                'subjects_athenaweb',
                'ncs',
                'errors',
                'division',
                'divisions',
                'avaliation',
                'avaliations',
                'itinerary_only',
                'applications',
                'period',
                'selected_application',
            ]
            
        def get_subjects(self, obj):
            subjects = [
                {
                    "id": str(subject.id),
                    "name": subject.__str__(),
                } for subject in obj.get_subjects()
            ]
            return subjects
        
        def get_classes(self, obj):
            return []
        def get_selected_classes(self, obj):
            return []
        def get_subjects_relation(self, obj):
            return []
        def get_phases(self, obj):
            return []
        def get_selected_phase(self, obj):
            return None
        def get_logs(self, obj):
            return []
        def get_students(self, obj):
            return []
        def get_subjects_activesoft(self, obj):
            return []
        def get_subjects_ischolar(self, obj):
            return []
        def get_subjects_athenaweb(self, obj):
            return []
        def get_nc(self, obj):
            return None
        def get_ncs(self, obj):
            return []
        def get_errors(self, obj):
            return []
        def get_avaliation(self, obj):
            return None
        def get_avaliations(self, obj):
            return None
        def get_division(self, obj):
            return None
        def get_divisions(self, obj):
            return []
        def get_itinerary_only(self, obj):
            return False
        def get_applications(self, obj):
            return []
        def get_period(self, obj):
            return None
        def get_selected_application(self, obj):
            return None
    
    def get(self, request):
        """
            -- DOC_EXAMS_EXAMSGRADELIST_GET
        """
        grade = self.request.GET.get('grade')
        user = self.request.user
        client = user.client
        now = timezone.now()
        
        exams = Exam.objects.only('id', 'name').filter(
            Q(
                coordinations__unity__client=client,
                application__isnull=False,
                application__date__year=now.year, 
                application__students__id_erp__isnull=False,
            ),
            Q(
                Q(
                    is_abstract=True,
                    questions__grade=grade
                ) |
                Q(
                    is_abstract=False,
                    examteachersubject__grade=grade
                )
            )
        ).distinct()
                
        return Response(self.OutputSerializer(exams, many=True).data)

class StudentsExamListAPIView(CheckHasPermissionAPI, APIView):
    class OutputSerializer(serializers.ModelSerializer):
        score = serializers.SerializerMethodField()
        active_soft_data = serializers.SerializerMethodField()
        ischolar_data = serializers.SerializerMethodField()
        athenaweb_data = serializers.SerializerMethodField()
        sophia_data = serializers.SerializerMethodField()
        errors = serializers.SerializerMethodField()
        timeout_error = serializers.BooleanField(default=False)
        classe = serializers.SerializerMethodField()
        classe_list = serializers.SerializerMethodField()
        score_loaded = serializers.BooleanField(default=False)
        expanded = serializers.BooleanField(default=False)
        
        class Meta:
            model = Student
            fields = [
                'id',
                'name',
                'id_erp',
                'enrollment_number',
                'id_enrollment_erp',
                'score_loaded',
                'errors',
                'timeout_error',
                'active_soft_data',
                'athenaweb_data',
                'sophia_data',
                'score',
                'classe',
                'expanded',
                'ischolar_data',
                'classe_list',
            ]
        
        def get_score(self, obj):
            return None
        
        def get_classe(self, obj):
            return self.get_classe_list(obj)[0] if self.get_classe_list(obj) else None

        def get_classe_list(self, obj):
            integration_token = self.context.get('integration_token')

            classes = obj.classes.filter(
                Q(
                    temporary_class=False,
                    school_year=timezone.now().year
                ),
                Q(integration_token=integration_token) if integration_token else Q(),
            ).distinct().order_by(
                '-created_at',
            )

            data = []
            if classes:
                for classe in classes:                    
                    if classe.id_erp:
                        data.append({
                            "id": str(classe.id),
                            "name": classe.name,
                            "id_erp": classe.id_erp,
                            "integration_token": str(classe.integration_token.id) if classe.integration_token else None,
                            "grade": {
                                "id": str(classe.grade.id),
                                "name": classe.grade.__str__(),
                            },
                            "is_itinerary": classe.is_itinerary,
                        })    
                return data
            
            return data  

        def get_active_soft_data(self, obj):
            return None
        
        def get_ischolar_data(self, obj):
            return None
        
        def get_athenaweb_data(self, obj):
            return None
        
        def get_sophia_data(self, obj):
            return None
        
        def get_errors(self, obj):
            return []
        
    authentication_classes = [CsrfExemptSessionAuthentication]
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

    def get(self, request):
        
        user = self.request.user
        client = user.client
        integration = client.integration
        exam_id = self.request.GET.get('exam')
        token = request.GET.get('token', None) # Se a integração for activesoft vai ser preciso passar o token
        
        application_students = ApplicationStudent.objects.filter(
            application__exam=exam_id
        ).annotate_is_present_with_subquery().filter(
            is_present=True
        ).values('student_id')
        
        students = Student.objects.filter(
            client=client,
            id_erp__isnull=False,
            id__in=application_students
        ).distinct()

        if integration.erp == Integration.ACTIVESOFT:
            
            if not token:
                return Response('Você deve informar o token que será vinculado na integração', status=status.HTTP_400_BAD_REQUEST)
            
            students = students.filter(integration_token=token)
        
        return Response(self.OutputSerializer(students, many=True, context={ 'exam': exam_id, 'integration_token': token }).data)