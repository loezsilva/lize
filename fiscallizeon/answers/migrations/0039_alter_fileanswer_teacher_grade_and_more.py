# Generated by Django 4.0.6 on 2023-04-22 21:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('answers', '0038_proofanswer_group_attachments'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fileanswer',
            name='teacher_grade',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True, verbose_name='Nota atribuída'),
        ),
        migrations.AlterField(
            model_name='textualanswer',
            name='teacher_grade',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True, verbose_name='Nota atribuída'),
        ),
    ]
