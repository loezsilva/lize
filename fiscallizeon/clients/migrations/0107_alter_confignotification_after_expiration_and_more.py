# Generated by Django 4.0.6 on 2023-10-02 13:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0106_confignotification_after_expiration_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='confignotification',
            name='after_expiration',
            field=models.SmallIntegerField(choices=[(0, 'Um dia após de expirar'), (1, 'Dois dias após expirar'), (2, 'Três dias após expirar'), (3, 'Quatro dias após expirar'), (4, 'Cinco dias após expirar')], default=0, help_text='Este campo define a quantidade de dias após a expiração da data de entrega dos cadernos para notificar os coordenadores.', verbose_name='Notificação pós-expiração'),
        ),
        migrations.AlterField(
            model_name='confignotification',
            name='coordination_after_expiration',
            field=models.SmallIntegerField(choices=[(0, 'Um dia após de expirar'), (1, 'Dois dias após expirar'), (2, 'Três dias após expirar'), (3, 'Quatro dias após expirar'), (4, 'Cinco dias após expirar')], default=0, help_text='Este campo define a quantidade de dias após a expiração da data de entrega dos cadernos para notificar os coordenadores.', verbose_name='Notificação pós-expiração para os coordenadores'),
        ),
        migrations.AlterField(
            model_name='confignotification',
            name='coordination_first_notification',
            field=models.SmallIntegerField(choices=[(0, 'Um dia antes de expirar'), (1, 'Dois dias antes expirar'), (2, 'Três dias antes expirar'), (3, 'Quatro dias antes expirar'), (4, 'Cinco dias antes expirar')], default=0, help_text='Quantos dias antes da data de entrega a primeira notificação será enviada.', verbose_name='Primeira notificação'),
        ),
        migrations.AlterField(
            model_name='confignotification',
            name='coordination_second_notification',
            field=models.SmallIntegerField(blank=True, choices=[(0, 'Um dia antes de expirar'), (1, 'Dois dias antes expirar'), (2, 'Três dias antes expirar'), (3, 'Quatro dias antes expirar')], help_text='Quantos dias antes da data de entrega a segunda notificação será enviada.', null=True, verbose_name='Segunda notificação'),
        ),
        migrations.AlterField(
            model_name='confignotification',
            name='first_notification',
            field=models.SmallIntegerField(choices=[(0, 'Um dia antes de expirar'), (1, 'Dois dias antes expirar'), (2, 'Três dias antes expirar'), (3, 'Quatro dias antes expirar'), (4, 'Cinco dias antes expirar')], default=0, help_text='Quantos dias antes da data de entrega a primeira notificação será enviada.', verbose_name='Primeira notificação'),
        ),
        migrations.AlterField(
            model_name='confignotification',
            name='second_notification',
            field=models.SmallIntegerField(blank=True, choices=[(0, 'Um dia antes de expirar'), (1, 'Dois dias antes expirar'), (2, 'Três dias antes expirar'), (3, 'Quatro dias antes expirar')], help_text='Quantos dias antes da data de entrega a segunda notificação será enviada.', null=True, verbose_name='Segunda notificação'),
        ),
    ]
