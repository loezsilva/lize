from rest_framework import serializers

from django.shortcuts import get_object_or_404

from fiscallizeon.questions.models import Question
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.exams.models import ExamQuestion, StatusQuestion
from fiscallizeon.answers.models import OptionAnswer, TextualAnswer, FileAnswer
from fiscallizeon.answers.serializers.file_answers import FileAnswerDetailedSerializer
from fiscallizeon.answers.serializers.textual_answers import TextualAnswerDetailedSerializer
from fiscallizeon.answers.serializers.option_answers import OptionAnswerDetailedSerializer
from fiscallizeon.applications.serializers.application_student import ApplicationStudentWithAnswerSerializer
from fiscallizeon.questions.serializers.questions import QuestionSerializer, QuestionExamElaborationSerializer
from fiscallizeon.corrections.models import CorrectionFileAnswer, CorrectionTextualAnswer, CorrectionCriterion

from django.db.models import Q

class ExamQuestionAnswersSerializer(serializers.ModelSerializer):    
    answers = serializers.SerializerMethodField()
    question = QuestionSerializer()

    class Meta:
        model = ExamQuestion
        fields = ('id', 'exam', 'order', 'weight', 'question', 'answers')

    def get_answers(self, obj):
        request = self.context['request']
        school_class_pk = request.query_params.get('class', None)
        school_class = None

        if school_class_pk:
            school_class = get_object_or_404(SchoolClass, pk=school_class_pk)
            students = school_class.students.all()

        if obj.question.category == Question.CHOICE:
            answers = OptionAnswer.objects.filter(
                status=OptionAnswer.ACTIVE,
                question_option__question=obj.question,
            ).order_by('student_application__student__name')

            answers = answers.filter(student_application__student__in=students) if school_class else answers            
            return OptionAnswerDetailedSerializer(answers, many=True).data

        if obj.question.category == Question.FILE:
            answers = FileAnswer.objects.filter(
                question=obj.question
            ).order_by('student_application__student__name')

            answers = answers.filter(student_application__student__in=students) if school_class else answers
            return FileAnswerDetailedSerializer(answers, many=True).data

        if obj.question.category == Question.TEXTUAL:
            answers = TextualAnswer.objects.filter(
                question=obj.question
            ).order_by('student_application__student__name')

            answers = answers.filter(student_application__student__in=students) if school_class else answers
            return TextualAnswerDetailedSerializer(answers, many=True).data
        
class ExamQuestionAnswersV2Serializer(serializers.ModelSerializer):
    from fiscallizeon.questions.serializers.questions import QuestionSerializer
    
    applications_student = serializers.SerializerMethodField()
    question = QuestionSerializer()
    question_number = serializers.SerializerMethodField()

    class Meta:
        model = ExamQuestion
        fields = ('id', 'exam', 'order', 'weight', 'question', 'applications_student', 'question_number')

    def get_applications_student(self, obj):
        
        from fiscallizeon.applications.models import ApplicationStudent
        request = self.context['request']
        school_class_pk = request.query_params.get('class', None)
        school_class = None
        students = []

        try:
            school_class = SchoolClass.objects.get(pk=school_class_pk)
            students = school_class.students.all()
        except:
            pass

        applications_student = ApplicationStudent.objects.filter(
            Q(student__in=students) if students else Q(), 
            Q(application__exam=obj.exam)
        ).order_by('student__name')
        
        applications_student_data = ApplicationStudentWithAnswerSerializer(
            applications_student,
            context={'request': request, 'question': obj.question},
            many=True,
        ).data

        return applications_student_data
    
    def get_question_number(self, obj):
        return obj.exam.number_print_question(obj.question)
    
    def to_representation(self, instance):
        self.get_applications_student(instance)
        self.fields['question'].context.update(self.context)

        return super().to_representation(instance)


class ExamQuestionAndBaseTextsSerializer(serializers.ModelSerializer):
    from fiscallizeon.questions.serializers.questions import QuestionAndSerializerSimple
    question = QuestionAndSerializerSimple(many=False, read_only=True)
    class Meta:
        model = ExamQuestion
        fields = ('id', 'order', 'question')

    # def get_base_texts(self, examquestion):
    #     return BaseTextSimpleSerializer(instance=examquestion.question.base_texts.all(), many=True).data

class ExamQuestionExamElaborationSerializer(serializers.ModelSerializer):
    question = QuestionExamElaborationSerializer(many=False, read_only=True)
    status_list = serializers.SerializerMethodField()
    last_status = serializers.SerializerMethodField()
    can_be_remove = serializers.BooleanField()

    class Meta:
        model = ExamQuestion
        fields = ('id', 'question', 'order', 'status_list', 'last_status', 'weight', 'can_be_remove', 'source_exam_teacher_subject', 'exam_teacher_subject',  'block_weight')

    def get_status_list(self, obj):
        return obj.status_list

    def get_last_status(self, obj):
        from fiscallizeon.exams.serializers.exams import StatusQuestionSerializer
        
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
    