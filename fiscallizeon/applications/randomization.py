import random
import copy
import hashlib
import json
from itertools import groupby, chain, cycle

from django.conf import settings

from fiscallizeon.applications.models import ApplicationStudent, RandomizationVersion, ApplicationRandomizationVersion
from fiscallizeon.questions.models import Question
from fiscallizeon.exams.json_utils import get_exam_base_json


def randomize_exam_json(exam_json, random_questions=True, random_alternatives=False, random_subjects=False, group_categories=False):
    for exam_teacher_subject in exam_json['exam_teacher_subjects']:
        questions = exam_teacher_subject['exam_questions']

        if random_alternatives:
            for question in questions:
                if question["category"] == Question.CHOICE:
                    random.shuffle(question['alternatives'])

        if random_questions:
            regular_questions = list(filter(lambda q: not q['base_texts'] and not q['block'], questions))
            block_questions = list(filter(lambda q: q['block'], questions))
            text_based_questions = list(filter(lambda q: q['base_texts'] and not q['block'], questions))

            sorted_block_questions = sorted(block_questions, key=lambda q: q['block'])
            sorted_text_based_questions = sorted(text_based_questions, key=lambda q: q['base_texts'])

            grouped_block_questions = [
                list(g) for _, g in groupby(sorted_block_questions, lambda q: q['block'])
            ]
            grouped_text_based_questions = [
                list(g) for _, g in groupby(sorted_text_based_questions, lambda q: q['base_texts'])
            ]

            random.shuffle(regular_questions)
            final_questions = [regular_questions]

            for question in grouped_block_questions:
                final_questions.insert(random.randint(0, len(final_questions)), question)

            for question in grouped_text_based_questions:
                random.shuffle(question)
                final_questions.insert(random.randint(0, len(final_questions)), question)

            exam_teacher_subject['exam_questions'] = list(chain(*final_questions))

        if group_categories:
            choice_questions, textual_questions, sum_questions = [], [], []
            for question in exam_teacher_subject['exam_questions']:
                if question['category'] in (0, 2):
                    textual_questions.append(question)
                    continue
                elif question['category'] == Question.SUM_QUESTION:
                    sum_questions.append(question)
                    continue

                choice_questions.append(question)
            
            exam_teacher_subject['exam_questions'] = choice_questions + sum_questions + textual_questions

    if random_subjects:
        random.shuffle(exam_json['exam_teacher_subjects'])


def randomize_application(application):
    exam_json = get_exam_base_json(application.exam)
    
    application.exam.clear_questions_numbers_cache()

    application_students_versions = []
    application_students = ApplicationStudent.objects.using('default').filter(application=application)
    application_randomization_versions = []

    last_randomization_versions = ApplicationRandomizationVersion.objects.using('default').get_last_versions(
        application=application
    )

    md5 = hashlib.md5()
    md5.update(json.dumps(exam_json).encode('utf8'))
    current_exam_hash = md5.hexdigest()

    #Verificando se já há alguma randomização para essa mesma prova a fim de evitar várias versões de randomização
    last_exam_hash = last_randomization_versions.last().exam_hash if last_randomization_versions else None
    if last_exam_hash == current_exam_hash:
        for application_student in application_students:
            randomization_version = RandomizationVersion.objects.using('default').filter(
                application_randomization_version__in=last_randomization_versions,
                application_student=application_student,
                version_number=last_randomization_versions.first().version_number
            ).first()

            if not randomization_version:
                application_randomization_version = random.choice(last_randomization_versions)
                randomization_version = RandomizationVersion.objects.create(
                    application_randomization_version=application_randomization_version,
                    application_student=application_student,
                    version_number=application_randomization_version.version_number,
                    exam_json=application_randomization_version.exam_json
                )

            application_students_versions.append({
                'pk': str(randomization_version.application_student.pk),
                'randomization_version': randomization_version.version_number,
                'application_randomization_version': str(randomization_version.application_randomization_version_id),
            })

    else:
        for i in range(1, settings.TOTAL_RANDOMIZATION_VERSIONS + 1):
            print(f"# Gerando versão randomizada {i} da aplicação {application.exam.name}")
            application_json = copy.deepcopy(exam_json)
            randomize_exam_json(
                application_json, 
                random_alternatives=application.exam.random_alternatives,
                random_subjects=application.exam.group_by_topic,
                random_questions=application.exam.random_questions,
                group_categories=True, #Caso exista necessidade no futuro, esse parâmetro pode ser adicionado ao caderno
            )
            application_randomization_version = ApplicationRandomizationVersion.objects.create(
                application=application, 
                version_number=last_randomization_versions.first().version_number + 1 if last_randomization_versions else 1,
                sequential=i, 
                exam_json=application_json,
                exam_hash=current_exam_hash,
            )
            application_randomization_versions.append(application_randomization_version)

        application_versions_cycle = cycle(application_randomization_versions)
        for application_student in application_students.order_by('?'):
            application_randomization_version = next(application_versions_cycle)
            randomization_version = RandomizationVersion.objects.create(
                application_randomization_version=application_randomization_version,
                application_student=application_student,
                version_number=application_randomization_version.version_number,
                exam_json=application_randomization_version.exam_json
            )

            application_students_versions.append({
                'pk': str(application_student.pk),
                'randomization_version': randomization_version.version_number,
                'application_randomization_version': str(randomization_version.application_randomization_version_id),
            })

    return application_students_versions