import pandas as pd

from girth import threepl_mml, ability_3pl_eap

from django.db.models import F

from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.answers.models import OptionAnswer


application_pk = "f4a0c369-5a17-4e33-8b1b-5135a7ef65f5"

def calculate_enem_tri(application):
    application_students = ApplicationStudent.objects.filter(
        application=application,
        is_omr=True
    )

    answers = OptionAnswer.objects.filter(
        student_application__in=application_students,
        status=OptionAnswer.ACTIVE,
    ).annotate(
        is_correct=F('question_option__is_correct')
    )

    if not answers:
        print("Aplicação sem respostas objetivas!")
        return

    answers_df = pd.DataFrame.from_records(
        answers.values('student_application', 'question_option__question', 'is_correct')
    )

    answers_pivot = answers_df.pivot(
        index='question_option__question', 
        columns='student_application', 
        values='is_correct'
    ).fillna(False)

    answers_np = answers_pivot.to_numpy()
    parameters = threepl_mml(answers_np)
    averages = ability_3pl_eap(
        answers_np, 
        parameters['Difficulty'], 
        parameters['Discrimination'], 
        parameters['Guessing']
    )

    grades = averages * 100 + 500

    grades_df = pd.DataFrame({
        'student_application': answers_pivot.columns,
        'grade': grades,
    }).set_index('student_application')

    application_students_df = pd.DataFrame.from_records(
        application_students.values('id', 'student__name')
    ).set_index('id')

    merged_df = pd.concat([application_students_df, grades_df], axis=1)

    answers_t = answers_pivot.T
    answers_t['correct_count'] = answers_t.sum(axis=1)
    final_df = pd.concat([merged_df, answers_t.loc[:, ['correct_count']]], axis=1)

    for _, row in final_df.sort_values(by=['correct_count']).iterrows():
        formatted_row = 'Aluno: {:<60} | Nota: {:<20} | Acertos: {:<5}'.format(
            row["student__name"],
            row["grade"],
            row["correct_count"],
        )
        print(formatted_row)

    print("### Resumo")
    print("Total de alunos:", application_students.count())

    max_index = final_df['grade'].idxmax()
    student_max = final_df.loc[max_index]
    print(f"Maior nota: {student_max['student__name']} - {student_max['grade']}")

    min_index = final_df['grade'].idxmin()
    student_min = final_df.loc[min_index]
    print(f"Menor nota: {student_min['student__name']} - {student_min['grade']}")