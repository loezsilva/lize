import os
import shutil
import requests
import copy
from datetime import timedelta

from simple_history.models import HistoricalRecords

from django.db import models
from django.db.models.deletion import PROTECT
from django.db.models import Case, Value, Q, When, Count, F
from django.utils import timezone

from fiscallizeon.core.storage_backends import PublicMediaStorage
from fiscallizeon.core.models import BaseModel
from fiscallizeon.accounts.models import User
from fiscallizeon.applications.models import ApplicationStudent, Application
from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.questions.models import Question
from fiscallizeon.omr.managers import OMRStudentsManager
from fiscallizeon.exams.models import ExamQuestion, Exam
from fiscallizeon.subjects.models import Subject
from django_lifecycle import hook

class OMRCategory(BaseModel):
    OTHER, FISCALLIZE, ENEM, RIO_15, RIO_18, RIO_MIRIM_15, HYBRID_025, SIMULADO_ELEVA, \
    DISCURSIVE_025, SALTA_DEFAULT, ELIT, SUM_1, OFFSET_1, SUBJECTS_1, REDUCED_MODEL, \
    ESSAY_1, SESI_32, OFFSET_SCHOOLCLASS= range(18)

    
    SEQUENTIAL_CHOICES = (
        (OTHER, "Outro"),
        (FISCALLIZE, "Fiscallize (objetivas)"),
        (ENEM, "ENEM"),
        (RIO_15, "Rio - 15 questões"),
        (RIO_18, "Rio - 18 questões"),
        (RIO_MIRIM_15, "Rio - Mirim"),
        (HYBRID_025, "Híbrido - 0.25"),
        (SIMULADO_ELEVA, "Simulado Eleva"),
        (DISCURSIVE_025, "Discursiva - 0.25"),
        (SALTA_DEFAULT, "Salta Padrão - 100 Questões"),
        (ELIT, "ELIT"),
        (SUM_1, "Somatório"),
        (OFFSET_1, "Offset"),
        (SUBJECTS_1, "EFAI"),
        (REDUCED_MODEL, "Modelo reduzido"),
        (ESSAY_1, "Modelo redação"),
        (SESI_32, "SESI"),
        (OFFSET_SCHOOLCLASS, "Offset não identificado"),
    )

    name = models.CharField(verbose_name='Nome', max_length=255)
    template = models.JSONField(verbose_name='JSON de mapeamento')
    dettached_template = models.JSONField(verbose_name='JSON de mapeamento de matrícula', blank=True, null=True)
    marker_image = models.ImageField(
        verbose_name='Imagem de marcador',
        upload_to='omr_static/',
        blank=True,
        null=True,
        storage=PublicMediaStorage()
    )
    sequential = models.PositiveSmallIntegerField(verbose_name='Sequencial interno', default=OTHER, choices=SEQUENTIAL_CHOICES)
    is_native = models.BooleanField(verbose_name='Modelo fiscallize?', default=True)
    enabled = models.BooleanField(verbose_name='Habilitado', default=True)
    supports_foreign_language = models.BooleanField(verbose_name='Tem suporte a lingua estrangeira', default=False)
    is_discursive = models.BooleanField(verbose_name='É modelo discursivo?', default=False)
    is_hybrid = models.BooleanField(verbose_name='É modelo híbrido?', help_text="Marque se for modelo de objetivas e notas de discursivas", default=False)
    discursive_grade_setps = models.PositiveSmallIntegerField(verbose_name='Número de possibilidades de nota discursiva', default=5)
    max_objectives_count = models.PositiveSmallIntegerField(verbose_name='Número máximo de questões objetivas', default=150)
    column_objectives_count = models.PositiveSmallIntegerField(verbose_name='Número máximo de questões objetivas por coluna', default=30)
    max_discursives_count = models.PositiveSmallIntegerField(verbose_name='Número máximo de questões discursivas (modelo híbrido)', default=36)
    column_discursives_count = models.PositiveSmallIntegerField(verbose_name='Número máximo de questões discursivas por coluna', default=12)


    class Meta:
        verbose_name = 'Template de gabarito'
        verbose_name_plural = 'Templates de gabarito'
        ordering = ('sequential', )
        permissions = (
            ('export_offset_answer_sheet', 'Pode exportar folha de respostas offset'),
            ('export_offset_answer_sheet_schoolclass', 'Pode exportar folha de respostas offset não identificaa'),
        )

    def __str__(self):
        return self.name

    def get_omr_marker_path(self):
        if not self.marker_image:
            return None

        tmp_omr_dir = "/tmp/fiscallizeon_omr"
        os.makedirs(tmp_omr_dir, exist_ok=True)
        
        with requests.get(self.marker_image.url, stream=True) as r:
            tmp_filepath = os.path.join(tmp_omr_dir, os.path.basename(str(self.marker_image)))
            with open(tmp_filepath, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

        return tmp_filepath

    def get_exam_json(self, exam):
        exam_questions = ExamQuestion.objects.filter(
            exam=exam,
            question__number_is_hidden=False
        ).availables()

        choice_questions_count = exam_questions.filter(question__category=Question.CHOICE).count()

        if not self.is_hybrid and not choice_questions_count:
            raise Exception('Prova sem questões objetivas')

        json_obj = copy.deepcopy(self.template)

        if exam.has_foreign_languages:
            foreign_questions_remove_count = 0
            if exam.is_abstract:
                foreign_questions = exam.get_foreign_exam_questions()
                foreign_questions_remove_count = foreign_questions.count() // 2
            elif foreign_subjects := exam.get_foreign_exam_teacher_subjects():
                foreign_questions_remove_count = foreign_subjects[0].examquestion_set.count()

            choice_questions_count -= foreign_questions_remove_count
        elif self.supports_foreign_language:
            del json_obj['Singles'][0]
            del json_obj['QBlocks']['Language']

        if self.sequential not in [self.FISCALLIZE, self.HYBRID_025, self.SUM_1, self.SUBJECTS_1, self.REDUCED_MODEL]:
            return json_obj

        questions_range = range(1, choice_questions_count + 1)
        singles = [f'q{i}' for i in questions_range]
        json_obj['Singles'] = singles

        if exam.has_foreign_languages:
            singles.insert(0, 'Language')

        if self.sequential == self.SUBJECTS_1:
            exam_questions = exam_questions.filter(question__category=Question.CHOICE)
            if exam.is_abstract:
                subject_ids = list(exam_questions.order_by('order').values_list('question__subject', flat=True))
            else:
                subject_ids = list(exam_questions.order_by(
                    'exam_teacher_subject__order', 'order'
                ).values_list(
                    'exam_teacher_subject__teacher_subject__subject', flat=True
                ))

            seen = set()
            subject_ids = [x for x in subject_ids if not (x in seen or seen.add(x))]
            subjects = Subject.objects.get_ordered_pks(subject_ids).annotate_questions_count(exam).values(
                'name', 'questions_count'
            )

            print(subjects.values('name', 'questions_count'))

            keys_remove = [f'MCQBlock{k}' for k in range(subjects.count() + 1, 11)]
            for key in keys_remove:
                del json_obj['QBlocks'][key]

            questions_index = 1
            for i, subject in enumerate(subjects, 1):
                q_nos = [[
                    [f'q{qi}' for qi in range(questions_index, questions_index + subject['questions_count'])]
                ]]
                json_obj['QBlocks'][f'MCQBlock{i}']['qNos'] = q_nos
                questions_index += subject['questions_count']

            return json_obj

        blocks = [
            len(singles[block:block+self.column_objectives_count]) 
            for block in range(0, self.max_objectives_count, self.column_objectives_count)
        ]

        for i, block in enumerate(blocks):
            if block:
                q_nos = [[
                    [f'q{i+1}' for i in range(i*self.column_objectives_count, i*self.column_objectives_count+blocks[i])]
                ]]
                json_obj['QBlocks'][f'MCQBlock{i+1}']['qNos'] = q_nos
            else:
                del json_obj['QBlocks'][f'MCQBlock{i+1}']

        if self.is_hybrid:
            discursive_questions_count = exam_questions.filter(question__category=Question.TEXTUAL).count()

            questions_range = range(1, discursive_questions_count + 1)
            singles = [f'd{i}' for i in questions_range]
            blocks = [
                len(singles[block:block+self.column_discursives_count]) 
                for block in range(0, self.max_discursives_count, self.column_discursives_count)
            ]
            
            json_obj['Singles'].extend(singles)

            for i, block in enumerate(blocks):
                if block:
                    q_nos = [[
                        [f'd{i+1}' for i in range(i*self.column_discursives_count, i*self.column_discursives_count+blocks[i])]
                    ]]
                    json_obj['QBlocks'][f'MCDBlock{i+1}']['qNos'] = q_nos
                else:
                    del json_obj['QBlocks'][f'MCDBlock{i+1}']

        elif self.sequential == self.SUM_1:
            sum_questions_count = exam_questions.filter(question__category=Question.SUM_QUESTION).count()

            keys_remove = [f'Sum{k}' for k in range(sum_questions_count + 1, 16)]
            for key in keys_remove:
                del json_obj['QBlocks'][key]
                del json_obj['Concatenations'][key]

        return json_obj

class OMRUpload(BaseModel):
    PENDING, PROCCESSING, FINISHED, ERROR, UNKNOWN, REPROCESSING = range(6)
    STATUS_CHOICES = (
        (PENDING, "Em fila"),
        (PROCCESSING, "Processando"),
        (FINISHED, "Finalizado"),
        (ERROR, "Erro"),
        (UNKNOWN, "Desconhecido"),
        (REPROCESSING, "Reprocessando"),
    )

    user = models.ForeignKey(User, verbose_name='Usuário', on_delete=PROTECT, related_name='user_upload')
    omr_category = models.ForeignKey(
        OMRCategory, 
        verbose_name='Categoria de gabarito do upload', 
        blank=True, 
        null=True,
        on_delete=models.PROTECT
    )
    status = models.PositiveSmallIntegerField(
        'Status', 
        choices=STATUS_CHOICES,
        default=PENDING
    )
    notes = models.TextField('Observações', blank=True, null=True)
    filename = models.TextField('Arquivo enviado', blank=True, null=True)
    processing_log = models.TextField('Resultado da operação', default='', blank=True, null=True)
    error_pages_count = models.PositiveSmallIntegerField('Folhas com erro', default=0)
    total_pages = models.PositiveSmallIntegerField('Páginas lidas com sucesso', default=0)
    raw_pdf = models.FileField(
        'Arquivo original',
        upload_to='omr/raw_uploads/',
        storage=PrivateMediaStorage(),
        blank=True,
        null=True
    )
    application_students = models.ManyToManyField(
        ApplicationStudent, 
        verbose_name='Alunos', 
        related_name='omr_uploads', 
        blank=True,
        through='OMRStudents'
    )
    application = models.ForeignKey(
        Application, 
        verbose_name='Aplicação associada',
        blank=True, 
        null=True,
        on_delete=models.PROTECT
    )
    school_class = models.ForeignKey(
        SchoolClass, 
        verbose_name='Turma associada',
        blank=True, 
        null=True,
        on_delete=models.PROTECT
    )
    
    ignore_qr_codes = models.BooleanField('Ignorar QR codes', default=False)
    gamma_option = models.DecimalField('Gamma aplicado', max_digits=3, decimal_places=2, blank=True, null=True)
    
    # Utilizado para a correção rápida de uploads na para 12/04/2023
    # Após o perrengue podeamos deletar essa variável...
    corrected = models.BooleanField("Marcado como já corrigido", default=False, blank=True)
    seen = models.BooleanField("Marcado como já visto", default=False, blank=True)
    deleted_at = models.DateTimeField("Data em que foi deletado", blank=True, null=True)
    deleted_by = models.ForeignKey(User, verbose_name='Usuário que deletou', related_name='deleted_by', on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        verbose_name = 'Upload de gabaritos'
        verbose_name_plural = 'Uploads de gabaritos'

    def __str__(self):
        return str(self.created_at)

    def get_full_url(self):
        return self.raw_pdf.url

    def append_processing_log(self, error_message):
        self.processing_log += error_message + '\n'
        self.error_pages_count += 1
        self.save()

    def get_unsolved_errors(self):
        return self.omrerror_set.filter(
            is_solved=False,
        )

    def get_associateds_files(self):
        return self.omrerror_set.filter(
            is_solved=True,
            is_associated_file=True,
        )

    def get_unsolved_discursive_errors(self):
        return self.omrdiscursiveerror_set.filter(
            is_solved=False,
        )
    
    @property
    def can_be_reprocessed(self):
        if not self.raw_pdf or self.omr_category or self.school_class:
            return False
        
        return self.created_at + timedelta(days=14) >= timezone.localtime(timezone.now())

    @property
    def total_errors_count(self):
        return self.get_unsolved_errors().count() + self.error_pages_count
    
    @property
    def student_page_error_count(self):
        from fiscallizeon.answers.models import OptionAnswer
        from fiscallizeon.exams.models import StatusQuestion
        
        queryset = self.omrstudents_set.prefetch_related(
            'application_student__option_answers',
            'application_student__textual_answers',
            'application_student__file_answers',
            'application_student__sum_answers',
            'application_student__empty_option_questions',
            'application_student__application__exam__examquestion__statusquestion'
        ).annotate(
            answered_optionanswers_count=Count(
                'application_student__option_answers', filter=Q(
                    Q(
                        application_student__application__exam=F('application_student__application__exam'),
                        application_student__option_answers__status=OptionAnswer.ACTIVE,
                        application_student__option_answers__question_option__question__exams=F('application_student__application__exam')
                    ),
                    ~Q(application_student__option_answers__question_option__question__examquestion__statusquestion__status__in=StatusQuestion.get_unavailables_status())
                ), distinct=True
            ),
            answered_sumanswers_count=Count(
                'application_student__sum_answers', filter=Q(
                    Q(
                        application_student__application__exam=F('application_student__application__exam'),
                        application_student__sum_answers__question__exams=F('application_student__application__exam')
                    ),
                    ~Q(application_student__sum_answers__question__examquestion__statusquestion__status__in=StatusQuestion.get_unavailables_status())
                ), distinct=True
            ),
            answered_textualanswers_count=Count(
                'application_student__textual_answers', filter=Q(
                    Q(
                        application_student__application__exam=F('application_student__application__exam'),
                        application_student__textual_answers__teacher_grade__isnull=False,
                        application_student__textual_answers__question__exams=F('application_student__application__exam')
                    ),
                    ~Q(application_student__textual_answers__exam_question__statusquestion__status__in=StatusQuestion.get_unavailables_status())
                ), distinct=True
            ),
            answered_fileanswers_count=Count(
                'application_student__file_answers', filter=Q(
                    Q(
                        application_student__application__exam=F('application_student__application__exam'),
                        application_student__file_answers__teacher_grade__isnull=False,
                        application_student__file_answers__question__exams=F('application_student__application__exam')
                    ),
                    ~Q(application_student__file_answers__exam_question__statusquestion__status__in=StatusQuestion.get_unavailables_status())
                ), distinct=True
            ),
            empty_option_questions_count=Count(
                'application_student__empty_option_questions', filter=Q(
                    Q(
                        application_student__application__exam=F('application_student__application__exam'),
                    ),
                    ~Q(application_student__empty_option_questions__examquestion__statusquestion__status__in=StatusQuestion.get_unavailables_status())
                ), distinct=True
            ),
            answered_questions_count=F('answered_optionanswers_count') + F('answered_sumanswers_count') + F('answered_textualanswers_count') + F('answered_fileanswers_count') + F('empty_option_questions_count'),
            questions_count=Count('application_student__application__exam__examquestion', filter=Q(
                Q(
                    Q(application_student__application__exam__examquestion__statusquestion__active=True) | Q(application_student__application__exam__examquestion__statusquestion__isnull=True)
                ),
                ~Q(application_student__application__exam__examquestion__statusquestion__status__in=StatusQuestion.get_unavailables_status())
            ), distinct=True),
            availables_question_count=Case(
                When(
                    Q(application_student__application__exam__is_english_spanish=True),
                    then=F('questions_count') - 5
                ),
                default=F('questions_count')
            ),
            exist_error=Case(
                When(
                    Q(
                        checked=True
                    ),
                    then=Value(False)
                ),
                When(
                    Q(
                        answered_questions_count__lt=F('availables_question_count')
                    ),
                    then=Value(True)
                ),
                default=Value(False)
            )
        )
        
        return queryset.filter(exist_error=True).count()
    
    @property
    def get_classes(self):
        return SchoolClass.objects.filter(
            Q(
                Q(students__in=self.application_students.all().values_list('student')),
                Q(school_year=self.application_students.all().order_by('application__date').last().application.date.year) if self.application_students.all() else Q()
            )
        ).distinct().select_related(
            'coordination__unity'
        )
        
    def omrstudents(self):
        return self.omrstudents_set.all().order_by('application_student__student__name')

    @hook('after_update', when='status', is_now=FINISHED)
    def recalculate_followup_dashboard(self):
        """
            TASK PARA RECALCULAR OS ARQUIVOS DO DASH
        """
        from fiscallizeon.analytics.tasks import generate_data_exam_followup_cards_task
        task = generate_data_exam_followup_cards_task
        
        exams = Exam.objects.filter(application__applicationstudent__in=self.application_students.all()).distinct()
        
        for exam in exams:
            result = task.apply_async(task_id=f'RECALCULATE_APPLICATION_FOLLOWUP_DASHBOARD_CARDS_{str(exam.pk)}', kwargs={
                "exam_pk": str(exam.pk),
            }).forget()

class OMRStudents(BaseModel):
    upload = models.ForeignKey(OMRUpload, verbose_name='Upload', on_delete=models.CASCADE)
    application_student = models.ForeignKey(ApplicationStudent, verbose_name='Aluno', on_delete=models.CASCADE)
    successful_questions_count = models.PositiveSmallIntegerField('Número de respostas contabilizadas', default=0)
    scan_image = models.ImageField(
        'Imagem do escaneamento', 
        upload_to='omr/scans/', 
        null=True, blank=True, 
        storage=PrivateMediaStorage()
    )
    checked = models.BooleanField(null=True, blank=True)
    checked_by = models.ForeignKey("accounts.User", verbose_name=("Usuário que checou"), on_delete=models.CASCADE, null=True, blank=True)
    
    history = HistoricalRecords(excluded_fields=['created_at', 'updated_at'])

    objects = OMRStudentsManager()

    class Meta:
        verbose_name = 'Aluno do upload de gabarito'
        verbose_name_plural = 'Alunos do upload de gabarito'
        
    @property
    def count_questions(self):
        
        exam = self.application_student.application.exam
        exam_questions = exam.examquestion_set.availables(exclude_annuleds=True)

        if exam.is_abstract and exam.is_english_spanish == True:
            return exam_questions.count() - 5

        first_foreign_language = exam.examteachersubject_set.filter(is_foreign_language=True).first()
        questions_first_foreign_language = exam_questions.filter(exam_teacher_subject=first_foreign_language).distinct()
        
        # Remove 
        if first_foreign_language and questions_first_foreign_language:
            exam_questions = exam_questions.exclude(pk__in=questions_first_foreign_language)
        
        return exam_questions.count()

class OMRError(BaseModel):
    OTHER, QR_UNRECOGNIZED, MARKERS_NOT_FOUND, STUDENT_NOT_FOUND, MISSING_RANDOMIZATION_VERSION, APPLICATION_NOT_FOUND = range(6)
    CATEGORY_CHOICES = (
        (QR_UNRECOGNIZED, "QRCode não identificado"),
        (MARKERS_NOT_FOUND, "Marcações não identificadas"),
        (STUDENT_NOT_FOUND, "Aplicação ou aluno não encontrado"),
        (MISSING_RANDOMIZATION_VERSION, "Versão de randomização não encontrada"),
        (APPLICATION_NOT_FOUND, "Aplicação ou caderno não encontrado(s)"),
        (OTHER, "Outro"),
    )

    upload = models.ForeignKey(OMRUpload, verbose_name='Upload', on_delete=models.CASCADE)
    omr_category = models.ForeignKey(
        OMRCategory,
        verbose_name='Categoria do OMR',
        blank=True,
        null=True,
        on_delete=models.PROTECT
    )
    student = models.ForeignKey(
        Student,
        verbose_name='Aluno',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )
    error_image = models.ImageField(
        'Imagem do escaneamento',
        upload_to='omr/scans/',
        storage=PrivateMediaStorage()
    )
    application = models.ForeignKey(
        Application,
        verbose_name='Aplicação',
        help_text='Considera essa aplicação na hora de ler os gabaritos (a aplicação do aluno será atualizada após o upload)',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )
    category = models.PositiveSmallIntegerField('Categoria', default=OTHER, choices=CATEGORY_CHOICES)
    page_number = models.PositiveSmallIntegerField('Página no documento', default=0)
    randomization_version = models.PositiveSmallIntegerField('Versão da randomização', default=0)
    is_solved = models.BooleanField('Reolvido', default=False)
    is_associated_file = models.BooleanField('É um arquivo associado ao upload', default=False)
    
    class Meta:
        verbose_name = 'Erro de leitura de gabarito'
        verbose_name_plural = 'Erros de leitura de gabarito'

class OMRDiscursiveError(BaseModel):
    OTHER, QUESTION_NOT_FOUND = range(2)
    CATEGORY_CHOICES = (
        (QUESTION_NOT_FOUND, "Questão não identificada"),
        (OTHER, "Outro"),
    )

    upload = models.ForeignKey(OMRUpload, verbose_name='Upload', on_delete=models.CASCADE)
    omr_category = models.ForeignKey(
        OMRCategory,
        verbose_name='Categoria do OMR',
        blank=True,
        null=True,
        on_delete=models.PROTECT
    )
    application_student = models.ForeignKey(ApplicationStudent, verbose_name='Aluno', on_delete=models.PROTECT)
    version_number = models.PositiveSmallIntegerField('Versão da randomização', default=0)
    category = models.PositiveSmallIntegerField('Categoria', default=OTHER, choices=CATEGORY_CHOICES)
    is_solved = models.BooleanField('Reolvido', default=False)
    error_image = models.ImageField(
        'Imagem do escaneamento',
        upload_to='omr/scans/',
        storage=PrivateMediaStorage()
    )

    class Meta:
        verbose_name = 'Erro de leitura de questão discursiva'
        verbose_name_plural = 'Erros de leitura de questões discursivas'


class OMRDiscursiveScan(BaseModel):
    omr_student = models.ForeignKey(OMRStudents, verbose_name='OMR Student', on_delete=models.CASCADE)
    upload_image = models.ImageField(
        'Imagem do escaneamento (discursiva)', 
        upload_to='omr/scans/',
        storage=PrivateMediaStorage()
    )
    image_hash = models.CharField('Hash MD5 do arquivo', default='', max_length=32, blank=True, null=True)
    is_essay = models.BooleanField('É redação', default=False)

    class Meta:
        verbose_name = 'Escaneamento de questão discursiva'
        verbose_name_plural = 'Escaneamentos de questões discursivas'