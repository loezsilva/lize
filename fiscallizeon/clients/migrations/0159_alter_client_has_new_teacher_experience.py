# Generated by Django 4.2.19 on 2025-04-02 00:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0158_clientquestionsconfiguration_teachers_coordinations_can_edit_questions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='has_new_teacher_experience',
            field=models.BooleanField(default=True, verbose_name='Tem acesso a nova experiência de professor'),
        ),
    ]
