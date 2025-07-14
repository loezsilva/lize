from email.mime import image
import re

from itertools import tee

from django.db import models
from django.db.models import Q
from django.db.models.functions import Now
from django.db.models.fields import DateTimeField
from django.db.models.expressions import ExpressionWrapper, F
from django.shortcuts import resolve_url as r
from django.conf import settings
from django.utils.functional import cached_property

from django.utils import timezone
from django.utils.html import strip_tags

from django.core.cache import cache

from django_lifecycle import hook, AFTER_UPDATE

from tinymce.models import HTMLField

from simple_history.models import HistoricalRecords
from fiscallizeon.core.models import BaseModel
from fiscallizeon.classes.models import Grade
from fiscallizeon.accounts.models import User
from fiscallizeon.subjects.models import Topic, Subject
from fiscallizeon.bncc.models import Abiliity, Competence
from fiscallizeon.clients.models import QuestionTag, SchoolCoordination
from fiscallizeon.questions.managers import QuestionManager
from fiscallizeon.corrections.models import TextCorrection
from fiscallizeon.answers.tasks.update_answers_grades import update_sum_answers_grades
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.inspectors.models import Inspector
from django.core.exceptions import ValidationError

from django.urls import reverse



class Question(BaseModel):
    topic = models.ForeignKey(Topic, verbose_name='Tópico/Assunto', on_delete=models.CASCADE, null=True, blank=True)
    topics = models.ManyToManyField(Topic, verbose_name="Assuntos abordados", related_name="questions", blank=True)
    subject = models.ForeignKey(Subject, verbose_name='Disciplina', on_delete=models.CASCADE, null=True, blank=True)
    # comentar essa linha depois do migrate
    # coordination = models.ForeignKey(SchoolCoordination, verbose_name="Coordenação", on_delete=models.CASCADE, null=True, blank=True)
    coordinations = models.ManyToManyField(SchoolCoordination, verbose_name="Coordenações autorizadas", related_name="questions", help_text="Selecione as coordenações que terão acesso a essa questão")

    abilities = models.ManyToManyField(Abiliity, verbose_name="Habilidades", blank=True)
    competences = models.ManyToManyField(Competence, verbose_name="Competências", blank=True)
    grade = models.ForeignKey(Grade, verbose_name='Ano/Série', on_delete=models.CASCADE, null=True, blank=True)
    
    board = models.CharField('Banca', max_length=255, null=True, blank=True)
    institution = models.CharField('Instituição', max_length=255, null=True, blank=True)
    elaboration_year = models.PositiveIntegerField('Ano de elaboração', blank=True, null=True)
    is_public = models.BooleanField('É pública', default=False)

    is_abstract = models.BooleanField('A questão é abstrata, usada apenas na geração de gabarito avulso', default=False)
    
    source_question = models.ForeignKey('Question', verbose_name='Questão original', on_delete=models.CASCADE, null=True, blank=True, related_name="question_copies")
    
    TEXTUAL, CHOICE, FILE, SUM_QUESTION, CLOZE = range(5)
    CATEGORY_TYPES = (
        (TEXTUAL, 'Discursiva'),
        (CHOICE, 'Objetiva'),
        (FILE, 'Arquivo anexado'),
        (SUM_QUESTION, 'Somatório'),
        (CLOZE, 'Preencher lacunas'),
    )
    EASY, MEDIUM, HARD, UNDEFINED = range(4)
    LEVEL_CHOICES = (
        (EASY, "Fácil"),
        (MEDIUM, "Médio"),
        (HARD, "Difícil"),
        (UNDEFINED, "Indefinido"),
    )
    level = models.PositiveSmallIntegerField('Nível de dificuldade', choices=LEVEL_CHOICES, default=UNDEFINED)
    enunciation = HTMLField('Enunciado da questão')
    category = models.PositiveSmallIntegerField('Tipo da questão', choices=CATEGORY_TYPES, default=CHOICE)
    commented_awnser = HTMLField('Resposta comentada', blank=True, null=True)
    feedback = HTMLField('Feedback do professor', blank=True, null=True)

    created_by = models.ForeignKey(User, verbose_name="Criado por", null=True, blank=True, on_delete=models.PROTECT)
    
    base_texts = models.ManyToManyField('questions.BaseText', verbose_name=("Textos base da questão"), blank=True)

    objects = QuestionManager()
    
    print_only_enunciation = models.BooleanField("Imprimir apenas enunciado", default=False, help_text="Marque esta opção se deseja remover o espaço para resposta do aluno (aplicável apenas para questões discursivas).")
    is_essay = models.BooleanField("É uma redação", default=False, help_text='Marcando esta opção o malote de provas será impresso com uma folha de redação.')
    theme = models.CharField("Tema da redação", help_text="Se a questão for redação você deve digitar o tema", max_length=512, blank=True, null=True)
    
    BLANK_SPACE, LINE = range(2)
    TEXT_QUESTION_FORMATS = (
        (BLANK_SPACE, 'Espaço em branco'),
        (LINE, 'Imprimir linhas'),
    )
    text_question_format = models.PositiveSmallIntegerField(
        'Tipo de impressão de linhas',
        choices=TEXT_QUESTION_FORMATS,
        default=BLANK_SPACE,
    )
    
    quantity_lines = models.PositiveSmallIntegerField('Quantidade de linhas', default=5, help_text="Defina a quantidade  de linhas que será impressa caso seja uma questão discursiva")
    draft_rows_number = models.PositiveSmallIntegerField('Quantidade de linhas para rascunho.', default=0, help_text="Caso deseje adicionar ao caderno uma área para rascunho ou cálculos, informe um valor maior que zero")
    break_enunciation = models.BooleanField("Permitir quebra do enunciado", default=False, help_text="Marque se deseja permitir que o enunciado seja quebrado na página ou coluna quando possível.")
    break_alternatives = models.BooleanField("Permitir quebra das alternativas", default=False, help_text="Marque se deseja permitir que as alternativas sejam quebradas na página ou coluna quando possível.")
    force_one_column = models.BooleanField("Forçar uma coluna", default=False, help_text="Marque esta opção se desejar que a questão seja impressa em uma coluna, independente do tipo do tipo de prova.")
    
    force_break_page = models.BooleanField("Forçar quebra de página", default=False, help_text="Marque esta opção se desejar que a questão esteja obrigatoriamente na próxima página.")
    number_is_hidden = models.BooleanField("Não mostrar numeração", default=False, help_text="Marque esta opção se desejar que a questão não seja impressa com a numeração.")
    force_choices_with_statement = models.BooleanField(
		'Forçar alternativas junto ao enunciado.',
		default=False,
		help_text='As alternativas de cada questão serão exibidas imediatamente junto ao enunciado. (Quebra de enunciado será desconsiderado.)',
	)

    adapted = models.BooleanField("Adaptada", default=False, help_text="Questão adaptada?")

    history = HistoricalRecords(cascade_delete_history=True, excluded_fields=['created_at', 'updated_at'])
    text_correction = models.ForeignKey(TextCorrection, verbose_name="Template de correção", on_delete=models.CASCADE, null=True, blank=True)
	
    support_content_question = HTMLField('Conteudo de apoio à resposta', blank=True, null=True)
    
    SUPPORT_CONTENT_POSITION_CHOICES = [
        ('center', 'Centralizado'),
        ('left', 'À Esquerda'),
        ('right', 'À Direita'),
    ]
    support_content_position = models.CharField(
        max_length=10,
        choices=SUPPORT_CONTENT_POSITION_CHOICES,
        default='center',
        blank=True, 
        null=True,  
    )
    
    answer_video = models.URLField("Link da resposta em vídeo", null=True, blank=True)
    PANDA, YOUTUBE = range(2)
    ANSWER_VIDEO_TYPE_CHOICE = (
        (PANDA, "Panda Vídeo"),
        (YOUTUBE, "Youtube")
    )
    answer_video_type = models.SmallIntegerField("Fonte do vídeo", choices=ANSWER_VIDEO_TYPE_CHOICE, default=YOUTUBE, null=True, blank=True)
    superpro_id = models.IntegerField(
        'ID da questão no Super Professor', null=True, blank=True
    )

    created_with_ai = models.BooleanField("Criada com inteligencia artificial", default=False, blank=True)

    cloze_content = models.CharField(
        "Conteúdo da questão de preenchimento de lacunas",
        max_length=1000,
        blank=True,
        null=True,
        help_text="Utilize o formato [[opção]] para definir lacunas"
    )
    incorrect_cloze_alternatives = models.CharField(
        "Alternativas incorretas da questão de preenchimento de lacunas",
        max_length=1000,
        blank=True,
        null=True,
        help_text="Informe as alternativas separadas por vírgula"
    )

    class Meta:
        verbose_name = 'Questão'
        verbose_name_plural = 'Questões'
        permissions = (
            ('can_duplicate_question', 'Pode duplicar questões'),
            ('can_add_subject_question', 'Pode cadastrar assuntos na criação de cadernos'),
            ('can_add_ability_and_competence_question', 'Pode cadastrar habilidade e competência na criação de cadernos')

        )

    def __str__(self):
        return f'{self.grade or "Sem série"} - {strip_tags(self.enunciation)}'
    
    def clean(self):
        # Tivemos problema com o caracter: (-) em formulas matemáticas como (P=2n-¹) onde no front era mostrado um caracter [] (Quabradinho)
        # A idéia é substituir n-¹ por <sup></sup> que é bem entendido pelo HTML, e faz basicamente a mesma coisa.
        # task: https://app.clickup.com/t/86a78210r
        self.enunciation = re.sub(r'(?<!<sup>)⁻(?!<\/sup>)', '<sup>-</sup>', str(self.enunciation))

    def get_theme(self):
        return self.theme if self.theme else self.get_enunciation_str()
    
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
            details = []

            for change in delta.changes:
                field_name = getattr(type(self), change.field).field.verbose_name.capitalize()
                fields.append(field_name)
                old_value = change.old if change.old is not None else 'N/A' 
                new_value = change.new if change.new is not None else 'N/A' 

                details.append({
                    'field_name': field_name,
                    'old_value': old_value,
                    'new_value': new_value
                })
            
            list_changes.append({
                'history_date': new_record.history_date,
                'history_user': new_record.history_user,
                'fields': ', '.join(fields),
                'details': details,

            })
        
        letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
        option_changes = []
        for idx, option in enumerate(self.alternatives.all()):
            option_history = option.history.all().order_by('history_date')
            if option_history.exists():
                for option_pair in self._pair_iterable_for_delta_changes(option_history.iterator()):
                    old_option, new_option = option_pair
                    option_delta = new_option.diff_against(old_option)

                    if option_delta.changes:
                        for change in option_delta.changes:
                            option_changes.append({
                                'history_date': new_option.history_date,
                                'history_user': new_option.history_user,
                                'fields': f"Texto da alternativa",
                                'details': [{
                                    'field_name': f'Texto da alternativa {letters[idx]}',  
                                    'old_value': change.old if change.old is not None else 'N/A',
                                    'new_value': change.new if change.new is not None else 'N/A'
                                }]
                            })

        all_changes = list_changes + option_changes
        all_changes_sorted = sorted(all_changes, key=lambda x: x['history_date'], reverse=True)

        return (all_changes_sorted)

    @property
    def get_emmbbeded_video_answer(self):
        if self.answer_video_type == self.PANDA and self.answer_video:
            video_id = self.answer_video.split('?v=')[1]
            return f'<iframe id="panda-{video_id}" style="position: absolute; top: 0; left: 0; bottom: 0; right: 0; width: 100%; height: 100%; border:none; overflow:hidden;" src="{self.answer_video}" allow="accelerometer;gyroscope;encrypted-media;picture-in-picture" allowfullscreen=true fetchpriority="high"></iframe>'

        elif self.answer_video_type == self.YOUTUBE and self.answer_video:
            if not "embed" in self.answer_video:
                if "watch?v=" in self.answer_video:
                    self.answer_video = self.answer_video.replace("watch?v=", "embed/")
                elif "youtu.be" in self.answer_video:
                    self.answer_video = self.answer_video.replace("youtu.be/", "youtube.com/embed/")
                    
                src = re.split(r'\b[&]+.*$', self.answer_video)
                src = re.split(r'\b[=]+.*$', src[0])[0]
            
            return f'<iframe style="position: absolute; top: 0; left: 0; bottom: 0; right: 0; width: 100%; height: 100%; border:none; overflow:hidden;" src="{src}" title="Resposta comentada em vídeo" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
        
        return ''

    
    def get_absolute_url(self, application_student_pk):
        return r(
            'api:applications-student:question-detail',
            application_student_id=application_student_pk,
            question_id=self.pk
        )
        
    @property
    def it_has_used(self):
        """
            VERIFICA SE A QUESTÃO JÁ ESTÁ EM USO EM ALGUM CADERNO
        """
        from fiscallizeon.applications.models import Application
        from fiscallizeon.exams.models import ExamQuestion, Exam
        
        exam_questions = ExamQuestion.objects.filter(question=self).availables()

        exams = Exam.objects.only('id').filter(
            pk__in=exam_questions.values_list('exam_id', flat=True)
        ).distinct()

        exams_closed = exams.filter(
            status=Exam.CLOSED
        ).exists()

        if exams_closed:
            return (True, "Esta questão não pode ser alterada, pois está sendo utilizada em um caderno que já foi fechado.")

        applications = Application.objects.filter(
            Q(exam__in=self.exams.all()),
            Q(exam__examquestion__in=exam_questions),
        ).annotate(
            datetime_end = ExpressionWrapper(F('date') + F('end'), output_field=DateTimeField()),
            date_end_time_end = ExpressionWrapper(F('date_end') + F('end'), output_field=DateTimeField())
        ).filter(
            Q(
                Q(
                    Q(date_end_time_end__isnull=False, date_end_time_end__lt=timezone.localtime(timezone.now())) |
                    Q(date_end_time_end__isnull=True, datetime_end__lt=timezone.localtime(timezone.now()))
                )|
                Q(
                    Q(answer_sheet__isnull=False),
                    ~Q(answer_sheet="")
                )
            )
        )

        if applications.exists():
            return (True, "Esta questão está em uma aplicação que já foi iniciada e não pode ser editada.")
        
        for exam in exams:
            if exam.check_is_bag_exist():
                return (True, "Esta questão não pode ser alterada, pois está sendo utilizada em um caderno que tem malote associado.")
        
        return (False, '')
        
    def reason_can_be_updated(self, user=None):
        """
            DEFINE SE A QUESTÃO PODE OU NÃO SER EDITADA OU DELETADA
        """
        from fiscallizeon.exams.models import StatusQuestion, ExamQuestion
        CACHE_KEY = f'QUESTION_CAN_BE_UPDATED_{self.pk}_user_{user.pk if user else ""}'

        if not cache.get(CACHE_KEY):   
             
            if user:
                #se for DECISÃO PODE PASSAR DIRETO, iremos fazer um ajuste depois para permitir apenas para usuários específicos
                client = user.client
                
                # if not client or str(client.pk) == "a2b1158b-367a-40a4-8413-9897057c8aa2":
                #     return True

                last_status = StatusQuestion.objects.filter(
                    exam_question__question=self, 
                    active=True
                ).order_by(
                    'created_at'
                ).exclude(
                    status__in=[StatusQuestion.SEEN, StatusQuestion.RESPONSE]
                ).last()

                last_status_is_approved = True if last_status and last_status.status == StatusQuestion.APPROVED else False
                
                if user.user_type == settings.TEACHER and user.questions_configuration:
                    if last_status_is_approved and user.questions_configuration.block_edit_question_aproveds:
                        message = f"Esta questão já foi aprovada pela coordenação e não pode ser editada."
                        cache.set(CACHE_KEY, (False, message), 60)
                        return (False, message)

                teacher_can_edit = False
                if user.user_type == settings.TEACHER:
                    teacher_instance = Inspector.objects.filter(user=user).first()
                    if teacher_instance and teacher_instance.is_discipline_coordinator and client.teachers_coordinations_can_edit_questions:
                        teacher_can_edit = True

                if self.created_by and (user.id != self.created_by.id) and (user.user_type != settings.COORDINATION) and not teacher_can_edit:
                    message = "Essa questão foi criada por outro professor e não pode ser editada."
                    cache.set(CACHE_KEY, (False, message), 60)
                    return (False, message)
                
                # verifica se a questão está em alguma prova com prazo de elaboração expirado
                if user.user_type == settings.TEACHER:
                    if ExamQuestion.objects.filter(
                        question=self,
                        exam__elaboration_deadline__lt=timezone.localtime(timezone.now()).date(),
                        exam_teacher_subject__teacher_subject__teacher__user=user
                    ).exists():
                        message = "A edição desta questão não é permitida, pois o prazo para elaboração da solicitação já foi encerrado."
                        cache.set(CACHE_KEY, (False, message), 60)
                        return (False, message)
            
            it_has_used, reason = self.it_has_used
            if it_has_used:
                cache.set(CACHE_KEY, (False, reason), 60)
                return (False, reason)
            
            cache.set(CACHE_KEY, (True, ''), 60)
    
        return cache.get(CACHE_KEY)
    
    def can_be_updated_with_reason(self, user=None):
        can_be_updated, reason = self.reason_can_be_updated(user)
        return {
            "can_be_updated": can_be_updated,
            "reason": reason
        }
    
    def can_be_updated(self, user=None):
        can_be_updated, reason = self.reason_can_be_updated(user)
        return can_be_updated

    @hook(AFTER_UPDATE)
    def renew_exam_questions_cache(self):
        from fiscallizeon.exams.models import Exam
        exams = self.exams.filter(
            application__date=timezone.now().astimezone().date()
        )

        for exam in exams:
            exam.clear_questions_numbers_cache()
            exist = cache.get(f'QUESTIONS_{str(exam.pk)}')
            if exist:
                exam.generate_exam_questions_cache()

    @hook(AFTER_UPDATE)
    def update_sum_answers_grade(self):
        if self.category == self.SUM_QUESTION:
            update_sum_answers_grades.apply_async(args=[self.pk])

    def get_commented_awnser_str(self):
        return strip_tags(self.commented_awnser) if self.commented_awnser else None

    def get_feedback_str(self):
        return strip_tags(self.feedback) if self.feedback else None

    def get_enunciation_str(self):
        return strip_tags(self.enunciation)

    def enunciation_escaped(self):
        return self.enunciation.replace("\\", "\\\\").replace('&quot;', '"').replace('"', '\\"')


    def support_content_question_escaped(self):
        if not self.support_content_question:
            return ''

        return self.support_content_question.replace("\\", "\\\\").replace('&quot;', '"').replace('"', '\\"')

    def commented_awnser_escaped(self):
        if self.commented_awnser:
            return self.commented_awnser.replace("\\", "\\\\").replace('&quot;', '"').replace('"', '\\"')

    def feedback_escaped(self):
        if self.feedback:
            return self.feedback.replace("\\", "\\\\").replace('&quot;', '"').replace('"', '\\"')
        
    def object_serialized(self):
        from fiscallizeon.questions.serializers.questions import QuestionSerializerSimple
        question_serialized = QuestionSerializerSimple(self)
        return question_serialized.data

    @property
    def has_feedback(self):
        if not self.category == self.CHOICE:
            return False

        return self.alternatives.filter(is_correct=True).exists()

    @property
    def is_canceled(self):
        return not self.alternatives.filter(is_correct=False).exists()

    @property
    def correct_alternatives(self):
        if self.category in [self.CHOICE, self.SUM_QUESTION]:
            return self.alternatives.filter(
                is_correct=True
            )
        return []
    
    def duplicate_question(self, user, adapted=None):
        import uuid
        
        instance = self
        
        original_question = Question.objects.get(pk=instance.pk)
        
        copy_question = Question.objects.get(pk=instance.pk)
        copy_question.pk = uuid.uuid4()
        copy_question.source_question = original_question
        copy_question.is_public = False
        copy_question.created_by = user
        
        if adapted:
            copy_question.adapted = True
        copy_question.save()
        
        copy_question.topics.set(original_question.topics.all())
        copy_question.abilities.set(original_question.abilities.all())
        copy_question.competences.set(original_question.competences.all())
        copy_question.coordinations.set(user.get_coordinations())

        if original_question.category in [Question.CHOICE, Question.SUM_QUESTION]:
            for index, alternative in enumerate(original_question.alternatives.all().order_by('created_at'), 1):
                QuestionOption.objects.create(
                    question=copy_question,
                    text=alternative.text,
                    is_correct=alternative.is_correct,
                    index=index,
                )
        
        return copy_question
    
    def duplicate_question_with_conditions(self, user, adapted=None, keep_alternatives=None,  keep_pedagogical_data=None):
        import uuid

        instance = self
        
        original_question = Question.objects.get(pk=instance.pk)
        
        copy_question = Question.objects.get(pk=instance.pk)
        copy_question.pk = uuid.uuid4()
        copy_question.source_question = original_question
        copy_question.is_public = False
        copy_question.created_by = user
        
        if adapted:
            copy_question.adapted = True
        copy_question.save()
        
        if keep_pedagogical_data:
            copy_question.topics.set(original_question.topics.all())
            copy_question.abilities.set(original_question.abilities.all())
            copy_question.competences.set(original_question.competences.all())
        
        copy_question.coordinations.set(user.get_coordinations())

        if original_question.category in [Question.CHOICE, Question.SUM_QUESTION]:
            for index, alternative in enumerate(original_question.alternatives.all().order_by('created_at'), 1):
                alternative_is_correct = False
                if keep_alternatives:
                    alternative_is_correct  = alternative.is_correct
    
                QuestionOption.objects.create(
                    question=copy_question,
                    text=alternative.text,
                    is_correct=alternative_is_correct,
                    index=index,
                )
        
        return copy_question
    
    @property
    def urls(self):
        return {
            "api_update": reverse('questions:questions-detail', kwargs={ "pk": self.pk }),
            "api_improve": reverse('questions:questions-improve', kwargs={ "pk": self.pk }),
            "api_solve": reverse('questions:questions-solve', kwargs={ "pk": self.pk }),
            "api_classify_ability": reverse('questions:questions-classify-ability', kwargs={ "pk": self.pk }),
            "api_classify_competence": reverse('questions:questions-classify-competence', kwargs={ "pk": self.pk }),
            "api_classify_topic": reverse('questions:questions-classify-topic', kwargs={ "pk": self.pk }),
            "api_update_improve": reverse('questions:questions-update-improve', kwargs={ "pk": self.pk }),
            "api_get_improve": reverse('questions:questions-get-improve', kwargs={ "pk": self.pk }),
        }

    def pedagogical_data(self):
        return {
            "segment": self.grade.level if self.grade else 1,
            "level_display": self.get_level_display() if self.level is not None  else None,
            "grades": [],
            "grade": str(self.grade.id) if self.grade else None,
            "grade_name": str(self.grade.full_name) if self.grade else None,
            "knowledgeArea": str(self.subject.knowledge_area.pk) if self.subject and self.subject.knowledge_area else None,
            "knowledgeAreaName": str(self.subject.knowledge_area.name) if self.subject and self.subject.knowledge_area else None,
            "knowledgeAreas": [],
            "subjects": [],
            "subject": {
                "id": self.subject.id,
                "name": self.subject.name,
                "parent_subject": str(self.subject.parent_subject.id) if self.subject.parent_subject else None,
                "parent_subject_name": str(self.subject.parent_subject.name) if self.subject.parent_subject else None
            } if self.subject else None
        }

    def get_improve(self):
        from fiscallizeon.ai.models import QuestionImprove
        
        question_improve = None

        if hasattr(self, 'questionimprove'):
            return self.questionimprove

        question_improve, created = QuestionImprove.objects.update_or_create(
            question=self
        )

        return question_improve
    
    @cached_property
    def get_alternatives_ordered(self):
        return self.alternatives.all().order_by("index")
    
