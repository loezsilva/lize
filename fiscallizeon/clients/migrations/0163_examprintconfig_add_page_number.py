# Generated by Django 4.2.19 on 2025-04-25 21:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0162_merge_20250412_1519'),
    ]

    operations = [
        migrations.AddField(
            model_name='examprintconfig',
            name='add_page_number',
            field=models.BooleanField(default=False, help_text='Designa se o número da página deve ser adicionado ao rodapé do caderno.', verbose_name='Adicionar numeração em todas as páginas.'),
        ),
    ]
