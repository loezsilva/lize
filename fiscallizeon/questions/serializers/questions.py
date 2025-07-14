import json
from html import unescape

import numpy as np
from rest_framework import serializers

from django.db import transaction
from django.utils.html import strip_tags
from django.db.models.functions import Length
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Case, Count, F, OuterRef, Q, Subquery, Sum, Value, When


from fiscallizeon.applications.models import RandomizationVersion
from fiscallizeon.exams import json_utils
from fiscallizeon.exams.models import Exam, ExamQuestion
from fiscallizeon.answers.serializers.file_answers import FileAnswerImgAnnotationsSerializer
from fiscallizeon.questions.models import Question, QuestionOption, SugestionTags
from fiscallizeon.questions.serializers.base_texts import BaseTextSimpleSerializer
from fiscallizeon.subjects.serializers.topics import TopicSimpleSerializer
from fiscallizeon.bncc.serializers.ability import AbilitySimpleSerializer
from fiscallizeon.bncc.serializers.competence import CompetenceSimpleSerializer
from fiscallizeon.answers.models import FileAnswer, TextualAnswer
from fiscallizeon.answers.models import TextualAnswer
from fiscallizeon.core.utils import generate_random_string
from fiscallizeon.core.templatetags.cdn_url import cdn_url
from fiscallizeon.answers.serializers.textual_answers import TextualAnswerDetailedNoSimilarSerializer
from fiscallizeon.corrections.models import CorrectionCriterion, CorrectionTextualAnswer, CorrectionFileAnswer
from fiscallizeon.ai.serializers.questions import QuestionImproveSerializer, CorrectDiscursiveQuestionSerializer

class QuestionOptionSimpleSerializer(serializers.ModelSerializer):
    urls = serializers.JSONField(read_only=True)
    class Meta:
        model = QuestionOption
        fields = ('id', 'text', 'is_correct', 'urls')

class QuestionTemplateStripedOptionSimpleSerializer(serializers.ModelSerializer):
    text = serializers.SerializerMethodField()
    class Meta:
        model = QuestionOption
        fields = ('id', 'text', 'is_correct', 'index')

    def get_text(self, obj):
        return strip_tags(obj.text)

class QuestionOptionCreateSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ('question', 'text', 'is_correct', 'index')

class QuestionOptionSimpleWithAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ('id', 'text', 'is_correct')

class CorrectionTextualAnswerSerializer(serializers.ModelSerializer):
    order = serializers.IntegerField(source='correction_criterion.order')
    class Meta:
        model = CorrectionTextualAnswer
        fields = ('id', 'textual_answer', 'correction_criterion', 'order', 'point')

class CorrectionFileAnswerSerializer(serializers.ModelSerializer):
    order = serializers.IntegerField(source='correction_criterion.order')
    class Meta:
        model = CorrectionFileAnswer
        fields = ('id', 'file_answer', 'correction_criterion', 'order', 'point')

