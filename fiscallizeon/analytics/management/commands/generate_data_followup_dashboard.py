import time
from django.utils import timezone
from django.core.management.base import BaseCommand

from django.db.models import Q, Case, When, Value
from django.utils import timezone
from datetime import timedelta
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.applications.models import Application
from fiscallizeon.clients.models import Client, Unity, SchoolCoordination
from fiscallizeon.exams.models import Exam
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.analytics.models import GenericPerformancesFollowUp
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Command para gerar os dados do dashboard de acompanhamento.'

    def add_arguments(self, parser):
        parser.add_argument('--deadline', default=None)
        parser.add_argument('--exam_pk', default=None)
        parser.add_argument('--client_pk', default=None)
        parser.add_argument('--last_hours', default=4, type=int)
        parser.add_argument('--last_days', default=30, type=int)
        
        return super().add_arguments(parser)
    
    def handle(self, *args, **kwargs):
        start_time = time.time()        
        deadline = kwargs['deadline']
        exam_pk = kwargs['exam_pk']
        client_pk = kwargs['client_pk']
        last_days = kwargs['last_days']
        
        clients = Client.objects.using('readonly2').filter(
            Q(has_followup_dashboard=True),
            Q(pk=client_pk) if client_pk else Q(),
        )
        
        for client in clients:
            applications = Application.objects.using('readonly2').filter(
                Q(category=Application.PRESENTIAL),
                Q(exam__coordinations__unity__client=client),
                Q(exam=exam_pk) if exam_pk else Q(
                    Q(
                        Q(deadline_for_correction_of_responses__isnull=False),
                        Q(
                            Q(deadline_for_correction_of_responses=deadline) if deadline else Q(deadline_for_correction_of_responses__gte=timezone.now() - timedelta(days=last_days))
                        )
                    ),
                ),
            ).exclude(
                exam__name__icontains="canguru"
            ).exclude(
                exam__name__icontains="bolsa"
            ).applieds()
            
            applications_pks = list(applications.values_list('pk', flat=True))

            print(timezone.now() - timedelta(days=last_days))
            
            for deadline in list(sorted(set(applications.values_list('deadline_for_correction_of_responses', flat=True)))):
                print("---", deadline)
                exams = Exam.objects.using('readonly2').filter(
                    application__in=applications_pks,
                    application__deadline_for_correction_of_responses=deadline,
                ).distinct()
                
                exams_count = int(exams.count())
                
                count = 0
                
                for exam in exams:
                    try:
                        count += 1
                        unities = Unity.objects.using('readonly2').filter(pk__in=exam.coordinations.all().values('unity')).distinct()
                        
                        for unity in unities:
                            
                            classes = SchoolClass.objects.using('readonly2').filter(
                                Q(
                                    pk__in=applications.filter(exam=exam, applicationstudent__student__classes__coordination__unity=unity).values_list('applicationstudent__student__classes', flat=True),
                                    coordination__unity=unity,
                                    school_year=exam.created_at.year,
                                    temporary_class=False,
                                ),
                            ).exclude(
                                name__icontains="bolsa"
                            ).distinct()
                            
                            for classe in classes:
                                
                                quantities = exam.get_answers_awaiting_response(school_class=classe)
                                
                                inspectors = Inspector.objects.using('readonly2').filter(
                                    teachersubject__active=True,
                                    teachersubject__classes=classe,
                                    teachersubject__school_year__gte=2023,
                                    teachersubject__subject__in=exam.examteachersubject_set.using('readonly2').values('teacher_subject__subject'),
                                ).exclude(
                                    name__icontains="professor"
                                ).distinct()

                                performance_classe = exam.performances_followup.using('readonly2').filter(
                                    deadline=deadline, 
                                    school_class=classe, 
                                    unity=unity, 
                                    type=GenericPerformancesFollowUp.ANSWERS,
                                    coordination=classe.coordination,
                                ).last()

                                if performance_classe:
                                    performance_classe.objective_quantity = quantities['objective_quantity']
                                    performance_classe.objective_total = quantities['objective_total']
                                    
                                    performance_classe.discursive_quantity = quantities['discursive_quantity']
                                    performance_classe.discursive_total = quantities['discursive_total']
                                    
                                    performance_classe.quantity = quantities['objective_quantity'] + quantities['discursive_quantity']
                                    performance_classe.total = quantities['objective_total'] + quantities['discursive_total']
                                    
                                    performance_classe.save()
                                    
                                else:
                                    performance_classe = GenericPerformancesFollowUp.objects.create(
                                        content_type=ContentType.objects.get_for_model(exam.__class__),
                                        object_id=exam.pk,
                                        deadline=deadline,
                                        unity=Unity.objects.using('default').get(pk=unity.pk),
                                        type=GenericPerformancesFollowUp.ANSWERS,
                                        coordination= SchoolCoordination.objects.using('default').get(pk=classe.coordination.pk),
                                        school_class=SchoolClass.objects.using('default').get(pk=classe.pk),
                                        objective_quantity=quantities['objective_quantity'],
                                        objective_total=quantities['objective_total'],
                                        discursive_quantity=quantities['discursive_quantity'],
                                        discursive_total=quantities['discursive_total'],
                                        quantity=quantities['objective_quantity'] + quantities['discursive_quantity'],
                                        total=quantities['objective_total'] + quantities['discursive_total'],
                                    )
                                    
                                performance_classe.inspectors.set(inspectors)
                                performance_classe.objective_examquestions.set(quantities['objective_examquestions_pks'])
                                performance_classe.discursive_examquestions.set(quantities['discursive_examquestions_pks'])
                        
                        print(f"{count} de {exams_count} finalizados, já vai em: {'%.2f' % float(time.time() - start_time)}")
                    except Exception as e:
                        print(e)
                    
            client.last_update_followup_dashboard = timezone.now()
            client.save(skip_hooks=True)
            
        return f"TEMPO TOTAL FOI DE: {'%.2f' % float(time.time() - start_time)} segundos *******"
