# Generated by Django 4.0.6 on 2024-01-13 00:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0049_alter_historicalquestion_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='question',
            options={'permissions': (('can_duplicate_question', 'Pode duplicar questões'),), 'verbose_name': 'Questão', 'verbose_name_plural': 'Questões'},
        ),
    ]