class QuestionSerializer(serializers.ModelSerializer):
    from fiscallizeon.analytics.api.serializers.base_texts import BaseTextSimpleSerializer

    alternatives = serializers.SerializerMethodField()
    competences =  CompetenceSimpleSerializer(many=True, read_only=True)
    abilities = AbilitySimpleSerializer(many=True, read_only=True)
    topics =  TopicSimpleSerializer(many=True, read_only=True)
    category = serializers.CharField(source='get_category_display')
    base_texts = BaseTextSimpleSerializer(many=True, read_only=True)
    generate_correction_criterion = serializers.SerializerMethodField()
    text_correction_answer = serializers.SerializerMethodField()
    uses = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = (
            'id', 
            'updated_at', 
            'level', 
            'enunciation', 
            'commented_awnser', 
            'feedback', 
            'alternatives', 
            'competences', 
            'abilities', 
            'topics', 
            'category', 
            'is_abstract', 
            'base_texts',
            'text_correction',
            'generate_correction_criterion',
            'text_correction_answer',
            'uses',
            'created_by',
            'board',
            'is_essay',
            'created_with_ai',
            'cloze_content',
            'incorrect_cloze_alternatives',
        )


    def get_text_correction_answer(self, obj):
        if self.context.get('application_student', None):
            if obj.category == Question.TEXTUAL:
                return CorrectionTextualAnswerSerializer(CorrectionTextualAnswer.objects.filter(
                    textual_answer__student_application__id=self.context["application_student"], 
                    correction_criterion__text_correction=obj.text_correction,
                ), many=True).data
            
            if obj.category == Question.FILE:
                return CorrectionFileAnswerSerializer(CorrectionFileAnswer.objects.filter(
                    file_answer__student_application__id=self.context["application_student"], 
                    correction_criterion__text_correction=obj.text_correction,
                ), many=True).data

        return []


    def get_generate_correction_criterion(self, obj):
        if obj.text_correction:
            correction = CorrectionCriterion.objects.filter(text_correction=obj.text_correction)
            list_points = []
            for criterion in correction:

                list_generate_point = []
                for generate_point in np.arange(start=0, stop=criterion.maximum_score+criterion.step, step=criterion.step):
                    list_generate_point.append(generate_point)
                
                list_points.append({
                    'id': criterion.id,
                    'name': criterion.name,
                    'order': criterion.order,
                    'maximum_score': criterion.maximum_score,
                    'value': list_generate_point
                    })
            return sorted(list_points, key=lambda x: x['order'])
        return []

    def get_alternatives(self, question):
        randomization_version_pk = self.context['randomization_version_pk'] if self.context.get('randomization_version_pk') else None
            
        if question.category in [Question.CHOICE, Question.SUM_QUESTION]:
            alternatives = question.alternatives.distinct()
            
            if randomization_version_pk:
                randomization_version = RandomizationVersion.objects.get(pk=randomization_version_pk)
                
                question_json = list(filter(lambda _question: _question["pk"] == question.id, json_utils.convert_json_to_choice_questions_list(randomization_version.exam_json)))
                alternatives_pks = [alternative for alternative in question_json[0]['alternatives']]
                preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(alternatives_pks)])
                alternatives = alternatives.order_by(preserved)
            
            return QuestionOptionSimpleSerializer(alternatives, many=True).data
        return []
    
    def get_uses(self, obj):
        from fiscallizeon.exams.models import Exam
        
        exams = Exam.objects.filter(
            questions=obj,
        ).distinct().order_by('-created_at')
        
        uses = []
        for exam in exams:
            application = exam.application_set.all().last()
            uses.append({
                "exam_name": exam.__str__(),
                "exam_id": exam.id,
                "application_date": application.date if application else None 
            })
        return uses
    
