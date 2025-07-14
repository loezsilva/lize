import json
from rest_framework import serializers
from django.conf import settings 
from django.db.models import Sum, Q
from fiscallizeon.accounts.models import User
from fiscallizeon.classes.serializers import GradeSerializer
from fiscallizeon.clients.models import QuestionTag, SchoolCoordination
from fiscallizeon.core.templatetags.exams_tags import get_details

from fiscallizeon.inspectors.serializers.inspectors import TeacherSubjectSerializer, TeacherSubjectSimpleSerializer, TeacherSubjectVerySimpleSerializer

from fiscallizeon.exams.models import (
    ClientCustomPage,
    Exam,
    ExamOrientation,
    ExamQuestion,
    ExamTeacherSubject,
    ExamTeacherSubjectFile,
    QuestionTagStatusQuestion,
    StatusQuestion,
)
from fiscallizeon.exams.serializers.exam_questions import ExamQuestionExamElaborationSerializer
from fiscallizeon.materials.serializer.materials import StudyMaterialSimpleSerializer
from fiscallizeon.questions.models import Question
from fiscallizeon.questions.serializers.questions import ExamTemplateQuestionSerializer, QuestionSerializerSimple
from django.utils import timezone

class ExamSimpleSerializer(serializers.ModelSerializer):

    status = serializers.CharField(source='get_status_display')
    category_display = serializers.CharField(source='get_category_display')
    questions_count = serializers.SerializerMethodField()
    class Meta:
        model = Exam
        fields = ('id', 'name', 'questions_count', 'status', 'is_english_spanish', 'category_display')

    def get_questions_count(self, obj):
        return obj.examquestion_set.availables(exclude_annuleds=True).count()

class TagsCountSerializer(serializers.Serializer):
    name = serializers.CharField()
    count = serializers.IntegerField()

class QuestionTagStatusQuestionSerializer(serializers.ModelSerializer):
    tags_display = serializers.SerializerMethodField()
    class Meta:
        model = QuestionTagStatusQuestion
        fields = ('status', 'tags', 'tags_display')

    def get_tags_display(self, obj):
        return obj.tags.using('default').values_list('name', flat=True)

class StatusQuestionSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    user_name = serializers.SerializerMethodField()
    responses = serializers.SerializerMethodField()
    is_checked_by = serializers.SerializerMethodField()

    class Meta:
        model = StatusQuestion
        fields = ('id', 'status', 'status_display', 'note', 'created_at', 'user_name', 'annuled_give_score', 'question_fragment', 'responses', 'annuled_distribute_exam_teacher_subject','is_checked_by')

    def get_user_name(self, status):
        return status.user and status.user.get_user_full_name
    
    def get_responses(self, status):
        return StatusQuestionSerializer(
            StatusQuestion.objects.filter(
                status=StatusQuestion.RESPONSE,
                source_status_question=status
            ).order_by('created_at'),
            many=True
        ).data
    
    def get_is_checked_by(self, status):
        if status.is_checked_by:
            return status.is_checked_by.get_user_full_name
        return None

