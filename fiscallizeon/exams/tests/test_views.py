from mixer.backend.django import mixer
from django.contrib.auth.models import Permission

from fiscallizeon.exams.models import Exam
from fiscallizeon.accounts.models import User
from fiscallizeon.students.models import Student
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.clients.models import SchoolCoordination, Client, Unity, CoordinationMember
from fiscallizeon.exams.models import ClientCustomPage
from django.urls import reverse_lazy
from django.utils import timezone
import datetime
from django.db.models import Q
from fiscallizeon.core.utils import CustomTransactionTestCase

class TestExamViewsManager(CustomTransactionTestCase):
    databases = '__all__'

    def setUp(self):
        # Adiciona todas as permissões     
        self.coordinator = mixer.blend(User)

        # Pega todas as permissões do sistema
        emams_permissions = Permission.objects.filter(codename__in=['view_exam'])
        self.coordinator.user_permissions.set(emams_permissions)

        self.my_client = mixer.blend(Client, has_public_questions=True, has_exam_elaboration=True)
        self.student = mixer.blend(Student, client=self.my_client)
        self.student_user = self.student.user
        unity = mixer.blend(Unity, client=self.my_client)
        coordination = mixer.blend(SchoolCoordination, unity=unity)
        self.custom_page = mixer.blend(ClientCustomPage)
        self.coordination_member = mixer.blend(CoordinationMember, user=self.coordinator, coordination=coordination)
        self.student_user.must_change_password = False
        self.application_student = mixer.blend(ApplicationStudent, student=self.student, application=mixer.blend(Application))
        self.student_user.save()
        
        # Cria 2 para o ano passado
        for i in range(2):
            mixer.blend(Exam, coordinations=[coordination.id], created_at=(timezone.now() - datetime.timedelta(days=365)))
        # Cria 2 para esse ano
        for i in range(2):
            mixer.blend(Exam, coordinations=[coordination.id], created_at=timezone.now())
        # Cria 2 para o ano que vem    
        for i in range(2):
            mixer.blend(Exam, coordinations=[coordination.id], created_at=(timezone.now() + datetime.timedelta(days=365)))
        
        self.client.force_login(user=self.coordinator)

    def test_examlistview_context(self):
        """
            Testa context do examlist para ver se as variáveis importantes permanecem
        """
        
        response = self.client.get(reverse_lazy('exams:exams_list'), follow=True)
        
        self.assertEqual(response.status_code, 200)

        view = response.context['view']
        
        context = view.get_context_data()
        
        # Variáveis necessárias no context
        self.assertIsNotNone(context['year'])
        self.assertIsNotNone(context['q_is_late'])
        self.assertIsNotNone(context['category'])
        self.assertIsNotNone(context['exam_headers'])
        
        # Necessárias para os filtros
        self.assertIsNotNone(context['grades'])
        self.assertIsNotNone(context['teaching_stages'])
        self.assertIsNotNone(context['education_systems'])
        self.assertIsNotNone(context['subjects'])
        self.assertIsNotNone(context['count_filters'])
        self.assertIsNotNone(context['selected_filter'])
        self.assertIsNotNone(context['q_name'])
        self.assertIsNotNone(context['q_subjects'])
        self.assertIsNotNone(context['q_has_questions'])
        self.assertIsNotNone(context['q_is_unprecedented'])
        self.assertIsNotNone(context['q_grades'])
        self.assertIsNotNone(context['q_teaching_stages'])
        self.assertIsNotNone(context['q_education_systems'])
        self.assertIsNotNone(context['q_has_wrongs_await'])
        self.assertIsNotNone(context['q_unanswered'])
        self.assertIsNotNone(context['q_created_by'])
        self.assertIsNotNone(context['q_is_printed'])
        self.assertIsNotNone(context['q_is_late'])

    
    def test_custompages_context(self):
        """
            Testa context do custompages para ver se as variáveis importantes permanecem
        """
        url = reverse_lazy('exams:custom-pages-print')
        url += f"?application_student={str(self.application_student.id)}"
        url += f"&custom_page={str(self.custom_page.id)}"
        response = self.client.get(url, follow=True)
        
        view = response.context['view']
        
        context = view.get_context_data()
        
        # Variáveis necessárias no context
        # Variáveis que estão aqui não poderão ser removidas do contexto pois afetará alguma view ou função
        self.assertIsNotNone(context['application_student'])
        self.assertIsNotNone(context['custom_pages'])
        
        
    def test_examlistview_year(self):
        """
            Testa o filtro de ano para ter certeza de que só retornará
            cadernos do ano que foi passado no filtro
        """
        
        years = [(timezone.now().year - 1), timezone.now().year,  (timezone.now().year + 1)]
        for year in years:
            
            response = self.client.get(f"{reverse_lazy('exams:exams_list')}?year={year}", follow=True)
            
            self.assertEqual(response.status_code, 200)

            view = response.context['view']
            
            queryset = view.get_queryset()
            
            # Case não tenha nenhum caderno de ano diferente então o teste deve dar ok
            self.assertFalse(queryset.filter(Q(created_at__year__lt=year) | Q(created_at__year__gt=year)).exists())