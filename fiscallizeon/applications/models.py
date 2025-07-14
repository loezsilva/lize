import json
import time
import mimetypes

from datetime import datetime, timedelta
from decimal import Decimal
from itertools import tee
from uuid import UUID

from django.conf import settings

from django.apps import apps
from django.db import models
from django.db.models import (
    Avg, F, Q, Sum, OuterRef, Subquery, Count, IntegerField, DecimalField, Value, ExpressionWrapper, DateTimeField, ExpressionWrapper, Case, When, BooleanField, UUIDField, CharField
)
from django.db.models.functions import Coalesce, Cast
from django.template.loader import get_template
from django.utils import timezone
from django.core.cache import cache

from fiscallizeon.applications.utils import convert_uuids
from simple_history.models import HistoricalRecords
from django_lifecycle import hook
from tinymce.models import HTMLField
from fiscallizeon.core.utils import round_half_up

from fiscallizeon.accounts.models import User
from fiscallizeon.answers.models import OptionAnswer, TextualAnswer, FileAnswer, SumAnswer
from fiscallizeon.applications.managers import (
    ApplicationStudentManager, ApplicationManager, RandomizationVersionManager, ApplicationRandomizationVersionManager
)
from fiscallizeon.applications.threadings import (
    JanusVideoRoomCreateThread, JanusVideoRoomDeleteThread
)
from fiscallizeon.bncc.utils import get_bncc
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.core.models import BaseModel
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.core.utils import get_task_celery
from fiscallizeon.distribution.models import RoomDistribution
from fiscallizeon.exams.models import Exam, ExamQuestion, StatusQuestion
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.questions.models import Question
from fiscallizeon.students.models import Student
from fiscallizeon.core.threadings.sendemail import EmailThread
from fiscallizeon.core.templatetags.cdn_url import cdn_url

from fiscallizeon.bncc.models import Abiliity, Competence
from fiscallizeon.subjects.models import Subject, Topic
from fiscallizeon.clients.models import Client

from django.contrib.contenttypes.fields import GenericRelation

from django.urls import reverse


def answer_sheet_file_directory_path(instance, filename):
    return f'applications/answer_sheets/{str(instance.pk)}/{filename}'

