import math
import numpy as np
import time

from datetime import datetime, timedelta
from random import randint, shuffle
from statistics import fmean

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Avg, F, Q, ExpressionWrapper, DateTimeField
from django.template.loader import get_template
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse

from django_lifecycle import hook

from fiscallizeon.accounts.models import User
from fiscallizeon.clients.models import Client
from fiscallizeon.core.models import BaseModel
from fiscallizeon.core.threadings.sendemail import EmailThread
from fiscallizeon.students.managers import StudentManager


class Student(BaseModel):
    user = models.OneToOneField(User, verbose_name="Usuário", on_delete=models.CASCADE, related_name="student", blank=True, null=True)
    client = models.ForeignKey(Client, verbose_name="Cliente", on_delete=models.PROTECT, null=True, blank=True)
    name = models.CharField("Nome do aluno", max_length=100, blank=False, null=False)
    enrollment_number = models.CharField("Número de matrícula", max_length=255, null=False, blank=False)
    email = models.EmailField("Endereço de email", null=False, blank=False)
    id_erp = models.CharField("ID ERP", max_length=255, null=True, blank=True)
    birth_of_date = models.DateField("Data de nascimento", null=True, blank=True)
    responsible_email = models.EmailField("Email do responsável", null=True, blank=True)
    responsible_email_two = models.EmailField("Segundo email do responsável", null=True, blank=True)
    responsible_email_three = models.EmailField("Terceiro email do responsável", null=True, blank=True)
    responsible_email_four = models.EmailField("Quarto email do responsável", null=True, blank=True)
    is_atypical = models.BooleanField("É aluno atípico?", default=False, help_text="Marque se o aluno for atípico, como autista, TDAH, etc.")
    #os campos abaixo são utilizados para cadastro de assinaturas do tri lize
    state = models.CharField("Estado", null=True, blank=True, max_length=255)
    school_name = models.CharField("Nome da Escola", null=True, blank=True, max_length=512)
    id_enrollment_erp = models.CharField("ID de matrícula no ERP", null=True, blank=True, max_length=255)

    integration_token = models.ForeignKey('integrations.IntegrationToken', verbose_name="Token utilizado para integração", on_delete=models.CASCADE, related_name="students", blank=True, null=True)

    objects = StudentManager()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"
        ordering = ['-created_at']
        permissions = (
            ('can_import_student', "Pode importar alunos"),
            ('can_reset_password', "Pode resetar senha dos alunos"),
            ('can_active_student', "Pode ativar ou desativar alunos"),
            ('can_export_student', 'Pode exportar alunos'),
            ('can_import_students_application', 'Pode importar alunos em aplicações')
        )
        
    @property
    def urls_v3(self):
        return {
            'applications_availables_today': reverse('app:applications-availables-today'),
            'applications_list': reverse('app:applications-list'),
            'scheduled_applications_list': reverse('app:applications-list') + '?only_scheduled=true',
            'without_scheduled_applications_list': reverse('app:applications-list') + '?without_scheduled=true',
            'recently_released_results_applications_list': reverse('app:applications-list') + '?recently_released_results=true',
            'performance_summary': reverse('app:student-performance-summary'),
            'current_school_class': reverse('app:student-current-school-class'),
            'current_school_class_colleagues': reverse('app:student-colleagues'),
        }

    @hook('before_create')
    def check_max_students(self):
        from .utils import MAX_STUDENTS_MESSAGE
        if self.client.max_students_quantity:
            students_count = self.client.student_set.filter(user__is_active=True).count()
            if students_count >= self.client.max_students_quantity:
                raise ValueError(MAX_STUDENTS_MESSAGE)
    
    def switch_student_status(self):
        if self.user:
            self.user.is_active = not self.user.is_active
            self.user.save()

    def get_last_class(self):
        return self.classes.filter(
            temporary_class=False,
        ).distinct().order_by(
            'school_year', 'name'
        ).last()
    
    def get_classes_current_year(self):
        return self.classes.filter(
            school_year=timezone.now().year
        ).distinct().order_by(
            'name'
        )
    def create_user(self, username=None, password=None):
        
        username_code = f'{self.client.code}-' if self.client.code else ''
        username_code += f'{(username or self.enrollment_number)}'

        if not self.user:
            new_email, new_username = None, None
            
            count_usernames = User.objects.filter(username=username_code).count()
            if count_usernames:
                new_username = (username_code) + "-" + str(count_usernames + 2)
            
            active_user = User.objects.filter(
                Q(
                    Q(email=self.email) | Q(username=new_username or username_code)
                ),
            ).first()

            if active_user and not hasattr(active_user, 'student'):
                self.user = active_user
                return

            if User.objects.filter(email=self.email).exists():
                start_email = self.email.split('@')[0]
                end_email = self.email.split('@')[1]
                new_email = f'{start_email}-{self.enrollment_number}@{end_email}'
                
            unique_username = new_username or username_code
            unique_email = new_email or self.email
            
            user = User.objects.create(
                username=unique_username, 
                email=unique_email,
                name=self.name
            )
                
            _password = (password or (datetime.strftime(self.birth_of_date, '%d%m%Y') if self.birth_of_date else self.enrollment_number))
            
            user.set_password(_password)
                        
            """ Envia email para o aluno dando boas vindas caso ele seja um aluno da mentorrize """
            if self.client.type_client == 3:
                template = get_template('mentorize/mail_template/welcome.html')
                html = template.render({"object": self, "username": (user.email), "password": _password, "email":True})
                subject = 'Seja bem vindo(a) a Mentorizze'
                to = [self.email]
                EmailThread(subject, html, to).start()
                user.must_change_password = True            
            
            if self.enrollment_number == "1234":
                user.must_change_password = True

            user.save()
            self.user = user

    def get_all_events(self):
        from fiscallizeon.events.models import Event
        students = self.applicationstudent_set.all()
        return Event.objects.filter(
            student_application__in=students
        )

    def get_finished_application_student(self):
        today = timezone.localtime(timezone.now())
        
        if self.client.type_client == 3:
            return self.applicationstudent_set.filter(end_time__isnull=False)
        
        return self.applicationstudent_set.all().get_finished_application_student()

    def get_finished_exams_current_year(self):
        return self.get_finished_application_student().filter(
            application__exam__isnull=False,
            application__date__year=timezone.now().year,
        )

    def get_option_answers_current_year(self):
        from fiscallizeon.answers.models import OptionAnswer
        return OptionAnswer.objects.filter(
            student_application__in=self.get_finished_application_student(),
            status=OptionAnswer.ACTIVE,
            student_application__application__date__year=timezone.now().year
        ).distinct()

    def get_correct_option_answers(self):
        return self.get_option_answers_current_year().filter(
            question_option__is_correct=True
        )
    
    def get_last_proof(self, application_student):
        from fiscallizeon.answers.models import ProofAnswer
        return ProofAnswer.objects.filter(application_student=application_student).order_by('-created_at').first()


    @hook("before_create")
    def create_user_signal(self):
        self.create_user()
        
    @hook("after_create")
    def create_automatic_applications(self):
        from fiscallizeon.applications.models import ApplicationStudent, Application
        
        if not self.user:
            return    

        applications = Application.objects.annotate(
            datetime_start = ExpressionWrapper(F('date') + F('start') + timedelta(hours=3), output_field=DateTimeField()),
            datetime_end = ExpressionWrapper(F('date') + F('end') + timedelta(hours=3), output_field=DateTimeField()),
            date_end_datetime_end = ExpressionWrapper(F('date_end') + F('end') + timedelta(hours=3), output_field=DateTimeField())
        ).filter(
            Q(
                exam__coordinations__unity__client__in=self.user.get_clients_cache(), 
                leveling_test=True, 
                datetime_start__lte=timezone.now()
            ),
            Q(
                Q(category=Application.MONITORIN_EXAM, datetime_end__gt=timezone.now()) |
                Q(category=Application.HOMEWORK, date_end_datetime_end__gt=timezone.now())
            )
        ).distinct()
        
        for application in applications:
            ApplicationStudent.objects.create(student=self, application=application)

        self.send_email_after_create()

    def send_email_after_create(self):
        if self.user.client_send_email_to_student_after_create:
            token = default_token_generator.make_token(self.user)
            uid = urlsafe_base64_encode(force_bytes(self.user.pk))
            password_reset_url = f'{settings.BASE_URL}/conta/confirmar-redefinicao/{uid}/{token}/'

            template = get_template('students/mail_template/welcome.html')
            html = template.render({
                'USER': self.user,
                'PASSWORD_RESET_LINK': password_reset_url,
                'PASSWORD_RESET_LINK_DAYS': settings.PASSWORD_RESET_TIMEOUT // 86400, # a day has 86400 seconds
                'PASSWORD_RESET_LINK_EXPIRATION_DATE': timezone.now() + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT),
            })
            subject = 'Bem-vindo à Lize'
            to = [self.user.email]

            EmailThread(subject, html, to).start()

    @property
    def first_name(self):
        return self.name.split(" ")[0]
    
    @property
    def finish_application_students(self):
        from fiscallizeon.applications.models import Application
        return self.applicationstudent_set.filter(
            Q(
                Q( 
                    Q(application__category=Application.MONITORIN_EXAM),
                    Q(start_time__isnull=False), 
                    Q(end_time__isnull=False)
                ) |
                Q(
                    Q(application__category=Application.PRESENTIAL),
                    Q(is_omr=True)
                ) |
                Q(
                    Q(application__category=Application.HOMEWORK),
                    Q(
                        Q(option_answers__isnull=False) |
                        Q(textual_answers__isnull=False) |
                        Q(file_answers__isnull=False)
                    )
                )
            )
        ).distinct()

    @property
    def finish_applications_count(self):
        return self.finish_application_students.count()
    

    @property
    def missing_applications_count(self):
        return self.applicationstudent_set.filter(start_time__isnull=True).count()

    @property
    def pauses_count(self):
        from fiscallizeon.events.models import Event

        return self.get_all_events().filter(event_type=Event.BATHROOM).count()

    @property
    def pause_average_duration(self):
        from fiscallizeon.events.models import Event

        events = self.get_all_events()
        events = events.filter(
            response=Event.APPROVED,
            event_type=Event.BATHROOM,
            start__isnull=False,
            end__isnull=False
        ).aggregate(average=Avg(F('end') - F('start')))
        
        average = events['average']
        
        return average

    @property
    def average_duration(self):
        students = self.applicationstudent_set.filter(
            start_time__isnull=False, 
            end_time__isnull=False
        ).aggregate(average=Avg(F('end_time') - F('start_time')))
        
        average = students['average']
        
        return average
    
    @property
    def can_create_lists(self):
        from fiscallizeon.applications.models import Application
        filtred_applications = Application.objects.filter(
            Q(
                Q(automatic_creation=True) | Q(leveling_test=True)
            ), 
            Q(applicationstudent__end_time__isnull=True, applicationstudent__student=self) 
        )
        return not filtred_applications.exists()        
    
    def generate_performances_in_bnccs(self, calculate_subjects=True, recalculate=True):
        from fiscallizeon.subjects.models import Topic
        from fiscallizeon.subjects.models import Subject
        from fiscallizeon.exams.models import ExamQuestion
        from fiscallizeon.bncc.models import Abiliity, Competence     
        
        start_process = time.time()

        if not calculate_subjects:
            questions_availables = ExamQuestion.objects.filter(question__in=self.finish_application_students.distinct().values_list('application__exam__questions')).availables().distinct()
            topics = Topic.objects.filter(question__examquestion__in=questions_availables).distinct()
            abilities = Abiliity.objects.filter(question__examquestion__in=questions_availables).distinct()
            competences = Competence.objects.filter(question__examquestion__in=questions_availables).distinct()
            
            for topic in topics:
                performances = []
                questions_availables_filtred = ExamQuestion.objects.filter(question__topics=topic)
                if questions_availables_filtred.count():
                    topic_performance = topic.last_performance(student=self)
                    
                    for application_student in self.finish_application_students.filter(application__exam__questions__in=questions_availables_filtred.values('question')).distinct():
                        performances.append(application_student.get_performance(bncc_pk=topic.pk, recalculate=recalculate))
                    
                    if topic_performance:
                        topic_performance.using('default').update(
                            performance=fmean(performances) if performances else 0,
                            process_time=timedelta(seconds=(time.time() - start_process))
                        )
                    else:
                        topic.performances.create(
                            student=self, 
                            performance=fmean(topic_performance) if topic_performance else 0,
                            process_time=timedelta(seconds=(time.time() - start_process))
                        )
                
                
            for ability in abilities:
                performances = []
                ability_performance = ability.last_performance(student=self)
                questions_availables_filtred = ExamQuestion.objects.filter(question__abilities=ability)
                for application_student in self.finish_application_students.filter(application__exam__questions__in=questions_availables_filtred.values('question')).distinct():
                    performances.append(application_student.get_performance(bncc_pk=ability.pk, recalculate=recalculate))
                
                if ability_performance:
                    ability_performance.using('default').update(
                        performance=fmean(performances) if performances else 0,
                        process_time=timedelta(seconds=(time.time() - start_process))
                    )
                else:
                    ability.performances.create(
                        student=self, 
                        performance=fmean(performances) if performances else 0,
                        process_time=timedelta(seconds=(time.time() - start_process))
                    )
                    
            for competence in competences:                
                performances = []
                competence_performance = competence.last_performance(student=self)
                
                for application_student in self.finish_application_students.distinct():
                    performances.append(application_student.get_performance(bncc_pk=competence.pk, recalculate=recalculate))
                
                if competence_performance:
                    competence_performance.using('default').update(
                        performance=fmean(performances) if performances else 0,
                        process_time=timedelta(seconds=(time.time() - start_process))
                    )
                else:
                    competence.performances.create(
                        student=self, 
                        performance=fmean(performances) if performances else 0,
                        process_time=timedelta(seconds=(time.time() - start_process))
                    )
            
            return
        
        exam_questions = ExamQuestion.objects.availables().filter(exam__application__applicationstudent__in=self.finish_application_students).distinct()
        exam_questions_pks = exam_questions.values_list('pk', flat=True)
        
        subjects = Subject.objects.filter(
            Q(teachersubject__examteachersubject__examquestion__in=exam_questions)
        ).distinct()
        
        for subject in subjects:

            exam_questions = ExamQuestion.objects.filter(
                Q(pk__in=exam_questions_pks),
                Q(
                    Q(question__subject=subject) |
                    Q(exam_teacher_subject__teacher_subject__subject=subject)
                ),
            )
            
            topics = Topic.objects.filter(pk__in=exam_questions.values_list('question__topics')).distinct()
            for topic in topics:
                topic_performance = topic.last_performance(student=self, subject=subject)
                if not topic_performance or recalculate:
                    subject.get_performance(student=self, bncc_pk=topic.pk, recalculate=recalculate)
            
            abilities = Abiliity.objects.filter(pk__in=exam_questions.values_list('question__abilities')).distinct()
            for ability in abilities:
                ability_performance = ability.last_performance(student=self, subject=subject)
                if not ability_performance or recalculate:
                    subject.get_performance(student=self, bncc_pk=ability.pk, recalculate=recalculate)
                    
            competences = Competence.objects.filter(pk__in=exam_questions.values_list('question__competences')).distinct()
            for competence in competences:
                competence_performance = competence.last_performance(student=self, subject=subject)
                if not competence_performance or recalculate:
                    subject.get_performance(student=self, bncc_pk=competence.pk, recalculate=recalculate)
            
            
    def generate_performances_in_subjects(self, recalculate=True):
        from fiscallizeon.subjects.models import Subject
        from fiscallizeon.applications.models import ApplicationStudent
        
        applications_student = self.finish_application_students.distinct()
        
        subjects = Subject.objects.filter(
            Q(
                Q(teachersubject__examteachersubject__in=applications_student.values_list('application__exam__teacher_subjects', flat=True)) |
                Q(pk__in=applications_student.values_list('application__exam__questions__subject', flat=True))
            )
        ).distinct()
        
        for subject in subjects:
            subject_performance = subject.last_performance(student=self)
            if not subject_performance or recalculate:
                subject.get_performance(student=self, recalculate=recalculate)
    
    def run_recalculate_performances(self):
        
        from fiscallizeon.analytics.tasks import generate_student_performances_after_finish_application
        
        task = generate_student_performances_after_finish_application
        
        result = task.apply_async(task_id=f'RECALCULATE_STUDENT_PERFORMANCE_{str(self.pk)}', kwargs={
            "student_pk": self.pk,
        }).forget()
        
    def get_questions_for_list(self, subject, priority, questions_per_list=10):
        from fiscallizeon.subjects.models import Topic
        from fiscallizeon.questions.models import Question
        from fiscallizeon.applications.models import Application

        topics = Topic.objects.filter(subject=subject).distinct()
        
        all_questions = Question.objects.filter(
            subject=subject,
            category=Question.CHOICE,
            coordinations__unity__client__in=self.user.get_clients_cache()
        )
        
        questions = all_questions.exclude(
            exams__application__applicationstudent__student=self,
            exams__application__applicationstudent__end_time__isnull=True,
        ).distinct()
        
        if priority == Application.HIGH:
            _range = [0, 50]
        elif priority == Application.MEDIUM:
            _range = [0, 75]
        elif priority == Application.LOW:
            _range = [0, 100]
            
        topics_with_performances = topics.filter(
            performances__subject=subject,
            performances__student=self,
            performances__performance__range=_range,
        ).order_by('performances__performance').distinct()
        
        selected_questions = []
        
        magic_number = topics_with_performances.count() if topics_with_performances.count() else questions_per_list
        
        for i in range(0, math.ceil(questions_per_list / magic_number)):
            
            if topics_with_performances:
                for topic in topics_with_performances:
                    
                    question = questions.filter(
                        topics=topic,
                    ).exclude(
                        pk__in=selected_questions
                    ).order_by('created_at').first()
                    
                    if not question:
                        question = questions.filter(
                            topics=topics_with_performances.exclude(pk=topic.pk).order_by('?').first(),
                        ).exclude(
                            pk__in=selected_questions
                        ).order_by('created_at').first()
                    
                    if question:
                        selected_questions.append(question.pk)
                        
                    if len(selected_questions) == questions_per_list:
                        return selected_questions
                    
            else:
                return all_questions.filter(subject=subject)[:questions_per_list].values_list('pk', flat=True)
        
        return selected_questions
    
    def create_list(self, subject, priority, questions_per_list=10):
        from fiscallizeon.exams.models import Exam, ExamTeacherSubject, TeacherSubject, ExamQuestion, Question
        from fiscallizeon.applications.models import Application
        from fiscallizeon.inspectors.models import Inspector
        
        now = timezone.now() - timedelta(hours=3)
        
        filtred_applications = Application.objects.filter(
            automatic_creation=True, 
            applicationstudent__end_time__isnull=True, 
            applicationstudent__student=self, 
            exam__questions__subject=subject, 
        )
        
        if not filtred_applications.exists():
            teacher = Inspector.objects.using('default').get(
                coordinations__unity__client__in=self.user.get_clients_cache(),
                is_abstract=True,
            )
            teacher_subject, created = TeacherSubject.objects.using('default').get_or_create(
                teacher=teacher,
                subject=subject,
            )
            if teacher_subject:
                
                questions = self.get_questions_for_list(subject=subject, priority=priority)
            
                if questions:
                
                    exam = Exam.objects.create(
                        name=f'LISTA DE {subject.name.upper()}',
                        category=Exam.HOMEWORK,
                        elaboration_deadline=now.now(),
                        release_elaboration_teacher=now.now(),
                    )
                    
                    exam_teacher_subject = ExamTeacherSubject.objects.create(
                        teacher_subject=teacher_subject,
                        exam=exam,
                        quantity=questions_per_list,
                    )
                    
                    for (index, question_pk) in enumerate(questions):
                        question = Question.objects.get(pk=question_pk)
                        ExamQuestion.objects.create(
                            question=question,
                            exam=exam,
                            order=index,
                            exam_teacher_subject=exam_teacher_subject
                        )

                    application = Application.objects.create(
                        category=Application.HOMEWORK,
                        priority=priority,
                        automatic_creation=True,
                        exam=exam,
                        date=now.date(),
                        start=now.time(),
                        end=now.time(),
                        date_end=now + timedelta(days=365)
                    )

                    exam.teacher_subjects.add(teacher_subject)
                    exam.coordinations.set(self.user.get_coordinations_cache())
                    application.students.add(self)
    
    def create_lists(self):
        from fiscallizeon.subjects.models import Subject, Topic
        from fiscallizeon.applications.models import Application
        
        if self.user.client_has_automatic_creation and self.can_create_lists:
            
            subjects = Subject.objects.filter(performances__student=self, performances__isnull=False).distinct()
            
            for subject in subjects:
                
                subject_performance = subject.last_performance(student=self).first()
                
                if subject_performance:
                    if subject_performance.performance <= 50:
                        self.create_list(subject=subject, priority=Application.HIGH)
                    elif subject_performance.performance > 50 and subject_performance.performance <= 75:
                        self.create_list(subject=subject, priority=Application.MEDIUM)
                    elif subject_performance.performance > 75:
                        self.create_list(subject=subject, priority=Application.LOW)
                        
        else:
            print('NÃO PODE CRIAR LISTAS AUTOMATICAMENTE OU AINDA EXISTE LISTAS EM ABERTO')
            
    @hook('after_update', when_any=['responsible_email', 'responsible_email_two', 'responsible_email_three', 'responsible_email_four'], has_changed=True)
    def set_student_in_parent(self):
        from fiscallizeon.parents.models import Parent
        emails = []
        if self.responsible_email and "@" in self.responsible_email:
            emails.append(self.responsible_email)
            
        if self.responsible_email_two and "@" in self.responsible_email_two:
            emails.append(self.responsible_email_two)
        
        if self.responsible_email_three and "@" in self.responsible_email_three:
            emails.append(self.responsible_email_three)

        if self.responsible_email_four and "@" in self.responsible_email_four:
            emails.append(self.responsible_email_four)
        
        if emails:
            parents = Parent.objects.filter(
                email__in=emails
            )
            
            for parent in parents:
                parent.students.add(self.id)
                parent.save(skip_hooks=True)
                
                if parent.user and parent.user.is_active == False:
                    parent.user.is_active = True
                    parent.user.save()
    
    def deactive_parent(self, responsible_email):
        from fiscallizeon.parents.models import Parent
        
        if responsible_email:
            parent = Parent.objects.using('default').filter(email=responsible_email).first()
            if parent:
                childrens = parent.students.using('default').all()
                
                parent.students.set(childrens.exclude(pk=self.pk))
                parent.save(skip_hooks=True)
                
                if parent.user and not parent.students.using('default').exists():
                    parent.user.is_active = False
                    parent.user.save()
    
    @hook('after_update', when='responsible_email', has_changed=True, is_now=None)
    def deactive_parent_one(self):
        if "@" in self.initial_value('responsible_email'):
            self.deactive_parent(self.initial_value('responsible_email'))
                
    @hook('after_update', when='responsible_email_two', has_changed=True, is_now=None)
    def deactive_parent_two(self):
        if "@" in self.initial_value('responsible_email_two'):
            self.deactive_parent(self.initial_value('responsible_email_two'))

    @hook('after_update', when='responsible_email_three', has_changed=True, is_now=None)
    def deactive_parent_three(self):
        if "@" in self.initial_value('responsible_email_three'):
            self.deactive_parent(self.initial_value('responsible_email_three'))     
    
    @hook('after_update', when='responsible_email_four', has_changed=True, is_now=None)
    def deactive_parent_four(self):
        if "@" in self.initial_value('responsible_email_four'):
            self.deactive_parent(self.initial_value('responsible_email_four')) 
    
    def get_sisu_course(self):
        return self.studentsisucourse_set.order_by('created_at').last()
    
    @property
    def last_class_is_high_school(self):
        from fiscallizeon.classes.models import Grade
        last_classe = self.get_last_class()
        return last_classe and last_classe.grade.level == Grade.HIGHT_SCHOOL
    @property
    def user_is_active(self):
        return self.user and self.user.is_active
    
    def get_total_answerds(self):

        return (
            self.get_finished_application_student().get_annotation_count_answers(
                only_total_answers=True
            )
            .aggregate(
                sum_total_correct_answers=models.Sum('total_correct_answers'),
                sum_total_incorrect_answers=models.Sum('total_incorrect_answers'),
                sum_total_partial_answers=models.Sum('total_partial_answers'),
                sum_total_answers=models.Sum('total_answers'),
            )
        )

class StudentSisuCourse(BaseModel):
    student = models.ForeignKey("Student", verbose_name=("Aluno"), on_delete=models.CASCADE)
    courses_ids = ArrayField(models.IntegerField("ID do curso"))
    states = ArrayField(models.CharField("Estado", max_length=2, default="RN"))
    year = models.SmallIntegerField("Ano do curso", default=timezone.localtime(timezone.now()).year)
    
    class Meta:
        verbose_name = 'Curso escolhido no SISU'
        verbose_name_plural = 'Cursos escolhidos no SISU'