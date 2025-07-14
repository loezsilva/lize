from django.db import models

from fiscallizeon.core.models import BaseModel
from tinymce.models import HTMLField
from django_lifecycle import hook

class OpenAIQuery(BaseModel):
    STOP, LENGTH, FUNCTION_CALL, CONTENT_FILTER, NULL = 'stop', 'length', 'function_call', 'content_filter', 'null'
    FINISH_REASON_CHOICES = (
        (STOP, 'Sucesso'),
        (LENGTH, 'Incompleto'),
        (FUNCTION_CALL, 'Chamada de função'),
        (CONTENT_FILTER, 'Filtro de conteúdo'),
        (NULL, 'Desconhecido'),
    )

    user_prompt = models.TextField('Prompt do usuário')
    gpt_model = models.CharField('Modelo GPT', max_length=128)
    input_tokens = models.PositiveIntegerField('Número de tokens de entrada', blank=True, null=True)
    output_tokens = models.PositiveIntegerField('Número de tokens de saída', blank=True, null=True)
    finish_reason = models.CharField('Status de finalização', max_length=64, choices=FINISH_REASON_CHOICES, default=NULL, blank=True, null=True)

    OTHER, QUESTION_GENERATION, QUESTION_IMPROVEMENT, QUESTION_SOLVING, ANSWER_CORRECTION = range(5)
    PROMPT_CATEGORY_CHOICES = (
        (QUESTION_GENERATION, 'Geração de questão'),
        (QUESTION_IMPROVEMENT, 'Melhoramento de questão'),
        (QUESTION_SOLVING, 'Resolução de questão'),
        (ANSWER_CORRECTION, 'Correção de questão discursiva'),
    )

    prompt_category = models.PositiveSmallIntegerField('Categoria do prompt', choices=PROMPT_CATEGORY_CHOICES, default=OTHER)
    
    user = models.ForeignKey("accounts.User", verbose_name=("Usuário"), on_delete=models.PROTECT, blank=True, null=True)
    client = models.ForeignKey("clients.Client", verbose_name=("Cliente"), on_delete=models.PROTECT, blank=True, null=True)
    ai_model = models.ForeignKey(
        'ai.AIModel', verbose_name='modelo de IA', on_delete=models.PROTECT, blank=True, null=True
    )
    cost = models.DecimalField('custo (em dólar)', max_digits=9, decimal_places=6, blank=True, null=True)

    class Meta:
        verbose_name = 'Prompt GPT'
        verbose_name_plural = 'Prompts GPT'

    def __str__(self):
        return self.user_prompt[:100]

    def get_calculated_cost(self):
        UNIT = 1_000_000

        if not self.input_tokens or not self.output_tokens or not self.ai_model:
            return 0

        input_unit = self.ai_model.input_price / UNIT
        output_unit = self.ai_model.output_price / UNIT

        input_value = input_unit * self.input_tokens
        output_value = output_unit * self.output_tokens
        return input_value + output_value

    @hook('before_create')
    def set_client(self):
        self.client = self.user.client if self.user else None