class Application(BaseModel):
    school_classes = models.ManyToManyField(SchoolClass, verbose_name="Adicionar alunos por turma", related_name="applications", blank=True)
    inspectors = models.ManyToManyField(Inspector, verbose_name="Fiscais que irão monitorar esta aplicação", related_name="applications", help_text="Deixe em branco caso deseja um fiscal Fiscallize" ,blank=True)
    students = models.ManyToManyField(Student, verbose_name="Adicionar alunos específicos", related_name="applications", blank=True, through="ApplicationStudent")

    exam = models.ForeignKey(Exam, verbose_name='Caderno de provas que será aplicado', null=True, blank=True, on_delete=models.PROTECT)
    
    room_distribution = models.ForeignKey(RoomDistribution, verbose_name="Ensalamento", null=True, blank=True, on_delete=models.SET_NULL)
    
    date = models.DateField("Data do início da aplicação")
    start = models.TimeField("Horário inicial da aplicação")
    end = models.TimeField("Horário final da aplicação")

    date_end = models.DateField("Data final da aplicação", null=True, blank=True)
    
    min_time_finish = models.DurationField("Tempo mínimo para finalizar prova", default="01:00:00", help_text="Formato: HH:MM:SS", blank=True)
    min_time_pause = models.DurationField("Tempo mínimo para pausar prova", default="01:00:00", help_text="Formato: HH:MM:SS", blank=True)
    max_time_tolerance = models.DurationField("Tempo de tolerância para iniciar a prova", default="00:10:00", help_text="Formato: HH:MM:SS", blank=True)
    max_time_finish = models.DurationField("Tempo máximo para realização", help_text="Formato: HH:MM:SS", blank=True,
    null=True)
    block_after_tolerance = models.BooleanField("Bloquear prova após tolerância", help_text="Marque se o aluno não poderá acessar o ambiente de prova após o tempo de tolerância", default=False)

    subject = models.CharField("Disciplinas", max_length=150, blank=True, null=True, help_text="Separe cada disciplina por virgula (,) ")
    orientations = HTMLField("Orientações para aplicação", blank=True, null=True, default="<ul><li></li></ul>")

    orchestrator_id = models.CharField("Id da aplicação no orquestrador", max_length=150, blank=True, null=True)
    prefix = models.CharField("Prefixo do domínio na Digital Ocean", max_length=150, blank=True, null=True)

    text_room_id = models.CharField("Id do ChatRoom no Janus", max_length=150, blank=True, null=True)
    text_room_pin = models.CharField("Pin do ChatRoom no Janus", max_length=150, blank=True, null=True)

    video_room_id = models.CharField("ID da Sala de video no Janus", max_length=255, blank=True, null=True, help_text="Identificador único da sala de video no Janus")
    video_room_pin = models.CharField("PIN da Sala de video no Janus", max_length=255, blank=True, null=True, help_text="Código obrigatório para entrar na sala")
    video_room_secret = models.CharField("Secret da sala de video no Janus", max_length=255, blank=True, null=True, help_text="Código necessário para editar e excluir sala")

    hide_knowledge_areas_name = models.BooleanField(
		'ocultar nome das áreas de conhecimento?',
		default=False,
		help_text='Designa se durante uma aplicação online, os nomes das áreas do conhecimento devem ser ocultados.',
	)
    hide_subjects_name = models.BooleanField(
		'ocultar nome das disciplinas?',
		default=False,
		help_text='Designa se durante uma aplicação online, os nomes das disciplinas devem ser ocultados.',
	)

    can_be_done_pc = models.BooleanField("Pode ser feito no PC", help_text="Marque se o aluno pode fazer no computador", default=True)
    can_be_done_cell = models.BooleanField("Pode ser feito no Celular", help_text="Marque se o aluno pode fazer no Celular", default=True)
    can_be_done_tablet = models.BooleanField("Pode ser feito no Tablet", help_text="Marque se o aluno pode fazer no Tablet", default=True)
    duplicate_application = models.BooleanField("Aplicação Duplicada", default=False)
    print_ready = models.BooleanField("Pronta para impressão", default=False)
    book_is_printed = models.BooleanField("Caderno já impresso", default=False)
    book_pages = models.IntegerField("Páginas do caderno", default=0)
    bag_pages = models.IntegerField("Páginas do malote", default=0)
    
    MONITORING, EXAM, MONITORIN_EXAM, PRESENTIAL, HOMEWORK = range(5)
    CATEGORY_CHOICES = (
        # (MONITORING, "Apenas Monitoramento"),
        # (EXAM, "Apenas Prova"),
        (MONITORIN_EXAM, "Online"),
        (PRESENTIAL, "Presencial"),
        (HOMEWORK, "Lista de Exercício"),
    )

    category = models.PositiveSmallIntegerField('Qual tipo de aplicação?', choices=CATEGORY_CHOICES, default=MONITORIN_EXAM)

    application_type = models.ForeignKey('ApplicationType',on_delete=models.SET_NULL, related_name='applications', null=True, blank=True, verbose_name="Tipo de aplicação", help_text="Tipo de aplicação personalizada")
    
    student_stats_permission_date = models.DateTimeField(
        verbose_name='Data para liberação dos resultados para os alunos', 
        help_text='Deixe vazio para que o resultado nunca seja liberado.',
        blank=True,
        null=True,
    )

    last_answer_sheet_generation = models.DateTimeField('Data da última geração de gabarito', blank=True, null=True)
    end_last_answer_sheet_generation = models.DateTimeField('Data final da última geração de gabarito', blank=True, null=True)
    
    answer_sheet = models.FileField(
        verbose_name='Caderno de respostas', 
        storage=PrivateMediaStorage(),
        blank=True,
        null=True,
        max_length=512
    )

    WAITING, EXPORTING, FINISHED, ERROR, OTHER = range(5)
    SHEET_EXPORTING_STATUS = (
        (WAITING, "Aguardando"),
        (EXPORTING, "Exportando"),
        (FINISHED, "Finalizado"),
        (ERROR, "Erro"),
        (OTHER, "Desconhecido"),
    )

    sheet_exporting_status = models.PositiveSmallIntegerField(
        'Status da exportação da folha de respostas', 
        choices=SHEET_EXPORTING_STATUS, 
        default=WAITING
    )

    sheet_exporting_count = models.PositiveSmallIntegerField('Quantidade de exportações', default=0)

    is_presential_sync = models.BooleanField(default=False)

    deadline_to_request_review = models.DateField("Data limite para o aluno solicitar correção da resposta", help_text="Limite para o aluno solicitar a revisão da resposta", null=True, blank=True)
    
    inspectors_fiscallize  = models.BooleanField("Fiscais da Fiscallize", help_text="Marque essa opção se deseja um fiscal Fiscallize", default=False)
    
    automatic_creation = models.BooleanField("Gerada automaticamente", default=False)
    leveling_test = models.BooleanField("Lista de nivelamento, para novos alunos", default=False)
    
    LOW, MEDIUM, HIGH = range(3)
    PRIORITY_CHOICES = (
        (LOW, 'Baixa'),
        (MEDIUM, 'Média'),
        (HIGH, 'Alta'),
    )
    priority = models.PositiveSmallIntegerField('Prioridade', choices=PRIORITY_CHOICES, default=LOW, blank=True)
    release_result_at_end = models.BooleanField('liberar resultado ao finalizar?', default=False)
    
    allow_student_redo_list = models.BooleanField('Permitir que o aluno refaça a lista', default=False)

    deadline_for_correction_of_responses = models.DateField("Data limite para os professores corrigirem as respostas", help_text="Limite para os professores corrigirem as respostas", null=True, blank=True)
    deadline_for_sending_response_letters = models.DateField("Data limite para envio dos cartões resposta", help_text="Limite para o envio dos cartões resposta", null=True, blank=True)
    
    show_result_only_for_started_application = models.BooleanField('Mostrar resultado apenas para alunos que iniciaram a prova?', default=False)

    token_online = models.CharField("Token de acesso para aplicação online", max_length=8, blank=True, null=True)

    objects = ApplicationManager()
    history = HistoricalRecords(excluded_fields=['created_at', 'updated_at'])

    def __str__(self):
        return str(self.created_at)
        
    class Meta:
        verbose_name = "Aplicação"
        verbose_name_plural = "Aplicações"
        ordering = ('-date', '-start')
        permissions = (
            ('can_disclose_application', 'Pode liberar resultado de aplicações'),
            ('can_add_and_remove_students', 'Pode adicionar ou remover alunos'),
            ('can_remove_generated_bag', 'Pode remover malote gerado'),
            ('can_duplicate_application', 'Pode duplicar aplicações'),
            ('can_print_bag_application', 'Pode imprimir malote'),
            ('can_access_print_list', 'Pode acessar a lista de impressão'),
        )

    @property
    def urls(self):
        return {
            "api_change_is_printed": reverse("applications:api-change-is-printed", kwargs={ "pk": self.pk }),
            "api_change_book_is_printed": reverse("applications:api_change_book_is_printed", kwargs={ "pk": self.pk }),
            "api_change_print_ready": reverse("applications:api_change_print_ready", kwargs={ "pk": self.pk }),
            "remove_application_exam_bag": reverse("applications:remove_application_exam_bag", kwargs={"pk": self.pk}),
            "application_pages_quantity": reverse("applications:application_pages_quantity", kwargs={"pk": self.pk}),
        }

    @property
    def urls_v3(self):
        return {
            
        }

    def count_students(self):
        return self.students.count()

    @property
    def get_subjects(self):
        from fiscallizeon.subjects.serializers.subjects import SubjectKnowledgeAreaSerializer
        subjects = SubjectKnowledgeAreaSerializer(
            Subject.objects.filter(
                pk__in=self.exam.examteachersubject_set.all().values_list(
                    'teacher_subject__subject__pk', flat=True
                )
            ).distinct(),
            many=True
        ).data
        subjects = convert_uuids(subjects)
        return json.loads(json.dumps(subjects))
        
    def _pair_iterable_for_delta_changes(self, iterable):
        a, b = tee(iterable)
        next(b, None)
        return zip(a,b)

    def changes(self):
        poll_iterator = self.history.all().order_by('history_date').iterator()
        list_changes = []
        for record_pair in self._pair_iterable_for_delta_changes(poll_iterator):
            old_record, new_record = record_pair
            delta = new_record.diff_against(old_record)

            fields = []
            for change in delta.changes:
                if change.field == 'answer_sheet':
                    storage = PrivateMediaStorage()
                    list_changes.append({
                        'history_date': new_record.history_date,
                        'history_user': new_record.history_user or 'Sistema',
                        'urls': storage.url(new_record.answer_sheet),
                        'fields': getattr(Application, change.field).field.verbose_name.capitalize()
                    })
                    continue

                fields.append(getattr(Application, change.field).field.verbose_name.capitalize())
              

            list_changes.append({
                'history_date': new_record.history_date,
                'history_user': new_record.history_user or 'Sistema',
                'fields': ', '.join(fields),
            })
            
        return reversed(list_changes)


    @property
    def date_time_start_tz(self):
        return timezone.make_aware(datetime.combine(self.date, self.start))

    @property
    def date_time_end_tz(self):
        if self.category == Application.HOMEWORK:
            return timezone.make_aware(datetime.combine(self.date_end, self.end))
        return timezone.make_aware(datetime.combine(self.date, self.end))

    @property     
    def date_time_clean_room(self):
        return self.date_time_start_tz - timedelta(minutes=10)

    @property
    def can_be_opened(self):
        start_limit = self.date_time_start_tz - timedelta(minutes=10)
        end_limit = self.date_time_end_tz
        now = timezone.localtime(timezone.now())
        return start_limit <= now <= end_limit

    @property
    def min_time_end(self):
        return self.date_time_start_tz + self.min_time_finish
    
    def get_students(self):
        return self.students.all()
    
    def create_students_applications(self):
        students = Student.objects.filter(
            classes__in=self.school_classes.all()
        ).distinct()
        self.students.set(students, clear=True)

    def create_students_rooms(self):
        if self.category in [self.MONITORING, self.MONITORIN_EXAM]:
            JanusVideoRoomCreateThread(
                ApplicationStudent.objects.using('default').filter(
                    application=self,
                ), self
            ).start()

    @hook("after_delete")
    def remove_students_rooms(self):
        if self.category in [self.MONITORING, self.MONITORIN_EXAM]:
            JanusVideoRoomDeleteThread(self).start()

    @property
    def get_status(self):
        return ""

    def missing_students_count(self, coordinations=None):
        return self.exam.get_application_students(coordinations=coordinations).filter(Q(
            Q(
                Q(application__category=Application.MONITORIN_EXAM),
                Q(start_time__isnull=True), 
                Q(end_time__isnull=True)
            ) |
            Q(
                Q(application__category=Application.PRESENTIAL),
                Q(is_omr=False)
            ) |
                Q(
                    Q(application__category=Application.HOMEWORK),
                    Q(
                        Q(option_answers__isnull=True),
                        Q(textual_answers__isnull=True),
                        Q(file_answers__isnull=True)
                    )
                )
        )).count()

    def finish_students_count(self, coordinations=None):
        return self.exam.get_application_students(coordinations=coordinations).filter(
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
            ),
        ).distinct().count()
    
    def get_all_events(self):
        from fiscallizeon.events.models import Event

        students = self.applicationstudent_set.all()
        return Event.objects.filter(
            student_application__in=students
        )

    def pauses_count(self):
        from fiscallizeon.events.models import Event
        return self.get_all_events().filter(event_type=Event.BATHROOM).count()

    @property
    def average_duration(self):
        students = self.applicationstudent_set.filter(
            start_time__isnull=False, 
            end_time__isnull=False
        ).aggregate(average=Avg(F('end_time') - F('start_time')))
        
        average = students['average']
        
        return average

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
    def is_happening(self):
        now = timezone.localtime(timezone.now())
        return self.date_time_start_tz <= now <= self.date_time_end_tz

    @property
    def is_time_finished(self):
        now = timezone.localtime(timezone.now())
        return now > self.date_time_end_tz

    @property
    def is_date_after_today(self):
        today = datetime.today()
        return self.date > today.date()
    
    @property
    def has_open_applications_exam(self):
        now = timezone.localtime(timezone.now())
        applications = self.exam.application_set.annotate(
            datetime_end = ExpressionWrapper(F('date') + F('end') + timedelta(hours=3), output_field=DateTimeField()),
            date_end_time_end = ExpressionWrapper(F('date_end') + F('end') + timedelta(hours=3), output_field=DateTimeField())
        ).filter(
            Q(
                Q(date_end_time_end__isnull=False, date_end_time_end__gte=now) |
                Q(date_end_time_end__isnull=True, datetime_end__gte=now)
            )
        )
        return applications.exists()

    @property
    def is_homework_and_can_add_student(self):
        """Verifica se a aplicação é uma lista de exercício e está acontecendo ou ainda vai acontecer"""
        return self.category == Application.HOMEWORK and (self.is_happening or self.is_date_after_today)

    @property
    def student_can_be_remove_or_add(self):
        if self.is_date_after_today and not self.answer_sheet or self.is_homework_and_can_add_student:
            return True
        return False

    def get_related_classes(self):
        application_school_classes = self.school_classes.filter(
            school_year=self.date.year,
        ).order_by(
            'coordination__unity__name','name'
        )

        avulse_application_students = self.students.exclude(
            applicationstudent__student__classes__in=application_school_classes,
        ).distinct()

        avulse_students_classes = SchoolClass.objects.filter(
            students__in=avulse_application_students,
            temporary_class=False,
            school_year=self.date.year
        ).order_by(
            'coordination__unity__name','name'
        )

        return application_school_classes.union(avulse_students_classes)

    def get_classes(self):
        from fiscallizeon.classes.models import SchoolClass
        return SchoolClass.objects.filter(
            applications=self
        ).prefetch_related(
            'coordination__unity'
        ).annotate(students_count=Count('students', filter=Q(students__in=self.students.all()))).filter(students_count__gt=0).values('pk', 'name', 'coordination__unity__name', 'students_count',  'school_year')
    
    # # @hook('after_save', when_any=['end', 'date_end'], has_changed=True)
    # def celery_task(self):
    #     from django_celery_beat.models import PeriodicTask, CrontabSchedule
        
    #     if self.category != Application.PRESENTIAL:
    #         final_date_time = timezone.localtime(timezone.make_aware(datetime.combine(self.date_end if self.date_end else self.date, self.end)))
    #         initial_date_time = timezone.localtime(timezone.make_aware(datetime.combine(self.date, self.start)))
            
    #         run_task_time = final_date_time + timedelta(hours=2)
            
    #         crontab, _ = CrontabSchedule.objects.update_or_create(
    #             periodictask__name__icontains=str(self.exam.id),
    #             defaults={
    #                 "minute": run_task_time.minute,
    #                 "hour": run_task_time.hour,
    #                 "timezone": 'America/Recife'
    #             }
    #         )
            
    #         PeriodicTask.objects.update_or_create(
    #             name__icontains=str(self.exam.id),
    #             defaults={
    #                 "name": f"Gerar performances do exam {str(self.exam.id)}",
    #                 "start_time": initial_date_time,
    #                 "crontab": crontab,
    #                 "description": 'Calcular performance dos alunos',
    #                 "task": get_task_celery('analytics', 'generate_student_performances_after_exam_finished'),
    #                 "one_off": True,
    #                 "kwargs": json.dumps({
    #                     "delete_after_run": True,
    #                     "especific_exam_pk": str(self.exam.id),
    #                 })
    #             }
    #         )
    
    @property
    def is_printed(self):
        return self.exam.is_printed if self.exam else False

    def run_recalculate_followup_task(self):
        from fiscallizeon.analytics.tasks import generate_data_exam_followup_task
        task = generate_data_exam_followup_task
        
        result = task.apply_async(task_id=f'RECALCULATE_APPLICATION_FOLLOWUP_DASHBOARD_{str(self.pk)}', kwargs={
            "exam_pk": str(self.exam.pk),
            "deadline": self.deadline_for_correction_of_responses,
            "applications_pks": [str(self.pk)],
        }).forget()
    
    @hook('after_update', when='deadline_for_correction_of_responses', has_changed=True, is_not=None)
    def change_deadline_in_genericperformances_followup(self):
        
        GenericPerformancesFollowUp = apps.get_model('analytics', 'GenericPerformancesFollowUp')
        
        old_deadline = self.initial_value('deadline_for_correction_of_responses')
        
        performances = GenericPerformancesFollowUp.objects.filter(
            object_id=self.exam.pk,
            deadline=old_deadline,
        ).update(deadline=self.deadline_for_correction_of_responses)
        
