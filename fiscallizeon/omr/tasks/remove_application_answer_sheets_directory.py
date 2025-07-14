import os
import shutil

from fiscallizeon.celery import app

@app.task
def remove_application_answer_sheets_directory(application_pk):
    target_directory = os.path.join(
        os.sep, 'code', 'tmp', 'answer_sheets',
        str(application_pk)
    )
    try:
        shutil.rmtree(target_directory)
        print(f'Removed {application_pk}')
        return application_pk
    except Exception as e:
        print(e)
