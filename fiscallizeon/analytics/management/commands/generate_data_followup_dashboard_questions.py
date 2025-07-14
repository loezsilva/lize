import time
from django.utils import timezone
from django.core.management.base import BaseCommand

from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from fiscallizeon.clients.models import Client
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
        now = timezone.now()
        
        client_pk = kwargs['client_pk']
        exam_pk = kwargs['exam_pk']
        deadline = kwargs['deadline']
        last_days = kwargs['last_days']
        
        clients = Client.objects.using('readonly2').filter(
            Q(has_followup_dashboard=True),
            Q(pk=client_pk) if client_pk else Q()
        )
        
        for client in clients:
            # print('####', client.name)
            
            exams = Exam.objects.using('readonly2').filter(
                Q(coordinations__unity__client=client),
                Q(pk=exam_pk) if exam_pk else Q(
                    Q(elaboration_deadline=deadline) if deadline else \
                    Q(
                        elaboration_deadline__isnull=False,
                        elaboration_deadline__gte=now - timedelta(days=last_days),
                    ),
                ),
            )
            
            for deadline in list(sorted(set(exams.values_list('elaboration_deadline', flat=True)))):
                print('deadline -----------', deadline)
                count = 0
                
                for exam in exams.filter(elaboration_deadline=deadline).distinct():
                    print(exam.name)
                    count += 1
                    
                    exam_teachers_subjects = exam.examteachersubject_set.all()
                    
                    for exam_teacher_subject in exam_teachers_subjects:
                    
                        quantities = exam.get_exam_teacher_subject_questions_pending_followup(exam_teacher_subject=exam_teacher_subject)
                    
                        performance = exam.performances_followup.using('readonly2').filter(
                            deadline=deadline, 
                            type=GenericPerformancesFollowUp.QUESTIONS,
                        ).last()

                        if performance:
                            performance.quantity = quantities['total'] - quantities['quantity']
                            performance.total = quantities['total']
                            performance.save()
                                
                        else:
                            performance = exam.performances_followup.create(
                                deadline=deadline,
                                type=GenericPerformancesFollowUp.QUESTIONS,
                                quantity=quantities['total'] - quantities['quantity'],
                                total=quantities['total'],
                            )
                        
                        performance.inspectors.set([exam_teacher_subject.teacher_subject.teacher])
                    
                    print(f"{count} de {exams.distinct().count()} finalizados, já vai em: {'%.2f' % float(time.time() - start_time)}")
            
            client.last_update_followup_dashboard = timezone.now()
            client.save(skip_hooks=True)
            
        return f"TEMPO TOTAL FOI DE: {'%.2f' % float(time.time() - start_time)} segundos *******"