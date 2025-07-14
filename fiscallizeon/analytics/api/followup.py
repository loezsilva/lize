from rest_framework.views import APIView
from rest_framework.response import Response

from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication
from fiscallizeon.applications.models import Application
from datetime import datetime
from django.db.models import Q, Sum, Count
from fiscallizeon.exams.models import Exam
from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from fiscallizeon.analytics.models import GenericPerformancesFollowUp
from fiscallizeon.inspectors.models import Inspector
    

def format_value(value):
    if value and value > 0:
        return value
    return 0

PERMORMANCES_TYPES = {
    'correction': GenericPerformancesFollowUp.ANSWERS,
    'cards': GenericPerformancesFollowUp.CARDS,
    'questions': GenericPerformancesFollowUp.QUESTIONS,
}

class FollowUpAPIView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

    def get(self, request, format=None):
        from fiscallizeon.clients.models import Unity
        
        type = self.request.GET.get('type', 'correction')
        
        today = datetime.now()
        user = self.request.user
        show_finisheds = self.request.GET.get('show_finisheds')
        
        coordinations = user.get_coordinations_cache()
        
        applications = Application.objects.filter(
            Q(exam__coordinations__in=coordinations),
            Q(created_at__year=datetime.now().year),
        ).annotate(
            exams_count=Count('exam')
        ).applieds().filter(exams_count__gt=0)
        
        filter_type = 'deadline_for_correction_of_responses'
        
        if type == 'correction':
            applications = applications.filter(
                Q(deadline_for_correction_of_responses__isnull=False),
                Q(deadline_for_correction_of_responses__gte=today.date()) if not show_finisheds in ['true', True] else Q()
            )
        elif type == 'cards':
            applications = applications.filter(
                Q(deadline_for_sending_response_letters__isnull=False),
                Q(deadline_for_sending_response_letters__gte=today.date()) if not show_finisheds in ['true', True] else Q()
            )
            filter_type = 'deadline_for_sending_response_letters'
        
        groups = []
        
        exams = Exam.objects.filter(
            Q(performances_followup__isnull=False),
            Q(created_at__year=datetime.now().year),
            Q(application__in=applications) if not type == 'questions' else Q()
        ).distinct()

        for deadline in list(sorted(set(exams.filter(elaboration_deadline__isnull=False).values_list('elaboration_deadline', flat=True) if type == 'questions' else applications.values_list(filter_type, flat=True)))):

            if type == 'correction':
                filtred_exams = exams.filter(application__deadline_for_correction_of_responses=deadline)
            elif type == 'cards':
                filtred_exams = exams.filter(application__deadline_for_sending_response_letters=deadline)
            elif type == 'questions':
                filtred_exams = exams.filter(elaboration_deadline=deadline)            
            
            unities = Unity.objects.filter(coordinations__in=coordinations).distinct()
            
            groups.append({
                "deadline": deadline,
                "type": type,
                "quantity": 0,
                "total": 0,
                "selected_unity": '',
                "exams_names": filtred_exams.values_list('name', flat=True),
                "teachers": [],
                "exams": [],
                "unities": [ 
                    { 
                        "id": str(unity.id), 
                        "name": unity.name, 
                        "quantity": 0, 
                        "load": False,
                    } for unity in unities
                ],
            })
            
        return Response(groups)

