# Generated by Django 3.2.4 on 2022-01-26 20:08

from django.db import migrations, models
import fiscallizeon.core.storage_backends
import fiscallizeon.materials.models


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0003_studymaterial_stage'),
    ]

    operations = [
        migrations.AddField(
            model_name='studymaterial',
            name='thumbnail',
            field=models.FileField(blank=True, null=True, storage=fiscallizeon.core.storage_backends.PrivateMediaStorage(), upload_to=fiscallizeon.materials.models.study_material_thumbnail_file_directory_path, verbose_name='Capa do material'),
        ),
    ]
