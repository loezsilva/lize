# Generated by Django 4.0.6 on 2023-09-21 12:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0089_merge_20230911_1423'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='deadline_for_sending_response_letters',
            field=models.DateField(blank=True, help_text='Limite para o envio dos cartões resposta', null=True, verbose_name='Tempo limite envio dos cartões resposta'),
        ),
    ]