class ExamQuestionSerializer(serializers.ModelSerializer):
    question = QuestionSerializerSimple(many=False, read_only=True)
    status_list = serializers.SerializerMethodField()
    last_status = serializers.SerializerMethodField()
    has_answer = serializers.SerializerMethodField()
    can_be_remove = serializers.SerializerMethodField()
    exam_question_number = serializers.CharField(read_only=True)
    has_duplicate_enunciation = serializers.SerializerMethodField()

    class Meta:
        model = ExamQuestion
        fields = ('id', 'question', 'order', 'status_list', 'last_status', 'weight', 'has_answer', 'can_be_remove', 'block_weight', 'exam_question_number', 'has_duplicate_enunciation')

    def get_has_duplicate_enunciation(self, obj):
        return obj.has_duplicate_enunciation

    def get_status_list(self, obj):
        return obj.status_list
    
    def get_has_answer(self, obj):
        from fiscallizeon.answers.models import TextualAnswer, FileAnswer, OptionAnswer, SumAnswer

        textual_answers = TextualAnswer.objects.filter(student_application__application__exam=obj.exam).exists()
        file_answers = FileAnswer.objects.filter(student_application__application__exam=obj.exam).exists()
        option_answers = OptionAnswer.objects.filter(student_application__application__exam=obj.exam).exists()
        sum_answers = SumAnswer.objects.filter(student_application__application__exam=obj.exam).exists()
        
        if textual_answers or file_answers or option_answers or sum_answers:
            return True
        
        return False

    def get_last_status(self, obj):
        
        statusquestion = StatusQuestion.objects.filter(
            exam_question=obj,
            exam_question__exam_teacher_subject=obj.exam_teacher_subject
        ).exclude(
            status__in=[StatusQuestion.SEEN, StatusQuestion.RESPONSE]
        ).order_by('created_at').last()
        
        status = StatusQuestionSerializer(instance=statusquestion).data
        
        if not statusquestion:
            status["status"] = StatusQuestion.OPENED
            status["status_display"] = StatusQuestion.STATUS_CHOICES[StatusQuestion.OPENED][1]

        return status
    
    def get_can_be_remove(self, obj):
        return obj.can_be_remove

class ExamQuestionVerySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamQuestion
        fields = ('id', 'weight', 'order')

class ExamSumWeightSerializer(serializers.ModelSerializer):
    class ExamTeacherSubjectSumWeightSerializer(serializers.ModelSerializer):
        sum_weight = serializers.SerializerMethodField()
        class Meta:
            model = ExamTeacherSubject
            fields = ['id', 'sum_weight']
            
        def get_sum_weight(self, obj):
            total = obj.examquestion_set.using('default').availables(exclude_annuleds=True).aggregate(sum=Sum('weight')).get("sum") or 0
            return total
            
    
    sum_weight = serializers.SerializerMethodField()
    exam_teacher_subjects = ExamTeacherSubjectSumWeightSerializer(source="examteachersubject_set", many=True, read_only=True)

    class Meta:
        model = Exam
        fields = ['sum_weight', 'exam_teacher_subjects']
        
    def get_sum_weight(self, obj):
        total = obj.examquestion_set.using('default').availables(exclude_annuleds=True).aggregate(sum=Sum('weight')).get("sum") or 0
        return total

class ExamTeacherSubjectSimpleSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    class Meta:
        model = ExamTeacherSubject
        fields = [
            'id',
            'name',
        ]

    def get_name(self, obj):
        return obj.__str__()

