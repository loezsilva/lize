# Generated by Django 4.0.6 on 2024-01-17 17:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0052_merge_20240117_1422'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='sugestiontags',
            options={'verbose_name': 'Tag de sugestão', 'verbose_name_plural': 'Tags de sugestão'},
        ),
    ]
