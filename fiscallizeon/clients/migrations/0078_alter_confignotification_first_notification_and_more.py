# Generated by Django 4.0.6 on 2023-03-09 19:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0077_alter_confignotification_client'),
    ]

    operations = [
        migrations.AlterField(
            model_name='confignotification',
            name='first_notification',
            field=models.SmallIntegerField(choices=[(1, '1 dia'), (2, '2 dias'), (3, '3 dias'), (4, '4 dias'), (5, '5 dias')], default=1, help_text='Quantos dias antes da data de entrega a primeira notificação será enviada.', verbose_name='Primeira notificação'),
        ),
        migrations.AlterField(
            model_name='confignotification',
            name='second_notification',
            field=models.SmallIntegerField(choices=[(0, 'não notificar'), (1, '1 dia'), (2, '2 dias'), (3, '3 dias'), (4, '4 dias')], default=0, help_text='Quantos dias antes da data de entrega a segunda notificação será enviada.', verbose_name='Segunda notificação'),
        ),
    ]
