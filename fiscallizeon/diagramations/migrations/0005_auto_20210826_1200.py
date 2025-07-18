# Generated by Django 3.2.4 on 2021-08-26 15:00

from django.db import migrations, models
import fiscallizeon.core.storage_backends
import fiscallizeon.diagramations.models


class Migration(migrations.Migration):

    dependencies = [
        ('diagramations', '0004_auto_20210824_1506'),
    ]

    operations = [
        migrations.AddField(
            model_name='diagramationrequest',
            name='exam_file_discursive',
            field=models.FileField(blank=True, help_text='Envie o arquivos com as questẽos que serão diagramadas. Arquivo: .pdf, .doc ou .docx', null=True, storage=fiscallizeon.core.storage_backends.PrivateMediaStorage(), upload_to=fiscallizeon.diagramations.models.material_file_directory_path, verbose_name='Arquivo das questões dicursivas'),
        ),
        migrations.AlterField(
            model_name='diagramationrequest',
            name='exam_file',
            field=models.FileField(help_text='Envie o arquivos com as questẽos que serão diagramadas. Arquivo: .pdf, .doc ou .docx', storage=fiscallizeon.core.storage_backends.PrivateMediaStorage(), upload_to=fiscallizeon.diagramations.models.material_file_directory_path, verbose_name='Arquivo das questões objetivas'),
        ),
    ]
