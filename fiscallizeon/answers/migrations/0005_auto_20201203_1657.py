# Generated by Django 3.0.7 on 2020-12-03 19:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0022_application_category'),
        ('answers', '0004_optionanswer_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='optionanswer',
            name='student_application',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='option_answers', to='applications.ApplicationStudent', verbose_name='Aluno'),
        ),
    ]
