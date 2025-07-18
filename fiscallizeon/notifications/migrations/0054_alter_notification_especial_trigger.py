# Generated by Django 4.0.6 on 2024-02-28 17:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0053_merge_20240227_1632'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='especial_trigger',
            field=models.SmallIntegerField(blank=True, choices=[(0, 'Depois de diagramar uma prova'), (1, 'Depois ver resultados de um caderno (Coordenação)'), (2, 'Depois de enviar notas para Activesoft'), (3, 'Depois de ver resultados de uma aplicação (Aluno)'), (4, 'Depois que o aluno revisar uma questão'), (5, 'Enquanto ver resultado de um caderno (Coordenação)')], null=True, verbose_name='Ações específicas para quando criar a notificação'),
        ),
    ]
