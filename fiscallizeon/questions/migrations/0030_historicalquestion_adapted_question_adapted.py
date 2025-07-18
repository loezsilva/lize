# Generated by Django 4.0.2 on 2022-03-31 03:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0029_historicalquestion_force_break_page_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalquestion',
            name='adapted',
            field=models.BooleanField(default=False, help_text='Questão adaptada?', verbose_name='Adaptada'),
        ),
        migrations.AddField(
            model_name='question',
            name='adapted',
            field=models.BooleanField(default=False, help_text='Questão adaptada?', verbose_name='Adaptada'),
        ),
    ]
