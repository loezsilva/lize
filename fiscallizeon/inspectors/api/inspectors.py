import io
import csv

import logging
import re
from django.utils import timezone
from django.db.models import Q
from rest_framework import filters, generics, viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from django.conf import settings
from fiscallizeon.accounts.models import User
from fiscallizeon.core.utils import CheckHasPermission
from django.contrib.auth.mixins import LoginRequiredMixin
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

from fiscallizeon.inspectors.models import Inspector, TeacherSubject
from fiscallizeon.subjects.models import Subject, Grade
from fiscallizeon.inspectors.serializers.inspectors import (
    InspectorSerializer, InspectorsCreateUpdateSerializer, TeacherSerializer
)
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.clients.models import SchoolCoordination, CoordinationMember
from django.utils.functional import cached_property
from django.db import transaction
from django.db.models.deletion import ProtectedError

logger = logging.getLogger()

class InspectorViewSet(LoginRequiredMixin, CheckHasPermission, viewsets.ModelViewSet):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    serializer_class = InspectorSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )
    model = Inspector

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return InspectorsCreateUpdateSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = Inspector.objects.filter(
            Q(
                inspector_type=Inspector.TEACHER,
				coordinations__unity__client=self.request.user.client
			)
        ).distinct()

        queryset = queryset.filter(
            user__is_active=True
        )

        return queryset.order_by("-created_at")
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        email = data.get('email')
        
        teacher_subjects_json = data.get('subjects')
        
        subjects = list(map(lambda x: x.get('subject').get('id'), data['subjects']))
        
        # Remove Teacher Subjects
        teacher_subjects_to_remove = TeacherSubject.objects.using('default').filter(
            subject__in=instance.subjects.all(), teacher=instance
        ).difference(
            TeacherSubject.objects.using('default').filter(
                subject__in=subjects, teacher=instance
            )
        )
        
        for teacher_subject in teacher_subjects_to_remove:
            try:
                teacher_subject.delete()
            except ProtectedError:
                teacher_subject.active = False
                teacher_subject.save()
        instance.coordinations.set(data['coordinations'])
        
        associate_coordination_member = CoordinationMember.objects.filter(
            user__email=email,
        ).first()
        groups_coordination = []

        if associate_coordination_member:
            for custom_group in associate_coordination_member.user.custom_groups.all():
                groups_coordination.append(str(custom_group.pk)) 

        if custom_groups := data.get('custom_groups'):
            instance.user.custom_groups.set(custom_groups)
        else:
            instance.add_custom_groups()
        
        if associate_coordination_member and groups_coordination:
            for group in groups_coordination:
                instance.user.custom_groups.add(group)
        
        for teacher_subject_json in teacher_subjects_json:
            
            if id := teacher_subject_json.get('id'):
                teacher_subject = TeacherSubject.objects.using('default').get(id=id)
            else:
                teacher_id = teacher_subject_json.get('teacher').get('id')
                subject_id = teacher_subject_json.get('subject').get('id')
                
                teacher_db = Inspector.objects.using('default').get(id=teacher_id)
                subject_db = Subject.objects.using('default').get(id=subject_id)
                
                try:
                    teacher_id = teacher_subject_json.get('teacher').get('id')
                    subject_id = teacher_subject_json.get('subject').get('id')
                    
                    # Alterei para um filter para conseguir tratar melhor
                    teacher_subjects = TeacherSubject.objects.using('default').filter(
                        teacher=teacher_db,
                        subject=subject_db,
                        school_year=timezone.now().year,
                    )
                    
                    # Esse código é necessário para garantir que o professor não tenha mais de uma disciplina
                    if teacher_subjects.exists():
                        
                        teacher_subject = teacher_subjects.first()
                        teacher_subject.active = True # Ativa a disciplina
                        teacher_subject.save(skip_hooks=True)
                        
                        """
                            Essa parte do código é responsável por remover disciplinas que não em nenhuma solicitação e que são duplicadas.
                            Não deve ser removida, pois é necessário para garantir que o professor não tenha mais de uma disciplina
                        """
                        if teacher_subjects.count() > 1:
                            
                            # Pega todas as disciplinas que não estão em nenhuma solicitação
                            teacher_subjects_to_delete = teacher_subjects.filter(
                                classes__isnull=True, 
                                examteachersubject__isnull=True
                            ).exclude(
                                id=teacher_subject.id
                            )
                            
                            if teacher_subjects_to_delete.exists():
                                try:
                                    teacher_subjects_to_delete.delete()
                                except ProtectedError:
                                    # Desativa a disciplina sem excluir
                                    teacher_subjects_to_delete.update(active=False)
                            
                    else:
                        
                        # Caso não exista, cria
                        teacher_subject, created = TeacherSubject.objects.update_or_create(
                            teacher=teacher_db,
                            subject=subject_db,
                            school_year=timezone.now().year,
                            defaults={
                                "active": True,
                            }
                        )
                
                except Exception as e:
                    print(e)
                    return Response({
                        'detail': f'Ocorreu um erro ao tentar atualizar o professor!'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
            teacher_subject.classes.set(teacher_subject_json.get('classes'))

        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        instance.clean_coordinations_cache()

        return Response(serializer.data)

    def perform_create(self, serializer):

        data = self.request.data
        email = data.get('email')
        
        associate_coordination_member = CoordinationMember.objects.filter(
            user__email=email,
        ).first()

        inspector_instance = serializer.save()
        inspector_instance.coordinations.set(data['coordinations'])
        
        if custom_groups := data.get('custom_groups'):
            inspector_instance.user.custom_groups.set(custom_groups)
        else:
            inspector_instance.add_custom_groups()
        
        if associate_coordination_member:
            for custom_group in associate_coordination_member.user.custom_groups.all():
                data['custom_groups'].append(str(custom_group.pk))

        teacher_subjects = data.get('subjects')
        for _teacher_subject in teacher_subjects:
            teacher_subject, created = TeacherSubject.objects.get_or_create(
                teacher=Inspector.objects.using('default').get(pk=inspector_instance.id),
                subject=Subject.objects.get(pk=_teacher_subject.get('subject').get('id')),
                school_year=timezone.now().year,
            )
            teacher_subject.classes.set(_teacher_subject.get('classes'))
            
    @action(detail=True, methods=['GET'])
    def subjects_data(self, request, pk=None):
        """
            Retorna as disciplinas salvas para o professor
        """
        inspector_instance = self.get_object()
        
        subjects_data = TeacherSubject.objects.using('default').filter(
            teacher=inspector_instance,
            school_year=timezone.now().year,
            active=True
        ).distinct('subject')

        subjects_infos = [
            {
                "id": teacher_subject.subject.id,
                "classes": list(teacher_subject.classes.all().values_list('pk', flat=True)),
                "name": teacher_subject.subject.name,
                "grade": teacher_subject.subject.knowledge_area.name,
                "grades_id": list(teacher_subject.subject.knowledge_area.grades.all().values_list('pk', flat=True)),
            }
            
            for teacher_subject in subjects_data
        ]
        
        return Response(subjects_infos,status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['PATCH'])
    def update_teacher_user(self, request, pk=None):
        """
            Atualiza os dados do usuário do professor
        """
        teacher_erros = {"password": [], "username": []}

        data = request.data
        inspector = self.get_object()
        password = data.get('password')
        confirmation_password = data.get('confirmation_password')
        must_change_password = data.get('must_change_password')

        try:
            # se somente must_change_password for true e todos os outros campos forem nulos, altera somente o must_change_password
            if must_change_password and not password and not confirmation_password:
                inspector.user.must_change_password = must_change_password
                inspector.user.save()
                return Response("Usuário alterado com sucesso")

            # se must_change_password for alterado
            if must_change_password and not password and not confirmation_password:
                inspector.user.must_change_password = must_change_password
                inspector.user.save()
                return Response("Usuário alterado com sucesso")

            if password and confirmation_password:
                if password != confirmation_password:
                    teacher_erros['password'].append("As senhas não conferem")
                if len(password) & len(confirmation_password) < 8:
                    teacher_erros['password'].append("A senha precisa ter no mínimo 8 caracteres")
                if len(re.findall(r"[a-z]", password)) < 1:
                    teacher_erros['password'].append("Sua senha precisa conter letras minúsculas")
                if len(re.findall("['`()_><;:!~@#$%^&+=]",password)) < 1:
                    teacher_erros['password'].append("Sua senha precisa conter caracteres especiais")
                if not teacher_erros.get('password') and not teacher_erros.get('username'):
                    inspector.user.set_password(password)
                    if must_change_password:
                        inspector.user.must_change_password = must_change_password
                    inspector.user.save()
                    return Response("Usuário alterado com sucesso")
                
                inspector.clean_coordinations_cache()

                return Response({
                    'errors': "\n".join(teacher_erros['password']),
                }, status=status.HTTP_206_PARTIAL_CONTENT)
            else:
                return Response("Preencha os campos de senha", status=status.HTTP_206_PARTIAL_CONTENT)
        except Exception as e:
            print(e)
            return Response("Erro ao alterar o usuário", status=status.HTTP_206_PARTIAL_CONTENT)

    @cached_property
    def get_availables_subjects(self):
        user = self.request.user 
        if user:
            return user.get_availables_subjects()
        return []
        
        
    @action(detail=False, methods=['POST'])
    def import_teachers(self, request, pk=None):
        """
            Importação dos professores via CSV
        """
        file = request.data.get('file')
        
        replace_subjects = request.data.get('replace_subjects', False) == 'true'
        replace_coordinations = request.data.get('replace_coordinations', False) == 'true'
        replace_permissions = request.data.get('replace_permissions', False) == 'true'
        
        reader = csv.DictReader(io.StringIO(file.read().decode('utf-8')))
        
        # <option value="coord">Coordenador de disciplina</option>
        # <option value="coge">Corrige erratas</option>
        # <option value="elab">Elabora questões</option>
        # <option value="cog">Corretor respostas de alunos de outros professores</option>
        # <option value="cogeo">Corrige erratas de outros professores</option>
        # <option value="qf">O professor pode utilizar o formatador de questões</option>
        
        teachers_erros = []
        
        if replace_subjects or replace_coordinations or replace_permissions:
            emails = request.data.get('teachers_emails').split(',') if request.data.get('teachers_emails') else []

            teachers = Inspector.objects.filter(
                email__in=emails
            )
            
            for teacher_db in teachers:
                
                if replace_coordinations:
                    # Remove o professor das coordenações
                    teacher_db.coordinations.set([])
                
                if replace_subjects:
                    # Remove o professor das disciplinas
                    for teacher_subject in TeacherSubject.objects.filter(teacher=teacher_db, examteachersubject__isnull=True):
                        try:
                            teacher_subject.delete()
                        except ProtectedError:
                            teacher_subject.active = False
                            teacher_subject.save()

                if replace_permissions:
                    teacher_db.can_response_wrongs = False
                    teacher_db.can_elaborate_questions = False
                    teacher_db.is_discipline_coordinator = False
                    teacher_db.can_answer_wrongs_others_teachers = False
                    teacher_db.can_correct_questions_other_teachers = False
                    teacher_db.has_question_formatter = False
                    teacher_db.save(skip_hooks=True)
    
        for teacher in reader:

            with transaction.atomic():
                try:

                    coordination = teacher['coordenacao'].strip() if teacher['coordenacao'] else None
                    classes_names = teacher['turmas'].split(',') if teacher['turmas'] else []
                    
                    permissions = teacher['permissoes'].split(',') if teacher['permissoes'] else []
                    subjects = teacher['disciplinas'].split(',') if teacher['disciplinas'] else []
                    
                    if not coordination:
                        raise SchoolCoordination.DoesNotExist
                    
                    teacher_db, created = Inspector.objects.update_or_create(
                        email=teacher['email'].strip(),
                        defaults={
                            "name": teacher['nome'].strip()
                        }
                    )
                    teacher_db.coordinations.add(coordination)

                    if not teacher_db.user:
                        user = teacher_db.create_user()
                    else:
                        user = teacher_db.user
                        
                    user.name = teacher_db.name
                    
                    teacher_db.add_custom_groups()
                    
                    # Permissões do professor
                    if 'coge' in permissions:
                        teacher_db.can_response_wrongs = True
                    if 'elab' in permissions:
                        teacher_db.can_elaborate_questions = True
                    if 'coord' in permissions:
                        teacher_db.is_discipline_coordinator = True
                    if 'cogeo' in permissions:
                        teacher_db.can_answer_wrongs_others_teachers = True
                    if 'cog' in permissions:
                        teacher_db.can_correct_questions_other_teachers = True
                    if 'qf' in permissions:
                        teacher_db.has_question_formatter = True

                    # Disciplinas
                    for subject_name in subjects:
                        subject_name, knowledge_area, segment = subject_name.split(' - ')
                        teacher_subject, created = TeacherSubject.objects.update_or_create(
                            teacher=teacher_db,
                            school_year=timezone.now().year,
                            subject=self.get_availables_subjects.get(
                                name__iexact=subject_name, 
                                knowledge_area__name__icontains=knowledge_area,
                                knowledge_area__grades__level__in=[
                                    Grade.HIGHT_SCHOOL
                                ] if 'médio' in segment.lower() else [
                                    Grade.ELEMENTARY_SCHOOL,
                                    Grade.ELEMENTARY_SCHOOL_2
                                ]
                            ),
                            defaults={
                                "active": True,
                            }
                        )
                        
                        for classe_name in classes_names:
                            try:
                                classe_db = SchoolClass.objects.get(
                                    coordination=SchoolCoordination.objects.get(pk=coordination),
                                    name__iexact=classe_name.strip(),
                                    school_year=timezone.now().year,
                                )
                                
                                teacher_subject.classes.add(classe_db)
                            except Exception as e:
                                if type(e) == SchoolClass.DoesNotExist:
                                    teachers_erros.append({
                                        "name": teacher['nome'],
                                        "text": f"Não encontramos a turma {classe_name} na coordenação",
                                    })
                                elif type(e) == SchoolCoordination.DoesNotExist:
                                    teachers_erros.append({
                                        "name": teacher['nome'],
                                        "text": f"Coordenação não encontrada",
                                    })
                                else:
                                    teachers_erros.append({
                                        "name": teacher['nome'],
                                        "text": f"Erro ao tentar importar o aluno {e}",
                                    })

                                transaction.set_rollback(True)

                                return Response({
                                    'errors': teachers_erros,
                                })
                
                except Exception as e:

                    if type(e) == Subject.DoesNotExist:
                        teachers_erros.append({
                            "name": teacher['nome'],
                            "text": f"A disciplina {subject_name} não foi encontrada",
                        })
                    elif type(e) == Subject.MultipleObjectsReturned:
                        teachers_erros.append({
                            "name": teacher['nome'],
                            "text": f"Tem mais de uma disciplina com o nome: {subject_name}",
                        })
                    else:
                        teachers_erros.append({
                            "name": teacher['nome'],
                            "text": repr(e)
                        })

                    transaction.set_rollback(True)

                    return Response({
                        'errors': teachers_erros,
                    })
                
        return Response({
            'errors': teachers_erros,
        })


class TeacherListView(generics.ListAPIView):
    serializer_class = TeacherSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)

    def get_queryset(self):
        return Inspector.objects.filter(
            inspector_type=Inspector.TEACHER,
            coordinations__unity__client__in=self.request.user.get_clients_cache(),
            user__is_active=True,
        ).order_by('-created_at')