class QuestionExamElaborationSerializer(serializers.ModelSerializer):
    
    from fiscallizeon.analytics.api.serializers.base_texts import BaseTextSimpleSerializer

    alternatives = serializers.SerializerMethodField()
    # competences =  CompetenceSimpleSerializer(many=True, read_only=True)
    # abilities = AbilitySimpleSerializer(many=True, read_only=True)
    # topics =  TopicSimpleSerializer(many=True, read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    base_texts_data = BaseTextSimpleSerializer(source="base_texts", many=True, read_only=True)
    generate_correction_criterion = serializers.SerializerMethodField()
    text_correction_answer = serializers.SerializerMethodField()
    uses = serializers.SerializerMethodField()
    urls = serializers.JSONField(read_only=True)
    pedagogical_data = serializers.JSONField(read_only=True)
    improve = QuestionImproveSerializer(source='questionimprove',read_only=True)
    can_be_updated = serializers.SerializerMethodField()
    can_be_updated_reason = serializers.SerializerMethodField()
    correction_with_competencies = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = (
            'id', 
            'updated_at', 
            'level', 
            'enunciation', 
            'commented_awnser', 
            'feedback', 
            'alternatives', 
            'competences', 
            'abilities', 
            'topics', 
            'category', 
            'category_display', 
            'is_abstract', 
            'base_texts',
            'base_texts_data',
            'text_correction',
            'generate_correction_criterion',
            'support_content_question',
            'text_correction_answer',
            'uses',
            'created_by',
            'urls',
            'answer_video',
            'answer_video_type',
            'subject',
            'grade',
            'pedagogical_data',
            'source_question',
            'improve',
            'created_with_ai',
            'quantity_lines',
            'is_essay',
            'text_question_format',
            'can_be_updated',
            'can_be_updated_reason',
            'created_with_ai',
            'correction_with_competencies',
            'board',
            'elaboration_year',
            'cloze_content',
            'incorrect_cloze_alternatives',
        )

    def get_text_correction_answer(self, obj):
        if self.context.get('application_student', None):
            if obj.category == Question.TEXTUAL:
                return CorrectionTextualAnswerSerializer(CorrectionTextualAnswer.objects.filter(
                    textual_answer__student_application__id=self.context["application_student"], 
                    correction_criterion__text_correction=obj.text_correction,
                ), many=True).data
            
            if obj.category == Question.FILE:
                return CorrectionFileAnswerSerializer(CorrectionFileAnswer.objects.filter(
                    file_answer__student_application__id=self.context["application_student"], 
                    correction_criterion__text_correction=obj.text_correction,
                ), many=True).data
        return []

    def get_generate_correction_criterion(self, obj):
        if obj.text_correction:
            correction = CorrectionCriterion.objects.filter(text_correction=obj.text_correction)
            list_points = []
            for criterion in correction:

                list_generate_point = []
                for generate_point in np.arange(start=0, stop=criterion.maximum_score+criterion.step, step=criterion.step):
                    list_generate_point.append(generate_point)
                
                list_points.append({
                    'id': criterion.id,
                    'name': criterion.name,
                    'order': criterion.order,
                    'maximum_score': criterion.maximum_score,
                    'value': list_generate_point
                    })
            return sorted(list_points, key=lambda x: x['order'])
        return []

    def get_alternatives(self, question):
        randomization_version_pk = self.context['randomization_version_pk'] if self.context.get('randomization_version_pk') else None
            
        if question.category in [Question.CHOICE, Question.SUM_QUESTION]:
            alternatives = question.alternatives.using('default').all().distinct()
            
            if randomization_version_pk:
                randomization_version = RandomizationVersion.objects.get(pk=randomization_version_pk)
                
                question_json = list(filter(lambda _question: _question["pk"] == question.id, json_utils.convert_json_to_choice_questions_list(randomization_version.exam_json)))
                alternatives_pks = [alternative for alternative in question_json[0]['alternatives']]
                preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(alternatives_pks)])
                alternatives = alternatives.order_by(preserved)
            
            return QuestionOptionSimpleSerializer(alternatives, many=True).data
        return []
    
    def get_uses(self, obj):
        from fiscallizeon.exams.models import Exam
        
        coordinations = self.context['request'].user.get_coordinations_cache()
        questions = [f'{obj.pk}']
        if obj.is_public:
            questions = [f'{question.pk}' for question in obj.question_copies.filter(coordinations__in=coordinations)]

        exams = Exam.objects.filter(
            questions__in=questions,
            coordinations__in=coordinations,
        ).distinct().order_by('-created_at')
        
        uses = []
        for exam in exams:
            application = exam.application_set.all().last()
            uses.append({
                "exam_name": exam.__str__(),
                "exam_id": exam.id,
                "application_date": application.date if application else None 
            })
        
        return uses
    
    def get_can_be_updated_with_reason(self, user, question: Question):
        return question.reason_can_be_updated(user)
    
    def get_can_be_updated(self, question):
        user =  self.context['request'].user
        can_be_updated, reason = self.get_can_be_updated_with_reason(user, question)
        return can_be_updated
    
    def get_can_be_updated_reason(self, question):
        user =  self.context['request'].user
        can_be_updated, reason = self.get_can_be_updated_with_reason(user, question)
        return reason
    
    def get_correction_with_competencies(self, obj):
        return True if obj.text_correction else False

class QuestionSerializerNoAnswer(QuestionSerializer):
    alternatives = QuestionOptionSimpleWithAnswerSerializer(many=True, read_only=True)

