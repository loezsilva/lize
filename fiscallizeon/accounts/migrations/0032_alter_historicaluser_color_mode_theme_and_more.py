# Generated by Django 4.2.18 on 2025-02-13 21:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0031_rename_has_app_access_historicaluser_can_access_app_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicaluser',
            name='color_mode_theme',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(0, 'Cinza'), (1, 'Verde'), (2, 'Azul'), (3, 'Roxo'), (4, 'Rosa'), (5, 'Vermelho'), (6, 'Laranja'), (7, 'Amarelo')], default=0, verbose_name='cor do tema'),
        ),
        migrations.AlterField(
            model_name='user',
            name='color_mode_theme',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(0, 'Cinza'), (1, 'Verde'), (2, 'Azul'), (3, 'Roxo'), (4, 'Rosa'), (5, 'Vermelho'), (6, 'Laranja'), (7, 'Amarelo')], default=0, verbose_name='cor do tema'),
        ),
    ]
