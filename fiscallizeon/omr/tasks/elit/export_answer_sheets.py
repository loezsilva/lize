import os
import uuid

from celery import chord, states
from django.utils import timezone
from django.template.loader import render_to_string

from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.core.print_service import print_to_spaces
from fiscallizeon.omr.tasks.elit.group_answer_sheet_files import group_answer_sheet_files
from fiscallizeon.omr.tasks.export_school_class_attendance_list import export_school_class_attendance_list
from fiscallizeon.celery import app


@app.task
def error_handle(request, *args, **kwargs):
    application = Application.objects.filter(pk=request.args[0])
    application.update(sheet_exporting_status=Application.ERROR)

    app.backend.store_result(
        task_id=f'EXPORT_SHEETS_{request.args[0]}_{request.args[1]}',
        result=None,
        state=states.FAILURE,
    )

    app.backend.store_result(
        task_id=f'GROUP_FILES_APPLICATION_{request.args[0]}_{request.args[1]}',
        result=None,
        state=states.FAILURE,
    )

@app.task
def print_elit_class_answer_sheet(application_pk, school_class_pk, target_directory):
    try:
        print(f'Creating ELIT answer sheet from {application_pk} - Class: {school_class_pk}')

        application = Application.objects.get(pk=application_pk)
        school_class = SchoolClass.objects.get(pk=school_class_pk)
        
        application_students = ApplicationStudent.objects.filter(
            application=application
        ).filter_by_school_class(
            school_class
        ).order_by('student__name')

        school_class_students_count = application_students.count()

        for start_index in range(0, school_class_students_count, 8):
            students_chunk = application_students[start_index:start_index + 8]

            template_name = 'omr/export_elit_answer_sheet.html'

            context = {
                'client': school_class.coordination.unity.client,
                'school_class': school_class,
                'application': application,
                'application_students': students_chunk
            }
            
            html_content = render_to_string(template_name, context)

            tmp_filename = f'tmp/{uuid.uuid4()}.html'
            with open(tmp_filename, 'w') as file:
                file.write(html_content)

            remote_filename = f'elit_answer_sheet_{school_class.pk}_{int(start_index/8)}'

            fs = PrivateMediaStorage()
            remote_html_path = fs.save(
                os.path.join(target_directory, f'{remote_filename}.html'),
                open(tmp_filename, 'rb')
            )
            os.remove(tmp_filename)

            post_data = {
                "filename": f'{remote_filename}.pdf',
                "check_loaded_element": True,
                "spaces_path": os.path.join(fs.root_path, target_directory),
                "url": fs.url(remote_html_path),
            }

            print_to_spaces(post_data)

    except IndexError as e:
        print(f'### Error exporting ELIT answer sheet for {application_pk} - Class: {school_class_pk}: {e}')


@app.task(bind=True, autoretry_for=(Exception,), max_retries=8, retry_backoff=True)
def export_answer_sheets(self, application_pk, export_version=0):

    self.update_state(state='PROGRESS')

    application = Application.objects.get(pk=application_pk)
    school_classes = application.get_related_classes()

    assets_tasks = []
    remote_directory = os.path.join(
        'omr', 'exports', application_pk, str(export_version)
    )

    for school_class in school_classes:
        assets_tasks.append(
            print_elit_class_answer_sheet.s(
                application_pk, str(school_class.pk), remote_directory
            )
        )
        assets_tasks.append(
            export_school_class_attendance_list.s(
                application_pk, str(school_class.pk), remote_directory
            )
        )

    result = chord(
        assets_tasks
    )(
        group_answer_sheet_files.si(
            application_pk, export_version
        ).set(
            task_id=f'GROUP_FILES_APPLICATION_{application.pk}_{export_version}'
        ).on_error(
            error_handle.s()
        )
    )