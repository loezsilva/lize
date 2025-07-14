import uuid
from rest_framework import serializers
from fiscallizeon.applications.models import ApplicationStudent, Application
from fiscallizeon.exams.models import Exam, ExamQuestion, ExamTeacherSubject
from fiscallizeon.students.models import Student
from fiscallizeon.subjects.models import Subject, KnowledgeArea
from fiscallizeon.classes.models import SchoolClass, Grade
from fiscallizeon.questions.models import Question, QuestionOption, BaseText
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.answers.models import OptionAnswer, FileAnswer, TextualAnswer, SumAnswer

class OptionSerializer(serializers.Serializer):
    index = serializers.IntegerField()
    option = serializers.UUIDField()

class CreateAnswerSerializer(serializers.Serializer):
    TYPE_CHOICES = (
        ('option', 'Objetiva'),
        ('sum', 'Somatório'),
        ('textual', 'Textual'),
        ('file', 'Arquivo anexado'),
    )
    category = serializers.ChoiceField(choices=TYPE_CHOICES)
    exam_question = serializers.UUIDField()
    text = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField(required=False, allow_null=True)
    options = serializers.ListField(
        child=OptionSerializer(),
        required=False
    )

    def validate(self, data):
        answer_category = data.get('category')
        text = data.get('text', None)
        file = data.get('file', None)
        options = data.get('options', [])

        # Validações por tipo de resposta
        if 'option' in answer_category or 'sum' in answer_category:
            if not options:
                raise serializers.ValidationError({
                    "options": "Este campo deve conter pelo menos uma opção para respostas objetivas ou de somatório."
                })
            for option in options:
                if not isinstance(option, dict):
                    raise serializers.ValidationError({
                        "options": "Cada item deve ser um dicionário contendo 'index' e 'option'."
                    })
                if 'index' not in option or 'option' not in option:
                    raise serializers.ValidationError({
                        "options": "Cada item deve conter os campos 'index' (int) e 'option' (UUID)."
                    })
                if not isinstance(option['index'], int):
                    raise serializers.ValidationError({
                        "options": f"O campo 'index' deve ser um inteiro. Valor inválido encontrado: {option['index']}"
                    })
                try:
                    uuid.UUID(str(option['option']))
                except ValueError:
                    raise serializers.ValidationError({
                        "options": f"O campo 'option' deve ser um UUID válido. Valor inválido encontrado: {option['option']}"
                    })

        if 'textual' in answer_category and not text:
            raise serializers.ValidationError({"text": "Este campo é obrigatório para respostas textuais."})

        if 'file' in answer_category and not file:
            raise serializers.ValidationError({"file": "Este campo é obrigatório para respostas com arquivo anexado."})

        return data