from datetime import datetime

from decimal import Decimal
from rest_framework import serializers
from fiscallizeon.applications.models import ApplicationStudent, Application
from fiscallizeon.exams.models import Exam, ExamQuestion, ExamTeacherSubject, StatusQuestion
from fiscallizeon.students.models import Student
from fiscallizeon.subjects.models import Subject, KnowledgeArea
from fiscallizeon.classes.models import SchoolClass, Grade
from fiscallizeon.questions.models import Question, QuestionOption, BaseText, Topic, Abiliity, Competence
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.answers.models import OptionAnswer, FileAnswer, TextualAnswer, SumAnswer
from fiscallizeon.materials.models import StudyMaterial
from ..answers.functions import get_answer_object
from fiscallizeon.core.templatetags.exams_tags import get_correct_option_answer
from fiscallizeon.corrections.models import CorrectionTextualAnswer, CorrectionFileAnswer
from django.db.models import Case, Count, F, OuterRef, Q, Subquery, Sum, Value, When

class ExamSerializer(serializers.ModelSerializer):
    urls = serializers.JSONField(source='urls_v3')
    subjects = serializers.SerializerMethodField()
    
    class Meta:
        model = Exam
        fields = ['id', 'name', 'subjects', 'urls']
    
    def get_subjects(self, obj):
        return SubjectSerializer(
            instance=Subject.objects.filter(id__in=obj.teacher_subjects.values_list('subject_id', flat=True)),
            many=True,
            context={'exam': obj}
        ).data

class ApplicationSerializer(serializers.ModelSerializer):
    exam = ExamSerializer()
    category_display = serializers.CharField(source='get_category_display')
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    
    class Meta:
        model = Application
        fields = ['exam', 'date', 'start', 'end', 'start_date', 'end_date', 'date_end', 'category', 'category_display', 'allow_student_redo_list']

    def get_start_date(self, obj):
        return datetime.combine(obj.date, obj.start)

    def get_end_date(self, obj):
        return datetime.combine(obj.date, obj.end)
        
class ApplicationStudentSerializer(serializers.ModelSerializer):
    application = ApplicationSerializer()
    urls = serializers.JSONField(source='urls_v3')
    started_in = serializers.DateTimeField(source='start_time')
    finished_in = serializers.DateTimeField(source='end_time')
    
    class Meta:
        model = ApplicationStudent
        fields = ['id', 'application', 'started_in', 'finished_in', 'urls']
        
        
class StudentSerializer(serializers.ModelSerializer):
    urls = serializers.JSONField(source='urls_v3')
    nickname = serializers.CharField(source='user.nickname')
    class Meta:
        model = Student
        fields = ['name', 'nickname', 'enrollment_number', 'birth_of_date', 'urls']

class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = ['id', 'full_name']
        
class SchoolClassSerializer(serializers.ModelSerializer):
    grade = GradeSerializer()
    class Meta:
        model = SchoolClass
        fields = ['id', 'name', 'grade']
        
class ColleaguesSerializer(serializers.ModelSerializer):
    nickname = serializers.CharField(source='user.nickname')
    avatar = serializers.ImageField(source='user.avatar')
    mood = serializers.IntegerField(source='user.mood') 
    
    class Meta:
        model = Student
        fields = ['id', 'name', 'nickname', 'avatar', 'mood']

class StudyMaterialSerializer(serializers.ModelSerializer):
    #TODO:
    is_favorite = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()
    send_by = serializers.SerializerMethodField()
    class Meta:
        model = StudyMaterial
        fields = ['id', 'title', 'thumbnail', 'material', 'stage', 'emphasis', 'release_material_study', 'send_by', 'subjects', 'updated_at', 'is_favorite', 'send_by', 'material_video']

    def validate_thumbnail(self, value):
        if value and hasattr(value, 'content_type'):
            if not value.content_type in ["image/jpeg", "image/png", "image/gif", "image/jpg", "image/webp"]:
                raise serializers.ValidationError("Arquivo de imagem inválido")
        return value
    
    def get_is_favorite(self, obj):
            return obj.is_favorite

    def get_subjects(self, obj):
        return SimpleSubjectSerializer(
            instance=obj.subjects.all(),
            many=True
        ).data
    
    def get_send_by(self, obj):
        if obj.send_by:
            return obj.send_by.name
        return None

class KnowledgeAreaSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = KnowledgeArea
        fields = ['name']
        
class SimpleSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name']
        
class SubjectSerializer(serializers.ModelSerializer):
    knowledge_area = KnowledgeAreaSerializer()
    questions = serializers.SerializerMethodField()
    class Meta:
        model = Subject
        fields = ['id', 'name', 'is_foreign_language_subject', 'knowledge_area', 'questions']
    def get_questions(self, obj):
        if 'exam' not in self.context:
            return []
        exam = self.context['exam']
        exam_questions = exam.examquestion_set.availables()
        return SimpleExamQuestionSerializer(instance=exam_questions, many=True).data
        
class SimpleQuestionAlternativesSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ['id', 'text']

class BaseTextSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseText
        fields = ['id', 'title', 'text']

class SimpleQuestionSerializer(serializers.ModelSerializer):
    # subject = SubjectSerializer()
    alternatives = SimpleQuestionAlternativesSerializer(many=True)
    category_display = serializers.CharField(source='get_category_display')
    base_texts = BaseTextSerializer(many=True)
    
    class Meta:
        model = Question
        fields = ['enunciation', 'category', 'category_display', 'base_texts', 'alternatives'] # 'subject'

class SimpleExamQuestionSerializer(serializers.ModelSerializer):
    question = SimpleQuestionSerializer()
    number = serializers.SerializerMethodField()
    
    class Meta:
        model = ExamQuestion
        fields = ['id', 'number', 'question']
      
    def get_number(self, obj):
        return obj.exam_question_number
    
class TakeTestExamQuestionSerializer(SimpleExamQuestionSerializer):
    answer = serializers.SerializerMethodField()
    
    class Meta:
        model = ExamQuestion
        fields = ['id', 'number', 'question', 'answer']
        
    def get_answer(self, obj):
        application_student: ApplicationStudent = self.context['application_student']
        return get_answer_object(application_student, obj.question)

class TeacherSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Inspector
        fields = ['name']
    
class TakeTestSerializer(serializers.ModelSerializer):
    teacher = TeacherSerializer(source='teacher_subject.teacher')
    subject = SubjectSerializer(source='teacher_subject.subject')
    exam_questions = serializers.SerializerMethodField()
    
    class Meta:
        model = ExamTeacherSubject
        fields = ['id', 'teacher', 'subject', 'exam_questions']
      
    def get_exam_questions(self, obj):
        application_student = self.context['application_student']
        exam_questions = obj.examquestion_set.availables()
        return TakeTestExamQuestionSerializer(instance=exam_questions, many=True, context={ 'application_student': application_student }).data
    

class TakeTestSubjectsSerializer(serializers.ModelSerializer):
    exam_questions = serializers.SerializerMethodField()
    knowledge_area = KnowledgeAreaSerializer()
    
    class Meta:
        model = Subject
        fields = ['id', 'name', 'is_foreign_language_subject', 'knowledge_area', 'exam_questions']
      
    def get_exam_questions(self, obj):
        application_student = self.context['application_student']
        exam_questions = application_student.application.exam.examquestion_set.availables().filter(exam_teacher_subject__teacher_subject__subject=obj).order_by('order')
        return TakeTestExamQuestionSerializer(instance=exam_questions, many=True, context={ 'application_student': application_student }).data

class PreviousFeedbackExamQuestion(serializers.ModelSerializer):
    correct_answer = serializers.SerializerMethodField()
    class Meta:
        model = ExamQuestion
        fields = ['id', 'correct_answer']
    
    def get_correct_answer(self, obj):
        return get_correct_option_answer(question=obj.question)

class PreviousFeedbackExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = ['name']

class PreviousFeedbackApplicationSerializer(serializers.ModelSerializer):
    exam = PreviousFeedbackExamSerializer()
    category_display = serializers.CharField(source='get_category_display')
    class Meta:
        model = Application
        fields = ['exam', 'date', 'category', 'category_display']
        

class PreviousFeedbackSerializer(serializers.ModelSerializer):
    application = PreviousFeedbackApplicationSerializer()
    questions_summary = serializers.SerializerMethodField()
    exam_questions = serializers.SerializerMethodField()
    class Meta:
        model = ApplicationStudent
        fields = ['id', 'application', 'questions_summary', 'exam_questions']
        
    def get_exam_questions(self, obj):
        exam_questions = (
            obj.application.exam.examquestion_set
            .filter(question__number_is_hidden=False)
            .availables()
            .order_by('exam_teacher_subject__order', 'order')
        )
        
        return PreviousFeedbackExamQuestion(exam_questions, many=True).data

    def get_questions_summary(self, obj):
        exam_questions = obj.application.exam.examquestion_set.availables()
        
        return [
            {
                'label': 'Objetivas',
                'value': exam_questions.filter(question__category=Question.CHOICE).count()
            },
            {
                'label': 'Discursivas',
                'value': exam_questions.filter(question__category=Question.TEXTUAL).count()
            },
            {
                'label': 'Anexo',
                'value': exam_questions.filter(question__category=Question.FILE).count()
            },
            {
                'label': 'Somatório',
                'value': exam_questions.filter(question__category=Question.SUM_QUESTION).count()
            },
        ]
        
class ExamQuestionResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    question_id = serializers.CharField(source='question.id')
    enunciation = serializers.CharField(source='question.enunciation')
    alternatives = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    question_weight = serializers.SerializerMethodField()
    commented_awnser = serializers.SerializerMethodField()
    question_number = serializers.SerializerMethodField()
    teacher_feedback = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    category_display = serializers.SerializerMethodField()
    answer = serializers.SerializerMethodField()
    img_annotations = serializers.SerializerMethodField()
    topics = serializers.SerializerMethodField()
    abilities = serializers.SerializerMethodField()
    competences = serializers.SerializerMethodField()
    text_correction_answer = serializers.SerializerMethodField()
    have_correction_answer = serializers.SerializerMethodField()
    annuled = serializers.SerializerMethodField()
    annuled_give_score = serializers.SerializerMethodField()
    
    def get_answer(self, obj):
        return {
            'answer_text': self.get_textual_answer(obj=obj),
            'answer_file': self.get_file_answer(obj=obj),
            'checked_answers': self.get_checked_answers(obj=obj),
        }

    def get_annuled(self, obj):
        status = StatusQuestion.objects.filter(exam_question=obj, active=True).first()
        return status.status == StatusQuestion.ANNULLED if status else False
        
    def get_annuled_give_score(self, obj):
        status = StatusQuestion.objects.filter(exam_question=obj, active=True).first()
        return status.annuled_give_score if status else False
        
    class AlternativeSerializer(serializers.ModelSerializer):
        class Meta:
            model = QuestionOption
            fields = ('id', 'text', 'is_correct')

    class TopicSerializer(serializers.ModelSerializer):
        class Meta:
            model = Topic
            fields = ('id', 'name')

    class AbiliitySerializer(serializers.ModelSerializer):
        class Meta:
            model = Abiliity
            fields = ('id', 'text')

    class CompetenceSerializer(serializers.ModelSerializer):
        class Meta:
            model = Competence
            fields = ('id', 'text')

    def get_commented_awnser(self, obj):
        return {
            "text": obj.question.commented_awnser,
            "video": obj.question.get_emmbbeded_video_answer,
        }

    def get_subject_object(self, obj):
        if obj.exam.is_abstract:
            return obj.question.subject if obj.question.subject else ""
        return obj.exam_teacher_subject.teacher_subject.subject
    
    def get_subject(self, obj):
        subject = self.get_subject_object(obj)
        if subject:
            return {
                "id": str(subject.id),
                "name": str(subject),
            }
        return None
    
    def get_have_correction_answer(self, obj):
        if obj.question.category == Question.TEXTUAL:
            return CorrectionTextualAnswer.objects.filter(
                textual_answer__question=obj.question,
                textual_answer__student_application=self.context['application_student'],
            ).exists()
        if obj.question.category == Question.FILE:
            return CorrectionFileAnswer.objects.filter(
                file_answer__question=obj.question,
                file_answer__student_application=self.context['application_student'],
            ).exists()
        return False

    def get_text_correction_answer(self, obj):
        if obj.question.category == Question.TEXTUAL:
            textual = TextualAnswer.objects.filter(question=obj.question.pk, 
                student_application=self.context['application_student'],
                ).first()
            return CorrectionTextualAnswer.objects.filter(textual_answer=textual,
                ).values('correction_criterion__name', 'point').order_by('correction_criterion__order')
        
        if obj.question.category == Question.FILE:
            file = FileAnswer.objects.filter(question=obj.question.pk, 
                student_application=self.context['application_student'],
                ).first()
            return CorrectionFileAnswer.objects.filter(file_answer=file,
                ).values('correction_criterion__name', 'point').order_by('correction_criterion__order')
        
        return []


    def _get_student_answer(self, application_student, question):
        if question.category == Question.CHOICE:
            return (
                OptionAnswer.objects.filter(
                    question_option__question=question,
                    student_application=application_student,
                )
                .filter(status=OptionAnswer.ACTIVE)
                .order_by('-created_at')
            )
        elif question.category == Question.SUM_QUESTION:
            return SumAnswer.objects.filter(
                question=question,
                student_application=application_student,
            )
        elif question.category == Question.TEXTUAL:
            return TextualAnswer.objects.filter(
                question=question,
                student_application=application_student,
            )
        elif question.category == Question.FILE:
            return FileAnswer.objects.filter(
                question=question,
                student_application=application_student,
            )

        return None

    def get_alternatives(self, exam_question):

        from fiscallizeon.applications.models import RandomizationVersion 
        from fiscallizeon.exams import json_utils

        if exam_question.question.category in [Question.CHOICE, Question.SUM_QUESTION]:
            alternatives = exam_question.question.alternatives.distinct()
            
            if self.context['application_student'].read_randomization_version > 0:
                randomization_version = RandomizationVersion.objects.filter(
                    application_student=self.context['application_student'],
                    version_number=self.context['application_student'].read_randomization_version
                ).first()
                
                question_json = list(filter(lambda _question: _question["pk"] == exam_question.question.id, json_utils.convert_json_to_choice_questions_list(randomization_version.exam_json)))
                alternatives_pks = [alternative for alternative in question_json[0]['alternatives']]
                preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(alternatives_pks)])
                alternatives = alternatives.order_by(preserved)
            
            return self.AlternativeSerializer(alternatives, many=True).data
        
        return []


    def get_category(self, obj):
        return obj.question.category
    
    def get_category_display(self, obj):
        return obj.question.get_category_display()

    def get_textual_answer(self, obj):
        answers = TextualAnswer.objects.filter(
            question=obj.question,
            student_application=self.context['application_student'],
        ).order_by('-created_at')

        if answers:
            return answers[0].content

        return None

    def get_file_answer(self, obj):
        answers = FileAnswer.objects.filter(
            question=obj.question,
            student_application=self.context['application_student'],
        ).order_by('-created_at')

        if answers and answers[0].arquivo:
            return answers[0].arquivo.url

        return None

    def get_img_annotations(self, obj):
        answers = FileAnswer.objects.filter(
            question=obj.question,
            student_application=self.context['application_student'],
        ).order_by('-created_at')

        if answers and answers[0].arquivo:
            return answers[0].img_annotations

        return None
    
    def get_checked_answers(self, obj):
        from fiscallizeon.questions.models import Question
        
        if obj.question.category == Question.CHOICE:
            
            active_answers = (
                OptionAnswer.objects.filter(
                    question_option__question=obj.question,
                    student_application=self.context['application_student'],
                )
                .filter(status=OptionAnswer.ACTIVE)
                .order_by('-created_at')
            )
            answer = active_answers.values('question_option__pk')
            if answer:
                return [
                    answer[0]['question_option__pk']
                ]
            
        else:
            
            sum_answers = SumAnswer.objects.filter(
                question=obj.question,
                student_application=self.context['application_student'], 
            )
            if sum_answers:
                return list(
                    sum_answers[0].sumanswerquestionoption_set.filter(
                        checked=True
                    ).values_list(
                        'question_option_id', flat=True
                    )
                )        
        return []

    def get_percent_grade(self, obj):
        active_answers = self._get_student_answer(
            self.context['application_student'], obj.question
        )

        score = 0
        if obj.question.category == Question.CHOICE:
            active_answers_option = active_answers.values(
                'question_option__is_correct'
            )

            question_is_correct = None
            if active_answers_option:
                question_is_correct = active_answers_option[0][
                    'question_option__is_correct'
                ]

            if question_is_correct:
                score = Decimal(1.0)
        elif obj.question.category == Question.SUM_QUESTION:
            if active_answers:
                active_answer = active_answers[0]
                score = active_answer.grade
        else:
            if active_answers:
                active_answer = active_answers[0]
                if active_answer.grade:
                    score = active_answer.grade

        return score
    
    def get_grade(self, obj):
        return {
            'value': self.get_teacher_grade(obj=obj),
            'percent': self.get_percent_grade(obj=obj)
        }
    
    def get_teacher_grade(self, obj):
        active_answers = self._get_student_answer(
            self.context['application_student'], obj.question
        )

        score = 0
        if obj.question.category == Question.CHOICE:
            active_answers_option = active_answers.values(
                'question_option__is_correct'
            )

            question_is_correct = None
            if active_answers_option:
                question_is_correct = active_answers_option[0][
                    'question_option__is_correct'
                ]

            if question_is_correct:
                score = obj.weight
        elif obj.question.category == Question.SUM_QUESTION:
            if active_answers:
                active_answer = active_answers[0]
                score = active_answer.grade * obj.weight
        else:
            if active_answers:
                active_answer = active_answers[0]
                if active_answer.teacher_grade:
                    score = active_answer.grade * obj.weight

        return score

    def get_question_weight(self, obj):
        return obj.weight

    def get_teacher_feedback(self, obj):
        if obj.question.category in [Question.CHOICE, Question.SUM_QUESTION]:
            return None

        active_answers = self._get_student_answer(
            self.context['application_student'], obj.question
        )

        if not active_answers:
            return None

        return active_answers[0].teacher_feedback

    def get_topics(self, obj):
        return self.TopicSerializer(
            obj.question.topics.distinct(), many=True
        ).data

    def get_abilities(self, obj):
        return self.AbiliitySerializer(
            obj.question.abilities.distinct(), many=True
        ).data

    def get_competences(self, obj):
        return self.CompetenceSerializer(
            obj.question.competences.distinct(), many=True
        ).data

    def get_question_number(self, obj):
        return self.context['application_student'].application.exam.number_print_question(obj.question, randomization_version=self.context['randomization_version'])