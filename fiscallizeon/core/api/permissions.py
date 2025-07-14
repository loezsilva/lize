from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import GenericViewSet
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import Permission
from fiscallizeon.core.utils import CheckHasPermissionAPI, SimpleAPIPagination
from django.conf import settings
from fiscallizeon.accounts.models import User
from .serializers import CustomGroupSerializer, CustomGroupSimpleSerializer
from ...accounts.serializers.users import UserSimpleSerializer
from rest_framework.authentication import TokenAuthentication

from fiscallizeon.inspectors.models import Inspector

PERMISSIONS_DICT = {
    'exam': {
        'name': 'Cadernos',
        'permissions': {
            'exams.view_exam': 'Pode visualizar cadernos',
            'exams.add_exam': 'Pode adicionar cadernos',
            'inspectors.can_add_exercice_list': 'Pode adicionar lista de exercícios',
            'exams.change_exam': 'Pode alterar cadernos',
            'exams.delete_exam': 'Pode deletar cadernos',
            'exams.can_change_status_exam': 'Pode alterar o status dos cadernos',
            'exams.can_diagram_exam': 'Pode diagramar cadernos',
            'exams.can_review_questions_exam': 'Pode revisar questões dos cadernos',
            'exams.can_view_result_exam': 'Pode visualizar resultado dos cadernos',
            'exams.can_correct_answers_exam': 'Pode corrigir respostas dos cadernos',
            'exams.can_print_exam': 'Pode imprimir cadernos',
            'exams.can_duplicate_exam': 'Pode duplicar cadernos',
            'exams.can_import_exams': 'Pode importar cadernos',
            'exams.can_import_examteachersubjects': 'Pode importar solicitações a professores',
            'exams.export_results_exam': 'Pode exportar dados dos cadernos',
            'exams.can_view_confidential_exam': 'Pode visualizar cadernos confidenciais',
        }
    },
    'exam-teacher': {
        'name': 'Cadernos',
        'permissions': {
            'exams.view_exam': 'Pode visualizar cadernos',
            'exams.add_exam': 'Pode adicionar cadernos',
            'inspectors.can_add_exercice_list': 'Pode adicionar lista de exercícios',
            'exams.change_exam': 'Pode alterar cadernos',
            'exams.delete_exam': 'Pode deletar cadernos',
            'exams.can_change_status_exam': 'Pode alterar o status dos cadernos',
            'exams.can_review_questions_exam': 'Pode revisar questões dos cadernos',
            'exams.can_view_result_exam': 'Pode visualizar resultado dos cadernos',
            'exams.can_correct_answers_exam': 'Pode corrigir respostas dos cadernos',
            'exams.can_print_exam': 'Pode imprimir cadernos',
            'exams.can_duplicate_exam': 'Pode duplicar cadernos',
            'exams.can_view_confidential_exam': 'Pode visualizar cadernos confidenciais',
        }
    },
    'application': {
        'name': 'Aplicações',
        'permissions': {
            'applications.view_application': 'Pode visualizar aplicações',
            'applications.add_application': 'Pode adicionar aplicações',
            'applications.change_application': 'Pode alterar aplicações',
            'applications.delete_application': 'Pode deletar aplicações',
            'applications.can_disclose_application': 'Pode liberar resultado de aplicações',
            'applications.can_add_and_remove_students': 'Pode adicionar ou remover alunos',
            'applications.can_remove_generated_bag': 'Pode remover malote gerado',
            'applications.can_duplicate_application': 'Pode duplicar aplicações',
            'applications.can_print_bag_application': 'Pode imprimir malote',
            'applications.can_access_print_list': 'Pode acessar a lista de impressão de malotes',
        }
    },
    'material': {
        'name': 'Materiais de estudo',
        'permissions': {
            'materials.view_studymaterial': 'Pode visualizar material de estudo',
            'materials.add_studymaterial': 'Pode adicionar material de estudo',
            'materials.change_studymaterial': 'Pode alterar material de estudo',
            'materials.delete_studymaterial': 'Pode deletar material de estudo',
        }
    },
    'wrong': {
        'name': 'Erratas',
        'permissions': {
            'exams.view_wrong': 'Pode visualizar erratas',
        }
    },
    'question': {
        'name': 'Questões',
        'permissions': {
            'questions.view_question': 'Pode visualizar questões',
            'questions.add_question': 'Pode adicionar questões',
            'questions.change_question': 'Pode alterar questões',
            'questions.delete_question': 'Pode deletar questões',
            'questions.can_duplicate_question': 'Pode duplicar questões',
            'questions.can_add_subject_question': 'Pode cadastrar assuntos na criação de questões',
            'questions.can_add_ability_and_competence_question': 'Pode cadastrar BNCC na criação de questões'
        }
    },
    'obligation_field': {
        'name': 'Campos obrigatórios',
        'permissions': {
            'clients.change_clientteacherobligationconfiguration': 'Pode alterar campos obrigatórios',
        }
    },
    'question_configuration': {
        'name': 'Configurações de questões',
        'permissions': {
            'clients.change_clientquestionsconfiguration': 'Pode alterar as configurações das questões',
        }
    },
    'teacher': {
        'name': 'Professores',
        'permissions': {
            'inspectors.view_teacher': 'Pode visualizar professores',
            'inspectors.add_teacher': 'Pode adicionar professores',
            'inspectors.change_teacher': 'Pode alterar professores',
            'inspectors.delete_teacher': 'Pode deletar professores',
            'inspectors.can_reset_password': 'Pode resetar senha dos professores',            
            'inspectors.can_export_teacher': 'Pode exportar professores ',
        }
    },
    'inspector': {
        'name': 'Fiscais',
        'permissions': {
            'inspectors.view_inspector': 'Pode visualizar fiscais',
            'inspectors.add_inspector': 'Pode adicionar fiscais',
            'inspectors.change_inspector': 'Pode alterar fiscais',
            'inspectors.delete_inspector': 'Pode deletar fiscais',
        }
    },
    'student': {
        'name': 'Alunos',
        'permissions': {
            'students.view_student': 'Pode visualizar alunos',
            'students.add_student': 'Pode adicionar alunos',
            'students.change_student': 'Pode alterar alunos',
            'students.delete_student': 'Pode deletar alunos',
            'students.can_import_student': 'Pode importar alunos',
            'students.can_import_students_application': 'Pode importar alunos em aplicações',
            'students.can_reset_password': 'Pode resetar senha dos alunos',
            'students.can_active_student': 'Pode ativar ou desativar alunos',
            'students.can_export_student': 'Pode exportar alunos',
        }
    },
    'partner': {
        'name': 'Parceiros',
        'permissions': {
            'clients.view_partner': 'Pode visualizar parceiros',
            'clients.add_partner': 'Pode adicionar parceiros',
            'clients.change_partner': 'Pode alterar parceiros',
            'clients.delete_partner': 'Pode deletar parceiros',
        }
    },
    'coordination_member': {
        'name': 'Membros das coordenações',
        'permissions': {
            'clients.view_coordinationmember': 'Pode visualizar membros das coordenações',
            'clients.add_coordinationmember': 'Pode adicionar membros das coordenações',
            'clients.change_coordinationmember': 'Pode alterar membros das coordenações',
            'clients.delete_coordinationmember': 'Pode deletar membros das coordenações',
            'clients.can_export_coodinator': 'Pode exportar coordenadores',

        }
    },
    'bncc': {
        'name': 'Habilidades e competências',
        'permissions': {
            'bncc.view_abiliity': 'Pode visualizar habilidades',
            'bncc.add_abiliity': 'Pode adicionar habilidades',
            'bncc.change_abiliity': 'Pode alterar habilidades',
            'bncc.delete_abiliity': 'Pode deletar habilidades',
            # Competências
            'bncc.view_competence': 'Pode visualizar competências',
            'bncc.add_competence': 'Pode adicionar competências',
            'bncc.change_competence': 'Pode alterar competências',
            'bncc.delete_competence': 'Pode deletar competências',
        }
    },
    'subject': {
        'name': 'Disciplinas',
        'permissions': {
            'subjects.view_subject': 'Pode visualizar disciplina',
            'subjects.add_subject': 'Pode adicionar disciplina',
            'subjects.change_subject': 'Pode alterar disciplina',
            'subjects.delete_subject': 'Pode deletar disciplina',
            # Topics
            'subjects.view_topic': 'Pode visualizar assuntos',
            'subjects.add_topic': 'Pode adicionar assuntos',
            'subjects.change_topic': 'Pode alterar assuntos',
            'subjects.delete_topic': 'Pode deletar assuntos',
            # Relação entre disciplina
            'subjects.view_subjectrelation': 'Pode visualizar relação entre disciplinas',
            'subjects.add_subjectrelation': 'Pode adicionar relação entre disciplinas',
            'subjects.change_subjectrelation': 'Pode alterar relação entre disciplinas',
            'subjects.delete_subjectrelation': 'Pode deletar relação entre disciplinas',
            
        }
    },
    'distribution': {
        'name': 'Salas',
        'permissions': {
            'distribution.view_room': 'Pode visualizar salas',
            'distribution.add_room': 'Pode adicionar salas',
            'distribution.change_room': 'Pode alterar salas',
            'distribution.delete_room': 'Pode deletar salas',
        }
    },
    'exam_orientation': {
        'name': 'Orientações padrões',
        'permissions': {
            'exams.view_examorientation': 'Pode visualizar orientações',
            'exams.add_examorientation': 'Pode adicionar orientações',
            'exams.change_examorientation': 'Pode alterar orientações',
            'exams.delete_examorientation': 'Pode deletar orientações',
        }
    },
    'exam_header': {
        'name': 'Cabeçalhos Padrão',
        'permissions': {
            'exams.view_examheader': 'Pode visualizar cabeçalhos',
            'exams.add_examheader': 'Pode adicionar cabeçalhos',
            'exams.change_examheader': 'Pode alterar cabeçalhos',
            'exams.delete_examheader': 'Pode deletar cabeçalhos',
        }
    },
    'exam_print_config': {
        'name': 'Padrão de impressão de cadernos',
        'permissions': {
            'clients.view_examprintconfig': 'Pode visualizar padrões de impressão de caderno',
            'clients.add_examprintconfig': 'Pode adicionar padrões de impressão de caderno',
            'clients.change_examprintconfig': 'Pode alterar padrões de impressão de caderno',
            'clients.delete_examprintconfig': 'Pode deletar padrões de impressão de caderno',
        }
    },
    'teaching_stage': {
        'name': 'Etapas do ensino',
        'permissions': {
            'clients.view_teachingstage': 'Pode visualizar etapas do ensino',
            'clients.add_teachingstage': 'Pode adicionar etapas do ensino',
            'clients.change_teachingstage': 'Pode alterar etapas do ensino',
            'clients.delete_teachingstage': 'Pode deletar etapas do ensino',
        }
    },
    'education_system': {
        'name': 'Sistemas de ensino',
        'permissions': {
            'clients.view_educationsystem': 'Pode visualizar sistemas de ensino',
            'clients.add_educationsystem': 'Pode adicionar sistemas de ensino',
            'clients.change_educationsystem': 'Pode alterar sistemas de ensino',
            'clients.delete_educationsystem': 'Pode deletar sistemas de ensino',
        }
    },
    'question_tag': {
        'name': 'Tags de correção',
        'permissions': {
            'clients.view_questiontag': 'Pode visualizar tags de correção',
            'clients.add_questiontag': 'Pode adicionar tags de correção',
            'clients.change_questiontag': 'Pode alterar tags de correção',
            'clients.delete_questiontag': 'Pode deletar tags de correção',
        }
    },
    'classes': {
        'name': 'Turmas',
        'permissions': {
            'classes.view_schoolclass': 'Pode visualizar turmas',
            'classes.add_schoolclass': 'Pode adicionar turmas',
            'classes.change_schoolclass': 'Pode alterar turmas',
            'classes.delete_schoolclass': 'Pode deletar turmas',
        }
    },
    'course': {
        'name': 'Cursos',
        'permissions': {
            'classes.view_course': 'Pode visualizar cursos',
            'classes.add_course': 'Pode adicionar cursos',
            'classes.change_course': 'Pode alterar cursos',
            'classes.delete_course': 'Pode deletar cursos',
            
            # Tipos de curso
            'classes.view_coursetype': 'Pode visualizar tipos de cursos',
            'classes.add_coursetype': 'Pode adicionar tipos de cursos',
            'classes.change_coursetype': 'Pode alterar tipos de cursos',
            'classes.delete_coursetype': 'Pode deletar tipos de cursos',
            
            # Etapas dos cursos
            'classes.view_stage': 'Pode visualizar etapas dos cursos',
            'classes.add_stage': 'Pode adicionar etapas dos cursos',
            'classes.change_stage': 'Pode alterar etapas dos cursos',
            'classes.delete_stage': 'Pode deletar etapas dos cursos',
        }
    },
    'dashboard': {
        'name': 'Dashboards',
        'permissions': {
            'accounts.view_grade_map_dashboard': 'Pode visualizar o mapão de notas',
            'accounts.view_tri_dashboard': 'Pode visualizar o dashboard de TRI',
            'accounts.view_followup_dashboard': 'Pode visualizar dashboard de acompanhamento',
            'accounts.view_administration_dashboard': 'Pode visualizar o dashboard administrativo',
        }
    },
    'template': {
        'name': 'Gabarito avulso',
        'permissions': {
            'exams.view_template_exam': 'Pode visualizar gabarito avulso',
            'exams.add_template_exam': 'Pode adicionar gabarito avulso',
            'exams.change_template_exam': 'Pode alterar gabarito avulso',
            'exams.delete_template_exam': 'Pode deletar gabarito avulso',
            'exams.export_template_exam_results': 'Pode exportar dados de gabarito avulso',
            'exams.print_template_exam': 'Pode imprimir gabarito para divulgação',
            'exams.can_view_result_exam': 'Pode visualizar resultado dos cadernos',
            'exams.can_duplicate_template_exam':  'Pode duplicar gabarito avulso',
        }    

    },
    'omr': {
        'name': 'Leitura de cartões resposta',
        'permissions': {
            'omr.view_omrupload': 'Pode visualizar cartões resposta',
            'omr.add_omrupload': 'Pode enviar para correção automática',
            'omr.export_offset_answer_sheet': 'Pode exportar folha de respostas offset',
            'omr.export_offset_answer_sheet_schoolclass': 'Pode exportar folha de respostas offset não identificada',
            'exams.can_correct_answers_exam': 'Pode corrigir respostas dos alunos',
        }
    },

    'omr_teacher': {
        'name': 'Leitura de cartões resposta',
        'permissions': {
            'omr.view_omrupload': 'Pode visualizar cartões resposta',
            'omr.add_omrupload': 'Pode enviar para correção automática',
        }
    },

    'omrnps': {
        'name': 'Leitura de cartões NPS',
        'permissions': {
            'omrnps.add_npsapplication': 'Pode criar aplicação de NPS',
            'omrnps.view_npsapplication': 'Pode visualizar aplicações de NPS',
            'omrnps.add_omrnpsupload': 'Pode enviar cartões resposta NPS',
            'omrnps.view_omrnpsupload': 'Pode visualizar cartões resposta NPS',
            'omrnps.export_answer_sheet': 'Pode exportar malote de cartões resposta NPS',
        }
    },
    'notification': {
        'name': 'Alterar configurações de notificação',
        'permissions': {
            'clients.change_confignotification': 'Pode alterar configurações de notificações',
        }
    },
    'integration': {
        'name': 'Integrações com ERP',
        'permissions': {
            'integrations.view_integration': 'Tem acesso a integrações com ERP',
        }
    },
    'permissions': {
        'name': 'Permissões',
        'permissions': {
            'accounts.can_change_permissions': 'Pode alterar permissões',
        }
    },
}

