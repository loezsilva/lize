# Generated by Django 4.0.6 on 2024-12-18 13:22

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import simple_history.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0026_user_color_mode_theme_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='mood',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(0, 'Afetuoso'), (1, 'Radiante'), (2, 'Divertido'), (3, 'Hilariante'), (4, 'Brincalhão'), (5, 'Feliz'), (6, 'Grato'), (7, 'Satisfeito'), (8, 'Contente'), (9, 'Inocente'), (10, 'Apaixonado'), (11, 'Encantado'), (12, 'Envergonhado'), (13, 'Entediado'), (14, 'Exausto'), (15, 'Triste'), (16, 'Desolado'), (17, 'Irritado'), (18, 'Confuso'), (19, 'Tenso'), (20, 'Caveira'), (21, 'Alienígena'), (22, 'Com frio'), (23, 'Gato'), (24, 'Robô')], null=True, verbose_name='humor'),
        ),
        migrations.CreateModel(
            name='HistoricalUser',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ('username', models.CharField(blank=True, db_index=True, error_messages={'unique': 'A user with that username already exists.'}, help_text='150 caracteres ou menos. Letras, números e @/./+/-/_ apenas.', max_length=150, null=True, verbose_name='username')),
                ('name', models.CharField(blank=True, max_length=100, verbose_name='name')),
                ('email', models.EmailField(db_index=True, max_length=254, verbose_name='email address')),
                ('must_change_password', models.BooleanField(default=False, verbose_name='Deve mudar a senha no próximo acesso')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('temporarily_inactive', models.BooleanField(default=False, verbose_name='temporariamente inativo')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('genre', models.CharField(blank=True, choices=[('F', 'Feminino'), ('M', 'Masculino')], default='M', max_length=1, null=True, verbose_name='gênero')),
                ('phone', models.CharField(blank=True, default=None, max_length=15, null=True, validators=[django.core.validators.RegexValidator(code='invalid_phone', message='O número para contato não está no formato correto.', regex='^\\([1-9]{2}\\)\\ [2-9]{1}[0-9]{3,4}-[0-9]{4}$')], verbose_name='número para contato')),
                ('accept_terms_of_question_import', models.BooleanField(blank=True, default=False, verbose_name='Aceitou os termos da importação de questão')),
                ('schools', models.CharField(blank=True, max_length=254, null=True, verbose_name='Escola(as)')),
                ('how_did_you_meet_us', models.CharField(blank=True, choices=[('internet', 'Busca da internet'), ('social_media', 'Nas redes sociais'), ('friends', 'Amigos ou familiares'), ('others', 'Outros')], max_length=40, verbose_name='Como você nos conheceu?')),
                ('how_did_you_meet_us_form', models.CharField(blank=True, max_length=254, verbose_name='Você poderia especificar? (Opcional)')),
                ('accepted_terms_of_intellectual_rights_of_questions', models.BooleanField(blank=True, default=False, verbose_name='Aceitou os termos da importação de questão')),
                ('is_freemium', models.BooleanField(blank=True, default=False, verbose_name='Esta no ambiente freemium')),
                ('default_ai_credits', models.SmallIntegerField(blank=True, default=15, verbose_name='Crédito mensal')),
                ('interested_in_purchasing_more_credits', models.BooleanField(blank=True, default=False, verbose_name='Tem interesse em comprar mais créditos')),
                ('onboarding_responsible', models.BooleanField(default=False, verbose_name='responsável pela integração?')),
                ('can_request_ai_questions', models.BooleanField(default=False, verbose_name='Pode solicitar questão à IA')),
                ('nickname', models.CharField(blank=True, max_length=50, null=True, verbose_name='como gostaria de ser chamado(a)?')),
                ('avatar', models.TextField(blank=True, max_length=100, null=True)),
                ('color_mode_theme', models.PositiveSmallIntegerField(blank=True, choices=[(0, 'Cinza'), (1, 'Verde'), (2, 'Azul'), (3, 'Roxo'), (4, 'Rosa'), (5, 'Vermelho'), (6, 'Laranja'), (7, 'Amarelo')], null=True, verbose_name='cor do tema')),
                ('has_viewed_starter_onboarding', models.BooleanField(default=False, verbose_name='já visualizou a integração inicial?')),
                ('mood', models.PositiveSmallIntegerField(blank=True, choices=[(0, 'Afetuoso'), (1, 'Radiante'), (2, 'Divertido'), (3, 'Hilariante'), (4, 'Brincalhão'), (5, 'Feliz'), (6, 'Grato'), (7, 'Satisfeito'), (8, 'Contente'), (9, 'Inocente'), (10, 'Apaixonado'), (11, 'Encantado'), (12, 'Envergonhado'), (13, 'Entediado'), (14, 'Exausto'), (15, 'Triste'), (16, 'Desolado'), (17, 'Irritado'), (18, 'Confuso'), (19, 'Tenso'), (20, 'Caveira'), (21, 'Alienígena'), (22, 'Com frio'), (23, 'Gato'), (24, 'Robô')], null=True, verbose_name='humor')),
                ('history_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical usuário',
                'verbose_name_plural': 'historical usuários',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