class QuestionImprove(BaseModel):
    question = models.OneToOneField("questions.Question", verbose_name="Questão", on_delete=models.CASCADE)
    enunciation = HTMLField("Enunciado", blank=True, null=True)
    alternatives = models.JSONField("Alternativas", blank=True, null=True)
    enunciation_correction_detail = HTMLField("Enunciado", blank=True, null=True)
    commented_answer = HTMLField("Enunciado", blank=True, null=True)
    topics = models.ManyToManyField("subjects.Topic", verbose_name="Assuntos")
    abilities = models.ManyToManyField("bncc.abiliity", verbose_name="Habilidades")
    competences = models.ManyToManyField("bncc.competence", verbose_name="Competências")
    
    applied_topics = models.ManyToManyField("subjects.Topic", related_name="applieds", verbose_name="Assuntos Aplicados", blank=True)
    applied_abilities = models.ManyToManyField("bncc.abiliity", related_name="applieds", verbose_name="Habilidades Aplicados", blank=True)
    applied_competences = models.ManyToManyField("bncc.competence", related_name="applieds", verbose_name="Competências Aplicados", blank=True)
    
    IDDLE, IGNORED, APPLIED = range(3)
    STATUS_CHOICES = (
        (IDDLE, 'Aguardando'),
        (IGNORED, 'Ignorado'),
        (APPLIED, 'Aplicado'),
    )
    
    enunciation_status = models.SmallIntegerField("Correção de enunciado aplicada?", choices=STATUS_CHOICES, default=IDDLE)
    commented_answer_status = models.SmallIntegerField("Resposta comentada aplicada?", choices=STATUS_CHOICES, default=IDDLE)
    topics_status = models.SmallIntegerField("Assuntos aplicados?", choices=STATUS_CHOICES, default=IDDLE)
    abilities_status = models.SmallIntegerField("Habilidades aplicadas?", choices=STATUS_CHOICES, default=IDDLE)
    competences_status = models.SmallIntegerField("Competências aplicadas?", choices=STATUS_CHOICES, default=IDDLE)
    
    # Likes
    IDDLE, LIKE, DESLIKE = range(3)
    LIKE_CHOICES = (
        (IDDLE, 'Aguardando'),
        (LIKE, 'Gostou'),
        (DESLIKE, 'Não gostou'),
    )
    liked_enunciation = models.SmallIntegerField("Gostou da sugestão do enunciado?", choices=LIKE_CHOICES, default=IDDLE)
    liked_commented_answer = models.SmallIntegerField("Gostou da Resposta comentada?", choices=LIKE_CHOICES, default=IDDLE)
    liked_topics = models.SmallIntegerField("Gostou dos assuntos?", choices=LIKE_CHOICES, default=IDDLE)
    liked_abilities = models.SmallIntegerField("Gostou Habilidades?", choices=LIKE_CHOICES, default=IDDLE)
    liked_competences = models.SmallIntegerField("Gostou Competências?", choices=LIKE_CHOICES, default=IDDLE)

    class Meta:
        verbose_name = 'Aprimoramento de questão'
        verbose_name_plural = 'Aprimoramento de questões'

    @property
    def available_to_show(self):
        """
            Verifica se o usuário ignorou todos os aprimoramentos disponíveis para a questão
            O all verifica se todas as condições são verdadeiras
        """
        availables = []

        if self.enunciation_correction_detail:
            availables.append(self.enunciation_status in [self.IGNORED, self.APPLIED])
        if self.commented_answer:
            availables.append(self.commented_answer_status in [self.IGNORED, self.APPLIED])
        if self.topics.exists():
            availables.append(self.topics_status in [self.IGNORED, self.APPLIED])
        if self.abilities.exists():
            availables.append(self.abilities_status in [self.IGNORED, self.APPLIED])
        if self.competences.exists():
            availables.append(self.competences_status in [self.IGNORED, self.APPLIED])

        return not all(availables)
    
class AICredit(BaseModel):
    user = models.ForeignKey("accounts.User", verbose_name="Usuário", related_name="utilized_credits", on_delete=models.CASCADE)
    prompt = models.ForeignKey(OpenAIQuery, verbose_name="Prompt", on_delete=models.CASCADE)


class AIModel(BaseModel):
    identifier = models.CharField('identificador', max_length=255, unique=True)
    input_price = models.DecimalField(
        'preço entrada/1M tokens (em dólar)', max_digits=9, decimal_places=2, null=True, blank=True
    )
    output_price = models.DecimalField(
        'preço saída/1M tokens (em dólar)', max_digits=9, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name_plural = 'modelos de IA'
        verbose_name = 'modelo de IA'
        ordering = ('-created_at',)

    def __str__(self):
        return self.identifier