class QuestionHistoryTags(BaseModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    tags = models.ManyToManyField(QuestionTag, verbose_name="Tags da edição", blank=True)
    record_id = models.CharField('registro do histórico', max_length=100)
    note = models.CharField('nota de edição', max_length=100, default="")

class QuestionOption(BaseModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="alternatives")
    text = HTMLField('Texto da alternativa', null=False, blank=False)
    is_correct = models.BooleanField('É a alternativa correta', default=False)
    index = models.PositiveSmallIntegerField('Índice', default=0)
    history = HistoricalRecords(cascade_delete_history=True, excluded_fields=['created_at', 'updated_at'])

    class Meta:
        verbose_name = 'Alternativa'
        verbose_name_plural = 'Alternativas'
        ordering = ('created_at', )

    def __str__(self):
        return strip_tags(self.text)

    def clean(self):
        # Tivemos problema com o caracter: (-) em formulas matemáticas como (P=2n-¹) onde no front era mostrado um caracter [] (Quabradinho)
        # A idéia é substituir n-¹ por <sup></sup> que é bem entendido pelo HTML, e faz basicamente a mesma coisa.
        # task: https://app.clickup.com/t/86a78210r
        self.text = re.sub(r'(?<!<sup>)⁻(?!<\/sup>)', '<sup>-</sup>', str(self.text))

    def striped(self):
        return strip_tags(self.text)

    def text_escaped(self):
        return self.text.replace("\\", "\\\\").replace('&quot;', '"').replace('"', '\\"')
    
    @hook('before_create')
    def generate_index(self):
        if not self.index:
            if highest_index := QuestionOption.objects.using('default').filter(question=self.question).order_by('index').last():
                self.index = int(highest_index.index) + 1
    
    def get_index(self):
        options = QuestionOption.objects.using('default').filter(question=self.question).order_by('created_at')
        for index, option in enumerate(options):
            if option == self:
                return index
        return 0
    

    @property
    def urls(self):
        return {
            "api_update": reverse('questions:alternatives-detail', kwargs={ "pk": self.pk })
        }

class BaseText(BaseModel):
    title = models.CharField('Título', max_length=100)
    text = HTMLField('Texto Base')
    created_by = models.ForeignKey(User, verbose_name='Criado por', on_delete=models.PROTECT, blank=True)

    class Meta:
        verbose_name = 'Texto Base'
        verbose_name_plural = 'Textos Base'
        ordering = ('created_at', )

    def __str__(self):
        return self.title

    def text_escaped(self):
        return self.text.replace("\\", "\\\\").replace('&quot;', '"').replace('"', '\\"')

    def get_enunciation_str(self):
        return strip_tags(self.text)
    
    @property
    def can_delete(self):
        return not self.question_set.exists()
    
    @property
    def urls(self):
        return {
            "api_update": reverse('questions:base_text_retrive_update_destroy', kwargs={ "pk": self.pk })
        }
        
class SugestionTags(BaseModel):
    label = models.CharField("Label da tag", max_length=255)
    text = models.TextField("Texto da tag")
    user = models.ForeignKey("accounts.User", verbose_name=("Dono da TAG"), on_delete=models.CASCADE, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Tag de sugestão'
        verbose_name_plural = 'Tags de sugestão'