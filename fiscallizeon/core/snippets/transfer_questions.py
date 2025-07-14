import uuid

from django.db import transaction

from fiscallizeon.questions.models import Question, QuestionOption
from fiscallizeon.clients.models import SchoolCoordination

escalada_coordination = SchoolCoordination.objects.get(pk='1fcf2f8f-f156-423c-bae9-b5b5413a6942')
mentoria_coordination = SchoolCoordination.objects.get(pk='0bb45534-82f9-4979-b21b-97d7eec61c26')
target_coordination = SchoolCoordination.objects.filter(unity__client__pk='2e61ae21-b127-4b20-a889-e8a94ae9ceab')

questions = Question.objects.filter(coordinations__in=[escalada_coordination, mentoria_coordination])

with transaction.atomic():
    questions = Question.objects.filter(coordinations__in=[escalada_coordination, mentoria_coordination])

    for question in questions:
        original_question = Question.objects.get(pk=question.pk)
        copy_question = Question.objects.get(pk=question.pk)
        copy_question.pk = uuid.uuid4()
        copy_question.created_by = None
        copy_question.save()

        copy_question.coordinations.set(target_coordination)
        copy_question.topics.set(original_question.topics.all())
        copy_question.abilities.set(original_question.abilities.all())
        copy_question.competences.set(original_question.competences.all())

        if original_question.category == Question.CHOICE:
            for index, alternative in enumerate(original_question.alternatives.all().order_by('created_at'), 1):
                QuestionOption.objects.create(
                    question=copy_question,
                    text=alternative.text,
                    is_correct=alternative.is_correct,
                    index=index,
                )