class FollowUpGetItemQuantityAPIView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

    def get(self, request, format=None):
        type = self.request.GET.get('type', 'correction')
        
        user = self.request.user
        deadline = self.request.GET.get('deadline')
        coordinations = user.get_coordinations_cache()
        
        applications = Application.objects.annotate(
            exams_count=Count('exam')
        ).applieds().filter(exams_count__gt=0)
        
        if type == 'correction':
            applications = applications.filter(deadline_for_correction_of_responses__isnull=False, deadline_for_correction_of_responses__gte=deadline)
        elif type == 'cards':
            applications = applications.filter(deadline_for_sending_response_letters__isnull=False, deadline_for_sending_response_letters__gte=deadline)
        
        exams = Exam.objects.filter(
            Q(
                coordinations__in=coordinations,
            ),
            Q(application__in=applications) if type != 'questions' else Q(),
        )
        
        if type == 'correction':
            exams = exams.filter(application__deadline_for_correction_of_responses=deadline)
        elif type == 'cards':
            exams = exams.filter(application__deadline_for_sending_response_letters=deadline)
        elif type == 'questions':
            exams = exams.filter(elaboration_deadline=deadline)   
        
        performances = GenericPerformancesFollowUp.objects.filter(
            deadline=deadline,
            object_id__in=exams.values_list('id'),
            type=PERMORMANCES_TYPES[type],
        ).distinct()
        
        selected_unity = None
        
        if type in ['correction', 'questions']:
            performances_aggregations = performances.aggregate(quantity_sum=Sum('quantity'), total_sum=Sum('total'))
            if performances:
                selected_unity = performances.values('unity').annotate(sum_quantity=Sum('quantity')).order_by('-sum_quantity').values_list('unity', flat=True)[0]
                
        elif type == 'cards':
            performances_aggregations = performances.aggregate(quantity_sum=Sum('cards_quantity'), total_sum=Sum('cards_total'))
            if performances:
                selected_unity = performances.values('unity').annotate(sum_quantity=Sum('cards_quantity')).order_by('-sum_quantity').values_list('unity', flat=True)[0]
            
        quantity = performances_aggregations.get('quantity_sum')
        total = performances_aggregations.get('total_sum')
        
        return Response({
            "selected_unity": selected_unity,
            "quantity": format_value(quantity),
            "total": format_value(total)
        })

class FollowUpGetUnitySummaryAPIView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

    def get(self, request):
        type = self.request.GET.get('type', 'correction')
        
        user = self.request.user
        
        deadline = request.GET.get('deadline')
        unity_id = request.GET.get('unity_id')
        
        coordinations = user.get_coordinations_cache()
        
        exams = Exam.objects.filter(
            Q(
                coordinations__in=coordinations,
            ),
            Q(coordinations__unity=unity_id) if unity_id else Q()
        ).applieds().distinct()
        
        if type == 'correction':
            exams = exams.filter(application__deadline_for_correction_of_responses=deadline)
        elif type == 'cards':
            exams = exams.filter(application__deadline_for_sending_response_letters=deadline)
        elif type == 'questions':
            exams = exams.filter(elaboration_deadline=deadline)
        
        performances = GenericPerformancesFollowUp.objects.filter(
            Q(
                deadline=deadline,
                object_id__in=exams.values_list('id'),
                type=PERMORMANCES_TYPES[type],
            ),
            Q(unity=unity_id) if unity_id else Q(),
        ).distinct()
        
        if type == 'correction':
            performances_aggregations = performances.aggregate(quantity_sum=Sum('quantity'), total_sum=Sum('total'))
        elif type == 'cards':
            performances_aggregations = performances.aggregate(quantity_sum=Sum('cards_quantity'), total_sum=Sum('cards_total'))
        elif type == 'questions':
            performances_aggregations = performances.aggregate(quantity_sum=Sum('quantity'), total_sum=Sum('total'))
        
        quantity = performances_aggregations.get('quantity_sum')
        total = performances_aggregations.get('total_sum')
            
        unity_object = {
            "id": unity_id,
            "quantity": format_value(quantity),
            "total": format_value(total),
        }
        
        return Response(unity_object)