class ApplicationStudent(BaseModel):
    student = models.ForeignKey(Student, verbose_name="Aluno", on_delete=models.CASCADE)
    application = models.ForeignKey(Application, verbose_name="Aplicação", on_delete=models.CASCADE)

    start_time = models.DateTimeField('Início da prova', blank=True, null=True)
    end_time = models.DateTimeField('Término da prova', blank=True, null=True)
    custom_time_finish = models.DateTimeField('Término personalizado da prova', blank=True, null=True)

    text_room_id = models.CharField("ID da Sala de texto no Janus", max_length=255, blank=True, null=True, help_text="Identificador único da sala de texto no Janus")
    text_room_pin = models.CharField("PIN da Sala de texto no Janus", max_length=255, blank=True, null=True, help_text="Código obrigatório para entrar na sala")
    student_room_id = models.BigIntegerField("Código do aluno na sala", blank=True, null=True, help_text="Código do aluno na sala")

    justification_delay = models.TextField('Justificativa de atraso', blank=True, null=True)

    MOBILE, PC, TABLET = range(3)
    DEVICE_LIST = (
        (MOBILE, "Mobile"),
        (PC, "PC"),
        (TABLET, "Tablet")
    )
    device = models.SmallIntegerField("Tipo de dispositivo", choices=DEVICE_LIST, null=True, blank=True)
    device_family = models.CharField("Marca do dispositivo", null=True, blank=True, max_length=100)
    browser = models.CharField("Browser", null=True, blank=True, max_length=100)
    browser_version = models.CharField("Versão do Browser", null=True, blank=True, max_length=100)
    operation_system = models.CharField("Sistema operacional", null=True, blank=True, max_length=100)
    operation_system_version = models.CharField("Versão do Sistema operacional", null=True, blank=True, max_length=100)
    ip_address = models.GenericIPAddressField("Ip do Aluno", null=True, blank=True)

    empty_questions = models.PositiveIntegerField("Questões em branco", default=0)

    is_omr = models.BooleanField('Gerado por leitura de gabarito', default=False)
    read_randomization_version = models.PositiveIntegerField('Versão da randomização escaneada', default=0)
    
    feedback_after_clean = models.TextField("Feedback após zerar prova do aluno", blank=True, null=True)

    ENGLISH, SPANISH = range(2)
    FOREIGN_LANGUAGE_LIST = (
        (ENGLISH, "Inglês"),
        (SPANISH, "Espanhol"),
    )
    foreign_language = models.SmallIntegerField("Língua estrangeira escolhida", choices=FOREIGN_LANGUAGE_LIST, null=True, blank=True)
    
    performances = GenericRelation('analytics.GenericPerformances', related_query_name="applicationstudent_performance")

    email_sended_to_parent = models.BooleanField("Email enviado para o responsável", default=False)
    
    duplicated_answers = models.ManyToManyField("questions.Question", verbose_name=("Questão com respostas duplicadas"), blank=True)
    empty_option_questions = models.ManyToManyField("questions.Question", verbose_name=("Questões em branco"), related_name="empty_options", blank=True)
    missed = models.BooleanField("O aluno faltou", default=False)
    objects = ApplicationStudentManager()

    def __str__(self):
        return f'{self.student.name} - {self.application.date}'
    
    @property
    def exits_student_data(self):
        events_this_student = self.events.all().order_by('created_at')
        count_events_this_student = events_this_student.count()
        return {
            "count": count_events_this_student,
            "exits": events_this_student
        }
    
    @property
    def urls(self):
        return {
            "get_application_student_essay_question": reverse("exams:api-exam-get-application-student-essay-answer", kwargs={ "pk": self.pk }),
        }
    
    @property
    def urls_v3(self):
        return {
            "detail": reverse("app:applications-detail", kwargs={ "pk": self.pk }),
            "questions": reverse("app:applications-questions", kwargs={ "pk": self.pk }),
            "take_test": reverse("app:applications-take-test", kwargs={ "pk": self.pk }),
            "grade": reverse("app:applications-grade", kwargs={ "pk": self.pk }),
            "result": reverse("app:applications-result", kwargs={ "pk": self.pk }),
            "previous_feedback": reverse("app:applications-previous-feedback", kwargs={ "pk": self.pk }),
            "start": reverse("app:applications-start", kwargs={ "pk": self.pk }),
            "finish": reverse("app:applications-finish", kwargs={ "pk": self.pk }),
        }
    
    def get_last_class_student(self):
        school_class = self.student.classes.filter(
            pk__in=self.application.school_classes.all().values('pk')
        ).order_by(
            'school_year', 'name'
        ).last()

        return school_class if school_class else self.student.get_last_class()


    def get_status(self):    
        now = timezone.localtime(timezone.now())
        if self.missed:
            return "Ausente"
        if self.application.category == Application.PRESENTIAL:
            return "Em aberto" if self.application.date_time_start_tz >= now else "Realizado" if self.is_omr else "Ausente"
        elif self.application.category == Application.MONITORIN_EXAM:
            if self.application.date_time_start_tz >= now:
                if self.start_time and self.end_time:
                    return "Realizado"
                elif self.start_time and not self.end_time:
                    return "Realizando"
                else:
                    return "Ausente"
            else:
                return "Em aberto"
        else:
            if self.application.date_time_start_tz <= now:
                if self.start_time and self.application.date_time_end_tz <= now:
                    return "Realizado"
                elif self.start_time:
                    return "Realizando"
                else:
                    return "Ausente"
            else:
                return "Em aberto"

    @property
    def has_opened_messages(self):
        last_message = self.messages.last()
        return 1 if last_message and last_message.sender == self.student.user else 0
    
    @property
    def homework_is_time_finished(self):
        return True if self.application.category == Application.HOMEWORK and self.end_time else False

    @property
    def already_reached_max_time_finish(self):
        return self.application.category == Application.HOMEWORK and self.start_time and self.application.max_time_finish and (timezone.now() - self.start_time) > self.application.max_time_finish

    @property
    def time_left_to_finish(self):
        if self.application.max_time_finish:
            time_left = self.application.max_time_finish.seconds - ((timezone.now() - self.start_time).seconds)
            if time_left <= 0:
                return 0

            return time_left
        return None

    @property
    def date_time_start_tz(self):
        application_time_start_tz = timezone.make_aware(datetime.combine(self.application.date, self.application.start))

        if application_time_start_tz > self.created_at:
            return application_time_start_tz
        else:
            return self.created_at + timedelta(minutes=2)

    @property
    def start_time_tolerance(self):
        application_start = self.application.date_time_start_tz
        return application_start + timedelta(seconds=self.application.max_time_tolerance.seconds) 

    @property
    def is_tolerance_reached(self):
        now = timezone.now().astimezone()
        return now > self.start_time_tolerance
    
    @property
    def student_released_for_custom_time(self):
        
        # Se o resultado já foi liberado, sobrepõe o tempo final customizado
        if timezone.localtime(self.application.student_stats_permission_date) < timezone.localtime(timezone.now()):
            return False

        # Student tá liberado para fazer a application porque ele tem um custom_time e ela está dentro do prazo
        return self.custom_time_finish and self.custom_time_finish > timezone.localtime(timezone.now())
        
    @property
    def date_time_end_tz(self):

        end_time = self.custom_time_finish.time() if self.custom_time_finish else self.application.end

        if self.application.category == Application.HOMEWORK:
            return self.custom_time_finish if self.custom_time_finish else timezone.make_aware(datetime.combine(self.application.date_end, end_time))
        return timezone.make_aware(datetime.combine(self.application.date, end_time))

    @property
    def is_blocked_by_tolerance(self):
        if self.student_released_for_custom_time:
            return False
        return self.application.block_after_tolerance and self.is_tolerance_reached and not self.start_time

    @property
    def can_be_started(self):
        now = timezone.now().astimezone()
        
        application_start = self.application.date_time_start_tz - timedelta(minutes=2)

        if self.is_blocked_by_tolerance and not self.start_time:
            return False

        return now >= application_start and self.start_time == None and self.end_time == None

    def can_be_started_device(self, device=None):
        
        device = device if device != None else self.device

        if not device:
            return True

        return (device == self.MOBILE and self.application.can_be_done_cell) or \
                (device == self.PC and self.application.can_be_done_pc) or \
                (device == self.TABLET and self.application.can_be_done_tablet) 
    
    @property
    def can_be_finished(self):
        condition_one = self.start_time != None
        condition_two = timezone.localtime(timezone.now()) >= (self.application.date_time_start_tz + self.application.min_time_finish)
        condition_three = self.end_time == None

        return condition_one and condition_two and condition_three
        
    @property
    def count_opened_pauses(self):
        from fiscallizeon.events.models import Event
        if self.bathroom_events.filter(response=Event.PENDING).exists():
            return 1
        return 0

    @property
    def application_state(self):
        from fiscallizeon.events.models import Event
        
        last_event = self.events.filter(event_type=Event.BATHROOM).order_by('created_at').last()
        if self.start_time and self.end_time:
            return "finished"
        
        if not last_event:
            if not self.start_time and not self.end_time:
                return "waiting"
            elif self.start_time and not self.end_time:
                return "started"
        elif last_event.start and not last_event.end and last_event.response == Event.APPROVED:
            return "paused"
        elif last_event.start and last_event.end:
            return "started"
        else:
            return "started"

    @property
    def pending_event(self):
        from fiscallizeon.events.models import Event

        return self.events.filter(
            Q(
                Q(event_type=Event.BATHROOM),
                Q(response=Event.PENDING) |
                Q(
                    Q(response=Event.APPROVED), 
                    Q(end__isnull=True) 
                )
            )
        ).order_by('created_at').last()

    @property
    def pending_leave_event(self):
        from fiscallizeon.events.models import Event

        return self.events.filter(
            Q(
                Q(event_type=Event.LEAVE_TAB),
                Q(response=Event.PENDING)
            )
        ).last()

    def get_text_icon_device(self):
        if self.device == self.MOBILE: 
            return 'fas fa-mobile-alt'
        elif self.device == self.PC:
            return 'fas fa-desktop'
        else:
            return 'fas fa-tablet-alt'

    def get_text_icon_operation_system(self):
        if self.operation_system:
            operation_system = self.operation_system.lower()

            if operation_system in ['windows', 'linux']: 
                return f'fab fa-{operation_system.lower()}'
            elif operation_system == 'ios':
                return f'fab fa-apple'
            else:
                return '-'
        return '-'
        
    @property
    def bathroom_events(self):
        from fiscallizeon.events.models import Event
        return self.events.filter(event_type=Event.BATHROOM)

    def count_bathroom_events(self):
        return self.bathroom_events.filter(start__isnull=False, end__isnull=False).count()

    def get_question_error_reports(self):
        return self.student.user.error_reports.filter(
            application=self.application
        ).order_by('-created_at')

    def get_answered_textualanswers(self):
        from fiscallizeon.answers.models import TextualAnswer
        
        questions = self.application.exam.examquestion_set.select_related('question').filter(
            question__category=Question.TEXTUAL
        ).availables(exclude_annuleds=True).values_list('question__pk')
        
        if self.application.exam:
            return TextualAnswer.objects.select_related('question').filter(
                student_application=self,
                teacher_grade__isnull=False,
                question__in=questions
            )
        return TextualAnswer.objects.none()
    
    def get_answered_fileanswers(self):
        from fiscallizeon.answers.models import FileAnswer
        if self.application.exam:
            
            questions = self.application.exam.examquestion_set.select_related('question').filter(
                question__category=Question.FILE
            ).availables(exclude_annuleds=True).values_list('question__pk')
            
            return FileAnswer.objects.select_related('question').filter(
                student_application=self,
                teacher_grade__isnull=False,
                question__in=questions
            )
        return FileAnswer.objects.none()

    def get_answered_optionanswers(self):
        from fiscallizeon.answers.models import OptionAnswer
        
        questions = self.application.exam.examquestion_set.filter(
            question__category=Question.CHOICE
        ).availables(exclude_annuleds=True).values_list('question__pk')
        
        if self.application.exam:
            return self.option_answers.select_related('question_option').filter(
                status=OptionAnswer.ACTIVE,
                question_option__question__in=questions
            )

        return OptionAnswer.objects.none()
    
    def get_answered_sumanswers(self):
        from fiscallizeon.answers.models import SumAnswer
        
        questions = self.application.exam.examquestion_set.filter(
            question__category=Question.SUM_QUESTION
        ).availables(exclude_annuleds=True).values_list('question__pk')
        
        if self.application.exam:
            return self.sum_answers.select_related('question').filter(
                question__in=questions
            )

        return SumAnswer.objects.none()
    
    @property
    def examquestion_choices_subquery(self):
        return ExamQuestion.objects.filter(
            question=OuterRef('question_option__question'),              
            exam=OuterRef('student_application__application__exam'),
        ).availables(exclude_annuleds=True).distinct()
        
    @property
    def examquestion_subquery(self):
        return ExamQuestion.objects.filter(
            question=OuterRef('question'),              
            exam=OuterRef('student_application__application__exam'),
        ).availables(exclude_annuleds=True).distinct()
        
    def get_correct_optionanswers(self, subject=None):
        from fiscallizeon.answers.models import OptionAnswer
        if hasattr(self.application, 'exam'):
            
            options_answers = self.option_answers.filter(
                status=OptionAnswer.ACTIVE,
                question_option__is_correct=True,
                question_option__question=self.examquestion_choices_subquery.values('question')[:1]
            )
            if subject:
                options_answers = options_answers.filter(question_option__question__examquestion__exam_teacher_subject__teacher_subject__subject=subject)
                
            return options_answers.distinct()
        
        return OptionAnswer.objects.none()
        
    def get_correct_fileanswers(self, subject=None):
        from fiscallizeon.answers.models import FileAnswer
        if hasattr(self.application, 'exam'):
            
            file_answers = self.file_answers.filter(
                question=self.examquestion_subquery.values('question')[:1],
                teacher_grade__gte=self.examquestion_subquery.values('weight')[:1],
            )
            
            if subject:
                file_answers = file_answers.filter(question__examquestion__exam_teacher_subject__teacher_subject__subject=subject)
                
            return file_answers.distinct()
        
        return FileAnswer.objects.none()
    
    def get_correct_textualanswers(self, subject=None):
        from fiscallizeon.answers.models import TextualAnswer
        if hasattr(self.application, 'exam'):
            
            textual_answers = self.textual_answers.filter(
                question=self.examquestion_subquery.values('question')[:1],
                teacher_grade__gte=self.examquestion_subquery.values('weight')[:1],
            )
            
            if subject:
                textual_answers = textual_answers.filter(question__examquestion__exam_teacher_subject__teacher_subject__subject=subject)
                
            return textual_answers.distinct()
        
        return TextualAnswer.objects.none()
    
    def get_correct_partial_fileanswers(self, subject=None):
        from fiscallizeon.answers.models import FileAnswer
        if hasattr(self.application, 'exam'):
            
            
            
            file_answers = self.file_answers.filter(
                question=self.examquestion_subquery.values('question')[:1],
                teacher_grade__gt=0,
                teacher_grade__lt=self.examquestion_subquery.values('weight')[:1],
            )
            
            if subject:
                file_answers = file_answers.filter(question__examquestion__exam_teacher_subject__teacher_subject__subject=subject)
                
            return file_answers.distinct()
        
        return FileAnswer.objects.none()
    
    def get_correct_partial_textualanswers(self, subject=None):
        from fiscallizeon.answers.models import TextualAnswer
        if hasattr(self.application, 'exam'):
            
            textual_answers = self.textual_answers.filter(
                question=self.examquestion_subquery.values('question')[:1],
                teacher_grade__gt=0,
                teacher_grade__lt=self.examquestion_subquery.values('weight')[:1],
            )
            
            if subject:
                textual_answers = textual_answers.filter(question__examquestion__exam_teacher_subject__teacher_subject__subject=subject)
                
            return textual_answers.distinct()
        
        return TextualAnswer.objects.none()
    
    def get_incorrect_optionanswers(self, subject=None):
        from fiscallizeon.answers.models import OptionAnswer
        
        if hasattr(self.application, 'exam'):
            options_answers = self.option_answers.filter(
                status=OptionAnswer.ACTIVE,
                question_option__is_correct=False,
                question_option__question=self.examquestion_choices_subquery.values('question')[:1]
            )
            
            if subject:
                options_answers = options_answers.filter(question_option__question__examquestion__exam_teacher_subject__teacher_subject__subject=subject)
            
            return options_answers.distinct()
        
        return OptionAnswer.objects.none()
    
    def get_incorrect_fileanswers(self, subject=None):
        from fiscallizeon.answers.models import FileAnswer
        if hasattr(self.application, 'exam'):
            
            file_answers = self.file_answers.filter(
                question=self.examquestion_subquery.values('question')[:1],
                teacher_grade=0,
            )
            
            if subject:
                file_answers = file_answers.filter(question__examquestion__exam_teacher_subject__teacher_subject__subject=subject)
                
            return file_answers.distinct()
        
        return FileAnswer.objects.none()
    
    def get_incorrect_textualanswers(self, subject=None):
        from fiscallizeon.answers.models import TextualAnswer
        if hasattr(self.application, 'exam'):
            
            textual_answers = self.textual_answers.filter(
                question=self.examquestion_subquery.values('question')[:1],
                teacher_grade=0,
            )
            
            if subject:
                textual_answers = textual_answers.filter(question__examquestion__exam_teacher_subject__teacher_subject__subject=subject)
                
            return textual_answers.distinct()
        
        return TextualAnswer.objects.none()
    
    def total_answered_questions(self):
        total_option_answers = self.get_answered_optionanswers().count()
        total_textual_answers = self.get_answered_textualanswers().count()
        total_file_answers = self.get_answered_fileanswers().count()
        total_sum_answers = self.get_answered_sumanswers().count()
        total_empty_option_questions = self.empty_option_questions.availables(exam=self.application.exam, exclude_annuleds=True).count()

        return sum([total_option_answers, total_textual_answers, total_file_answers, total_sum_answers, total_empty_option_questions])
    
    def has_annotation_suspicion_taking_advantage(self):
        return self.annotations.filter(suspicion_taking_advantage=True).exists()

    @property
    def progress(self):
        return self.get_progress()
        
    def get_progress(self):
        Attachments = apps.get_model('answers', 'Attachments')
        OptionAnswer = apps.get_model('answers', 'OptionAnswer')
        Question = apps.get_model('questions', 'Question')

        if hasattr(self.application, 'exam'):
            exclude_questions = []
            exam = self.application.exam
            
            exam_questions = exam.examquestion_set.all().order_by('order').availables()
            
            if exam.is_english_spanish and self.foreign_language is not None:
                
                if exam.is_abstract:
                    
                    if self.foreign_language == self.ENGLISH:
                        exclude_questions = exam_questions[5:10].values_list('pk', flat=True)
                    else:
                        exclude_questions = exam_questions[0:5].values_list('pk', flat=True)
                    
                    exam_questions = exam_questions.exclude(pk__in=exclude_questions)
                    
                else:
                    
                    foreign_language_teachers = exam.examteachersubject_set.filter(is_foreign_language=True).order_by('order')
                    
                    if foreign_language_teachers:
                        if self.foreign_language == self.ENGLISH:
                            exclude_questions = foreign_language_teachers.last().examquestion_set.all().values_list('pk', flat=True)
                        else:
                            exclude_questions = foreign_language_teachers.first().examquestion_set.all().values_list('pk', flat=True)
                        
                        exam_questions = exam_questions.exclude(pk__in=exclude_questions)
            
            questions_pks = exam_questions.values_list('question__pk')
            
            resolved_questions = self.option_answers.filter(question_option__question__in=questions_pks, status=OptionAnswer.ACTIVE).distinct('question_option__question__id').count() + self.textual_answers.count()
            
            if not exam.group_attachments:
                resolved_questions += self.file_answers.filter(question__in=questions_pks).count()
            
            else:
                attachments = Attachments.objects.filter(application_student=self).values_list('exam_teacher_subject__pk', flat=True).distinct()
                exam_questions_attachments = exam_questions.filter(question__in=questions_pks, question__category=Question.FILE, exam_teacher_subject__in=attachments).count()
                resolved_questions += exam_questions_attachments
            
            if resolved_questions and exam_questions:
                return int(resolved_questions / exam_questions.count() * 100)
            
            return 0

    def get_score(self, subject=None, bncc_pk=None):
        extra_filters = Q()
        
        if subject:
            
            extra_filters = Q(
                Q(exam_teacher_subject__teacher_subject__subject=subject) |
                Q(question__subject=subject)
            )
            
            if self.application.exam and self.application.exam.is_abstract:
                extra_filters = Q(question__subject=subject)

        score = Decimal('0')

        if self.application.exam:
            all_exam_questions = self.application.exam.examquestion_set.select_related('question').filter(
                extra_filters,
            )

            exam_questions = all_exam_questions.availables(exclude_annuleds=True)

            annuled_give_score_questions = all_exam_questions

        else: 
            exam_questions = []
            annuled_give_score_questions = []
        
        if bncc_pk:
            bncc = get_bncc(bncc_pk)
            if type(bncc) == Abiliity:
                exam_questions = exam_questions.filter(question__abilities=bncc)
                annuled_give_score_questions = annuled_give_score_questions.filter(question__abilities=bncc)
            elif type(bncc) == Topic:
                exam_questions = exam_questions.filter(question__topics=bncc)
                annuled_give_score_questions = annuled_give_score_questions.filter(question__topics=bncc)
            elif type(bncc) == Competence:
                exam_questions = exam_questions.filter(question__competences=bncc)
                annuled_give_score_questions = annuled_give_score_questions.filter(question__competences=bncc)
        
        for exam_question in exam_questions:
            if exam_question.question.category == Question.CHOICE:
                option_answer = self.option_answers.select_related('question_option', 'question_option__question').filter(
                    question_option__question=exam_question.question,
                    status=OptionAnswer.ACTIVE,
                ).last()

                if (
                    option_answer
                    and option_answer.question_option.is_correct
                    and exam_question.weight
                ):
                    score += exam_question.weight
                    
            elif exam_question.question.category == Question.TEXTUAL:
                textual_answer = self.textual_answers.select_related('question').filter(
                    question=exam_question.question,
                ).last()

                if textual_answer and textual_answer.teacher_grade:
                    score += textual_answer.teacher_grade if textual_answer.teacher_grade < exam_question.weight else exam_question.weight
                    
                    
            elif exam_question.question.category == Question.FILE:
                file_answer = self.file_answers.select_related('question').filter(
                    question=exam_question.question,
                ).last()

                if file_answer and file_answer.teacher_grade:
                    score += file_answer.teacher_grade if file_answer.teacher_grade < exam_question.weight else exam_question.weight
                    
        for exam_question in annuled_give_score_questions:
            last_status = StatusQuestion.objects.filter(
                exam_question=exam_question, 
                active=True
            ).order_by(
                'created_at'
            ).last()
            if last_status and last_status.annuled_give_score:
                score += exam_question.weight
                
        return score

    def get_total_weight(self, subject=None, bncc_pk=None):
        
        if bncc_pk:
            bncc = get_bncc(bncc_pk)
            
            extra_filters = Q()
            if subject:
                extra_filters = Q(
                    Q(exam_teacher_subject__teacher_subject__subject=subject) |
                    Q(question__subject=subject)
                )
                if self.application.exam.is_abstract:
                    extra_filters = Q(question__subject=subject)
                
            exam_questions = ExamQuestion.objects.filter(
                Q(exam=self.application.exam),
                extra_filters
            ).availables(exclude_annuleds=True)
            
            if type(bncc) == Abiliity:
                exam_questions = exam_questions.filter(question__abilities=bncc)
            elif type(bncc) == Topic:
                exam_questions = exam_questions.filter(question__topics=bncc)
            elif type(bncc) == Competence:
                exam_questions = exam_questions.filter(question__competences=bncc)
            
            return {
                "questions_count": exam_questions.count(),
                "performance": exam_questions.aggregate(total_weight=Coalesce(Sum('weight'), Decimal('0')))['total_weight']
            }
        
        if not subject:
            return self.application.exam.get_total_weight() if self.application.exam else Decimal('0')
        
        extra_filters = Q()
        if subject:
            extra_filters = Q(
                Q(exam_teacher_subject__teacher_subject__subject=subject) |
                Q(question__subject=subject)
            )
            if self.application.exam.is_abstract:
                extra_filters = Q(question__subject=subject)
            
        return (
            ExamQuestion.objects.filter(
                Q(exam=self.application.exam),
                extra_filters,
            )
            .availables(exclude_annuleds=True, include_give_score=True)
            .aggregate(total_weight=Coalesce(Sum('weight'), Decimal('0')))['total_weight']
        )

    def get_performance(self, subject=None, bncc_pk=None, recalculate=False):
        
        start_process = time.time()
        
        if subject and bncc_pk:
            
            bncc = get_bncc(bncc_pk)
            
            bncc_performance = bncc.last_performance(subject=subject, student=self.student)
            
            if not recalculate and bncc_performance:
                return bncc_performance.first().performance
            
            total_weight = self.get_total_weight(subject=subject, bncc_pk=bncc_pk)
            score = round_half_up(self.get_score(subject=subject, bncc_pk=bncc_pk), 2)
            
            total_questions = total_weight['questions_count'] if total_weight['questions_count'] > 0 else 1
            
            performance = (score / round_half_up(total_weight['performance'], 2)) * 100 if total_weight['performance'] > 0 else 0
            
            process_time = time.time() - start_process
            
            if bncc_performance:
                bncc_performance.using('default').update(performance=performance, weight=total_questions, process_time=timedelta(seconds=process_time))                
            else:
                bncc.performances.create(
                    student=self.student,  
                    subject=subject,
                    performance=performance,
                    weight=total_questions,
                    process_time=timedelta(seconds=process_time),
                )
                
            return performance
        
        elif bncc_pk:
            
            bncc = get_bncc(bncc_pk)
            
            bncc_performance = bncc.last_performance(exam=self.application.exam, application_student=self)
            
            if not recalculate and bncc_performance:
                return bncc_performance.first().performance
            
            total_weight = self.get_total_weight(bncc_pk=bncc_pk)
            score = round_half_up(self.get_score(bncc_pk=bncc_pk), 2)
            total_questions = total_weight['questions_count'] if total_weight['questions_count'] > 0 else 1
            
            performance = (score / round_half_up(total_weight['performance'], 2)) * 100 if total_weight['performance'] > 0 else 0
            process_time = time.time() - start_process
            
            if bncc_performance:
                bncc_performance.using('default').update(performance=performance, weight=total_questions, process_time=timedelta(seconds=process_time))                
            else:
                bncc.performances.create(
                    application_student=self, 
                    exam=self.application.exam, 
                    performance=performance,
                    weight=total_questions,
                    process_time=timedelta(seconds=process_time),
                )
                
            return performance
        
        if subject:
            subject_performance = subject.last_performance(exam=self.application.exam, application_student=self)
            if not recalculate and subject_performance:
                return subject_performance.first().performance

            total_weight = round_half_up(self.get_total_weight(subject), 2)
            score = round_half_up(self.get_score(subject), 2)

            performance = (score / total_weight) * 100 if total_weight > 0 else 0
            process_time = time.time() - start_process

            if subject_performance:
                subject_performance.using('default').update(performance=performance, process_time=timedelta(seconds=process_time))
            else:
                subject.performances.create(
                    performance=performance, 
                    process_time=timedelta(seconds=process_time), 
                    application_student=self, 
                    exam=self.application.exam
                )
            return performance
        
        if not recalculate and self.last_performance:
            return self.last_performance.first().performance
        
        total_weight = round_half_up(self.get_total_weight(), 2)
        score = round_half_up(self.get_score(), 2)

        performance = (score / total_weight) * 100 if total_weight > 0 else 0
        process_time = time.time() - start_process
        
        if self.last_performance:
            self.last_performance.using('default').update(performance=performance, process_time=timedelta(seconds=process_time))
        else:
            self.performances.create(
                performance=performance, 
                process_time=timedelta(seconds=process_time), 
                application_student=self, 
                exam=self.application.exam
            )
        
        return performance
    
    def get_performance_v2(self, subject=None, bncc_pk=None):
        
        if subject:
            extra_filters = Q(
                Q(exam_teacher_subject__teacher_subject__subject=subject) |
                Q(question__subject=subject)
            )
            
            if self.application.exam.is_abstract:
                extra_filters = Q(question__subject=subject)
            
            total_weight = self.application.exam.get_total_weight(extra_filters=extra_filters)

        else:
            total_weight = self.application.exam.get_total_weight()

        total_grade = self.get_total_grade(subject=subject, include_give_score=False)
        
        if total_weight and total_grade:
            return round_half_up(total_grade, 2) / round_half_up(total_weight, 2) * 100
        
        return 0
    
    def get_total_grade(self, subject=None, exclude_annuleds=True, include_give_score=False):
        if application_student := ApplicationStudent.objects.filter(pk=self.pk).get_annotation_count_answers(subjects=[subject] if subject else [], only_total_grade=True, exclude_annuleds=exclude_annuleds, include_give_score=include_give_score).first():
            if not application_student.missed:
                return application_student.total_grade
        return None
    
    @property
    def last_performance(self):
        return self.performances.using('default').filter(exam=self.application.exam, application_student=self).order_by('-created_at')
    
    @property
    def can_view_grade(self):
        
        now = timezone.localtime(timezone.now())
        
        if self.application.release_result_at_end and self.start_time and self.end_time:
            return True
        
        if self.application.is_time_finished and not self.application.has_open_applications_exam:
            if self.application.student_stats_permission_date and self.application.student_stats_permission_date < now:
                return True
        
        return False
    
    def get_option_refs_subquery(self):
        ref_value = 'question_option__question__examquestion__exam_teacher_subject__teacher_subject__subject'
        ref_outer = 'exam_teacher_subject__teacher_subject__subject_id'
        if self.application.exam.is_abstract:
            ref_value = 'question_option__question__subject'
            ref_outer = 'question__subject_id'

        return ref_value, ref_outer

    def get_base_refs_subquery(self):
        ref_value = 'question__examquestion__exam_teacher_subject__teacher_subject__subject'
        ref_outer = 'exam_teacher_subject__teacher_subject__subject_id'
        if self.application.exam.is_abstract:
            ref_value = 'question__subject'
            ref_outer = 'question__subject_id'

        return ref_value, ref_outer

    def get_option_correct_subquery(self):
        ref_value, ref_outer = self.get_option_refs_subquery()

        return Subquery(
            OptionAnswer.objects.annotate(
                outer_subject_id=ExpressionWrapper(
                    OuterRef(ref_outer), output_field=UUIDField(),
                )
            )
            .filter(
                Q(**{f'{ref_value}_id': F('outer_subject_id')}) | Q(outer_subject_id=None, **{f'{ref_value}_id': None}),
                question_option__question=self.examquestion_choices_subquery.values('question')[:1],
                student_application=self,
                status=OptionAnswer.ACTIVE,
                question_option__is_correct=True,
            )
            .order_by()
            .values(ref_value)
            .annotate(count=Count('pk'))
            .values('count'),
            output_field=IntegerField(),
        )

    def get_option_incorrect_subquery(self):
        ref_value, ref_outer = self.get_option_refs_subquery()

        return Subquery(
            OptionAnswer.objects.annotate(
                outer_subject_id=ExpressionWrapper(
                    OuterRef(ref_outer), output_field=UUIDField(),
                )
            )
            .filter(
                Q(**{f'{ref_value}_id': F('outer_subject_id')}) | Q(outer_subject_id=None, **{f'{ref_value}_id': None}),
                question_option__question=self.examquestion_choices_subquery.values('question')[:1],
                student_application=self,
                status=OptionAnswer.ACTIVE,
                question_option__is_correct=False,
            )
            .order_by()
            .values(ref_value)
            .annotate(count=Count('pk'))
            .values('count'),
            output_field=IntegerField(),
        )

    def get_textual_correct_subquery(self):
        ref_value, ref_outer = self.get_base_refs_subquery()

        return Subquery(
            TextualAnswer.objects.annotate(
                outer_subject_id=ExpressionWrapper(
                    OuterRef(ref_outer), output_field=UUIDField(),
                )
            )
            .filter(
                Q(**{f'{ref_value}_id': F('outer_subject_id')}) | Q(outer_subject_id=None, **{f'{ref_value}_id': None}),
                student_application=self,
                teacher_grade=OuterRef('weight'),
            )
            .order_by()
            .values(ref_value)
            .annotate(count=Count('question__pk', distinct=True))
            .values('count'),
            output_field=IntegerField(),
        )

    def get_file_correct_subquery(self):
        ref_value, ref_outer = self.get_base_refs_subquery()

        return Subquery(
            FileAnswer.objects.annotate(
                outer_subject_id=ExpressionWrapper(
                    OuterRef(ref_outer), output_field=UUIDField(),
                )
            )
            .filter(
                Q(**{f'{ref_value}_id': F('outer_subject_id')}) | Q(outer_subject_id=None, **{f'{ref_value}_id': None}),
                question=self.examquestion_subquery.values('question')[:1],
                student_application=self,
                teacher_grade=OuterRef('weight'),
            )
            .order_by()
            .values(ref_value)
            .annotate(count=Count('pk'))
            .values('count'),
            output_field=IntegerField(),
        )

    def get_textual_incorrect_subquery(self):
        ref_value, ref_outer = self.get_base_refs_subquery()

        return Subquery(
            TextualAnswer.objects.annotate(
                outer_subject_id=ExpressionWrapper(
                    OuterRef(ref_outer), output_field=UUIDField(),
                )
            )
            .filter(
                Q(**{f'{ref_value}_id': F('outer_subject_id')}) | Q(outer_subject_id=None, **{f'{ref_value}_id': None}),
                question=self.examquestion_subquery.values('question')[:1],
                student_application=self,
                teacher_grade=Value(0),
            )
            .order_by()
            .values(ref_value)
            .annotate(count=Count('pk'))
            .values('count'),
            output_field=IntegerField(),
        )

    def get_file_incorrect_subquery(self):
        ref_value, ref_outer = self.get_base_refs_subquery()

        return Subquery(
            FileAnswer.objects.annotate(
                outer_subject_id=ExpressionWrapper(
                    OuterRef(ref_outer), output_field=UUIDField(),
                )
            )
            .filter(
                Q(**{f'{ref_value}_id': F('outer_subject_id')}) | Q(outer_subject_id=None, **{f'{ref_value}_id': None}),
                question=self.examquestion_subquery.values('question')[:1],
                student_application=self,
                teacher_grade=Value(0),
            )
            .order_by()
            .values(ref_value)
            .annotate(count=Count('pk'))
            .values('count'),
            output_field=IntegerField(),
        )

    def get_textual_partial_subquery(self):
        ref_value, ref_outer = self.get_base_refs_subquery()

        return Subquery(
            TextualAnswer.objects.annotate(
                outer_subject_id=ExpressionWrapper(
                    OuterRef(ref_outer), output_field=UUIDField(),
                )
            )
            .filter(
                Q(**{f'{ref_value}_id': F('outer_subject_id')}) | Q(outer_subject_id=None, **{f'{ref_value}_id': None}),
                student_application=self,
                teacher_grade__isnull=False,
            )
            .order_by()
            .values(ref_value)
            .annotate(count=Count('pk'))
            .values('count'),
            output_field=IntegerField(),
        )

    def get_file_partial_subquery(self):
        ref_value, ref_outer = self.get_base_refs_subquery()

        return Subquery(
            FileAnswer.objects.annotate(
                outer_subject_id=ExpressionWrapper(
                    OuterRef(ref_outer), output_field=UUIDField(),
                )
            )
            .filter(
                Q(**{f'{ref_value}_id': F('outer_subject_id')}) | Q(outer_subject_id=None, **{f'{ref_value}_id': None}),
                question=self.examquestion_subquery.values('question')[:1],
                student_application=self,
                teacher_grade__isnull=False,
            )
            .order_by()
            .values(ref_value)
            .annotate(count=Count('pk'))
            .values('count'),
            output_field=IntegerField(),
        )

    def get_option_score_subquery(self):
        ref_value, ref_outer = self.get_option_refs_subquery()

        return Subquery(
            OptionAnswer.objects.annotate(
                outer_subject_id=ExpressionWrapper(
                    OuterRef(ref_outer), output_field=UUIDField(),
                )
            )
            .filter(
                Q(**{f'{ref_value}_id': F('outer_subject_id')}) | Q(outer_subject_id=None, **{f'{ref_value}_id': None}),
                question_option__question=self.examquestion_choices_subquery.values('question')[:1],
                student_application=self,
                status=OptionAnswer.ACTIVE,
                question_option__is_correct=True,
            )
            .order_by()
            .values(ref_value)
            .annotate(score=Sum('question_option__question__examquestion__weight'))
            .values('score'),
            output_field=DecimalField(),
        )

    def get_textual_score_subquery(self):
        ref_value, ref_outer = self.get_base_refs_subquery()

        return Subquery(
            TextualAnswer.objects.annotate(
                outer_subject_id=ExpressionWrapper(
                    OuterRef(ref_outer), output_field=UUIDField(),
                )
            )
            .filter(
                Q(**{f'{ref_value}_id': F('outer_subject_id')}) | Q(outer_subject_id=None, **{f'{ref_value}_id': None}),
                question=self.examquestion_subquery.values('question')[:1],
                student_application=self,
            )
            .order_by()
            .values(ref_value)
            .annotate(score=Sum('teacher_grade'))
            .values('score'),
            output_field=DecimalField(),
        )

    def get_file_score_subquery(self):
        ref_value, ref_outer = self.get_base_refs_subquery()

        return Subquery(
            FileAnswer.objects.annotate(
                outer_subject_id=ExpressionWrapper(
                    OuterRef(ref_outer), output_field=UUIDField(),
                )
            )
            .filter(
                Q(**{f'{ref_value}_id': F('outer_subject_id')}) | Q(outer_subject_id=None, **{f'{ref_value}_id': None}),
                question=self.examquestion_subquery.values('question')[:1],
                student_application=self,
            )
            .order_by()
            .values(ref_value)
            .annotate(score=Sum('teacher_grade'))
            .values('score'),
            output_field=DecimalField(),
        )

    def get_option_correct_level_subquery(self, level):
        ref_value, ref_outer = self.get_option_refs_subquery()

        return Subquery(
            OptionAnswer.objects.annotate(
                outer_subject_id=ExpressionWrapper(
                    OuterRef(ref_outer), output_field=UUIDField(),
                )
            )
            .filter(
                Q(**{f'{ref_value}_id': F('outer_subject_id')}) | Q(outer_subject_id=None, **{f'{ref_value}_id': None}),
                question_option__question=self.examquestion_choices_subquery.values('question')[:1],
                student_application=self,
                status=OptionAnswer.ACTIVE,
                question_option__is_correct=True,
                question_option__question__level=level,
            )
            .order_by()
            .values(ref_value)
            .annotate(count=Count('pk', distinct=True))
            .values('count'),
            output_field=IntegerField(),
        )

    def get_textual_correct_level_subquery(self, level):
        ref_value, ref_outer = self.get_base_refs_subquery()

        return Subquery(
            TextualAnswer.objects.annotate(
                outer_subject_id=ExpressionWrapper(
                    OuterRef(ref_outer), output_field=UUIDField(),
                )
            )
            .filter(
                Q(**{f'{ref_value}_id': F('outer_subject_id')}) | Q(outer_subject_id=None, **{f'{ref_value}_id': None}),
                question=self.examquestion_subquery.values('question')[:1],
                student_application=self,
                teacher_grade=OuterRef('weight'),
                question__level=level,
            )
            .order_by()
            .values(ref_value)
            .annotate(count=Count('pk', distinct=True))
            .values('count'),
            output_field=IntegerField(),
        )

    def get_file_correct_level_subquery(self, level):
        ref_value, ref_outer = self.get_base_refs_subquery()

        return Subquery(
            FileAnswer.objects.annotate(
                outer_subject_id=ExpressionWrapper(
                    OuterRef(ref_outer), output_field=UUIDField(),
                )
            )
            .filter(
                Q(**{f'{ref_value}_id': F('outer_subject_id')}) | Q(outer_subject_id=None, **{f'{ref_value}_id': None}),
                question=self.examquestion_subquery.values('question')[:1],
                student_application=self,
                teacher_grade=OuterRef('weight'),
                question__level=level,
            )
            .order_by()
            .values(ref_value)
            .annotate(count=Count('pk', distinct=True))
            .values('count'),
            output_field=IntegerField(),
        )

    def get_exam_questions(self, exclude_annuleds=False):
        subquery_option_correct_easy = self.get_option_correct_level_subquery(Question.EASY)
        subquery_option_correct_medium = self.get_option_correct_level_subquery(Question.MEDIUM)
        subquery_option_correct_hard = self.get_option_correct_level_subquery(Question.HARD)
        subquery_option_correct_undefined = self.get_option_correct_level_subquery(Question.UNDEFINED)

        subquery_option_correct = self.get_option_correct_subquery()
        subquery_option_incorrect = self.get_option_incorrect_subquery()
        subquery_option_score = self.get_option_score_subquery()

        subquery_textual_correct_easy = self.get_textual_correct_level_subquery(Question.EASY)
        subquery_textual_correct_medium = self.get_textual_correct_level_subquery(Question.MEDIUM)
        subquery_textual_correct_hard = self.get_textual_correct_level_subquery(Question.HARD)
        subquery_textual_correct_undefined = self.get_textual_correct_level_subquery(Question.UNDEFINED)

        subquery_textual_correct = self.get_textual_correct_subquery()
        subquery_textual_incorrect = self.get_textual_incorrect_subquery()
        subquery_textual_partial = self.get_file_partial_subquery()
        subquery_textual_score = self.get_textual_score_subquery()

        subquery_file_correct_easy = self.get_file_correct_level_subquery(Question.EASY)
        subquery_file_correct_medium = self.get_file_correct_level_subquery(Question.MEDIUM)
        subquery_file_correct_hard = self.get_file_correct_level_subquery(Question.HARD)
        subquery_file_correct_undefined = self.get_file_correct_level_subquery(Question.UNDEFINED)

        subquery_file_correct = self.get_file_correct_subquery()
        subquery_file_incorrect = self.get_file_incorrect_subquery()
        subquery_file_partial = self.get_file_partial_subquery()
        subquery_file_score = self.get_file_score_subquery()

        extra_filters = (
            'exam_teacher_subject__teacher_subject__subject__id',
            'exam_teacher_subject__teacher_subject__subject__name',
            'exam_teacher_subject__teacher_subject__subject__knowledge_area__name',
        )
        if self.application.exam.is_abstract:
            extra_filters = (
                'question__subject__id',
                'question__subject__name',
                'question__subject__knowledge_area__name',
            )

        return (
            ExamQuestion.objects.filter(
                exam=self.application.exam,
            )
            .availables_without_distinct(exclude_annuleds=exclude_annuleds)
            .values(*extra_filters)
            .annotate(
                Count('pk', distinct=True),
                Sum('weight'),
                easy_count=Count('pk', filter=Q(question__level=Question.EASY), distinct=True),
                medium_count=Count('pk', filter=Q(question__level=Question.MEDIUM), distinct=True),
                hard_count=Count('pk', filter=Q(question__level=Question.HARD), distinct=True),
                undefined_count=Count('pk', filter=Q(question__level=Question.UNDEFINED), distinct=True),

                correct_easy_count=Coalesce(subquery_option_correct_easy, 0)+Coalesce(subquery_textual_correct_easy, 0)+Coalesce(subquery_file_correct_easy, 0),

                correct_medium_count=Coalesce(subquery_option_correct_medium, 0)+Coalesce(subquery_textual_correct_medium, 0)+Coalesce(subquery_file_correct_medium, 0),

                correct_hard_count=Coalesce(subquery_option_correct_hard, 0)+Coalesce(subquery_textual_correct_hard, 0)+Coalesce(subquery_file_correct_hard, 0),

                correct_undefined_count=Coalesce(subquery_option_correct_undefined, 0)+Coalesce(subquery_textual_correct_undefined, 0)+Coalesce(subquery_file_correct_undefined, 0),

                answer_correct__count=Coalesce(subquery_option_correct, 0)
                + Coalesce(subquery_textual_correct, 0)
                + Coalesce(subquery_file_correct, 0),
                answer_partial__count=Coalesce(subquery_textual_partial, 0)
                + Coalesce(subquery_file_partial, 0)
                - Coalesce(subquery_textual_correct, 0)
                - Coalesce(subquery_file_correct, 0)
                - Coalesce(subquery_textual_incorrect, 0)
                - Coalesce(subquery_file_incorrect, 0),
                answer_incorrect__count=Coalesce(subquery_option_incorrect, 0)
                + Coalesce(subquery_textual_incorrect, 0)
                + Coalesce(subquery_file_incorrect, 0),
                score=Coalesce(subquery_option_score, Decimal('0'))
                + Coalesce(subquery_textual_score, Decimal('0'))
                + Coalesce(subquery_file_score, Decimal('0')),
            )
        )

    def get_exam_questions_all(self):
        active_answers = OptionAnswer.objects.filter(
            question_option__question__pk=OuterRef('question__pk'),
            student_application=self,
            status=OptionAnswer.ACTIVE
        ).order_by('-created_at')

        textual_answer = TextualAnswer.objects.filter(
            question__pk=OuterRef('question__pk'),
            student_application=self,
        )

        file_answer = FileAnswer.objects.filter(
            question__pk=OuterRef('question__pk'),
            student_application=self,
        )

        return (
            ExamQuestion.objects.filter(
                exam=self.application.exam,
            )
            .availables_without_distinct()
            .annotate(
                is_correct_choice=Subquery(active_answers.values('question_option__is_correct')[:1]),
                score=Case(
                    When(question__category=Question.CHOICE, is_correct_choice=True, then=F('weight')),
                    When(question__category=Question.TEXTUAL, then=Subquery(textual_answer.values('teacher_grade')[:1])),
                    When(question__category=Question.FILE, then=Subquery(file_answer.values('teacher_grade')[:1])),
                    default=Value("0"),
                    output_field=DecimalField(),
                ),
            )
        )

    def get_exam_questions_incorrect_all(self):
        active_answers = OptionAnswer.objects.filter(
            question_option__question__pk=OuterRef('question__pk'),
            student_application=self,
            status=OptionAnswer.ACTIVE
        ).order_by('-created_at')

        textual_answer = TextualAnswer.objects.filter(
            question__pk=OuterRef('question__pk'),
            student_application=self,
        )

        file_answer = FileAnswer.objects.filter(
            question__pk=OuterRef('question__pk'),
            student_application=self,
        )

        return (
            ExamQuestion.objects.filter(
                exam=self.application.exam,
            )
            .availables_without_distinct()
            .annotate(
                is_correct_choice=Subquery(active_answers.values('question_option__is_correct')[:1]),
                teacher_grade=Case(
                    When(question__category=Question.TEXTUAL, then=Subquery(textual_answer.values('teacher_grade')[:1])),
                    When(question__category=Question.FILE, then=Subquery(file_answer.values('teacher_grade')[:1])),
                    When(question__category=Question.CHOICE, is_correct_choice=True, then=F('weight')),
                    default=Value(0.0),
                    output_field=DecimalField(),
                ),
                is_correct=Case(
                    When(question__category=Question.CHOICE, then=F('is_correct_choice')),
                    When(question__category=Question.FILE, teacher_grade=F('weight'), then=Value(True)),
                    When(question__category=Question.TEXTUAL, teacher_grade=F('weight'), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
            .filter(is_correct=False).order_by('-weight')
        )

    def get_exam_questions_easy_all(self):
        return self.get_exam_questions_incorrect_all().filter(
            question__level=Question.EASY
        )

    def check_question_perf(self):
        count_total = self.application.finish_students_count()

        eq_list = []
        for eq in ExamQuestion.objects.filter(exam=self.application.exam).availables_without_distinct():
            count_correct = 0
            student_correct = False
            student_performance = 0
            if eq.question.category == Question.CHOICE:
                count_total = OptionAnswer.objects.filter(
                    question_option__question=eq.question,
                    status=OptionAnswer.ACTIVE,
                    student_application__application__exam=self.application.exam,
                ).count()
                count_correct = (
                    OptionAnswer.objects.filter(
                        question_option__question=eq.question,
                        status=OptionAnswer.ACTIVE,
                        question_option__is_correct=True,
                        student_application__application__exam=self.application.exam,
                    ).count()
                )
                answer = OptionAnswer.objects.filter(
                    question_option__question=eq.question,
                    status=OptionAnswer.ACTIVE,
                    question_option__is_correct=True,
                    student_application=self,
                )
                if answer:
                    student_correct = True

            elif eq.question.category == Question.TEXTUAL:
                count_correct = (
                    TextualAnswer.objects.filter(
                        question=eq.question,
                        teacher_grade=eq.weight,
                        student_application__application__exam=self.application.exam,
                    ).count()
                )
                answer = TextualAnswer.objects.filter(
                    question=eq.question,
                    teacher_grade=eq.weight,
                    student_application=self,
                )
                if answer:
                    student_correct = True
                    student_performance = answer[0].teacher_grade
            elif eq.question.category == Question.FILE:
                count_correct = (
                    FileAnswer.objects.filter(
                        question=eq.question,
                        teacher_grade=eq.weight,
                        student_application__application__exam=self.application.exam,
                    ).count()
                )
                answer = FileAnswer.objects.filter(
                    question=eq.question,
                    teacher_grade=eq.weight,
                    student_application=self,
                )
                if answer:
                    student_correct = True
                    student_performance = answer[0].teacher_grade


            performance = (count_correct / count_total * 100) if count_total > 0 else 0
            if performance > 75 and not student_correct:
                eq_list.append({'object': eq, 'performance_total': performance, 'kind': 'performance'})

        return eq_list

    def get_latest_randomization_version(self):
        return self.randomization_versions.order_by('version_number').last()

    @classmethod
    def get_rank(cls, application_student, extra_filters={}, subject=None):
        queryset = cls.objects.filter(
            Q(
                Q(is_omr=True) |
                Q(start_time__isnull=False)
            )
        ).filter(
            application__exam=application_student.application.exam,
            **extra_filters
        ).distinct()

        subjects = None
        if subject:
            subjects = [subject]

        application_students = (
            queryset.get_annotation_count_answers(subjects=subjects, only_total_grade=True, exclude_annuleds=True)
            .order_by('-total_grade')
            .values_list('pk', flat=True)
        )
        total_count = int(queryset.count())
        try:
            rank = list(application_students).index(application_student.pk) + 1
            return rank, total_count
        except Exception as e:
            return total_count, total_count
    
    def get_correct_questions(self, include_partial=True, subjects_ids=None, only_partial=False):
        exam = self.application.exam
        
        exam_questions = exam.examquestion_set.availables(exclude_annuleds=True)
        
        if subjects_ids:
            exam_questions = exam_questions.filter(
                Q(question__subject__in=subjects_ids) if exam.is_abstract else Q(exam_teacher_subject__teacher_subject__subject__in=subjects_ids)
            )
            
        hits = []
        for exam_question in exam_questions:
            
            hit = {
                "id": str(exam_question.question.id),
                "category": str(exam_question.question.get_category_display()),
                "partial": False,
            }
            
            question_weight_subquery = Subquery(
                ExamQuestion.objects.filter(id=exam_question.id, exam=exam).values('weight')[:1]
            )
            
            file_answers = self.file_answers.filter(question=exam_question.question)
            textual_answers = self.textual_answers.filter(question=exam_question.question)
            
            if only_partial:
                partial_file_answers = file_answers.filter(
                    Q(teacher_grade__gt=0),
                    Q(teacher_grade__lt=question_weight_subquery),
                )
                print(partial_file_answers.values('teacher_grade'))
                partial_textual_answers = textual_answers.filter(
                    Q(teacher_grade__gt=0),
                    Q(teacher_grade__lt=question_weight_subquery),
                )
                print(partial_textual_answers.values('teacher_grade'))
                
                print(partial_file_answers.exists(), partial_textual_answers.exists())
                
                if partial_file_answers.exists() or partial_textual_answers.exists():
                    hit['partial'] = True
                    hits.append(hit)
                    
                return hits
            
            option_answers = self.get_correct_optionanswers().filter(question_option__question=exam_question.question)
            
            if include_partial:
                partial_file_answers = file_answers.filter(
                    Q(teacher_grade__gt=0),
                    Q(teacher_grade__lt=question_weight_subquery),
                )
                partial_textual_answers = textual_answers.filter(
                    Q(teacher_grade__gt=0),
                    Q(teacher_grade__lt=question_weight_subquery),
                )
                if partial_file_answers.exists() or partial_textual_answers.exists():
                    hit['partial'] = True
                    hits.append(hit)
                    
            if option_answers.exists() or file_answers.filter(teacher_grade__gte=question_weight_subquery).exists() or textual_answers.filter(teacher_grade__gte=question_weight_subquery).exists():
                hits.append(hit)
                
        return hits
    
    @hook('after_save', when='end_time', is_not=None, has_changed=True)
    def run_recalculate_student_performances(self):
        from django.core.cache import cache
        from django.core.cache.utils import make_template_fragment_key
        
        # Limpa cache do template do aluno
        cache_key = make_template_fragment_key("student_performance_dashboard", [str(self.student.id)])
        cache.delete(cache_key)
        
        if self.student.client.has_sisu_simulator:
            self.application.exam.run_recalculate_sisu_tri_cache()
        
        if self.student.client.type_client == 3: #"mentorizze"
            self.student.run_recalculate_performances()

    def get_last_answer_date(self):
        option_answer = self.option_answers.using('default').all().order_by('-updated_at').first()
        file_answer = self.file_answers.using('default').all().order_by('-updated_at').first()
        textual_answer = self.textual_answers.using('default').all().order_by('-updated_at').first()
        attachments = self.attachments.using('default').all().order_by('-updated_at').first()
        
        answers = list([])
        if option_answer:
            answers.append(datetime.strftime(option_answer.updated_at, "%s"))
        if file_answer:
            answers.append(datetime.strftime(file_answer.updated_at, "%s"))
        if textual_answer:
            answers.append(datetime.strftime(textual_answer.updated_at, "%s"))
        if attachments:
            answers.append(datetime.strftime(attachments.updated_at, "%s"))
            
        if len(answers):
            last_date_timestamp = int(sorted(answers)[len(answers) - 1])
            return datetime.strptime(str(datetime.fromtimestamp(last_date_timestamp)), "%Y-%m-%d %H:%M:%S")

        
        return None
    
    def total_corrected_answers(self):
        option_answer = self.option_answers.using('default').filter(status=OptionAnswer.ACTIVE, created_by__isnull=False)
        file_answer = self.file_answers.using('default').filter(grade__isnull=False, who_corrected__isnull=False)
        textual_answer = self.textual_answers.using('default').filter(grade__isnull=False, who_corrected__isnull=False)
        
        return option_answer.count() + file_answer.count() + textual_answer.count()
    
    def total_not_corrected_answers(self):
        option_answer = self.option_answers.using('default').filter(status=OptionAnswer.ACTIVE, created_by__isnull=True)
        file_answer = self.file_answers.using('default').filter(grade__isnull=False, who_corrected__isnull=True)
        textual_answer = self.textual_answers.using('default').filter(grade__isnull=False, who_corrected__isnull=True)
        
        return option_answer.count() + file_answer.count() + textual_answer.count()
    
    def get_files_urls(self, only_essay=False, return_object=False):
        from fiscallizeon.omr.models import OMRStudents, OMRDiscursiveScan            
        
        urls = {
            "objectives_urls": [],
            "discursive_urls": [],
            "essay_urls": [],
        }
        
        omr_students = OMRStudents.objects.filter(application_student=self).order_by('created_at')
        omr_discursives = OMRDiscursiveScan.objects.filter(omr_student__in=omr_students).order_by('created_at')
        essay_discursives = omr_discursives.filter(is_essay=True).order_by('created_at')
        
        def get_size(size):
            if size:
                return f"{size / (1024 * 1024):.2f} MB"
            return "0 MB"
        
        for i in omr_students:
            if file := i.scan_image:
                url = cdn_url(file.url)
                if return_object:
                    urls['objectives_urls'].append({
                        "name": file.name,
                        "type": mimetypes.guess_type(url)[0] or "desconhecido",
                        "date": i.created_at,
                        "size": get_size(file.size),
                        "url": url,
                    })
                else:
                    urls['objectives_urls'].append(url)
        
        discursive_hashes = []
        for i in omr_discursives:
            if (file := i.upload_image) and i.image_hash not in discursive_hashes:
                url = cdn_url(file.url)
                if return_object:
                    urls['discursive_urls'].append({
                        "name": file.name,
                        "type": mimetypes.guess_type(url)[0] or "desconhecido",
                        "date": i.created_at,
                        "size": get_size(file.size),
                        "url": url,
                    })
                else:
                    urls['discursive_urls'].append(url)
                    discursive_hashes.append(i.image_hash)
                
        essay_hashes = []
        for i in essay_discursives:
            if (file := i.upload_image) and i.image_hash not in essay_hashes:
                url = cdn_url(file.url)
                if return_object:
                    urls['essay_urls'].append({
                        "name": file.name,
                        "type": mimetypes.guess_type(url)[0] or "desconhecido",
                        "date": i.created_at,
                        "size": get_size(file.size),
                        "url": url,
                    })
                else:
                    urls['essay_urls'].append(url)
                    essay_hashes.append(i.image_hash)

        return urls
    
    def get_answers(self, question=None):
        answers = []
        
        if not question or question.category == Question.CHOICE:
            option_answers = self.option_answers.filter(
                Q(status=OptionAnswer.ACTIVE),
                Q(
                    question_option__question=question
                ) if question else Q()
            ).order_by('student_application__student__name')
            for answer in option_answers:
                answers.append({
                    'id': str(answer.id),
                    'option_answer': answer.question_option.id,
                    'is_correct': answer.question_option.is_correct,
                    'created_at': answer.created_at,
                    'created_by_name': answer.created_by.name if answer.created_by else '',
                    'teacher_grade': ExamQuestion.objects.get(exam=self.application.exam, question=answer.question_option.question).weight if answer.question_option.is_correct else 0,
                })

        if not question or question.category == Question.SUM_QUESTION:
            sum_answers = self.sum_answers.filter(
                Q(
                    question=question
                ) if question else Q()
            ).order_by('student_application__student__name')
            for answer in sum_answers:
                answers.append({
                    'id': str(answer.id),
                    'sum_value': answer.value,
                    'checked_options': list(answer.sumanswerquestionoption_set.filter(checked=True).values_list('question_option_id', flat=True)),
                    'created_at': answer.created_at,
                    'created_by_name': answer.created_by.name if answer.created_by else '',
                    'teacher_grade': ExamQuestion.objects.get(exam=self.application.exam, question=answer.question).weight * answer.grade,
                })
            
        if not question or question.category == Question.FILE:
            file_answers = self.file_answers.filter(
                Q(
                    question=question,
                ) if question else Q()    
            ).order_by('student_application__student__name')
            for answer in file_answers:
                suggestions = []
                if answer.ai_grade is not None and answer.ai_teacher_feedback:
                    suggestions.append({
                        'grade': answer.ai_grade,
                        'comment': answer.ai_teacher_feedback,
                        'teacher_feedback': answer.ai_student_feedback,
                    })
                
                # Adicionado em 04/07/2025 para resolver um problema na 
                # exibição de respostas do aluno no caderno randomizado
                exam_question_id = answer.exam_question.id

                answered_exam_question_id = exam_question_id
                
                randomization_version: RandomizationVersion = (
                    self.get_latest_randomization_version()
                )

                if randomization_version:
                    answered_exam_question_id = randomization_version.get_correct_answered_exam_question_id(
                        exam_question_id
                    ) 

                answers.append({
                    'id': str(answer.id),
                    'file': cdn_url(answer.arquivo.url) if answer.arquivo else None,
                    'teacher_grade': answer.teacher_grade,
                    'percent_grade': answer.grade,
                    'teacher_feedback': answer.teacher_feedback,
                    'img_annotations': answer.img_annotations if answer.img_annotations else [],
                    'suggestions': suggestions,
                    'answered_exam_question_id': answered_exam_question_id, # Relacionado ao 
                })
            
        if not question or question.category == Question.TEXTUAL:
            textual_answers = self.textual_answers.filter(
                Q(
                    question=question,
                ) if question else Q()    
            ).order_by('student_application__student__name')
            for answer in textual_answers:
                answers.append({
                    'id': str(answer.id),
                    'teacher_grade': answer.teacher_grade,
                    'percent_grade': answer.grade,
                    'teacher_feedback': answer.teacher_feedback,
                    'text': answer.content,
                })
            
        return answers
    
    def get_total_correct_answers(self, subject=None):
        return self.get_correct_optionanswers(subject=subject).count() + self.get_correct_fileanswers(subject=subject).count() + self.get_correct_textualanswers(subject=subject).count()
        
    def get_total_incorrect_answers(self, subject=None):
        return self.get_incorrect_optionanswers(subject=subject).count() + self.get_incorrect_fileanswers(subject=subject).count() + self.get_incorrect_textualanswers(subject=subject).count()
        
    def get_total_correct_partial_answers(self, subject=None):
        return self.get_correct_partial_fileanswers(subject=subject).count() + self.get_correct_partial_textualanswers().count()

    def can_be_corrected(self, teacher=None):
        now = timezone.localtime(timezone.now())

        deadline_exception = self.application.deadline_exceptions.filter(teacher=teacher).first()
        if teacher and deadline_exception:
            return deadline_exception.date >= now.date()

        if self.application.deadline_for_correction_of_responses:
            if self.application.deadline_for_correction_of_responses < now.date():
                return False
        return True


class Annotation(BaseModel):
    application_student = models.ForeignKey(ApplicationStudent, verbose_name="Aluno", on_delete=models.CASCADE, related_name="annotations")
    inspector = models.ForeignKey(User, verbose_name="Fiscal", on_delete=models.CASCADE)
    annotation = models.TextField("Anotação", max_length=255)
    suspicion_taking_advantage = models.BooleanField("Suspeita obtenção de vantagem", default=False)

    class Meta:
        verbose_name = "Anotação de aluno"
        verbose_name_plural = "Anotações de alunos"
        ordering = ('-created_at',)


class ApplicationAnnotation(BaseModel):
    application = models.ForeignKey(Application, verbose_name="Aplicação", on_delete=models.CASCADE, related_name="annotations")
    inspector = models.ForeignKey(User, verbose_name="Fiscal", on_delete=models.CASCADE)
    annotation = models.TextField("Anotação", max_length=255)

    class Meta:
        verbose_name = "Anotação de aplicação"
        verbose_name_plural = "Anotações de aplicações"
        ordering = ('-created_at',)


class ApplicationNotice(BaseModel):
    application = models.ForeignKey(Application, verbose_name="Aplicação", on_delete=models.CASCADE, related_name="notices")
    inspector = models.ForeignKey(User, verbose_name="Fiscal", on_delete=models.CASCADE)
    notice = models.TextField("Aviso", max_length=255)

    class Meta:
        verbose_name = "Aviso de aplicação"
        verbose_name_plural = "Avisos de aplicações"
        ordering = ('-created_at',)


class ApplicationRandomizationVersion(BaseModel):
    application = models.ForeignKey(
        Application,
        verbose_name="Aplicação",
        on_delete=models.CASCADE,
        related_name="randomization_versions"
    )
    version_number = models.PositiveSmallIntegerField("Versão", default=1)
    sequential = models.PositiveSmallIntegerField("Sequencial")
    exam_json = models.JSONField("Questões")
    exam_hash = models.CharField('Hash da prova no momento da geração', max_length=32, blank=True, null=True)

    objects = ApplicationRandomizationVersionManager()

    class Meta:
        verbose_name = "Versão da randomização de aplicação"
        verbose_name_plural = "Versões das randomizações de aplicação"
        unique_together = ('application', 'version_number', 'sequential')


class RandomizationVersion(BaseModel):
    application_randomization_version = models.ForeignKey(
        ApplicationRandomizationVersion,
        verbose_name="Randomização da aplicação",
        on_delete=models.CASCADE,
        related_name="student_randomization_versions",
        blank=True,
        null=True,
    )
    application_student = models.ForeignKey(
        ApplicationStudent,
        verbose_name="Aluno",
        on_delete=models.CASCADE,
        related_name="randomization_versions"
    )
    version_number = models.PositiveSmallIntegerField("Versão", default=1)
    exam_json = models.JSONField("Questões")

    objects = RandomizationVersionManager()

    class Meta:
        verbose_name = "Versão da randomização"
        verbose_name_plural = "Versões das randomizações"
        unique_together = ('application_student', 'version_number')

    def get_exam_questions_ids(self):

        exam_json = self.exam_json
        exam_questions = []
        
        for exam_teacher_subject in exam_json['exam_teacher_subjects']:
            for exam_question in exam_teacher_subject['exam_questions']:
                exam_questions.append(exam_question['pk'])

        return exam_questions
    
    def get_correct_answered_exam_question_id(self, answer_exam_question_id):
        exam_questions = self.get_exam_questions_ids()
        exam_question_index = exam_questions.index(str(answer_exam_question_id))
        
        exam_question_id = str(
            list(
                self.application_student.application.exam.examquestion_set.availables().order_by(
                'exam_teacher_subject__order', 'order'
                ).values_list('id', flat=True)
            )[exam_question_index]
        )
        
        return exam_question_id
    
class ApplicationType(BaseModel):
    name = models.CharField("Nome", max_length=255)
    created_by = models.ForeignKey(User, verbose_name="Criado por", on_delete=models.CASCADE, related_name="application_types")
    client = models.ForeignKey(Client, verbose_name="Cliente", on_delete=models.CASCADE, related_name="application_types")

    def __str__(self):
        return f"{self.name}"
    
    def get_absolute_url(self):
        return reverse('applications:type_application_list') 

class HashAccess(BaseModel):
    application_student = models.ForeignKey(ApplicationStudent, verbose_name="Aplicação do aluno", on_delete=models.CASCADE, related_name="hash_accesses")
    validity = models.DateField("Validade de acesso", default=timezone.now)

    class Meta:
        verbose_name = "Hash de acesso"
        verbose_name_plural = "Hashes de acesso"
        
    @hook("after_create")
    def send_notify_parent_when_result_open(self):
        if self.application_student.student.responsible_email:
            template = get_template('mail_template/send_notify_parent_when_result_open.html')
            html = template.render({"object":self, "email":True, "BASE_URL": settings.BASE_URL})
            subject = f'Resultado da avaliação - {self.application_student.application.exam.name.upper()}'
            to = [self.application_student.student.responsible_email]
            EmailThread(subject, html, to, self.application_student).start()


class ApplicationDeadlineCorrectionResponseException(BaseModel):
    application = models.ForeignKey(
        Application,
        verbose_name='aplicação',
        on_delete=models.CASCADE,
        related_name='deadline_exceptions',
    )
    teacher = models.ForeignKey(
        Inspector,
        verbose_name='professor',
        on_delete=models.CASCADE,
        related_name='deadline_exceptions',
    )
    date = models.DateField('tempo limite para correção das respostas')

    class Meta:
        verbose_name_plural = 'exceções da data limite para professores corrigirem respostas'
        verbose_name = 'exceção da data limite para professores corrigirem respostas'
        ordering = ('-created_at',)
        unique_together = ('application', 'teacher')

    def __str__(self):
        return f'{self.teacher} - {self.application} - {self.date}'
