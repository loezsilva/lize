# Generated by Django 4.0.6 on 2024-11-08 20:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inspectors', '0045_rename_is_ispector_ia_inspector_is_inspector_ia'),
    ]

    operations = [
        migrations.AddField(
            model_name='inspector',
            name='can_access_coordinator_profile',
            field=models.BooleanField(default=False, verbose_name='pode acessar perfil de coordenador'),
        ),
    ]
