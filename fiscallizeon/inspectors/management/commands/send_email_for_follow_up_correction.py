from django.core.management.base import BaseCommand
from django.template.loader import get_template
from django.conf import settings

import polars as pl
import os
from django.utils import timezone

from fiscallizeon.core.threadings.sendemail import EmailThread
from fiscallizeon.clients.models import Client, ConfigNotification

class Command(BaseCommand):
    """
    Task: 86a8j5wxm
    Envia email para professores que 
    possuem pendências de correção de respostas (usa lógica semelhante ao service de dashboards).

    Info no email: NOME DA PROVAS | TURMAS | QUANTIDADE DE PENDÊNCIAS | BOTÃO PARA TELA DE CORREÇÃO 

    """

    help = "Envia email para professores com pendências de correção de respostas."

    def extract_data_for_teacher(self, df: pl.LazyFrame, key: str, exam_id: str, teacher_id: str = None):
        """
        Encapsula a lógica de extrair items do dataframe followup_corrections
        """

        # Pega a linha daquele exam_id específico
        result = df.filter(pl.col("exam_id") == exam_id) # Removi o collect()

        if key == "classes":
            return result.filter(pl.col("teacher_id") == teacher_id).select(["classe_name", "classe_id"]).to_dicts()

        if key == "deadline":
            return result.select(key).unique().item()
        
        if key in ["objectives_pendings", "discursives_pendings"]:
            return result.filter(pl.col("teacher_id") == teacher_id).select(key).sum().item()
        
        if key == "exam_name":
            return result.select(key).unique().item()

    def handle(self, *args, **options):

        parquets_path = "tmp/dashboards"
        file_name = "followup-corrections"

        for client_pk in os.listdir(parquets_path):
            
            # Esse Try vai evitar que o código quebre caso tenha alguma pasta
            # com um nome que não seja um UUID de algum cliente ou dê algum erro durante a execução
            try:
                
                client_instance: Client = Client.objects.get(
                    pk=client_pk,
                )

                config_notification: ConfigNotification = (
                    client_instance.confignotification if
                    hasattr(client_instance, 'confignotification') else
                    None
                )
                
                # Adicionei esse if único.
                if (
                    client_instance.has_dashboards and 
                    config_notification and
                    config_notification.response_correction_notification
                ):

                    # Lê o parquet do client adicionando a coluna das pendências
                    # Removi a linha email
                    columns_to_use = [
                        "teacher_id",
                        "teacher_name",
                        "exam_id",
                        "exam_name",
                        "deadline",
                        "classe_id", # Adicionei classe_id
                        "classe_name", # Adicionei classe_name
                        "objectives_answers_total",
                        "objectives_answereds_total",
                        "discursives_answers_total",
                        "discursives_answereds_total",
                    ]

                    followup_corrections_df  = pl.scan_parquet(
                        f"{parquets_path}/{client_pk}/followup/{file_name}.parquet"
                    ).select( # Trouxe o select aqui pra cima
                        columns_to_use
                    ).filter(
                        pl.col('deadline').dt.year() >= timezone.now().date().year,
                        pl.col('deadline').dt.date() >= timezone.now().date(),
                    ).join(
                        pl.scan_parquet(f"{parquets_path}/{client_pk}/followup/teachers.parquet").select('teacher_id','email').unique(subset=["teacher_id"]),
                        on="teacher_id",
                        how="inner"
                    ).with_columns(
                        (pl.col('objectives_answers_total') - pl.col('objectives_answereds_total')).alias('objectives_pendings'),
                        (pl.col('discursives_answers_total') - pl.col('discursives_answereds_total')).alias('discursives_pendings')
                    ).filter( # Adicionei um filtro para ver se a pendência é zero, pois tem casso em que tudo foi corrigido.
                        (pl.col('objectives_pendings') > 0) | (pl.col('discursives_pendings') > 0)
                    ).collect() # Adicionei o collect()

                    if cadence := config_notification.cadence_send_email: # Trouxe a lógica do deadline, já que é um dado global e pode ser filtrado no dataframe
                        followup_corrections_df = followup_corrections_df.filter(
                            pl.col('deadline').dt.date() <= (timezone.now() + timezone.timedelta(days=cadence)).date()
                        )

                    grouped_for_teacher_df = followup_corrections_df.group_by("teacher_id","teacher_name","email").agg([ # Removi o collect()
                        pl.col("exam_id").unique().alias("exams_ids"),
                    ])

                    # Iterando sobre cada professor com pendências daquele client
                    for row in grouped_for_teacher_df.iter_rows(named=True):
                        
                        # Iterando sobre cada exam daquele professor
                        data_exam_this_teacher = []
                        for exam_id in row['exams_ids']:

                            deadline = self.extract_data_for_teacher(followup_corrections_df, "deadline", exam_id)
                            data_exam_this_teacher.append({
                                "exam_id": exam_id,
                                "exam_name": self.extract_data_for_teacher(followup_corrections_df, "exam_name", exam_id),
                                "classes": self.extract_data_for_teacher(followup_corrections_df, "classes", exam_id, row['teacher_id']),
                                "deadline": deadline,
                                "objectives_pendings": self.extract_data_for_teacher(followup_corrections_df, "objectives_pendings", exam_id, row["teacher_id"]),
                                "discursives_pendings": self.extract_data_for_teacher(followup_corrections_df, "discursives_pendings", exam_id, row['teacher_id']),
                            })   

                        data_email = {
                            "name_teacher": row['teacher_name'],
                            "email_teacher": row['email'],
                            "data_exam_this_teacher": data_exam_this_teacher,
                        }

                        # Só envia email se houver pendências
                        if data_exam_this_teacher:
                            template = get_template('inspectors/mail_template/send_question_correction.html')
                            html = template.render({
                                "data_email": data_email,
                                "BASE_URL": settings.BASE_URL,
                            })
                            subject = f'Respostas aguardando sua correção'
                            to = [row["email"]]
                            EmailThread(subject, html, to).start()

            except Exception as e:
                print(e)