class FollowUpGetExamsSummaryAPIView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

    def get(self, request, format=None):
        type = self.request.GET.get('type', 'correction')
        user = self.request.user
        
        deadline = request.GET.get('deadline')
        unity_id = request.GET.get('unity_id')
        
        teacher_id = request.GET.get('teacher_id')
        
        coordinations = user.get_coordinations_cache()
        
        applications = Application.objects.filter(
            Q(
                exam__coordinations__in=user.get_coordinations_cache(),
            ),
        ).applieds().distinct()
        
        if type == 'correction':
            applications = applications.filter(deadline_for_correction_of_responses=deadline)
        elif type == 'cards':
            applications = applications.filter(deadline_for_sending_response_letters=deadline)
        
        if not applications:
            return Response()
        
        exams = Exam.objects.filter(
            Q(coordinations__in=coordinations),
            Q(application__in=applications) if type != 'questions' else \
            Q(
                Q(elaboration_deadline=deadline),
                Q(coordinations__unity=unity_id) if unity_id else Q(),
            ),
        ).distinct()
        
        exams_objects = []
        
        for exam in exams:
            
            performances = exam.performances_followup.filter(
                Q(
                    deadline=deadline, 
                    type=PERMORMANCES_TYPES[type],
                ),
                Q( 
                    unity=unity_id, 
                    coordination__in=coordinations
                ) if type != 'questions' else Q(),
                Q(inspectors=teacher_id) if teacher_id else Q(),
            ).distinct()
            
            if type in ['correction', 'questions']:
                performances_aggregations = performances.aggregate(
                    quantity_sum=Sum('quantity'), 
                    total_sum=Sum('total'),
                    objective_quantity_sum=Sum('objective_quantity'),
                    objective_total_sum=Sum('objective_total'),
                    discursive_quantity_sum=Sum('discursive_quantity'),
                    discursive_total_sum=Sum('discursive_total'),
                )
            else: 
                performances_aggregations = performances.aggregate(
                    quantity_sum=Sum('cards_quantity'), 
                    total_sum=Sum('cards_total'),
                    objective_quantity_sum=Sum('objective_cards_quantity'),
                    objective_total_sum=Sum('objective_cards_total'),
                    discursive_quantity_sum=Sum('discursive_cards_quantity'),
                    discursive_total_sum=Sum('discursive_cards_total'),
                )
                
            quantity = performances_aggregations.get('quantity_sum')
            total = performances_aggregations.get('total_sum')
            objective_quantity = performances_aggregations.get('objective_quantity_sum')
            objective_total = performances_aggregations.get('objective_total_sum')
            discursive_quantity = performances_aggregations.get('discursive_quantity_sum')
            discursive_total = performances_aggregations.get('discursive_total_sum')
            
            if quantity:
                exam_object = {
                    "id": str(exam.id),
                    "name": exam.name,
                    "classes": [],
                    "quantity": format_value(quantity),
                    "total": format_value(total),
                    "objective_quantity": format_value(objective_quantity),
                    "objective_total": format_value(objective_total),
                    "discursive_quantity": format_value(discursive_quantity),
                    "discursive_total": format_value(discursive_total),
                    "collapsed": False,
                    "load": {
                        "quantity": True,
                        "classes_summary": False,
                    }
                }
                exams_objects.append(exam_object)
        
        return Response(exams_objects)

class FollowUpGetExamSummaryAPIView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

    def get(self, request):
        
        type = self.request.GET.get('type', 'correction')
        
        user = self.request.user
        
        deadline = request.GET.get('deadline')
        unity_id = request.GET.get('unity_id')
        
        exam = Exam.objects.get(
            pk=self.request.GET.get('exam_id'),
        )
        
        if type == 'questions':
            unity_id = None
        
        performances = exam.performances_followup.filter(
            Q(  
                deadline=deadline,
                type=PERMORMANCES_TYPES[type],
            ),
            Q(
                school_class__coordination__in=user.get_coordinations_cache(),
                unity_id=unity_id,
            ) if unity_id else Q()
        ).distinct()
        
        if type in ['correction', 'questions']:
            performances_aggregations = performances.aggregate(quantity_sum=Sum('quantity'), total_sum=Sum('total'))
        else:
            performances_aggregations = performances.aggregate(quantity_sum=Sum('cards_quantity'), total_sum=Sum('cards_total'))
        
        quantity = performances_aggregations.get('quantity_sum')
        total = performances_aggregations.get('total_sum')
            
        exam_object = {
            "id": str(exam.id),
            "quantity": format_value(quantity),
            "total": format_value(total),
        }
        
        return Response(exam_object)
    
