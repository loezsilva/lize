from mixer.backend.django import mixer
from django.contrib.auth.models import Permission

from fiscallizeon.exams.models import Exam, ExamTeacherSubject
from fiscallizeon.clients.models import SchoolCoordination, Client, Unity, CoordinationMember
from fiscallizeon.accounts.models import User
from fiscallizeon.questions.models import Question

from fiscallizeon.classes.models import Grade, SchoolClass
from fiscallizeon.students.models import Student
from fiscallizeon.inspectors.models import Inspector, TeacherSubject
from fiscallizeon.subjects.models import Subject, KnowledgeArea
from fiscallizeon.applications.models import Application
from django.utils import timezone
from django.utils.crypto import get_random_string
from datetime import datetime, timedelta

from django.core import management
import pytz

class ApplicationAndApplicationStudentsMixin:
    students_count = 5

    def setUp(self):
        management.call_command('initial_configs')

        # Criação de usuário coordenador
        self.username_coord = get_random_string(16)
        self.password_coord = get_random_string(16)
        all_permissions = Permission.objects.all()
        self.coordinator = mixer.blend(User, username=self.username_coord, can_request_ai_questions=False)
        self.coordinator.user_permissions.set(all_permissions)
        self.coordinator.set_password(self.password_coord)
        self.coordinator.save()

        # Criação de cliente e coordenação
        self.my_client = mixer.blend(Client, has_public_questions=True, has_exam_elaboration=True, has_wrongs=False, can_request_ai_questions=False, type_client=1)
        unity = mixer.blend(Unity, client=self.my_client)
        coordination = mixer.blend(SchoolCoordination, unity=unity)
        self.coordination_member = mixer.blend(CoordinationMember, user=self.coordinator, coordination=coordination)
        
        # Criação de questão
        self.question = mixer.blend(Question)
        self.question_two = mixer.blend(Question)

        # Criação de dois exames
        self.exam_one = mixer.blend(Exam, is_abstract=True)
        self.exam_two = mixer.blend(Exam, is_abstract=True)
        
        
        
        # Associação dos exames com a coordenação e questões
        self.exam_one.coordinations.add(coordination)
        self.exam_one.questions.add(self.question)
        self.exam_two.coordinations.add(coordination)
        self.exam_two.questions.add(self.question_two)
        

        # Criação de usuário aluno
        self.username = get_random_string(16)
        self.password = get_random_string(16)
        self.user = mixer.blend(User, username=self.username, can_request_ai_questions=False)
        self.user.set_password(self.password)
        self.user.save()
        self.student = mixer.blend(Student, user=self.user, client=self.my_client)
        
        # Criação de grau e classe
        self.grade = Grade.objects.all().order_by('?').first()
        self.school_class = mixer.blend(SchoolClass, grade=self.grade, coordination=coordination, school_year=timezone.now().year)
        self.school_class.students.add(self.student)
        self.school_class.save()

        # Criação de área de conhecimento e disciplinas
        self.knowledge_area = mixer.blend(KnowledgeArea, name="Conhecimento Básico")
        self.knowledge_area.grades.add(self.grade)
        self.knowledge_area.save()
        
        self.subject = mixer.blend(Subject, knowledge_area=self.knowledge_area, name="Matemática", parent_subject=None, client=self.my_client, created_by=self.coordinator, is_foreign_language_subject=False)
        self.subject_2 = mixer.blend(Subject, knowledge_area=self.knowledge_area, name="Português", parent_subject=None, client=self.my_client, created_by=self.coordinator, is_foreign_language_subject=False)
        
        # Atribuição das disciplinas as questões
        self.question.subject = self.subject 
        self.question.save()
        self.question_two.subject = self.subject_2 
        self.question_two.save()
        
        # Criação de professor e associação com disciplinas
        teacher_one = mixer.blend(Inspector, is_inspector_ia=True)
        teacher_one.coordinations.add(coordination.id)
        teacher_one.subjects.add(self.subject.id)
        self.teacher_subject_one = mixer.blend(TeacherSubject, teacher=teacher_one, subject=self.subject)
        self.teacher_subject_one.classes.add(self.school_class)

        recife_tz = pytz.timezone('America/Recife')
        now_naive = datetime.now()
        now_aware = recife_tz.localize(now_naive)
        formatted_date_str = now_aware.strftime('%Y-%m-%d')
        formatted_date = now_aware
        
        # Criação de aplicações (exames) associadas aos dois exames
        self.application = mixer.blend(Application,
            exam=self.exam_one,
            subject=self.subject,
            date=formatted_date,
            end=formatted_date + timedelta(hours=1),
            start=formatted_date - timedelta(hours=1),
            date_end=formatted_date + timedelta(days=1),
            date_start=formatted_date - timedelta(days=1),
            release_result_at_end=True,
            student_stats_permission_date=formatted_date
        )
        self.application.inspectors.add(teacher_one)
        self.application.students.add(self.student)
        self.application.save()
        
        self.application_2 = mixer.blend(Application,
            exam=self.exam_two,
            subject=self.subject_2,
            date=formatted_date,
            end=formatted_date + timedelta(hours=1),
            start=formatted_date - timedelta(hours=1),
            date_end=formatted_date + timedelta(days=1),
            date_start=formatted_date - timedelta(days=1),
            release_result_at_end=True,
            student_stats_permission_date=formatted_date
        )
        self.application_2.inspectors.add(teacher_one)
        self.application_2.students.add(self.student)
        self.application_2.school_classes.add(self.school_class)
        self.application_2.save()

    def login(self):
        self.page.goto(self.live_server_url)
        self.page.wait_for_timeout(1000)

        self.page.locator("#id_username").fill(self.username)
        self.page.locator("#id_password").fill(self.password)
        self.page.keyboard.press("Enter")

        self.page.wait_for_timeout(3000)