class QuestionSerializerSimple(serializers.ModelSerializer):
    from fiscallizeon.analytics.api.serializers.base_texts import BaseTextSerializer

    topic_name = serializers.SerializerMethodField()
    used_times = serializers.SerializerMethodField()

    created_by_name = serializers.SerializerMethodField()
    
    grade = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    knowledgeArea = serializers.SerializerMethodField()

    alternatives = serializers.SerializerMethodField()

    enunciation_html = serializers.SerializerMethodField()

    has_feedback = serializers.SerializerMethodField()

    can_be_updated = serializers.SerializerMethodField()

    base_texts = BaseTextSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = (
            'pk', 
            'id', 
            'enunciation', 
            'topic_name', 
            'get_level_display', 
            'used_times', 
            'get_category_display', 
            'grade', 
            'subject', 
            'knowledgeArea', 
            'alternatives', 
            'enunciation_html', 
            'has_feedback', 
            'created_by_name', 
            'can_be_updated', 
            'base_texts', 
            'adapted',
            'quantity_lines',
            'draft_rows_number',
            'break_enunciation',
            'force_break_page',
            'force_one_column',
            'print_only_enunciation',            
            'text_question_format',            
            'board',
            'support_content_question',
            'is_essay',
            'created_with_ai'
        )

    def get_can_be_updated(self, obj):
        request = self.context.get('request', None)
        if request:
            user = request.user 
            return obj.can_be_updated(user=user)  
        return False

    def get_has_feedback(self, question):
        return json.dumps(question.has_feedback)

    def get_created_by_name(self, question):
        return question.created_by.get_user_full_name if question.created_by else ""

    def get_enunciation_html(self, question):
        return question.enunciation_escaped().replace('\\"', '"')

    def get_grade(self, question):
        return str(question.grade) if question.grade else ""

    def get_subject(self, question):
        return str(question.subject.name) if question.subject else ""

    def get_knowledgeArea(self, question):
        return str(question.subject.knowledge_area.name) if question.subject else ""

    def get_alternatives(self, question):
        if question.category in [Question.CHOICE, Question.SUM_QUESTION]:
            return json.dumps(QuestionOptionSimpleWithAnswerSerializer(question.alternatives, many=True).data)
        
        return json.dumps([])

    def get_used_times(self, question):
        return question.exams.all().count()

    def get_topic_name(self, question):
        return question.topic.name if question.topic else ""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['enunciation'] = unescape(strip_tags(instance.enunciation))[:200]
        return data


