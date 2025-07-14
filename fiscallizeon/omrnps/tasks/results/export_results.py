import zipfile
import time
import os

import pandas as pd
from celery import states

from django.db.models import F

from fiscallizeon.celery import app
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.omrnps.models import TeacherAnswer, UnityAnswer


@app.task(bind=True)
def export_application_results(self, nps_applications_ids):
    current_unixtime = int(time.time())
    final_zip_filename = os.path.join('tmp', f'resultados_nps_{nps_applications_ids[0][:5]}_{current_unixtime}.zip')
    teacher_answers_filename = os.path.join('tmp', f'{nps_applications_ids[0]}_teacher_answers.csv')
    unity_answers_filename = os.path.join('tmp', f'{nps_applications_ids[0]}_unity_answers.csv')

    teacher_answers = TeacherAnswer.objects.filter(
        omr_nps_page__class_application__nps_application__in=nps_applications_ids
    ).select_related(
        'omr_nps_page__class_application__school_class',
        'omr_nps_page__class_application__school_class__coordination__unity',
        'teacher__teacher_subject__teacher',
        'teacher__teacher_subject__subject',
        'nps_application_axis__nps_axis',
    ).annotate(
        page_id=F('omr_nps_page_id'),
        class_name=F('omr_nps_page__class_application__school_class__name'),
        unity_name=F('omr_nps_page__class_application__school_class__coordination__unity__name'),
        teacher_name=F('teacher__teacher_subject__teacher__name'),
        teacher_order=F('teacher__order'),
        subject_name=F('teacher__teacher_subject__subject__name'),
        axis_name=F('nps_application_axis__nps_axis__name'),
    ).order_by(
        'omr_nps_page__created_at',
        'teacher__order',
        'nps_application_axis__order'
    ).values(
        'page_id', 'class_name', 'unity_name',
        'teacher_order', 'teacher_name', 'subject_name',
        'axis_name', 'grade'
    )

    df = pd.DataFrame(list(teacher_answers))
    df = df[['page_id','class_name', 'unity_name', 'teacher_order', 'teacher_name', 'subject_name', 'axis_name', 'grade']]
    df['axis_name'] = df['axis_name'].str.slice(0, 3)

    df = df.pivot_table(
        index=['page_id', 'class_name', 'unity_name', 'teacher_order', 'teacher_name', 'subject_name'], 
        columns='axis_name', 
        values='grade',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    df.replace(0, '', inplace=True)

    df.drop(['page_id', 'teacher_order'], axis=1, inplace=True)
    df = df.rename(columns={
        'class_name': 'turma',
        'unity_name': 'unidade',
        'teacher_name': 'professor',
        'subject_name': 'disciplina',
    })

    df.to_csv(teacher_answers_filename, index=False)

    unity_answers = UnityAnswer.objects.filter(
        omr_nps_page__class_application__nps_application__in=nps_applications_ids
    ).select_related(
        'omr_nps_page__class_application__school_class',
        'omr_nps_page__class_application__school_class__coordination__unity',
    ).annotate(
        class_name=F('omr_nps_page__class_application__school_class__name'),
        unity_name=F('omr_nps_page__class_application__school_class__coordination__unity__name'),
    ).order_by(
        'unity_name', 'class_name', 'omr_nps_page__created_at',
    ).values(
        'class_name', 'unity_name', 'grade'
    )

    df = pd.DataFrame(list(unity_answers))
    df = df[['class_name', 'unity_name', 'grade']]
    df.to_csv(unity_answers_filename, index=False)

    with zipfile.ZipFile(final_zip_filename, 'w') as zipf:
        zipf.write(teacher_answers_filename, 'professores.csv')
        zipf.write(unity_answers_filename, 'unidades.csv')

    fs = PrivateMediaStorage()
    remote_path = f'omrnps/results/{nps_applications_ids}/{os.path.basename(final_zip_filename)}'

    remote_file = fs.save(
        remote_path,
        open(final_zip_filename, 'rb')
    )
    
    os.remove(teacher_answers_filename)
    os.remove(unity_answers_filename)
    os.remove(final_zip_filename)

    self.update_state(state=states.SUCCESS, meta=fs.url(remote_file))