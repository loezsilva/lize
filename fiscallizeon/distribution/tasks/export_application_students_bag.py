import os
import uuid

from celery import states, chord

from fiscallizeon.celery import app
from fiscallizeon.applications.tasks.export_exam_application_student import export_exam_application_student
from fiscallizeon.omr.tasks.export_application_student_answer_sheet import export_application_student_answer_sheet
from fiscallizeon.distribution.tasks.group_application_students_files import group_application_students_files

@app.task(bind=True)
def export_application_students_bag(self, application_students_pk, print_params={}):
    self.update_state(state=states.STARTED)

    output_directory = os.path.join('ensalamentos', 'tmp', 'avulsos')

    task_list = []
    for application_student_pk in application_students_pk:
        task_list.extend([
            export_exam_application_student.s(
                application_student_pk, output_directory, print_params
            ),
            export_application_student_answer_sheet.s(
                application_student_pk, output_directory
            )
        ])
    try:
        subtask_id = f'EXPORT_APPLICATION_STUDENTS_BAG_{uuid.uuid4()}'
        chord(task_list)(
            group_application_students_files.si(
                application_students_pk
            ).set(task_id=subtask_id)
        )
        self.update_state(state=states.SUCCESS, meta={'task_id': subtask_id})
        return subtask_id

    except Exception as e:
        self.update_state(state=states.FAILURE)
        print(e)