# Generated by Django 4.0.2 on 2022-04-19 14:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('answers', '0027_alter_attachments_file_alter_fileanswer_arquivo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attachments',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Registrado em'),
        ),
        migrations.AlterField(
            model_name='attachments',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='Atualizado em'),
        ),
        migrations.AlterField(
            model_name='fileanswer',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Registrado em'),
        ),
        migrations.AlterField(
            model_name='fileanswer',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='Atualizado em'),
        ),
        migrations.AlterField(
            model_name='optionanswer',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Registrado em'),
        ),
        migrations.AlterField(
            model_name='optionanswer',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='Atualizado em'),
        ),
        migrations.AlterField(
            model_name='textualanswer',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Registrado em'),
        ),
        migrations.AlterField(
            model_name='textualanswer',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='Atualizado em'),
        ),
    ]
