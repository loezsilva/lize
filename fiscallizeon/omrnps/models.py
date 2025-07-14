import os
import shutil
import requests

from django.db import models

from django_lifecycle import hook

from fiscallizeon.clients.models import Client
from fiscallizeon.accounts.models import User
from fiscallizeon.core.storage_backends import PrivateMediaStorage, PublicMediaStorage
from fiscallizeon.core.models import BaseModel
from django.urls import reverse

class NPSApplication(BaseModel):
    school_classes = models.ManyToManyField("classes.SchoolClass", verbose_name="Turmas", through='ClassApplication')
    nps_axis = models.ManyToManyField("NPSAxis", verbose_name="Eixo avaliado", through='NPSApplicationAxis')
    client = models.ForeignKey(Client, verbose_name="Cliente", on_delete=models.PROTECT)
    date = models.DateField("Dia da aplicação", auto_now=False, auto_now_add=False)
    name = models.CharField("Nome", max_length=255, default='Formulário de avaliação de professores')
    show_teahcer_name = models.BooleanField("Mostrar nome do professor", default=False)
    export_count = models.PositiveSmallIntegerField("Número de exportações", default=0)
    last_answer_sheet_generation = models.DateTimeField('Data da última geração de malote', blank=True, null=True)

    answer_sheet = models.FileField(
        verbose_name='Malote de folhas de resposta',
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
        'Status da exportação da folha de repsostas', 
        choices=SHEET_EXPORTING_STATUS, 
        default=WAITING
    )

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Aplicação de NPS'
        verbose_name_plural = 'Aplicações de NPS'

    @property
    def has_answers(self):
        return TeacherAnswer.objects.filter(
            nps_application_axis__nps_application=self
        ).exists()

class ClassApplication(BaseModel):
    nps_application = models.ForeignKey(NPSApplication, verbose_name="Aplicação de NPS", on_delete=models.PROTECT)
    school_class = models.ForeignKey("classes.SchoolClass", verbose_name="Turma", on_delete=models.PROTECT)

    def __str__(self):
        return f'{self.nps_application} - {self.school_class}'
    
    @hook("after_create")
    def create_teacher_orders(self):
        teacher_subjects = self.school_class.teachersubject_set.filter(
            active=True,
            school_year=self.nps_application.date.year,
            teacher__user__is_active=True,
        ).distinct()

        for index, teacher_subject in enumerate(teacher_subjects):
            TeacherOrder.objects.get_or_create(
                teacher_subject=teacher_subject,
                class_application=self,
                order=index,
            )

    @property
    def total_questions(self):
        total_teachers = self.teacherorder_set.count()
        total_axis = self.nps_application.nps_axis.count()
        return (total_teachers * total_axis if total_teachers <= 16 else 16 * total_axis)

class TeacherOrder(BaseModel):
    teacher_subject= models.ForeignKey("inspectors.TeacherSubject", verbose_name="Professor", on_delete=models.PROTECT)
    order = models.SmallIntegerField("Ordem do professor no gabarito")
    class_application = models.ForeignKey(ClassApplication, verbose_name="Applicação da turma", on_delete=models.PROTECT)

    class Meta:
        ordering = ('order',)
        unique_together = (
            ('teacher_subject', 'order', 'class_application')
        )

    def __str__(self):
        return f'{self.teacher_subject.teacher}'

