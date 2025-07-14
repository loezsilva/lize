from mixer.backend.django import mixer
from django.contrib.auth.models import Permission

from fiscallizeon.exams.models import Exam
from fiscallizeon.clients.models import SchoolCoordination, Client, Unity, CoordinationMember
from fiscallizeon.accounts.models import User
from fiscallizeon.classes.models import Grade, SchoolClass
from fiscallizeon.students.models import Student

from django.utils import timezone
from django.utils.crypto import get_random_string

from django.core import management

class ApplicationUsablityMixin:
    students_count = 5

    def setUp(self):
        
        management.call_command('initial_configs')

        self.username = get_random_string(16)
        self.password = get_random_string(16)

        # Pega todas as permissões do sistema
        all_permissions = Permission.objects.all()

        # Crie um coordenador
        self.coordinator = mixer.blend(User, username=self.username)   
        
        # Adiciona todas as permissões     
        self.coordinator.user_permissions.set(all_permissions)
        
        # Seta uma senha
        self.coordinator.set_password(self.password)
        self.coordinator.save()

        # Crie um cliente, unidade e adiciona o coordenador como membro da coordenação
        self.my_client = mixer.blend(Client, has_public_questions=True, has_exam_elaboration=True, has_wrongs=False)
        unity = mixer.blend(Unity, client=self.my_client)
        coordination = mixer.blend(SchoolCoordination, unity=unity)
        self.coordination_member = mixer.blend(CoordinationMember, user=self.coordinator, coordination=coordination)
        
        # Crie um caderno e um gabarito avulso para essa coordenação
        self.exam = mixer.blend(Exam, is_abstract=False)
        self.template = mixer.blend(Exam, is_abstract=True)
        self.exam.coordinations.add(coordination)
        self.template.coordinations.add(coordination)

        # Escolhe uma serie aleatoria
        self.grade = Grade.objects.all().order_by('?').first()
        
        # Cria turma
        self.school_class = mixer.blend(SchoolClass, grade=self.grade, coordination=coordination, school_year=timezone.now().year)
        for i in range(self.students_count):  
            student = mixer.blend(Student, client=self.my_client)
            self.school_class.students.add(student)

        self.avulse_student = mixer.blend(Student, client=self.my_client)
        
    def login(self):
        self.page.goto(self.live_server_url)
        self.page.wait_for_timeout(1000)

        self.page.locator("#id_username").fill(self.username)
        self.page.locator("#id_password").fill(self.password)
        
        self.page.keyboard.press("Enter")
        
        self.page.wait_for_timeout(3000)
        