class FollowUpGetTeacherSummaryAPIView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

    def get(self, request):
        
        type = self.request.GET.get('type', 'correction')
        
        user = self.request.user
        
        deadline = request.GET.get('deadline')
        unity_id = request.GET.get('unity_id')
        
        teacher = Inspector.objects.get(
            pk=self.request.GET.get('teacher_id'),
        )
        
        performances = GenericPerformancesFollowUp.objects.filter(
            deadline=deadline, 
            school_class__coordination__in=user.get_coordinations_cache(),
            unity_id=unity_id,
            inspectors=teacher,
            type=GenericPerformancesFollowUp.ANSWERS if type == 'correction' else GenericPerformancesFollowUp.CARDS,
        ).distinct()
        
        if type == 'correction':
            performances_aggregations = performances.aggregate(quantity_sum=Sum('quantity'), total_sum=Sum('total'))
        else:
            performances_aggregations = performances.aggregate(quantity_sum=Sum('cards_quantity'), total_sum=Sum('cards_total'))
        
        quantity = performances_aggregations.get('quantity_sum')
        total = performances_aggregations.get('total_sum')
            
        teacher_object = {
            "id": str(teacher.id),
            "quantity": format_value(quantity),
            "total": format_value(total),
        }
        
        return Response(teacher_object)
    
class FollowUpGetTeachersSummaryAPIView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

    def get(self, request, format=None):
        
        from fiscallizeon.inspectors.models import Inspector
        
        type = self.request.GET.get('type', 'correction')
        
        user = self.request.user
        
        deadline = self.request.GET.get('deadline')
        unity_id = self.request.GET.get('unity_id', None)
        
        coordinations = user.get_coordinations_cache()
        
        if type == 'questions':
            exams = Exam.objects.filter(
                coordinations__in=coordinations,
                elaboration_deadline=deadline
            )
            
        else:
            applications = Application.objects.filter(
                Q(
                    exam__coordinations__in=coordinations,
                ),
                Q(deadline_for_correction_of_responses=deadline) if type == 'correction' else Q(deadline_for_sending_response_letters=deadline),
            ).applieds().distinct()
            
            if not applications:
                return Response()
        
            exams = Exam.objects.filter(
                application__in=applications,
            ).distinct()
        
        teacher_objects = []
        
        teachers_pks = GenericPerformancesFollowUp.objects.filter(
            Q(
                deadline=deadline,
                object_id__in=exams.values_list('id'),
            ),
            Q(unity=unity_id) if type != 'questions' else Q(),
            Q(inspectors__coordinations__unity=unity_id) if unity_id else Q()
        ).values_list('inspectors').distinct()
        
        teachers = Inspector.objects.filter(pk__in=teachers_pks)
        
        for teacher in teachers:
            
            performances = GenericPerformancesFollowUp.objects.filter(
                Q(
                    deadline=deadline,
                    object_id__in=exams.values_list('id'),
                    inspectors=teacher,
                    type=PERMORMANCES_TYPES[type],
                ),
                Q(unity=unity_id) if type != 'questions' else Q(),
            ).distinct()
            
            if type == 'correction':
                performances_aggregations = performances.aggregate(
                    quantity_sum=Sum('quantity'), 
                    total_sum=Sum('total'),
                    objective_quantity_sum=Sum('objective_quantity'),
                    objective_total_sum=Sum('objective_total'),
                    discursive_quantity_sum=Sum('discursive_quantity'),
                    discursive_total_sum=Sum('discursive_total'),
                )
            elif type == 'cards':
                performances_aggregations = performances.aggregate(
                    quantity_sum=Sum('cards_quantity'), 
                    total_sum=Sum('cards_total'),
                    objective_quantity_sum=Sum('objective_cards_quantity'),
                    objective_total_sum=Sum('objective_cards_total'),
                    discursive_quantity_sum=Sum('discursive_cards_quantity'),
                    discursive_total_sum=Sum('discursive_cards_total'),
                )
            
            elif type == 'questions':
                performances_aggregations = performances.aggregate(
                    quantity_sum=Sum('quantity'), 
                    total_sum=Sum('total'),
                    objective_quantity_sum=Sum('objective_cards_quantity'),
                    objective_total_sum=Sum('objective_cards_total'),
                    discursive_quantity_sum=Sum('discursive_cards_quantity'),
                    discursive_total_sum=Sum('discursive_cards_total'),
                )
            
            quantity = performances_aggregations.get('quantity_sum')
            total = performances_aggregations.get('total_sum')
            objective_quantity = performances_aggregations.get('objective_quantity_sum')
            objective_total = performances_aggregations.get('objective_total_sum')
            discursive_quantity = performances_aggregations.get('discursive_quantity_sum')
            discursive_total = performances_aggregations.get('discursive_total_sum')
            
            if quantity:
                teacher_object = {
                    "id": str(teacher.id),
                    "name": teacher.name,
                    "exams": [],
                    "quantity": format_value(quantity),
                    "total": format_value(total),
                    "objective_quantity": format_value(objective_quantity),
                    "objective_total": format_value(objective_total),
                    "discursive_quantity": format_value(discursive_quantity),
                    "discursive_total": format_value(discursive_total),
                    "collapsed": False,
                    "load": {
                        "quantity": True,
                        "exams": False,
                    }
                }
            
                teacher_objects.append(teacher_object)
        
        return Response(teacher_objects)
    