class QuestionExamSerializer(serializers.Serializer):
    pk = serializers.UUIDField()
    answer = serializers.UUIDField()
    answer_created_by_id = serializers.UUIDField()
    answer_created_by_name = serializers.UUIDField()
    answer_created_at = serializers.UUIDField()

    textual_answer = serializers.UUIDField()
    textual_answer_content = serializers.CharField()
    sum_question_sum_value = serializers.IntegerField()
    sum_question_checked_answers = serializers.ListField(child=serializers.UUIDField())
    file_answer = serializers.UUIDField()
    option_answer = serializers.UUIDField()
    corrected_but_no_answer = serializers.BooleanField()
    category = serializers.CharField(source='get_category_display')
    duration = serializers.DurationField()
    last_modified = serializers.DateTimeField()
    total_answers = serializers.IntegerField()
    is_correct = serializers.BooleanField(source='is_correct_choice')
    teacher_feedback = serializers.CharField()
    percent_grade = serializers.DecimalField(max_digits=7, decimal_places=6)
    teacher_grade = serializers.DecimalField(max_digits=10, decimal_places=4)
    question_weight = serializers.DecimalField(max_digits=10, decimal_places=4)
    similar_answers = serializers.SerializerMethodField()
    exam_teacher_subject = serializers.SerializerMethodField()
    text_correction_answer = serializers.SerializerMethodField()
    text_correction = serializers.SerializerMethodField()
    
    alternatives = serializers.SerializerMethodField()

    annuled = serializers.SerializerMethodField()
    empty = serializers.BooleanField()
    question_number = serializers.SerializerMethodField()
    suggestions = serializers.SerializerMethodField()
    class Meta:
        fields = (
            'pk', 
            'answer', 
            'textual_answer',
            'textual_answer_content',
            'file_answer', 
            'option_answer', 
            'corrected_but_no_answer',
            'is_correct', 
            'total_answers', 
            'duration', 
            'last_modified',
            'category',
            'teacher_feedback',
            'percent_grade',
            'teacher_grade',
            'question_weight',
            'similar_answers',
            'exam_teacher_subject',
            'text_correction_answer',
            'text_correction',
            'alternatives',
            'annuled',
            'empty',
            'is_essay',
            'question_number'
            'suggestions',
        )

    def get_question_number(self, question):
        exam = Exam.objects.get(pk=question.exam_id)
        randomization_version = RandomizationVersion.objects.filter(
            pk=question.randomization_version_pk
        ).first() if question.randomization_version_pk else None

        number = exam.number_print_question(
            question=question, 
            randomization_version=randomization_version
        )

        return number

    def get_text_correction(self, obj):
        return obj.text_correction.pk if obj.text_correction else None
    
    def get_alternatives(self, question):

        if question.category in [Question.CHOICE, Question.SUM_QUESTION]:
            alternatives = question.alternatives.distinct()
            
            if question.randomization_version_pk:
                randomization_version = RandomizationVersion.objects.get(pk=question.randomization_version_pk)
                
                question_json = list(filter(lambda _question: _question["pk"] == question.id, json_utils.convert_json_to_choice_questions_list(randomization_version.exam_json)))
                alternatives_pks = [alternative for alternative in question_json[0]['alternatives']]
                preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(alternatives_pks)])
                
                alternatives = alternatives.order_by(preserved)
            
            return QuestionOptionSimpleSerializer(alternatives, many=True).data
        
        return []

    def get_text_correction_answer(self, obj):
        if obj.category == Question.TEXTUAL:
            return CorrectionTextualAnswer.objects.filter(textual_answer=obj.textual_answer).values("id", "textual_answer", "correction_criterion", "correction_criterion__order", "point")
        if obj.category == Question.FILE:
            return CorrectionFileAnswer.objects.filter(file_answer=obj.file_answer).values("id", "file_answer", "correction_criterion", "correction_criterion__order", "point")
        return []

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.file_answer:
            answer = FileAnswer.objects.get(pk=instance.file_answer)
            if answer.arquivo:
                representation['file_answer_url'] = cdn_url(answer.arquivo.url)
            representation['img_annotations'] = answer.img_annotations
        return representation
    
    def get_exam_teacher_subject(self, instance):
        return instance.exam_teacher_subject if instance.exam_teacher_subject else ""

    def get_similar_answers(self, instance):
        similar_answers = TextualAnswer.objects.none()
        
        LIMIT_CONTENT_SIZE = 30

        if instance.textual_answer_content and len(instance.textual_answer_content) > LIMIT_CONTENT_SIZE:
            answer = TextualAnswer.objects.get(pk=instance.textual_answer)
            
            similar_answers = TextualAnswer.objects.annotate(
                content_lenght=Length('content')
            ).filter(
                question__pk=answer.question.pk,
                student_application__application__exam=answer.student_application.application.exam,
                content_lenght__gt=LIMIT_CONTENT_SIZE
            ).exclude(
                pk=answer.pk
            ).annotate(
                similarity=TrigramSimilarity('content', instance.textual_answer_content),
            ).filter(similarity__gt=0.8).order_by('-similarity')

        return TextualAnswerDetailedNoSimilarSerializer(similar_answers, many=True).data
    
    def get_annuled(self, question):
        from fiscallizeon.exams.models import StatusQuestion
        
        examquestion = ExamQuestion.objects.get(question=question, exam=question.exam_id)
        
        last_status = examquestion.statusquestion_set.filter(active=True).order_by('created_at').last()
        
        if last_status and last_status.status == StatusQuestion.ANNULLED:
            return True
        return False

    def get_suggestions(self, question):
        if hasattr(question,'suggestions'):
            return CorrectDiscursiveQuestionSerializer(data=question.suggestions).initial_data
        return CorrectDiscursiveQuestionSerializer(data={}).initial_data
class QuestionHistoricalSerializer(serializers.ModelSerializer):

    class Meta:
        model = Question
        fields = ('pk', )

class ExamTemplateQuestionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = (
            'coordinations',
            'topics', 
            'competences', 
            'abilities', 
            'subject',
            'grade',
            'category', 
            'is_abstract',
            'commented_awnser',
            'feedback',
            'is_essay',
        )


class AlternativeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ('text', 'is_correct', 'index')


