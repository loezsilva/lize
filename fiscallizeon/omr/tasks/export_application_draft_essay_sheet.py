import os

from fiscallizeon.celery import app
from fiscallizeon.core.print_service import print_to_spaces
from fiscallizeon.core.storage_backends import PrivateMediaStorage


@app.task(max_retries=10, retry_backoff=True, default_retry_delay=2)
def export_application_draft_essay_sheet(application_pk, output_dir, blank_pages=False):
    try:
        print(f'Creating draft essay answer sheet for {application_pk}')
        fs = PrivateMediaStorage()

        post_data = {
            "filename": f'draft_essay_{str(application_pk)}.pdf',
            "blank_pages": 'between' if blank_pages else '',
            "check_loaded_element": True,
            "wait_seconds": True,
            "spaces_path": os.path.join(fs.root_path, output_dir)
        }

        filename = f'essay_draft_answer_sheet_{application_pk}.html'
        remote_path = fs.url(os.path.join(output_dir, filename))
        post_data['url'] = remote_path
        return print_to_spaces(post_data)
    except Exception as e:
        print(f'### Error exporting draft essay answer sheet for {application_pk}: {e}')