import os

from celery import states, chord

from django.utils import timezone

from fiscallizeon.celery import app
from fiscallizeon.omrnps.models import NPSApplication
from fiscallizeon.omrnps.tasks.export.export_application_class_sheet import export_application_class_sheet
from fiscallizeon.omrnps.tasks.export.export_application_class_attendance_list import export_application_class_attendance_list
from fiscallizeon.omrnps.tasks.export.group_nps_files import group_nps_files

@app.task
def error_handle(request, *args, **kwargs):
    nps_application = NPSApplication.objects.filter(pk=request.args[0])
    nps_application.update(sheet_exporting_status=NPSApplication.ERROR)

    app.backend.store_result(
        task_id = f'EXPORT_NPS_BAG_{str(nps_application.pk)}_{nps_application.export_count}',
        result=None,
        state=states.FAILURE,
    )

    app.backend.store_result(
        task_id=f'GROUP_FILES_NPS_APPLICATION_{nps_application.pk}_{nps_application.export_count}',
        result=None,
        state=states.FAILURE,
    )

@app.task(bind=True)
def export_application_files(self, nps_application_pk, export_version):
    self.update_state(state=states.STARTED)

    nps_application = NPSApplication.objects.get(pk=nps_application_pk)
    nps_export_path = os.path.join('omrnps', 'tmp', str(nps_application.pk), str(export_version))

    assets_tasks = []
    for class_application in nps_application.classapplication_set.all():
        export_attendance_task = export_application_class_attendance_list.s(
            str(class_application.pk), nps_export_path
        )

        assets_tasks.append(export_attendance_task)

        export_sheet_task = export_application_class_sheet.s(
            str(class_application.pk), nps_export_path
        )
        assets_tasks.append(export_sheet_task)

    result = chord(
        assets_tasks
    )(
        group_nps_files.si(
            nps_application_pk, export_version
        ).set(
            task_id=f'GROUP_FILES_NPS_APPLICATION_{nps_application.pk}_{nps_application.export_count}'
        ).on_error(
            error_handle.s()
        )
    )

    return result