class FollowUpGetClassesSummaryAPIView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

    def get(self, request):
        from fiscallizeon.classes.models import SchoolClass
        
        type = self.request.GET.get('type', 'correction')
        
        deadline = request.GET.get('deadline')
        exam_id = request.GET.get('exam_id')
        unity_id = request.GET.get('unity_id')
        teacher_id = request.GET.get('teacher_id')
        
        coordinations = self.request.user.get_coordinations_cache()
        
        exam = Exam.objects.get(
            pk=exam_id,
        )
        
        classes_objects = []
        
        classes = SchoolClass.objects.filter(
            applications__in=exam.application_set.all(),
            coordination__in=coordinations,
            coordination__unity=unity_id,
        ).distinct()
        
        for classe in classes:
            performances = exam.performances_followup.filter(
                Q(
                    deadline=deadline,
                    school_class=classe,
                    coordination__in=coordinations,
                    unity=unity_id,
                    type=GenericPerformancesFollowUp.ANSWERS if type == 'correction' else GenericPerformancesFollowUp.CARDS,
                ),
                Q(inspectors=teacher_id) if teacher_id else Q(),
            )
            
            if type == 'correction':
                performances_aggregations = performances.aggregate(
                    quantity_sum=Sum('quantity'), 
                    total_sum=Sum('total'),
                    objective_quantity_sum=Sum('objective_quantity'),
                    objective_total_sum=Sum('objective_total'),
                    discursive_quantity_sum=Sum('discursive_quantity'),
                    discursive_total_sum=Sum('discursive_total'),
                )
            else:
                performances_aggregations = performances.aggregate(
                    quantity_sum=Sum('cards_quantity'), 
                    total_sum=Sum('cards_total'),
                    objective_quantity_sum=Sum('objective_cards_quantity'),
                    objective_total_sum=Sum('objective_cards_total'),
                    discursive_quantity_sum=Sum('discursive_cards_quantity'),
                    discursive_total_sum=Sum('discursive_cards_total'),
                )
            
            quantity = performances_aggregations.get('quantity_sum')
            total = performances_aggregations.get('total_sum')
            objective_quantity = performances_aggregations.get('objective_quantity_sum')
            objective_total = performances_aggregations.get('objective_total_sum')
            discursive_quantity = performances_aggregations.get('discursive_quantity_sum')
            discursive_total = performances_aggregations.get('discursive_total_sum')
            
            if quantity:
                classe_object = {
                    "id": str(classe.id),
                    "name": classe.__str__(),
                    "quantity": format_value(quantity),
                    "total": format_value(total),
                    "objective_quantity": format_value(objective_quantity),
                    "objective_total": format_value(objective_total),
                    "discursive_quantity": format_value(discursive_quantity),
                    "discursive_total": format_value(discursive_total),
                    "load": {
                        "quantity": True,
                    },
                    "unity": str(classe.coordination.unity.id),
                }
                classes_objects.append(classe_object)
                
        return Response(classes_objects)