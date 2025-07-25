# Generated by Django 3.2.4 on 2022-02-08 20:55

from django.db import migrations, models
import fiscallizeon.core.storage_backends
import fiscallizeon.materials.models


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0006_studymaterial_grades'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='studymaterial',
            options={'ordering': ['-created_at'], 'verbose_name': 'Material de estudo', 'verbose_name_plural': 'Materiais de estudo'},
        ),
        migrations.AlterField(
            model_name='studymaterial',
            name='thumbnail',
            field=models.FileField(blank=True, help_text='Arquivo de imagem: .png, .jpg, .jpeg, .gif', null=True, storage=fiscallizeon.core.storage_backends.PrivateMediaStorage(), upload_to=fiscallizeon.materials.models.study_material_thumbnail_file_directory_path, verbose_name='Capa do material (imagem)'),
        ),
    ]