AVAILABLE_PERMISSIONS = {
    'coordination': {
        'exam': PERMISSIONS_DICT['exam'],
        'application': PERMISSIONS_DICT['application'],
        'template': PERMISSIONS_DICT['template'],
        'question': PERMISSIONS_DICT['question'],
        'question_tag': PERMISSIONS_DICT['question_tag'],
        'omr': PERMISSIONS_DICT['omr'],
        'dashboard': PERMISSIONS_DICT['dashboard'],
        'material': PERMISSIONS_DICT['material'],
        'wrong': PERMISSIONS_DICT['wrong'],
        'student': PERMISSIONS_DICT['student'],
        'teacher': PERMISSIONS_DICT['teacher'],
        'inspector': PERMISSIONS_DICT['inspector'],
        'coordination_member': PERMISSIONS_DICT['coordination_member'],
        'partner': PERMISSIONS_DICT['partner'],
        'bncc': PERMISSIONS_DICT['bncc'],
        'subject': PERMISSIONS_DICT['subject'],
        'distribution': PERMISSIONS_DICT['distribution'],
        'exam_orientation': PERMISSIONS_DICT['exam_orientation'],
        'exam_header': PERMISSIONS_DICT['exam_header'],
        'exam_print_config': PERMISSIONS_DICT['exam_print_config'],
        'teaching_stage': PERMISSIONS_DICT['teaching_stage'],
        'education_system': PERMISSIONS_DICT['education_system'],
        'classes': PERMISSIONS_DICT['classes'],
        'course': PERMISSIONS_DICT['course'],
        'notification': PERMISSIONS_DICT['notification'],
        'obligation_field': PERMISSIONS_DICT['obligation_field'],
        'question_configuration': PERMISSIONS_DICT['question_configuration'],
        'integration': PERMISSIONS_DICT['integration'],
        'permissions': PERMISSIONS_DICT['permissions'],
    },
    'teacher': {
        'exam': PERMISSIONS_DICT['exam-teacher'],
        'application': PERMISSIONS_DICT['application'],
        'question': PERMISSIONS_DICT['question'],
        'omr' : PERMISSIONS_DICT['omr_teacher'],
        'material': PERMISSIONS_DICT['material']
    },
    'student': {
        
    },
    'partner': {
        'application': {
            'name': 'Aplicacões',
            'permissions': {
                'applications.can_access_print_list': 'Pode acessar a lista de impressão de malotes',
            }
        },
    },
    'inspector': {
        
    },
    'parent': {
        'application': {
            'name': 'Aplicacões',
            'permissions': {
                'applications.can_view_result_exam': 'Pode acessar a lista de impressão de malotes',
            }
        },
    }
}
class Permissions():
    
    @staticmethod
    def get_all_permissions(user_type=None):
        if user_type:
            return AVAILABLE_PERMISSIONS[user_type]
        return AVAILABLE_PERMISSIONS

