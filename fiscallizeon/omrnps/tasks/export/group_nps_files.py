import os
import zipfile
import shutil

from celery import states

from django.utils import timezone
from django.db.models import Count

from fiscallizeon.celery import app
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.omrnps.models import NPSApplication, ClassApplication
from fiscallizeon.clients.models import SchoolCoordination, Unity
from fiscallizeon.distribution.utils import merge_urls


@app.task(bind=True, autoretry_for=(Exception,), max_retries=5, retry_backoff=True)
def group_nps_files(self, nps_application_pk, export_version=0):
    print(f'Grouping files for NPS application {nps_application_pk}')
    self.update_state(state=states.STARTED)
    nps_application = NPSApplication.objects.get(pk=nps_application_pk)

    school_coordinations = SchoolCoordination.objects.filter(
        school_classes__classapplication__nps_application=nps_application
    ).distinct()

    unities = Unity.objects.filter(coordinations__in=school_coordinations).distinct()

    nps_application_tmp_path = os.path.join(
        os.sep, 'code', 'tmp', 'omrnps', str(nps_application_pk), str(export_version)
    )
    os.makedirs(nps_application_tmp_path, exist_ok=True)

    zip_filename = 'avaliacao-v{}-{}'.format(
        export_version,
        nps_application.date.strftime('%d-%m-%Y'),
    )
    
    zip_path = os.path.join(nps_application_tmp_path, f'{zip_filename}.zip')
    with zipfile.ZipFile(zip_path, "a", zipfile.ZIP_DEFLATED, allowZip64=True) as zip_file:
        base_remote_path = os.path.join(
            'omrnps', 'tmp', str(nps_application.pk), str(export_version)
        )
        fs = PrivateMediaStorage()
        
        for unity in unities:
            class_applications = ClassApplication.objects.filter(
                nps_application=nps_application,
                school_class__coordination__unity=unity
            ).annotate(
                students_count=Count('school_class__students')
            ).distinct()

            school_classes_files = []

            for class_application in class_applications:
                attendance_path = fs.url(
                    os.path.join(base_remote_path, 
                    f'attendance_{str(class_application.pk)}.pdf')
                )
                school_classes_files.append(attendance_path)

                full_pdf_paths = [
                    fs.url(os.path.join(base_remote_path, f'omrsheet_{str(class_application.pk)}.pdf'))
                ] * class_application.students_count

                full_pdf_paths_cdn = [p.replace('nyc3.digitaloceanspaces', 'nyc3.cdn.digitaloceanspaces') for p in full_pdf_paths]
                school_classes_files.extend(full_pdf_paths_cdn)

            unity_file = merge_urls(school_classes_files, nps_application_tmp_path)
            zip_file.writestr(f'{unity.name}.pdf', open(unity_file, 'rb').read())
            print(f"Arquivo da unidade {unity} agrupado com sucesso")

    fs = PrivateMediaStorage()
    saved_file = fs.save(
        f'omrnps/exports/{nps_application_pk}/{zip_filename}.zip',
        open(zip_path, 'rb')
    )

    nps_application.answer_sheet = saved_file
    nps_application.last_answer_sheet_generation = timezone.localtime(timezone.now())
    nps_application.sheet_exporting_status = NPSApplication.FINISHED
    nps_application.save()

    self.update_state(state=states.SUCCESS)
    print(f'Saved sheets bag for NPS application {nps_application_pk}')

    try:
        shutil.rmtree(os.path.dirname(nps_application_tmp_path), ignore_errors=True)
    except Exception as e:
        print(f'Erro ao remover diretório de omrnps: {e}')

    return saved_file