class ExamTeacherSubjectSerializer(serializers.ModelSerializer):
    teacher_subject = TeacherSubjectVerySimpleSerializer(many=False, read_only=True)
    grade = GradeSerializer(many=False, read_only=True)
    exam_questions_load = serializers.SerializerMethodField()
    exam_questions = serializers.SerializerMethodField()
    exam_questions_count = serializers.SerializerMethodField()
    status_count = serializers.SerializerMethodField()
    sum_weight = serializers.SerializerMethodField()
    relations = serializers.SerializerMethodField()
    has_questions_generate_or_modified_by_ia = serializers.SerializerMethodField()
    
    class Meta:
        model = ExamTeacherSubject
        fields = [
            'id', 
            'quantity', 
            'reviewed_by',
            'note', 
            'teacher_subject', 
            'grade', 
            'exam_questions', 
            'exam_questions_count', 
            'exam_questions_load', 
            'status_count', 
            'teacher_note', 
            'sum_weight', 
            'subject_note', 
            'block_subject_note',
            'is_foreign_language',
            'block_questions_quantity',
            'block_quantity_limit',
            'distribute_scores_freely',
            'order',
            'objective_quantity',
            'discursive_quantity',
            'relations',
            'has_error_create_exam_question_ia',
            'has_questions_generate_or_modified_by_ia'  
        ]

    def get_sum_weight(self, obj):
        # total = obj.examquestion_set.availables(exclude_annuleds=True).aggregate(sum=Sum('weight')).get("sum", 0)
        # return total
        return 0
        
    def get_status_count(self, obj):
        data = {}
        total = 0

        for status in StatusQuestion.STATUS_CHOICES:
            
            [ key, value ] = status
            
            # if key == StatusQuestion.OPENED:
            #     continue
            
            data[value] = StatusQuestion.objects.filter(
                Q(
                    status=key,
                    exam_question__exam_teacher_subject=obj,
                    active=True
                )
            ).exclude(
                Q(

                    Q(
                        active=True,
                        status=StatusQuestion.DRAFT
                    ) | 
                    Q(status=StatusQuestion.RESPONSE)
                )
            ).distinct().count()

            total += data[value]
        
        data[StatusQuestion.STATUS_CHOICES[StatusQuestion.OPENED][1]] += obj.examquestion_set.filter(statusquestion__isnull=True).count()
        
        return data
    
    def get_exam_questions_count(self, obj):
        exam_questions = obj.examquestion_set.all()

        status_question_pks = list(StatusQuestion.objects.filter(
            active=True, 
            status=StatusQuestion.DRAFT,
            exam_question__in=exam_questions
        ).values_list('exam_question', flat=True))

        return exam_questions.exclude(
            pk__in=status_question_pks
        ).distinct().count()
    
    def get_exam_questions_load(self, obj):
        return False
    
    def get_exam_questions(self, obj):
        return []
        # exam_questions = ExamQuestionSerializer(instance=obj.examquestion_set.all(), many=True, read_only=True)
        # return exam_questions.data

    def get_relations(self, obj):
        from fiscallizeon.subjects.models import SubjectRelation
        
        relations = SubjectRelation.objects.filter(subjects=obj.teacher_subject.subject)
        
        return relations.values_list('id', flat=True)
    
    def get_has_questions_generate_or_modified_by_ia(self, obj):
        exam_questions = obj.examquestion_set.all()
        
        has_questions_with_ai = exam_questions.filter(question__created_with_ai=True).exists()

        return has_questions_with_ai

class ExamTemplateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Exam
        fields = ('id', 'name', 'is_abstract', 'status', 'coordinations', 'is_english_spanish', 'start_number', 'category', 'is_enem_simulator', 'external_code')

class CustomPageDuplicateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientCustomPage
        fields = ['id', 'name']

class ExamQuestionCreateTemplateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ExamQuestion
        fields = ['question', 'exam', 'order', 'weight']

class ExamQuestionTemplateSerializer(serializers.ModelSerializer):

    question = ExamTemplateQuestionSerializer()

    class Meta:
        model = ExamQuestion
        fields = ['id', 'question', 'order', 'weight', 'is_foreign_language']


class ExamQuestionSimpleUpdateTemplateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ExamQuestion
        fields = ['order', 'weight', 'is_foreign_language']


class ExamTemplateUpdateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Exam
        fields = ['id', 'name', 'status', 'is_english_spanish', 'start_number', 'is_enem_simulator', 'external_code']
class ExamTemplateRetrieveSerializer(serializers.ModelSerializer):

    examquestions = ExamQuestionTemplateSerializer(source='examquestion_set', many=True)

    class Meta:
        model = Exam
        fields = ['id', 'name', 'examquestions']


class ExamQuestionTeacherSerializer(serializers.ModelSerializer):
    from fiscallizeon.questions.serializers.questions import QuestionTeacherSerializer
    
    question = QuestionTeacherSerializer(many=False)
    status_list = serializers.SerializerMethodField()
    last_status = serializers.SerializerMethodField()
    can_be_remove = serializers.SerializerMethodField()

    class Meta:
        model = ExamQuestion
        fields = ('id', 'question', 'order', 'status_list', 'last_status', 'weight', 'can_be_remove')

    def get_status_list(self, obj):
        return obj.status_list

    def get_last_status(self, obj):
        status = StatusQuestionSerializer(
            StatusQuestion.objects.filter(
                exam_question=obj,
                exam_question__exam_teacher_subject=obj.exam_teacher_subject
            ).exclude(
                status__in=[StatusQuestion.SEEN, StatusQuestion.RESPONSE]
            ).order_by('created_at').last()
        ).data
        
        if not status["status"]:
            status["status"] = "Em aberto"

        return status

    def get_can_be_remove(self, obj):
        return obj.can_be_remove
        