@extend_schema(tags=['Permissões'])
class PermissionsViewSet(CheckHasPermissionAPI, GenericViewSet):
    authentication_classes = (CsrfExemptSessionAuthentication, TokenAuthentication, )
    queryset = None
    
    def get_queryset(self):
        user = self.request.user
        
        queryset = user.client.get_groups()
        
        filters = {
            'q_name': self.request.GET.get('q_name'),
            'q_default': self.request.GET.get('q_default'),
            'q_segment': self.request.GET.getlist('q_segment'),
        }
        
        if q_name := filters['q_name']:
            queryset = queryset.filter(name__icontains=q_name)
        
        if filters['q_default']:
            queryset = queryset.filter(default=True)
        
        if q_segment := filters['q_segment']:
            queryset = queryset.filter(segment__in=q_segment)
        
        return queryset
    
    @action(detail=False, methods=["GET"])
    def groups(self, request, pk=None):
        
        groups = self.get_queryset()
        
        if segment := self.request.GET.get('segment'):
            groups = groups.filter(segment=segment)
        
        paginator = SimpleAPIPagination()
        instances = paginator.paginate_queryset(groups, request)
        
        return paginator.get_paginated_response(CustomGroupSerializer(instance=instances, many=True).data)
    
    @action(detail=False, methods=["GET"])
    def all_groups(self, request, pk=None):
        
        groups = self.get_queryset()
        
        if segment := self.request.GET.get('segment'):
            groups = groups.filter(segment=segment)
        
        return Response(CustomGroupSimpleSerializer(instance=groups, many=True).data)
    
    @action(detail=True, methods=["GET"])
    def group(self, request, pk=None):
        groups = self.get_queryset()
        return Response(CustomGroupSerializer(instance=groups.get(pk=pk)).data)

    @action(detail=True, methods=["DELETE"])
    def delete_group(self, request, pk=None):
        group = self.get_queryset().filter(can_update=True).get(pk=pk)
        
        try:
            if group.can_be_removed:
                group.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        
        except Exception as e:
            
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)
        
    @action(detail=False, methods=["POST", "PUT"])
    def create_update_group(self, request, pk=None):
        data = self.request.data.copy()
        
        data['client'] = self.request.user.get_clients_cache()[0]
        method = self.request.method
        
        groups = self.get_queryset().filter(can_update=True)
        
        serializer = CustomGroupSerializer(instance=groups.get(pk=data.get('id')) if method == 'PUT' else None, data=data)
        serializer.is_valid(raise_exception=True)
        group_instance = serializer.save()
        
        permissions = data.get('permissions')
        setable_permissions = []
        
        for permission in permissions:
            try:
                app_label = permission.split('.')[0]
                codename = permission.split('.')[1]                
                permission_instance = Permission.objects.get(content_type__app_label=app_label, codename=codename)
                setable_permissions.append(permission_instance.id)
            except:
                pass
        
        group_instance.permissions.set(setable_permissions)
        
        return Response(serializer.data, status=status.HTTP_200_OK if method == 'PUT' else status.HTTP_201_CREATED)

    @action(detail=True, methods=["GET"])
    def user(self, request, pk):
        
        user = User.objects.using('default').get(pk=pk)
        
        permissions = user.get_user_permissions()
        
        return Response(list(permissions))
    
    @action(detail=True, methods=["GET"])
    def user_groups(self, request, pk):
        
        user = User.objects.using('default').get(pk=pk)
        
        groups = user.custom_groups.all()
        
        return Response(list(groups.values_list('id', flat=True)))
    
    @action(detail=True, methods=['POST', 'PATCH'])
    def change_permission_user(self, request, pk):
        
        permission = self.request.data.get('permission')
        
        app_label = permission.split('.')[0]
        
        codename = permission.split('.')[1]
        
        user = User.objects.using('default').exclude(id=self.request.user.pk).get(pk=pk)
        
        if permission in user.get_all_permissions():
            user.remove_permission(app_label, codename)
        else:
            user.add_permission(app_label, codename)
            
        return Response()
    
    @action(detail=True, methods=['POST', 'PATCH'])
    def set_permission_user(self, request, pk):
        
        permissions = self.request.data.get('permissions')
        groups = self.request.data.get('groups')
        
        all_permissions = []
        
        for permission in permissions:
            try:
                app_label = permission.split('.')[0]
                codename = permission.split('.')[1]
                permission_instance = Permission.objects.get(content_type__app_label=app_label, codename=codename)
                all_permissions.append(permission_instance.id)
            except:
                pass
        
        user = User.objects.using('default').exclude(id=self.request.user.pk).get(pk=pk)
        user.custom_groups.set(groups)
        
        user.user_permissions.set(all_permissions)
            
        return Response()
    
    @action(detail=False, methods=["PATCH"])
    def change_groups_set(self, request):
        
        list_pks_inspectors = self.request.data.get('users')
        inspector_objects = Inspector.objects.using('default').filter(pk__in=list_pks_inspectors).select_related("user")
        user_objects = [inspector.user for inspector in inspector_objects if inspector.user]


        groups = self.request.data.get('groups')

        for user in user_objects:
            user.custom_groups.set(groups)

        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=["GET"], url_path='(?:/(?P<user_type>\w+))?')
    def permissions(self, request, user_type=None):

        types = {
            'aluno': settings.STUDENT,
            'alunos': settings.STUDENT,
            'coordenacao': settings.COORDINATION,
            'coordenacoes': settings.COORDINATION,
            'coordenadores': settings.COORDINATION,
            'coordenador': settings.COORDINATION,
            'professor': settings.TEACHER,
            'professores': settings.TEACHER,
        }
        
        user = self.request.user
        
        type = user.user_type
        
        if user_type:
            type = user_type
            try:
                type = types[type.lower()]
            except:
                pass
        
        return Response(Permissions.get_all_permissions(str(type)))
    
    
    @action(detail=True, methods=["GET"])
    def users(self, request, pk):
        group = self.get_queryset().filter(can_update=True).get(pk=pk)
        
        query = group.users.all() # Query se users
        
        paginator = SimpleAPIPagination()
        instances = paginator.paginate_queryset(query, request)
        
        return paginator.get_paginated_response(UserSimpleSerializer(instance=instances, many=True).data)