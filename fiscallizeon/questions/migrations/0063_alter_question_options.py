# Generated by Django 4.0.6 on 2024-04-15 16:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0062_alter_historicalquestion_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='question',
            options={'permissions': (('can_duplicate_question', 'Pode duplicar questões'), ('can_add_subject_question', 'Pode cadastrar assuntos na criação de cadernos')), 'verbose_name': 'Questão', 'verbose_name_plural': 'Questões'},
        ),
    ]