class QuestionOMRCreateSerializer(serializers.ModelSerializer):
    alternatives = AlternativeCreateSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = (
            'subject',
            'grade',
            'category',
            'is_abstract',
            'commented_awnser',
            'feedback',
            'level',
            'coordinations',
            'topics',
            'competences',
            'abilities',
            'alternatives',
            'quantity_lines',
            'is_essay',
            'text_question_format'
        )


class ExamQuestionOMRCreateSerializer(serializers.ModelSerializer):
    question = QuestionOMRCreateSerializer()

    class Meta:
        model = ExamQuestion
        fields = (
            'weight',
            'block_weight',
            'order',
            'is_foreign_language',
            'question',
        )


class ExamOMRCreateSerializer(serializers.ModelSerializer):
    examquestions = ExamQuestionOMRCreateSerializer(many=True, source='examquestion_set')

    class Meta:
        model = Exam
        fields = (
            'id',
            'name',
            'status',
            'is_english_spanish',
            'start_number',
            'is_enem_simulator',
            'show_ranking',
            'external_code',
            'coordinations',
            'examquestions',
            'template_quantity_alternatives',
            'teaching_stage',
            'related_subjects',
            'relations',
        )

    def create(self, validated_data):
        examquestions_data = validated_data.pop('examquestion_set')
        coordinations_data = validated_data.pop('coordinations')
        relations_data = validated_data.pop('relations')
        exam = Exam.objects.create(is_abstract=True, **validated_data)
        exam.coordinations.set(coordinations_data)
        exam.relations.set(relations_data)

        user =  self.context['request'].user
        if user.client_has_offset_answer_sheet:
            Exam.objects.generate_external_code(exam, user.get_clients().first())
        with transaction.atomic():

            question_instances = Question.objects.using('default').bulk_create([
                Question(
                    is_essay=examquestion_data['question']['is_essay'],
                    grade=examquestion_data['question']['grade'],
                    subject=examquestion_data['question']['subject'],
                    category=examquestion_data['question']['category'],
                    feedback=examquestion_data['question']['feedback'],
                    is_abstract=examquestion_data['question']['is_abstract'],
                    commented_awnser=examquestion_data['question']['commented_awnser'],
                    level=examquestion_data['question']['level'],
                    quantity_lines=examquestion_data['question']['quantity_lines'],
                    text_question_format=examquestion_data['question']['text_question_format']

                )
                for examquestion_data in examquestions_data
            ])
            
            for i, examquestion_data in enumerate(examquestions_data):
                question_instances[i].topics.set(examquestion_data['question']['topics'])
                question_instances[i].abilities.set(examquestion_data['question']['abilities'])
                question_instances[i].competences.set(examquestion_data['question']['competences'])
                question_instances[i].coordinations.set(examquestion_data['question']['coordinations'])
                question_instances[i].save()
               
            question_option_instances = QuestionOption.objects.using('default').bulk_create([
                QuestionOption(
                    question=question_instances[i],
                    text=alternative['text'],
                    is_correct=alternative['is_correct'],
                    index=alternative['index'],
                )
                for i, examquestion_data in enumerate(examquestions_data)
                if examquestion_data['question']['category'] == Question.CHOICE
                for alternative in examquestion_data['question']['alternatives']
            ])

            exam_question_instances = ExamQuestion.objects.using('default').bulk_create([
                ExamQuestion(
                    exam=exam,
                    question=question_instances[i],
                    order=examquestion_data['order'],
                    weight=0 if not examquestion_data['weight'] or float(examquestion_data['weight']) < 0 else examquestion_data['weight'],
                    block_weight=examquestion_data['block_weight'],
                    is_foreign_language=examquestion_data['is_foreign_language'],
                    short_code=generate_random_string(4).upper()
                )
                for i, examquestion_data in enumerate(examquestions_data)
            ])

        return exam


class AlternativeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ('text', 'is_correct', 'index')


class QuestionOMRUpdateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    alternatives = AlternativeUpdateSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = (
            'id',
            'subject',
            'grade',
            'category',
            'is_abstract',
            'commented_awnser',
            'feedback',
            'level',
            'coordinations',
            'topics',
            'competences',
            'abilities',
            'alternatives',
            'quantity_lines',
            'is_essay',
            'text_question_format'
        )


class ExamQuestionOMRUpdateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    question = QuestionOMRUpdateSerializer()

    class Meta:
        model = ExamQuestion
        fields = (
            'id',
            'weight',
            'block_weight',
            'order',
            'is_foreign_language',
            'question',
        )


class ExamOMRUpdateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    examquestions = ExamQuestionOMRUpdateSerializer(many=True, source='examquestion_set')

    class Meta:
        model = Exam
        fields = (
            'id',
            'name',
            'status',
            'is_english_spanish',
            'start_number',
            'is_enem_simulator',
            'show_ranking',
            'external_code',
            'coordinations',
            'examquestions',
            'template_quantity_alternatives',
            'relations',
            'teaching_stage',
        )

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.status = validated_data.get('status', instance.status)
        instance.is_english_spanish = validated_data.get('is_english_spanish', instance.is_english_spanish)
        instance.start_number = validated_data.get('start_number', instance.start_number)
        instance.is_enem_simulator = validated_data.get('is_enem_simulator', instance.is_enem_simulator)
        instance.show_ranking = validated_data.get('show_ranking', instance.show_ranking)
        instance.external_code = validated_data.get('external_code', instance.external_code)
        instance.template_quantity_alternatives = validated_data.get('template_quantity_alternatives', instance.template_quantity_alternatives)
        instance.teaching_stage = validated_data.get('teaching_stage', instance.teaching_stage)
        instance.relations.set(validated_data.get('relations', instance.relations))
        instance.save()

        examquestions_data = validated_data.pop('examquestion_set')
    
        existing_examquestion_ids = [f'{exam_question.id}' for exam_question in instance.examquestion_set.all()]
        request_examquestion_ids = [f'{examquestion_data.get("id")}' for examquestion_data in examquestions_data if examquestion_data.get('id')]

        examquestions_to_delete = set(existing_examquestion_ids) - set(request_examquestion_ids)

        # delete exam questions
        ExamQuestion.objects.filter(id__in=examquestions_to_delete).delete()

        for examquestion_data in examquestions_data:
            examquestion_id = f'{examquestion_data.get("id")}' if examquestion_data.get('id') else None

            if examquestion_id in existing_examquestion_ids:
                # update exam question
                examquestion = ExamQuestion.objects.get(id=examquestion_id)
                question_data = examquestion_data.pop('question')

                topics_data = question_data.pop('topics')
                abilities_data = question_data.pop('abilities')
                competences_data = question_data.pop('competences')
                coordinations_data = question_data.pop('coordinations')
                alternatives_data = question_data.pop('alternatives')

                question = examquestion.question
                # update question
                question.subject = question_data.get('subject', question.subject)
                question.grade = question_data.get('grade', question.grade)
                question.category = question_data.get('category', question.category)
                question.commented_awnser = question_data.get('commented_awnser', question.commented_awnser)
                question.feedback = question_data.get('feedback', question.feedback)
                question.level = question_data.get('level', question.level)
                question.quantity_lines =  question_data.get('quantity_lines', question.quantity_lines)
                question.text_question_format = question_data.get('text_question_format', question.text_question_format)
                question.is_essay = question_data.get('is_essay',question.is_essay)

                question.coordinations.set(coordinations_data)
                question.topics.set(topics_data)
                question.competences.set(competences_data)
                question.abilities.set(abilities_data)
                question.save()

                if question.category in [Question.CHOICE, Question.SUM_QUESTION]:
                    all_alternatives = question.alternatives.all()
                    existing_alternatives = {alt.index: alt for alt in all_alternatives}
                    provided_alternativoes = {alt['index']: alt for alt in alternatives_data}

                    for index, alt in provided_alternativoes.items():
                        if index in existing_alternatives:
                            existing_alternatives[index].is_correct = alt.get('is_correct', existing_alternatives[index].is_correct)
                            existing_alternatives[index].save()
                        else:
                            QuestionOption.objects.create(
                                question=question,
                                text=alt.get('text'),
                                is_correct=alt.get('is_correct'),
                                index=alt.get('index')
                            )

                    for index, alt in existing_alternatives.items():
                        if not index in provided_alternativoes:
                            alt.delete()

                question.save()
                examquestion.weight = examquestion_data.get('weight', examquestion.weight)
                examquestion.block_weight = examquestion_data.get('block_weight', examquestion.block_weight)
                examquestion.order = examquestion_data.get('order', examquestion.order)
                examquestion.is_foreign_language = examquestion_data.get('is_foreign_language', examquestion.is_foreign_language)
                examquestion.save()

            else:
                # create exam question
                question_data = examquestion_data.pop('question')

                topics_data = question_data.pop('topics')
                abilities_data = question_data.pop('abilities')
                competences_data = question_data.pop('competences')
                coordinations_data = question_data.pop('coordinations')
                alternatives_data = question_data.pop('alternatives')

                # create question
                question = Question.objects.create(**question_data)

                question.coordinations.set(coordinations_data)
                question.topics.set(topics_data)
                question.competences.set(competences_data)
                question.abilities.set(abilities_data)
                question.save()

                if question.category in [Question.CHOICE, Question.SUM_QUESTION]:
                    for alternative_data in alternatives_data:
                        # create alternative
                        QuestionOption.objects.create(question=question, **alternative_data)

                ExamQuestion.objects.create(exam=instance, question=question, **examquestion_data)

        return instance


