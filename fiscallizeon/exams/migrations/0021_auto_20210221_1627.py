# Generated by Django 3.0.7 on 2021-02-21 19:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0020_examquestion_order'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='examquestion',
            options={'ordering': ('order',), 'verbose_name': 'Questão na prova', 'verbose_name_plural': 'Questões na prova'},
        ),
    ]
