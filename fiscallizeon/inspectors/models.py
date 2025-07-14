from datetime import time, timedelta
from django.db import models
from django.core.cache import cache

from django_lifecycle import hook
from fiscallizeon.classes.models import Grade, SchoolClass

from django.apps import apps
from django.utils import timezone
from django.db.models.functions import Coalesce
from django.db.models import Q, Subquery, OuterRef
from django.conf import settings

from django.template.loader import get_template
from fiscallizeon.core.threadings.sendemail import EmailThread

from fiscallizeon.accounts.models import User
from fiscallizeon.core.models import BaseModel
from fiscallizeon.subjects.models import Subject
from fiscallizeon.clients.models import SchoolCoordination


# Create your models here.
class Inspector(BaseModel):
    user = models.OneToOneField(User, verbose_name="Usuário", on_delete=models.CASCADE, blank=True, null=True, related_name="inspector")
    name = models.CharField("Nome", max_length=50)
    email = models.EmailField("Endereço de email", unique=True, null=False, blank=False)
    can_access_coordinator_profile = models.BooleanField("pode acessar perfil de coordenador", default=False)
    TEACHER, INSPECTOR, OTHER = range(3)
    INSPECTOR_TYPE = (
        (TEACHER, "Professor"),
        (INSPECTOR, "Fiscal"),
        (OTHER, "Outro")
    )
    inspector_type = models.PositiveSmallIntegerField("Tipo de fiscal", choices=INSPECTOR_TYPE, default=TEACHER)
    coordinations = models.ManyToManyField(SchoolCoordination, verbose_name="Coordenações", through='InspectorCoordination', blank=True, related_name="inspectors")
    subjects = models.ManyToManyField(Subject, verbose_name="Disciplinas", through='TeacherSubject', blank=True)
    classes_he_teaches = models.ManyToManyField(SchoolClass, verbose_name="Turmas que ministra", blank=True, related_name="inspectors")
    is_discipline_coordinator = models.BooleanField("É coordenador de disciplina", default=False)
    is_inspector_ia = models.BooleanField("Professor virtual (IA)", default=False)

    # Permissions if is_discipline_coordinator
    can_viewed = models.BooleanField("dar Visto", default=True)
    can_approve = models.BooleanField("Aprovar", default=True)
    can_fail = models.BooleanField("Reprovar", default=True)
    can_update_note = models.BooleanField("Atualizar Nota", default=True)
    can_suggest_correction = models.BooleanField("Sugerir Correção", default=True)
    can_annul = models.BooleanField("Pode anular", default=True)
    id_backend = models.UUIDField("Identificador no fiscallize presenial", max_length=255, blank=True, null=True)
    
    # Geral permissions
    can_elaborate_questions = models.BooleanField("Pode elaborar questões", default=True)    
    can_response_wrongs = models.BooleanField("Pode responder erratas", default=True)
    can_answer_wrongs_others_teachers = models.BooleanField("Pode responder erratas de outros professores", default=False)

    can_correct_questions_other_teachers = models.BooleanField("pode corrigir respostas de alunos de cadernos de outros professores da mesma disciplina", default=False)
    is_abstract = models.BooleanField("Professor abstrato", default=False)
    enable_integration_superpro = models.BooleanField(
        'habilitar integração com Super Professor?',
        default=False,
    )
    enable_integration_superpro_via_file = models.BooleanField(
        'habilitar integração com Super Professor via arquivo?',
        default=False,
    )
    already_integrated_with_superpro = models.BooleanField(
        'já fez integração com Super Professor?', default=False
    )
    superpro_data = models.JSONField('dados do superpro', blank=True, null=True)
    
    skip_introduction_questions_bank = models.BooleanField('Pular introdução do banco de questões?', default=False)
    
    has_question_formatter = models.BooleanField("O professor pode utilizar o formatador de questões", default=False)
    
    has_ia_creation = models.BooleanField("O professor pode criar questão com IA", default=False)
    has_new_teacher_experience = models.BooleanField('Tem acesso a nova experiência de professor', default=False)

    show_questions_bank_tutorial = models.BooleanField("Exibir tutorial do banco de questões", default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Fiscal"
        verbose_name_plural = "Fiscais"
        permissions = (
            ('can_change_permissions_inspector', 'Pode alterar as permissões de fiscais'),
            ('can_change_permissions_teacher', 'Pode alterar as permissões de professores'),
            ('can_add_exercice_list', 'Pode adicionar lista de exercícios'),
            ('view_teacher', 'Pode visualizar professores'),
            ('add_teacher', 'Pode adicionar professores'),
            ('change_teacher', 'Pode alterar professores'),
            ('delete_teacher', 'Pode deletar professores'),
            ('can_import_teacher', 'Pode importar professores'),
            ('can_reset_password', "Pode resetar senha dos professores"),
        )

    def clean_coordinations_cache(self):
        if self.user:
            CACHE_KEY = f'USER_COORDINATIONS_{self.user.pk}'
            cache.delete(CACHE_KEY)

    def send_email_dashboard(self, stage):
        Exam = apps.get_model('exams', 'Exam')
        FileAnswer = apps.get_model('answers', 'FileAnswer')
        data = []
        answers = FileAnswer.objects.filter(
            student_application__application__exam__teaching_stage_id=stage, #p5 decisão
            who_corrected=self.user,
            created_at__year=timezone.now().year
        )
        exams_pks = list(answers.values_list('student_application__application__exam_id', flat=True).distinct())
        exams = Exam.objects.filter(id__in=exams_pks, created_at__year=timezone.now().year).distinct()
        for exam in exams.order_by('name'):
            classes = answers.filter(
                student_application__application__exam_id=str(exam.pk),
            ).values('student_application__student__classes')
            school_classes = SchoolClass.objects.filter(
                pk__in=classes,
                school_year=timezone.now().year
            ).distinct()
            for c in school_classes.order_by('name'):
                data.append({
                    "exam_name": exam.name,
                    "exam_id": str(exam.pk),
                    "class_name": c.name,
                    "class_id": str(c.pk),
                    "unity_name": c.coordination.unity.name,
                })

        template = get_template('mail_template/send_teacher_show_results.html')
        html = template.render({
            'inspector': self,
            'data': data,
            "BASE_URL": settings.BASE_URL
        })
        subject = 'Resultado da P1 disponível.'
        to = [self.user.email]
        print(html)

        EmailThread(subject, html, to).start()

    def add_custom_groups(self, client=None):
        # Se o cliente tiver algum grupo padrão eu seto esses grupos
        # se não eu pego os grupos padrões da Lize
        user = User.objects.using('default').filter(inspector=self).first()
        if not client:
            client = InspectorCoordination.objects.using('default').filter(inspector=self).first().coordination.unity.client
        
        if client:
            if client.has_default_groups('teacher'):
                groups = client.get_groups(with_annotations=False).filter(client__isnull=False, segment='teacher', default=True)
                for group in groups:
                    user.custom_groups.add(group)
            else:
                groups = client.get_groups(with_annotations=False).filter(client__isnull=True, segment='teacher', default=True)
                for group in groups:
                    user.custom_groups.add(group)

    def create_user(self):
        if not self.user and self.email:
            if user := User.objects.filter(username=self.email).first():
                self.user = user
                user.must_change_password = True
                self.save(skip_hooks=True)
            else:
                user = User.objects.create_user(
                    email=self.email.lower(),
                    name=self.name,
                    username=self.email.lower(),
                    password=self.email.lower(),
                )
                user.must_change_password = True
                user.save()
                self.user = user
                self.save(skip_hooks=True)
        return self.user

    @hook("after_create")
    def create_user_signal(self):
        self.create_user()

    @property
    def first_name(self):
        return self.name.split(" ")[0]
    
    def get_classes(self):
        TeacherSubject = apps.get_model('inspectors', 'TeacherSubject')
        
        return SchoolClass.objects.filter(
            pk__in=TeacherSubject.objects.filter(
                teacher=self,
                active=True
            ).distinct().values_list('classes'),
            school_year=timezone.now().year
        ).distinct()
        
    def get_exams_to_review(self, return_exam_teacher_subjects=False, with_details=False):
        from fiscallizeon.applications.models import Application
        from fiscallizeon.exams.models import Exam, ExamTeacherSubject
        from fiscallizeon.clients.models import EducationSystem
        from django.db.models import Count
        
        teacher = self
        coordinations = teacher.user.get_coordinations_cache()
        
        education_system = EducationSystem.objects.filter(unities__coordinations__in=coordinations).distinct()
        now = timezone.now()

        exams = Exam.objects.filter(
            Q(
                Q(
                    Q(created_at__year=now.year),
                    Q(
                        Q(
                            review_deadline__gte=now.date(),
                        ) |
                        Q(
                            review_deadline__isnull=True,
                        )
                    ) 
                ),
                Q(
                    Q(coordinations__in=coordinations),
                    Q(examteachersubject__teacher_subject__subject__in=teacher.subjects.all()),
                    Q(status__in=[Exam.ELABORATING, Exam.OPENED]),
                ),
                Q(
                    Q(education_system__isnull=True) |
                    Q(education_system__in=education_system)
                ),
                Q(
                    Q(release_elaboration_teacher__lte=timezone.now()) |
                    Q(release_elaboration_teacher__isnull=True)
                ),
                # Q(
                #     Q(examteachersubject__reviewed_by=teacher) |
                #     Q(examteachersubject__reviewed_by__isnull=True)
                # )
            )
        ).annotate(
            count=Count('examquestion'),
            date_start=Subquery(
                Application.objects.filter(
                    exam__pk=OuterRef("pk")
                ).annotate_date_start().order_by('date_start').values('date_start')[:1]
            )
        ).exclude(
            Q(count=0) |
            Q(created_by=teacher.user) |
            Q(
                Q(application__applicationstudent__start_time__isnull=False) |
                Q(application__applicationstudent__is_omr=True)
            ) |
            Q(date_start__isnull=False, date_start__lte=(timezone.now() - timedelta(hours=3)))
        ).order_by(
            'elaboration_deadline'
        )

        #adicionado verificação abaixo para o cliente sesi-ap-avaliações, ao adicionar 
        #para geral estávamos tendo problemas com o tamandaré
        if (
            str(teacher.user.client.pk) == "a5fd087a-97a9-44c8-9a8c-848cac8d0ccd"
            and not return_exam_teacher_subjects
        ):
            exams = exams.filter(
                Q(
                    Q(examteachersubject__reviewed_by=teacher) |
                    Q(examteachersubject__reviewed_by__isnull=True)
                )
            )
        
        
        if return_exam_teacher_subjects:
            exam_teacher_subjects = ExamTeacherSubject.objects.filter(
                Q(exam__in=exams),
                Q(teacher_subject__active=True),
                Q(teacher_subject__subject__in=teacher.subjects.all()),
                
            ).exclude(
                teacher_subject__teacher=teacher
            ).order_by(
                'exam__elaboration_deadline'
            )

            #adicionado verificação abaixo para o cliente sesi-ap-avaliações, ao 
            #adicionar para geral estávamos tendo problemas com o tamandaré
            if str(teacher.user.client.pk) == "a5fd087a-97a9-44c8-9a8c-848cac8d0ccd":
                exam_teacher_subjects = exam_teacher_subjects.filter(
                    Q(
                        Q(reviewed_by=teacher) |
                        Q(reviewed_by__isnull=True)
                    )
                )
            
            if with_details:
                exam_teacher_subjects = exam_teacher_subjects.detailed_status()
                
            return exam_teacher_subjects.distinct()
        
        else:
            exams = exams.exclude(
                examteachersubject__teacher_subject__teacher=teacher
            )
            
        return exams.distinct()
    
    def get_opened_exams(self, with_details=False):
        
        from fiscallizeon.exams.models import ExamTeacherSubject, Exam, StatusQuestion
        user = self.user
        
        exams_teacher_subject = ExamTeacherSubject.objects.filter(
            Q(
                Q(exam__coordinations__unity__client__in=user.get_clients_cache()),
                Q(teacher_subject__teacher=self),
                Q(
                    Q(exam__status=Exam.ELABORATING)|
                    Q(exam__status=Exam.OPENED)
                ),
                Q(
                    Q(exam__release_elaboration_teacher__lte=timezone.now())|
                    Q(exam__release_elaboration_teacher__isnull=True)
                )
            )
        ).annotate(
            questions_to_correct=Subquery(
                StatusQuestion.objects.filter(
                    exam_question__exam_teacher_subject=OuterRef('pk'),
                    status=StatusQuestion.CORRECTION_PENDING,
                    active=True
                ).exclude(~Q(exam_question__source_exam_teacher_subject=OuterRef('pk'))).values('id')[:1],
                output_field=models.UUIDField()
            )
        ).order_by(
            'exam__elaboration_deadline'
        ).exclude(
            # Q(
            #     Q(exam__category=Exam.HOMEWORK, exam__created_by=user)
            # ) |
            Q(
                Q(exam__application__applicationstudent__start_time__isnull=False) |
                Q(exam__application__applicationstudent__is_omr=True)
            ) |
            Q(
                Q(questions_to_correct__isnull=True),
                Q(exam__status=Exam.OPENED)
            )
        )
        if not user.client_has_late_questions:
            exams_teacher_subject = exams_teacher_subject.exclude(
                Q(exam__elaboration_deadline__lt=timezone.now())
            )
            
        if with_details:
            exams_teacher_subject = exams_teacher_subject.detailed_status()
        
        return exams_teacher_subject.distinct()
    
    @hook("after_update")
    def hook_after_update(self):
        if self.user:
            self.user.name = self.name
            self.user.save()

class InspectorCoordination(BaseModel):
    inspector = models.ForeignKey(Inspector, verbose_name="Fiscal", on_delete=models.CASCADE)
    coordination = models.ForeignKey(SchoolCoordination, verbose_name="Coordenação", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Fiscal da coordenação"
        verbose_name_plural = "Fiscais das coordenações"

class TeacherSubject(BaseModel):
    teacher = models.ForeignKey(Inspector, verbose_name="Professor", on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, verbose_name="Disciplina", on_delete=models.CASCADE)
    classes = models.ManyToManyField(SchoolClass, verbose_name=("Turmas"), blank=True)
    active = models.BooleanField(default=True)
    school_year = models.SmallIntegerField("Ano letivo", default="2025", blank=True)
    
    class Meta:
        verbose_name = "Lecionador da displina"
        verbose_name_plural = "Lecionadores das displinas"

    def __str__(self):
        return f'{self.subject.name} - {self.subject.knowledge_area.name} - {self.teacher.name}'

    def get_grades(self):
        grades = Grade.objects.filter(pk__in=self.classes.filter(school_year=timezone.now().year).values('grade')).distinct()
        return grades
