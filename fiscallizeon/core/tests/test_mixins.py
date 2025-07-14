from django.test import RequestFactory
from mixer.backend.django import mixer
from fiscallizeon.accounts.models import User
from fiscallizeon.clients.models import Client, SchoolCoordination, Unity, CoordinationMember
from fiscallizeon.exams.models import Exam
from fiscallizeon.students.models import Student
from fiscallizeon.omr.models import OMRUpload
from fiscallizeon.core.utils import CustomTransactionTestCase
from fiscallizeon.core.mixins import ClientIsObjectOwnerMixin, CreatedByIsObjectOwnerMixin, SameCoordinationUsersOwnerMixin, UserIsObjectOwnerMixin
from django.views.generic import ListView

# View genérica para testar o ClientIsObjectOwnerMixin
class GenericClientView(ClientIsObjectOwnerMixin, ListView):
    queryset = Student.objects.all()  # Define o queryset base da view como todos os alunos (Student)

    def __init__(self, user):
        # Cria uma request fake e atribui o usuário
        self.request = RequestFactory().get('/')
        self.request.user = user


# View genérica para testar o UserIsObjectOwnerMixin
class GenericUserView(UserIsObjectOwnerMixin, ListView):
    queryset = OMRUpload.objects.all()  # Define o queryset base como todos os uploads de OMR

    def __init__(self, user):
        # Cria uma request fake e atribui o usuário
        self.request = RequestFactory().get('/')
        self.request.user = user


# View genérica para testar o CreatedByIsObjectOwnerMixin
class GenericCreatedByView(CreatedByIsObjectOwnerMixin, ListView):
    queryset = Exam.objects.all()  # Define o queryset base como todos os exames

    def __init__(self, user):
        # Cria uma request fake e atribui o usuário
        self.request = RequestFactory().get('/')
        self.request.user = user


# View genérica para testar o SameCoordinationUsersOwnerMixin
class GenericCoordinationView(SameCoordinationUsersOwnerMixin, ListView):
    queryset = Exam.objects.all()  # Usa Exam como modelo de teste

    def __init__(self, user):
        self.request = RequestFactory().get('/')
        self.request.user = user

# Teste para validar os mixins de ownership
class TestObjectOwnerMixins(CustomTransactionTestCase):
    databases = '__all__'  # Permite acesso a todas as databases configuradas (caso use múltiplos bancos)

    def setUp(self):
        # Cria dois clientes diferentes
        self.client1 = mixer.blend(Client)
        self.client2 = mixer.blend(Client)

        # Cria uma unidade (Unity) para cada cliente
        unity_client1 = mixer.blend(Unity, client=self.client1)
        unity_client2 = mixer.blend(Unity, client=self.client2)

        # Cria uma coordenação (SchoolCoordination) para cada unidade
        coordination_client1 = mixer.blend(SchoolCoordination, unity=unity_client1)
        coordination_client2 = mixer.blend(SchoolCoordination, unity=unity_client2)

        # Cria dois usuários diferentes
        self.user1 = mixer.blend(User)
        self.user2 = mixer.blend(User)
        
        # Associa o user1 à coordenação do client1
        mixer.blend(
            CoordinationMember,
            user=self.user1,
            coordination=coordination_client1,
        )

        # Associa o user2 à coordenação do client2
        mixer.blend(
            CoordinationMember,
            user=self.user2,
            coordination=coordination_client2,
        )
        
    def test_object_client_is_owner_mixin_filters_correctly(self):
        # Cria um aluno de cada cliente
        obj_client1 = mixer.blend(Student, client=self.client1)
        obj_client2 = mixer.blend(Student, client=self.client2)

        # Cria uma view passando o user1
        view = GenericClientView(user=self.user1)
        queryset = view.get_queryset()

        # Verifica se o objeto do client1 está no queryset (deve estar)
        self.assertIn(obj_client1, queryset)

        # Verifica se o objeto do client2 não está no queryset (não deve estar)
        self.assertNotIn(obj_client2, queryset)

    def test_object_is_owner_mixin_filters_correctly(self):
        # Cria um upload de OMR para cada usuário
        obj_user1 = mixer.blend(OMRUpload, user=self.user1)
        obj_user2 = mixer.blend(OMRUpload, user=self.user2)

        # Cria uma view passando o user1
        view = GenericUserView(user=self.user1)
        queryset = view.get_queryset()

        # Verifica se o upload do user1 está no queryset (deve estar)
        self.assertIn(obj_user1, queryset)

        # Verifica se o upload do user2 não está no queryset (não deve estar)
        self.assertNotIn(obj_user2, queryset)

    def test_created_by_is_object_owner_mixin_filters_correctly(self):
        # Cria um Exam criado por cada usuário
        exam_user1 = mixer.blend(Exam, created_by=self.user1)
        exam_user2 = mixer.blend(Exam, created_by=self.user2)

        # Cria uma view com user1
        view = GenericCreatedByView(user=self.user1)
        queryset = view.get_queryset()

        # Deve conter apenas os exams criados por user1
        self.assertIn(exam_user1, queryset)
        self.assertNotIn(exam_user2, queryset)

    def test_same_coordination_users_mixin_filters_correctly(self):
        # Obtém as coordenações associadas a cada usuário (via cache)
        coord1 = self.user1.get_coordinations_cache()[0]
        coord2 = self.user2.get_coordinations_cache()[0]

        # Cria dois Exams (sem coordenação ainda)
        exam_coord1 = mixer.blend(Exam)
        exam_coord2 = mixer.blend(Exam)

        # Associa os Exams às respectivas coordenações
        exam_coord1.coordinations.add(coord1)
        exam_coord2.coordinations.add(coord2)

        # Cria uma view com o user1 (será usado para aplicar o filtro de coordenação)
        view = GenericCoordinationView(user=self.user1)

        # Obtém o queryset filtrado pelo mixin SameCoordinationUsersMixin
        queryset = view.get_queryset()

        # Verifica se o exame da coordenação do user1 está presente (deve estar)
        self.assertIn(exam_coord1, queryset)

        # Verifica se o exame da coordenação do user2 está ausente (deve estar)
        self.assertNotIn(exam_coord2, queryset)