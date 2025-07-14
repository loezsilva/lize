import time
from django.utils import timezone
from django.core.management.base import BaseCommand

from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.applications.models import Application
from fiscallizeon.clients.models import Client, Unity
from fiscallizeon.exams.models import Exam
from fiscallizeon.analytics.models import GenericPerformancesFollowUp

class Command(BaseCommand):
    help = 'Command para gerar os dados do dashboard de acompanhamento.'

    def add_arguments(self, parser):
        
        parser.add_argument('--deadline', default=None)
        parser.add_argument('--exam_pk', default=None)
        parser.add_argument('--client_pk', default=None)
        parser.add_argument('--last_days', type=int, default=30)
        
        return super().add_arguments(parser)
    
    def handle(self, *args, **kwargs):
        
        start_time = time.time()
        
        client_pk = kwargs['client_pk']
        exam_pk = kwargs['exam_pk']
        deadline = kwargs['deadline']
        last_days = kwargs['last_days']
        
        clients = Client.objects.using('readonly2').filter(
            Q(has_followup_dashboard=True),
            Q(pk=client_pk) if client_pk else Q()
        )
        
        for client in clients:
            applications = Application.objects.using('readonly2').filter(
                Q(exam__coordinations__unity__client=client),
                Q(exam=exam_pk) if exam_pk else Q(
                    Q(deadline_for_sending_response_letters=deadline) if deadline else \
                    Q(
                        deadline_for_sending_response_letters__isnull=False,
                        deadline_for_sending_response_letters__gte=timezone.now() - timedelta(days=last_days),
                    ),
                ),
            ).applieds()
            
            applications_pks = list(applications.values_list('pk', flat=True))
            
            for deadline in list(sorted(set(applications.values_list('deadline_for_sending_response_letters', flat=True)))):
                
                exams = Exam.objects.using('readonly2').filter(
                    application__in=applications_pks,
                    application__deadline_for_sending_response_letters=deadline,
                ).distinct()
                
                exams_count = int(exams.count())
                
                count = 0
                
                for exam in exams:
                    count += 1
                    unities = Unity.objects.using('readonly2').filter(pk__in=exam.coordinations.using('readonly2').all().values('unity')).distinct()
                        
                    for unity in unities:
                        
                        classes = SchoolClass.objects.using('readonly2').filter(
                            Q(
                                pk__in=applications.filter(exam=exam, applicationstudent__student__classes__coordination__unity=unity).values_list('applicationstudent__student__classes', flat=True),
                                coordination__unity=unity,
                                school_year=exam.created_at.year,
                                temporary_class=False,
                            ),
                        ).distinct()
                        
                        for classe in classes:
                            
                            quantities = exam.get_answers_awaiting_response(school_class=classe, get_cards=True)
                            
                            performance_classe = exam.performances_followup.using('readonly2').filter(
                                deadline=deadline, 
                                school_class=classe, 
                                unity=unity, 
                                type=GenericPerformancesFollowUp.CARDS,
                                coordination=classe.coordination,
                            ).last()

                            if performance_classe:
                                performance_classe.objective_cards_quantity = quantities['objective_cards_quantity']
                                performance_classe.objective_cards_total = quantities['objective_cards_total']
                                
                                performance_classe.discursive_cards_quantity = quantities['discursive_cards_quantity']
                                performance_classe.discursive_cards_total = quantities['discursive_cards_total']
                                
                                performance_classe.quantity = quantities['objective_cards_quantity'] + quantities['discursive_cards_quantity']
                                performance_classe.total = quantities['objective_cards_total'] + quantities['discursive_cards_total']
                                
                                performance_classe.save()
                                
                            else:
                                performance_classe = exam.performances_followup.create(
                                    deadline=deadline,
                                    unity=unity,
                                    type=GenericPerformancesFollowUp.CARDS,
                                    coordination=classe.coordination,
                                    school_class=classe,
                                    objective_cards_quantity=quantities['objective_cards_quantity'],
                                    objective_cards_total=quantities['objective_cards_total'],
                                    discursive_cards_quantity=quantities['discursive_cards_quantity'],
                                    discursive_cards_total=quantities['discursive_cards_total'],
                                    cards_quantity=quantities['objective_cards_quantity'] + quantities['discursive_cards_quantity'],
                                    cards_total=quantities['objective_cards_total'] + quantities['discursive_cards_total']
                                )
                    
                    print(f"{count} de {exams_count} finalizados, já vai em: {'%.2f' % float(time.time() - start_time)}")
                    
            client.last_update_followup_dashboard = timezone.now()
            client.save(skip_hooks=True)
            
            
        return f"TEMPO TOTAL FOI DE: {'%.2f' % float(time.time() - start_time)} segundos *******"