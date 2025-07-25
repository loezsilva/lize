# Generated by Django 3.2.4 on 2022-02-01 20:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inspectors', '0013_inspector_id_backend'),
    ]

    operations = [
        migrations.AddField(
            model_name='inspector',
            name='can_elaborate_questions',
            field=models.BooleanField(default=True, verbose_name='Pode elaborar questões'),
        ),
        migrations.AddField(
            model_name='inspector',
            name='can_response_wrongs',
            field=models.BooleanField(default=True, verbose_name='Pode responder questões erratas'),
        ),
    ]
