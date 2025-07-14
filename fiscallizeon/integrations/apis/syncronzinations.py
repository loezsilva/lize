from datetime import datetime

from django.db.models import Q
from django.http.response import JsonResponse
from django.template.defaultfilters import slugify
from django.utils import timezone

from rest_framework.response import Response
from rest_framework.views import APIView

from fiscallizeon.classes.models import Grade, SchoolClass
from fiscallizeon.clients.models import SchoolCoordination, Unity
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.students.models import Student

from fiscallizeon.integrations.models import Integration
from rest_framework import status

class SyncUnities(APIView):
    render_classes = JsonResponse
    authentication_classes = [CsrfExemptSessionAuthentication]
    
    def post(self, request):
        # Reseta os dados de sincronização
        user = self.request.user
        integration = user.client.integration
        data = request.data
        token = data.get('token', None) if isinstance(request.data, dict) else None # Se a integração for activesoft vai ser preciso passar o token
        unities = data.get('unities') if isinstance(request.data, dict) and data.get('unities') else data
        
        if integration.erp != Integration.ACTIVESOFT:            
            Unity.objects.filter(client=user.client).update(id_erp=None)
        
        for unity in unities:
            if integration.erp == Integration.ACTIVESOFT:
                if not token:
                    return Response('Você deve informar o token que será vinculado na integração', status=status.HTTP_400_BAD_REQUEST)
                unity_id = unity['unidade_id']
            elif integration.erp == Integration.ISCHOLAR:
                unity_id = unity['id_unidade']
            elif integration.erp == Integration.ATHENAWEB:
                unity_id = unity['id']
            elif integration.erp == Integration.SOPHIA:
                unity_id = unity['codigo']
                
            if unity["relation_id"]:
                Unity.objects.filter(pk=unity["relation_id"]).update(id_erp=unity_id, integration_token=integration.tokens.get(id=token) if token else None)
                unity["sync"] = True
            else:
                unity["sync"] = False
            
        return Response(unities)

class SyncClasses(APIView):
    render_classes = JsonResponse
    authentication_classes = [CsrfExemptSessionAuthentication]

    def post(self, request):
        user = self.request.user
        client = user.client
        integration = client.integration
        data = request.data
        token = data.get('token', None) if isinstance(request.data, dict) else None # Se a integração for activesoft vai ser preciso passar o token
        school_classes = data.get('school_classes') if isinstance(request.data, dict) and data.get('school_classes') else request.data
        
        if integration.erp == Integration.ACTIVESOFT:
            if not token:
                return Response('Você deve informar o token que será vinculado na integração', status=status.HTTP_400_BAD_REQUEST)
        
        for classe in school_classes:
            if integration.erp == Integration.ACTIVESOFT:
                grade_name = classe['serie_nome']
                classe_name = classe['nome']
            
            elif integration.erp == Integration.ISCHOLAR:
                grade_name = classe['curso']['nome']
                classe_name = classe['nome']
            
            elif integration.erp == Integration.ATHENAWEB:
                grade_name = classe['nome_nivel']
                classe_name = classe['nome']
                
            elif integration.erp == Integration.SOPHIA:
                grade_name = classe['curso']['descricao']
                classe_name = classe['nome']
                classe['id'] = classe['codigo']
            
            name = f"{grade_name} - {classe_name}" if self.request.GET.get('concatenate_serie') in [True, 'true'] else classe_name
            
            if classe["relation_id"] and classe.get("grade"):
                try:
                    synched_class = SchoolClass.objects.filter(
                        Q(
                            id_erp=classe["id"],
                            coordination__unity__client=client,
                        ),
                        Q(
                            integration_token=token,
                        ) if integration.erp == Integration.ACTIVESOFT else Q()
                    ).first()

                    if synched_class:
                        synched_class.name = name
                        synched_class.grade = Grade.objects.get(pk=classe.get("grade"))
                        synched_class.coordination = SchoolCoordination.objects.get(pk=classe["relation_id"])
                        synched_class.is_itinerary = classe.get("itinerary", False)
                        
                        if integration.erp == Integration.ACTIVESOFT:
                            synched_class.integration_token = integration.tokens.get(id=token)
                        
                        synched_class.save(skip_hooks=True)
                        continue

                    SchoolClass.objects.update_or_create(
                        name=name,
                        school_year=timezone.now().year,
                        coordination=SchoolCoordination.objects.get(pk=classe["relation_id"]),
                        defaults={
                            "id_erp": classe["id"],
                            "is_itinerary": classe.get("itinerary", False),
                            "grade": Grade.objects.get(pk=classe.get("grade")),
                            "integration_token": integration.tokens.get(id=token) if integration.erp == Integration.ACTIVESOFT else None,
                        }
                    )
                    classe["sync"] = True
                except Exception as e:
                    print("DUPLICAÇÃO DE TURMA", repr(e))
            elif not classe["relation_id"]:
                
                synched_class = SchoolClass.objects.filter(
                    id_erp=classe["id"],
                    coordination__unity__client=client,
                    integration_token=token,
                ).first()
                
                if synched_class:
                    synched_class.id_erp = None
                    synched_class.save(skip_hooks=True)
                    classe["sync"] = False
            
        return Response(school_classes)

