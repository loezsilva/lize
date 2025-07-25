# Generated by Django 4.0.6 on 2023-06-12 21:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0012_notification_show_form_notification_show_rating'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='answer_is_required',
            field=models.BooleanField(default=False, verbose_name='O Feedback é obrigatório'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='trigger',
            field=models.SmallIntegerField(blank=True, choices=[(0, 'Depois de criar'), (1, 'Depois de deletar'), (2, 'Depois de atualizar'), (3, 'Antes de criar'), (4, 'Antes de deletar'), (5, 'Antes de atualizar'), (6, 'Na listagem')], null=True, verbose_name='Quando chamar a modal'),
        ),
    ]