class TeacherAnswer(BaseModel):
    teacher = models.ForeignKey(TeacherOrder, verbose_name="Professor", on_delete=models.CASCADE)
    grade = models.PositiveSmallIntegerField("Nota")
    nps_application_axis = models.ForeignKey("NPSApplicationAxis", verbose_name="Eixo avaliado", on_delete=models.PROTECT)
    omr_nps_page = models.ForeignKey("omrnps.OMRNPSPage", verbose_name="Folha escaneada", on_delete=models.CASCADE, blank=True, null=True)
    created_by = models.ForeignKey(User, verbose_name='Criado por', on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        verbose_name = 'Avaliação de professor'
        verbose_name_plural = 'Avaliações de professor'

    def __str__(self):
        return f'{self.teacher.teacher_subject.teacher}'

class NPSApplicationAxis(BaseModel):
    nps_axis = models.ForeignKey("NPSAxis", verbose_name="Eixo", on_delete=models.CASCADE)
    nps_application = models.ForeignKey(NPSApplication, verbose_name="APlicação do NPS", on_delete=models.CASCADE)
    order = models.SmallIntegerField("Ordem do eixo na aplicação")

    class Meta:
        unique_together = (
            ('nps_axis', 'nps_application', 'order')
        )
        ordering = ["order"]

    def __str__(self):
        return f'{self.nps_axis.name}'

class NPSAxis(BaseModel):
    name = models.CharField("Nome", max_length=70)
    description = models.CharField("Descrição", max_length=255)

    def __str__(self):
        return f'{self.name} - {self.description}'

    class Meta:
        ordering = ('name', )
        verbose_name = 'Eixo de NPS'
        verbose_name_plural = 'Eixos de NPS'

class UnityAnswer(BaseModel):
    grade = models.PositiveSmallIntegerField("Nota")
    class_application = models.ForeignKey(ClassApplication, verbose_name="Turma da aplicação", on_delete=models.PROTECT)
    omr_nps_page = models.ForeignKey("omrnps.OMRNPSPage", verbose_name="Folha escaneada", on_delete=models.CASCADE, blank=True, null=True)
    created_by = models.ForeignKey(User, verbose_name='Criado por', on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        verbose_name = 'Resposta da unidade'
        verbose_name_plural = 'Respostas da unidade'

    def __str__(self):
        return str(self.class_application)

class OMRNPSCategory(BaseModel):
    OTHER, TEACHER_5_AXIS = range(2)
    SEQUENTIAL_CHOICES = (
        (OTHER, "Outro"),
        (TEACHER_5_AXIS, "Professores (5 eixos)"),
    )

    name = models.CharField(verbose_name='Nome', max_length=255)
    template = models.JSONField(verbose_name='JSON de mapeamento')
    marker_image = models.ImageField(
        verbose_name='Imagem de marcador',
        upload_to='omr_static/',
        blank=True,
        null=True,
        storage=PublicMediaStorage()
    )
    sequential = models.PositiveSmallIntegerField(verbose_name='Sequencial interno', default=OTHER, choices=SEQUENTIAL_CHOICES)
    enabled = models.BooleanField(verbose_name='Habilitado', default=True)

    class Meta:
        verbose_name = 'Categoria de NPS'
        verbose_name_plural = 'Categorias de NPS'
        ordering = ('sequential', )
        permissions = (
            ('export_answer_sheet', 'Pode exportar folha de respostas NPS'),
        )

    def __str__(self):
        return self.name
    
    def get_omr_marker_path(self):
        if not self.marker_image:
            return None

        tmp_omr_dir = "/tmp/omrnps"
        os.makedirs(tmp_omr_dir, exist_ok=True)
        
        with requests.get(self.marker_image.url, stream=True) as r:
            tmp_filepath = os.path.join(tmp_omr_dir, os.path.basename(str(self.marker_image)))
            with open(tmp_filepath, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

        return tmp_filepath
    
    def get_template_json(self, nps_application):
        template = self.template.copy()
        total_teachers = TeacherOrder.objects.filter(
            class_application__nps_application=nps_application
        ).count()

        teachers_diff = 16 - total_teachers

        if teachers_diff > 0:
            for i in range(1 + total_teachers, 17):
                del template["QBlocks"][f"MCQBlock{i}"]

        for question in range(1, total_teachers * 5 + 1):
            if question > 80:
                break

            template["Singles"].append(f'q{question}')
        return template

class OMRNPSUpload(BaseModel):
    PENDING, PROCCESSING, FINISHED, ERROR, UNKNOWN, REPROCESSING = range(6)
    STATUS_CHOICES = (
        (PENDING, "Em fila"),
        (PROCCESSING, "Processando"),
        (FINISHED, "Finalizado"),
        (ERROR, "Erro"),
        (UNKNOWN, "Desconhecido"),
        (REPROCESSING, "Reprocessando"),
    )

    user = models.ForeignKey(User, verbose_name='Usuário', on_delete=models.PROTECT)
    status = models.PositiveSmallIntegerField(
        'Status', 
        choices=STATUS_CHOICES,
        default=PENDING
    )
    processing_log = models.TextField('Resultado da operação', default='', blank=True, null=True)
    error_pages_count = models.PositiveSmallIntegerField('Folhas com erro', default=0)
    total_pages = models.PositiveSmallIntegerField('Páginas lidas', default=0)
    raw_pdf = models.FileField(
        'Arquivo original',
        upload_to='omrnps/raw_uploads/',
        storage=PrivateMediaStorage(),
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Upload de NPS'
        verbose_name_plural = 'Upload de NPS'

    def __str__(self):
        return f'{self.user} - {self.get_status_display()}'
    
    @property
    def urls(self):
        return {
            "total_errors": reverse('omrnps:omr_nps_upload_error', kwargs={ 'pk': self.id })
        }

    def get_filename(self):
        return os.path.basename(str(self.raw_pdf)) if self.raw_pdf else ''
    
    def append_processing_log(self, error_message):
        self.processing_log += error_message + '\n'
        self.error_pages_count += 1
        self.save()

    def get_unsolved_errors(self):
        return self.omrnpserror_set.filter(
            is_solved=False
        )
    
    def get_total_errors(self):
        total_questions = 0
        
        pages = OMRNPSPage.objects.filter(
            upload=self
        )
        
        for page in pages:
            class_application = page.class_application
            total_questions += class_application.total_questions
        
        total = (
            pages
            .annotate(
                total_read_answers=models.Count('teacheranswer', filter=models.Q(teacheranswer__created_by__isnull=True)),
                total_corrected_answers=models.Count('teacheranswer', filter=models.Q(teacheranswer__created_by__isnull=False)),
            )
            .values('total_read_answers', 'total_corrected_answers')
            .aggregate(
                total=models.Sum(models.F('total_read_answers') + models.F('total_corrected_answers'), output_field=models.IntegerField())
            ).get('total') or 0
        )
        
        return total_questions - total

class OMRNPSPage(BaseModel):
    upload = models.ForeignKey(OMRNPSUpload, verbose_name='Upload', on_delete=models.CASCADE)
    class_application = models.ForeignKey(ClassApplication, verbose_name='Turma', on_delete=models.CASCADE, blank=True, null=True)
    successful_answers_count = models.PositiveSmallIntegerField('Número de respostas contabilizadas', default=0)
    scan_image = models.ImageField(
        'Imagem do escaneamento', 
        upload_to='omrnps/scans/', 
        null=True, blank=True, 
        storage=PrivateMediaStorage()
    )

    class Meta:
        verbose_name = 'Página escaneada de NPS'
        verbose_name_plural = 'Páginas escaneadas de NPS'

    def __str__(self):
        return f'{self.upload}'

class OMRNPSError(BaseModel):
    OTHER, QR_UNRECOGNIZED, MARKERS_NOT_FOUND, CLASS_NOT_FOUND = range(4)
    CATEGORY_CHOICES = (
        (OTHER, "Outro"),
        (QR_UNRECOGNIZED, "QRCode não identificado"),
        (MARKERS_NOT_FOUND, "Marcações não identificadas"),
        (CLASS_NOT_FOUND, "Turma não encontrada"),
    )

    upload = models.ForeignKey(OMRNPSUpload, verbose_name='Upload', on_delete=models.CASCADE)
    omr_category = models.ForeignKey(
        OMRNPSCategory,
        verbose_name='Categoria do upload',
        blank=True,
        null=True,
        on_delete=models.PROTECT
    )
    error_image = models.ImageField(
        'Imagem do escaneamento',
        upload_to='omr/scans/',
        storage=PrivateMediaStorage()
    )

    category = models.PositiveSmallIntegerField('Categoria', default=OTHER, choices=CATEGORY_CHOICES)
    page_number = models.PositiveSmallIntegerField('Página no documento', default=0)
    is_solved = models.BooleanField('Reolvido', default=False)

    class Meta:
        verbose_name = 'Erro de leitura de NPS'
        verbose_name_plural = 'Erros de leitura de NPS'