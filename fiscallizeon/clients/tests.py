from mixer.backend.django import mixer

from fiscallizeon.accounts.models import User

from fiscallizeon.clients.models import Client, QuestionTag, SchoolCoordination, Unity
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.students.models import Student
from fiscallizeon.core.utils import CustomTransactionTestCase

# Create your tests here.
class TestQuestionTag(CustomTransactionTestCase):
    databases = '__all__'

    def setUp(self):
        self.question_tag = mixer.blend(QuestionTag, name="tag teste", type=QuestionTag.REVIEW)


    def test_question_tag_can_have_no_client(self):
        """
        Uma tag de questão deve poder ser criada sem um cliente associado
        """

        self.assertIsNone(self.question_tag.client)
        
class TestUserDeactivateHook(CustomTransactionTestCase):
    databases = '__all__'

    def setUp(self):
        self.client = mixer.blend(Client)
        self.unity = mixer.blend(Unity, client=self.client)

        self.user_student = mixer.blend(User)
        self.student = mixer.blend(Student, user=self.user_student, client=self.client)

    def test_client_hook_deactivates_users(self):
        """
        O hook deactivate_client_users deve desativar corretamente os usuários associados ao cliente
        """

        self.client.status = Client.DEACTIVED
        self.client.save()
        self.student.refresh_from_db() # Essa linha é necessária para atualizar a instância com o valor do banco que foi afetado pelo hook

        self.assertFalse(self.student.user.is_active, "O status do usuário não foi alterado")