class SyncInterships(APIView):
    render_classes = JsonResponse
    authentication_classes = [CsrfExemptSessionAuthentication]

    def get_valid_email(self, student):
        if not student['email']:
            return self.generate_valid_email(student)
        return student['email']

    def generate_valid_email(self, student):
        client = self.request.user.client
        email = slugify(f"{student['nome'].strip()} {student['matricula']} {client.code if client.code else student['id']}")
        return f"{email}@email-temp.com.br"
    
    def post(self, request):
        user = self.request.user
        client = user.client
        integration = client.integration
        data = request.data
        token = data.get('token', None) if isinstance(data, dict) else None # Se a integração for activesoft vai ser preciso passar o token
        interships = data.get('interships').copy() if isinstance(data, dict) and data.get('interships') else data.copy()
        
        if integration.erp == Integration.ACTIVESOFT:
            if not token:
                return Response('Você deve informar o token que será vinculado na integração', status=status.HTTP_400_BAD_REQUEST)
        
        remove_student_classes = self.request.GET.get('remove_student_classes')
        
        for intership in interships:
            try:
                intership_student = intership["student"]
                id_enrollment_erp = str(intership_student['id_enrollment_erp']) if 'id_enrollment_erp' in intership_student else None

                # student with id_erp
                student = Student.objects.using('default').filter(
                    Q(client=self.request.user.client),
                    Q(id_erp=intership_student['id']),
                    Q(integration_token=integration.tokens.get(id=token) if integration.erp == Integration.ACTIVESOFT else None)
                ).first()
                
                if student:
                    student.enrollment_number = str(intership_student['matricula'])
                    student.id_enrollment_erp = id_enrollment_erp
                    student.email = self.get_valid_email(intership_student)
                    student.name = str(intership_student['nome']).upper()
                    student.integration_token = integration.tokens.get(id=token) if integration.erp == Integration.ACTIVESOFT else None

                    if intership_student['data_nascimento']:
                        student.birth_of_date = datetime.strptime(
                            intership_student['data_nascimento'].split('T')[0], '%Y-%m-%d'
                        ).date()
                        student.save(skip_hooks=True)

                    student.user.is_active = True
                    student.user.save()
                    student.save()
                else:
                    # student with enrollment_number or email
                    student = (
                        Student.objects.using('default').filter(
                            Q(
                                Q(
                                    Q(id_erp__isnull=True) |
                                    Q(id_erp='')
                                ),
                                Q(client=client),
                                Q(
                                    Q(email=self.get_valid_email(intership_student)) |
                                    Q(enrollment_number=str(intership_student['matricula']))
                                ),
                                Q(integration_token=token) if integration.erp == Integration.ACTIVESOFT else Q()
                            )
                        ).first()
                    )

                    # if student and student.name != str(intership_student['nome']).upper():
                        # Aluno com mesmo email mas nome diferente.
                        # Tratar o aluno como não encontrado para cadastra-lo como um aluno novo em vez de substituir o aluno existente
                        # student = None

                    if student:
                        student.id_erp = intership_student['id']
                        student.enrollment_number = str(intership_student['matricula'])
                        student.id_enrollment_erp = id_enrollment_erp
                        student.email = self.get_valid_email(intership_student)
                        student.name = str(intership_student['nome']).upper()
                        student.integration_token = integration.tokens.get(id=token) if integration.erp == Integration.ACTIVESOFT else None

                        if intership_student['data_nascimento']:
                            student.birth_of_date = datetime.strptime(
                                intership_student['data_nascimento'].split('T')[0], '%Y-%m-%d'
                            ).date()
                            student.save(skip_hooks=True)
                            
                        student.user.is_active = True
                        student.user.save()
                        student.save()
                    else:
                        # create student
                        student = Student.objects.using('default').create(
                            client=client,
                            id_erp=intership_student['id'],
                            id_enrollment_erp=id_enrollment_erp,
                            enrollment_number=str(intership_student['matricula']),
                            email=self.get_valid_email(intership_student),
                            name=str(intership_student['nome']).upper(),
                            integration_token=integration.tokens.get(id=token) if integration.erp == Integration.ACTIVESOFT else None,
                        )

                        if intership_student['data_nascimento']:
                            student.birth_of_date = datetime.strptime(
                                intership_student['data_nascimento'].split('T')[0], '%Y-%m-%d'
                            ).date()
                            student.save(skip_hooks=True)


                classe = SchoolClass.objects.filter(coordination__unity__client__in=self.request.user.get_clients_cache(), id_erp=intership["turma_id"])
                
                if integration.erp == Integration.ACTIVESOFT:
                    classe = classe.filter(integration_token=token)
                
                if student and classe:
                    
                    if remove_student_classes: # Limpa as turmas do ano atual do aluno
                        [classe.students.remove(student) for classe in student.get_classes_current_year()]

                    classe.first().students.add(student)
                    intership["sync"] = True
            except Exception as e:
                print(repr(e))
                intership["error"] = f"O aluno não pode ser sincronizado {repr(e)}"

        return Response(interships)

sync_unities = SyncUnities.as_view()
sync_classes = SyncClasses.as_view()
sync_interships = SyncInterships.as_view()