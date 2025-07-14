from django import test 
from datetime import datetime
from django.core import management
from mixer.backend.django import mixer
from fiscallizeon.accounts.models import User
from django.utils.crypto import get_random_string
from django.contrib.auth.models import Permission

from fiscallizeon.exams.models import ClientCustomPage, Exam, ExamTeacherSubject, ExamQuestion, TeacherSubject
from fiscallizeon.questions.models import Question
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.students.models import Student
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.clients.models import CoordinationMember, SchoolCoordination, Client, Unity
from fiscallizeon.core.utils import CustomTransactionTestCase

class ExamTestMixin(CustomTransactionTestCase):
    databases = '__all__'
    
    def setUp(self):
        
        self.total_grade = 20
        
        self.client = mixer.blend(Client, has_public_questions=True, has_exam_elaboration=True)
        self.student = mixer.blend(Student, client=self.client)
        
        unity = mixer.blend(Unity, client=self.client)
        self.coordination = mixer.blend(SchoolCoordination, unity=unity)
        
        self.exam = mixer.blend(Exam, total_grade=self.total_grade, coordinations=[self.coordination.id])
        
        self.application_student = mixer.blend(ApplicationStudent, student=self.student, application=mixer.blend(Application, exam=self.exam))
        
        teacher_one = mixer.blend(Inspector)
        teacher_one.coordinations.add(self.coordination.id)
        teacher_subject_one = mixer.blend(TeacherSubject, teacher=teacher_one)
        exam_teacher_subject_one = mixer.blend(ExamTeacherSubject, exam=self.exam, teacher_subject=teacher_subject_one, block_subject_note=False)
        
        teacher_two = mixer.blend(Inspector)
        teacher_two.coordinations.add(self.coordination.id)
        teacher_subject_two = mixer.blend(TeacherSubject, teacher=teacher_two)
        exam_teacher_subject_two = mixer.blend(ExamTeacherSubject, exam=self.exam, teacher_subject=teacher_subject_two, block_subject_note=False)
        
        for i in range(5):
            mixer.blend(ExamQuestion, exam=self.exam, question=mixer.blend(Question), exam_teacher_subject=exam_teacher_subject_one)
            
        for i in range(5):
            mixer.blend(ExamQuestion, exam=self.exam, question=mixer.blend(Question), exam_teacher_subject=exam_teacher_subject_two)
            
        self.examquestions = self.exam.examquestion_set.all().order_by('?')


class CreateExamTestMixin:
    BASE_URL = 'http://localhost:8000'
    nome_exam = "nome_repetido"
    nome_exam_2 = "nome_repetido_2"
    
    def setUp(self):
        management.call_command('initial_configs')

        # Criação de usuário coordenador
        self.username = get_random_string(16)
        self.password = get_random_string(16)
        all_permissions = Permission.objects.all()
        self.coordinator = mixer.blend(User, username=self.username)
        self.coordinator.user_permissions.set(all_permissions)
        self.coordinator.set_password(self.password)
        self.coordinator.save()

        # Criação de cliente e coordenação
        self.my_client = mixer.blend(Client, has_public_questions=True, has_exam_elaboration=True, has_wrongs=False, can_request_ai_questions=False, type_client=1)
        self.unity = mixer.blend(Unity, client=self.my_client)
        self.coordination = mixer.blend(SchoolCoordination, unity=self.unity)
        self.coordination_member = mixer.blend(CoordinationMember, user=self.coordinator, coordination=self.coordination)

        # criar prova com mesmo nome no mesmo ano
        exam = mixer.blend(Exam, name=self.nome_exam, coordinations=[self.coordination])
        mixer.blend(Exam, name=self.nome_exam_2, coordinations=[self.coordination])
        self.exam_id = exam.id

    def login(self):
        self.page.goto(self.BASE_URL)
        
        self.page.locator("#id_username").fill(self.username)
        self.page.locator("#id_password").fill(self.password)
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(2000)