class ExamTemplateQuestionSerializer(serializers.ModelSerializer):

    alternatives = serializers.SerializerMethodField()
    competences =  CompetenceSimpleSerializer(many=True, read_only=True)
    abilities = AbilitySimpleSerializer(many=True, read_only=True)
    topics =  TopicSimpleSerializer(many=True, read_only=True)
    knowledge_area = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = (
            'id',
            'alternatives',
            'coordinations',
            'topics', 
            'competences', 
            'abilities', 
            'subject',
            'level',
            'grade',
            'knowledge_area',
            'category', 
            'is_abstract',
            'commented_awnser',
            'is_essay',
            'feedback',
        )
    def get_alternatives(self, question):
        if question.category in [Question.CHOICE, Question.SUM_QUESTION]:
            return QuestionTemplateStripedOptionSimpleSerializer(question.alternatives.distinct(), many=True).data
        return []


    def get_knowledge_area(self, question):
        return question.subject.knowledge_area.id if question.subject else ""

class ExamQuestionTemplateQuestionSerializer(serializers.ModelSerializer):
    question = ExamTemplateQuestionSerializer()
    class Meta:
        model = ExamQuestion
        fields = (
            'weight',
            'question', 
            'order', 
        )
class SimpleQuestionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Question
        fields = ('id',)
        
class QuestionAndFileAnswerSerializer(serializers.ModelSerializer):
    img_annotations = serializers.SerializerMethodField()
    class Meta:
        model = Question
        fields = ('pk', 'img_annotations')


    def get_img_annotations(self, question):        
        return FileAnswerImgAnnotationsSerializer(instance=FileAnswer.objects.get(question=question.first(), student_application=self.context['student_application'])).data['img_annotations']
        

class QuestionAndSerializerSimple(serializers.ModelSerializer):
    base_texts = BaseTextSimpleSerializer(many=True, read_only=True)
    class Meta:
        model = Question
        fields = ('id', 'base_texts')

class QuestionTeacherSerializer(serializers.ModelSerializer):

    category = serializers.CharField(source='get_category_display')
    enunciation = serializers.SerializerMethodField()
    used_times = serializers.SerializerMethodField()
    # can_be_updated = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = (
            'id', 
            'enunciation', 
            'commented_awnser', 
            'feedback', 
            'category', 
            'is_abstract', 
            'base_texts',
            'used_times', 
            'adapted',
            # 'can_be_updated',
        )

    def get_enunciation(self, question):
        return unescape(strip_tags(question.enunciation))[:200]
    
    def get_used_times(self, question):
        return question.exams.all().count()
    
    # def get_can_be_updated(self, question):
    #     user =  self.context['request'].user
    #     return question.can_be_updated(user)
    
class AlternativeSerializer(serializers.ModelSerializer):
    urls = serializers.JSONField(read_only=True)
    class Meta:
        model = QuestionOption
        fields = ('id', 'text', 'is_correct', 'urls')

class SugestionTagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SugestionTags
        fields = ['id', 'label', 'text']


class QuestionImageUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['support_image_question']

class ExamQuestionBlockWeightSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamQuestion
        fields = ['block_weight',  'weight'] 