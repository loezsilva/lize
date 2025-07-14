import queue
from fiscallizeon.celery import app
from fiscallizeon.applications.models import Application
from fiscallizeon.applications.tasks.export_exam_application_student import export_exam_application_student


"""
DEPRECATED
"""
@app.task
def export_application_exams(application_students_pks, output_dir, print_params={}, blank_pages=False):
    try:
        application_students_generator = (
            (application_student['pk'], output_dir, print_params, blank_pages, application_student.get('randomization_version', 0)) for application_student in application_students_pks
        )

        application_students_count = len(application_students_pks)
        chunk_size = application_students_count // 30 or 1

        return export_exam_application_student.chunks(
            application_students_generator, chunk_size
        ).group()

    except Exception as e:
        print(e)