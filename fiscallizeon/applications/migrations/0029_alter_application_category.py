# Generated by Django 3.2.3 on 2021-06-17 22:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0028_applicationstudent_empty_questions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='category',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Apenas Monitoramento'), (1, 'Apenas Prova'), (2, 'Monitoramento + Prova'), (3, 'Presencial')], default=2, verbose_name='Categoria da aplicação'),
        ),
    ]
