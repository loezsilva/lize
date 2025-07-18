# Generated by Django 4.0.6 on 2022-12-08 18:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0062_remove_clientquestionsconfiguration_can_delete_question_aproveds'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='clientquestionsconfiguration',
            name='can_edit_question_aproveds',
        ),
        migrations.AddField(
            model_name='clientquestionsconfiguration',
            name='block_edit_question_aproveds',
            field=models.BooleanField(default=False, help_text='Ao marcar esta opção, os professores não poderão alterar a questão após ela ser aprovada para uso.', verbose_name='Bloquar edição após aprovação'),
        ),
    ]
