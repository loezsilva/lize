from fiscallizeon.celery import app
from fiscallizeon.omr.utils import download_spaces_image
from fiscallizeon.omrnps.models import ClassApplication, OMRNPSUpload, OMRNPSError

@app.task
def process_data_without_qr(omr_upload_id, omr_error_list):
    nps_upload = OMRNPSUpload.objects.get(pk=omr_upload_id)
    sheets_data = []

    for omr_fix in omr_error_list:
        class_application = ClassApplication.objects.get(
            nps_application=omr_fix.get('application'),
            school_class=omr_fix.get('school_class'),
        )

        omr_nps_error = OMRNPSError.objects.get(pk=omr_fix['omr_nps_error'])
        error_image = download_spaces_image(str(omr_nps_error.error_image), 'tmp')

        sheet_data = {
            'sequential': 1,
            'omr_nps_error': omr_fix.get('omr_nps_error'),
            'page_number': omr_fix.get('page_number'),
            'object_id': str(class_application.pk),
            'file_path': error_image,
        }

        sheets_data.append(sheet_data)

    return (nps_upload.pk, sheets_data)