class ExamTeacherTeacherSubjectSerializer(serializers.ModelSerializer):
    questions  = ExamQuestionTeacherSerializer(source="examquestion_set", many=True)
    subject_name = serializers.CharField(source="teacher_subject.subject.name", read_only=True)
    subject_knowledge_area = serializers.CharField(source="teacher_subject.subject.knowledge_area.name", read_only=True)
    grade_name = serializers.CharField(source="grade.name_grade", read_only=True)
    
    class Meta:
        model = ExamTeacherSubject
        fields = ['id', 'teacher_subject', 'grade', 'grade_name', 'subject_name', 'subject_knowledge_area', 'quantity', 'questions']


class ExamTeacherSerializer(serializers.ModelSerializer):
    teacher_subjects = serializers.SerializerMethodField()    
    class Meta:
        model = Exam
        fields = ['id', 'name', 'base_text_location', 'teacher_subjects', 'is_english_spanish', 'random_alternatives', 'correction_by_subject', 'random_questions', 'group_by_topic']

    def get_teacher_subjects(self, obj):
        exam_teacher_subjects = ExamTeacherSubject.objects.using('default').filter(exam=obj).distinct()
        if hasattr(obj, 'user_pk'):
            user = User.objects.get(pk=obj.user_pk)
            teacher = user.inspector if hasattr(user, 'inspector') else None
            
            if teacher and user.user_type == settings.TEACHER: 
                exam_teacher_subjects = exam_teacher_subjects.filter(
                    teacher_subject__teacher__user=user,
                    teacher_subject__active=True,
                )
        return ExamTeacherTeacherSubjectSerializer(instance=exam_teacher_subjects.distinct(), many=True, read_only=True).data


class SchoolCoordinationSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolCoordination
        fields = ['id']

class ExamCoordinationSerializer(serializers.ModelSerializer):
    coordinations = serializers.SerializerMethodField()
    teacher_subjects = serializers.SerializerMethodField()
    materials = serializers.SerializerMethodField()
    application_is_finished = serializers.BooleanField(source='get_application_is_finished', read_only=True)

    class Meta:
        model = Exam
        exclude = ['is_abstract', 'questions']

    def get_materials(self, obj):
        return StudyMaterialSimpleSerializer(instance=obj.materials.using('default').all(), many=True).data if obj.materials.using('default').all() else []

    def get_teacher_subjects(self, obj):
        exam_teacher_subjects = ExamTeacherSubject.objects.using('default').filter(exam=obj)
        if hasattr(obj, 'user_pk'):
            user = User.objects.get(pk=obj.user_pk)
            teacher = user.inspector if hasattr(user, 'inspector') else None
            
            if teacher and user.user_type == settings.TEACHER:
                if teacher.is_discipline_coordinator:
                    exam_teacher_subjects = teacher.get_exams_to_review(return_exam_teacher_subjects=True).filter(exam=obj)
                else:
                    exam_teacher_subjects = exam_teacher_subjects.filter(
                        teacher_subject__teacher=teacher,
                        teacher_subject__active=True,
                    )
                
        return ExamTeacherSubjectSerializer(instance=exam_teacher_subjects.distinct(), many=True, read_only=True).data

    def get_coordinations(self, obj):
        return [coordination.get('id') for coordination in json.loads(json.dumps(SchoolCoordinationSimpleSerializer(instance=SchoolCoordination.objects.using('default').filter(pk__in=obj.coordinations.using('default').all().values_list('pk', flat=True)), many=True, read_only=True).data))]
    
class ExamTeacherSubjectUpdateSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamTeacherSubject
        fields = [
            'quantity', 
            'reviewed_by',
            'subject_note', 
            'block_subject_note', 
            'note', 
            'teacher_subject', 
            'grade',
            'block_questions_quantity',
            'block_quantity_limit',
            'distribute_scores_freely',
            'order',
            'objective_quantity',
            'discursive_quantity',
        ]

class ExamTeacherSubjectCreateSimpleSerializer(serializers.ModelSerializer):
    exam = serializers.PrimaryKeyRelatedField(queryset=Exam.objects.using('default').all())
    
    class Meta:
        model = ExamTeacherSubject
        exclude = ['teacher_note',]
    
class ExamOrientationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ExamOrientation
        fields = ['title', 'content']

class ExamToReviewSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Exam
        fields = ['id', 'category_name', 'name', 'elaboration_deadline', 'release_elaboration_teacher']
        
    def get_category_name(self, obj):
        return obj.get_category_display()
    
class ExamTeacherSubjectOpenedOrToReviewSerializer(serializers.ModelSerializer):
    exam = ExamToReviewSerializer(read_only=True, many=False)
    teacher_subject = TeacherSubjectSimpleSerializer(many=False, read_only=True)
    grade = GradeSerializer(read_only=True, many=False)
    questions_count = serializers.IntegerField(source='count')
    reviewed_questions_count = serializers.IntegerField(source='count_reviewed_questions')
    
    class Meta:
        model = ExamTeacherSubject
        exclude = ['created_at', 'updated_at']


class ExamTeacherSubjectFileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamTeacherSubjectFile
        fields = ('file', 'exam_teacher_subject',)


class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = ('id', 'name', 'quantity_alternatives')


class ExamTeacherSubjectExamElaborationSerializer(serializers.ModelSerializer):
    exam_questions  = serializers.SerializerMethodField() # queryset que chega na tela de professor
    subject_name = serializers.CharField(source="teacher_subject.subject.name", read_only=True)
    subject_knowledge_area = serializers.CharField(source="teacher_subject.subject.knowledge_area.name", read_only=True)
    subject_knowledge_area_pk = serializers.CharField(source="teacher_subject.subject.knowledge_area.pk", read_only=True)
    subject_pk = serializers.CharField(source="teacher_subject.subject.pk", read_only=True)
    grade_name = serializers.CharField(source="grade.name_grade", read_only=True)
    urls = serializers.JSONField()
    exam = ExamSerializer(read_only=True, many=False)
    show_questions_bank_tutorial = serializers.CharField(source="teacher_subject.teacher.show_questions_bank_tutorial", read_only=True)
    elaboration_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ExamTeacherSubject
        fields = [
            'id', 
            'teacher_subject', 
            'teacher_note', 
            'grade', 
            'grade_name', 
            'subject_name', 
            'subject_knowledge_area', 
            'quantity', 
            'exam_questions', 
            'block_subject_note', 
            'subject_note', 
            'urls', 
            'exam', 
            'subject_knowledge_area_pk', 
            'subject_pk', 
            'show_questions_bank_tutorial',
            'elaboration_expired',
        ]

    def get_exam_questions(self, obj):
        exam_questions = ExamQuestion.objects.filter(
            Q(
                Q(source_exam_teacher_subject=obj) | 
                Q(source_exam_teacher_subject__isnull=True, exam_teacher_subject=obj)
            )
        )
        serialized_exam_questions = [
            ExamQuestionExamElaborationSerializer(eq, context={'request': self.context['request']}).data
            for eq in exam_questions
        ]

        return serialized_exam_questions
    

class ExamQuestionNumberSerializer(serializers.ModelSerializer):
    exam_question_number = serializers.CharField(read_only=True)
    
    class Meta:
        model = ExamQuestion
        fields = ['id', 'exam_question_number']