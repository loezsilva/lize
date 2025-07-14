import os
import shutil

from fiscallizeon.celery import app

@app.task
def remove_distribution_directory(distribution_directory):
    try:
        shutil.rmtree(distribution_directory, ignore_errors=True)
        print(f'Removed {distribution_directory}')
        return distribution_directory
    except Exception as e:
        print(e)
