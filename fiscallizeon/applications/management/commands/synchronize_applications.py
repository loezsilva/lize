import requests

from datetime import datetime, timedelta

from django.utils import timezone
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import F, Min, Max

from fiscallizeon.applications.models import Application
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.clients.models import Client, SchoolCoordination
from fiscallizeon.applications.models import Application

class Command(BaseCommand):
    help = 'Sicroniza aplicações do sistema remoto com o sistema presencial'
    
    def add_arguments(self, parser):
        parser.add_argument('start', nargs="+", type=str)
        parser.add_argument('end', nargs="+", type=str)
        parser.add_argument('sync', nargs="+", type=str)


    def handle(self, *args, **kwargs):
        date = datetime.strptime(kwargs['start'][0], '%d-%m-%Y').date() 
        end_finish = datetime.strptime(kwargs['end'][0], '%d-%m-%Y').date()
        sync = True if kwargs['sync'][0] == "True" else False
        
        print(type(kwargs['sync'][0]), kwargs['sync'][0])
        print(sync, "sync")

        final_result = []
        applications = Application.objects.none()
        
        while date <= end_finish:
            const_time = 5
            
            applications = Application.objects.filter(
                date=date,
                exam__isnull=False,
                students__isnull=False
            ).distinct().order_by('start', 'end')

            if sync:
                applications = applications.filter(
                    inspectors__id_backend__isnull=False,
                    students__client__id_backend__isnull=False,
                    is_presential_sync=False,
                )

            inspectors = Inspector.objects.filter(
                applications__in=applications
            ).order_by("name").distinct()

            if sync:
                inspectors = inspectors.filter(
                    id_backend__isnull=False,
                )

            result = []

            for inspector in inspectors:
                specific_applications = applications.filter(inspectors=inspector).distinct()

                specific_applications_count = specific_applications.count()
                start = specific_applications.aggregate(Min('start'))['start__min']
                
                start_date = datetime.combine(timezone.now(), start)
                end_date = start_date

                end_date = end_date + timedelta(seconds=calculate_total_time(specific_applications))

                difference = (end_date - start_date).seconds / 3600

                effective_applications = int(difference / const_time)
                
                if difference % const_time != 0 or effective_applications == 0:
                    effective_applications += 1

                effective_applications = specific_applications_count if specific_applications_count < effective_applications else effective_applications
                
                # atenção: remover caso não seja necessário

                size_intervals = len(calculate_intervals(specific_applications))
                effective_applications =  size_intervals if size_intervals < effective_applications else effective_applications

                already_applications = []

                for application in range(effective_applications):
                    
                    specific_applications_start_min = datetime.combine(timezone.now(), specific_applications.aggregate(Min('start'))['start__min'])  

                    first_start_time = (specific_applications_start_min + timedelta(
                        hours=const_time * application
                        )
                    ).time()

                    last_end_time = (specific_applications_start_min + timedelta(
                        hours=(const_time + const_time * application))
                    ).time()

                    shift_applications = specific_applications.filter(
                        start__gte=first_start_time,
                        end__lte=last_end_time
                    )
                    
                    if not shift_applications or effective_applications == 1 and not calculate_total_time(specific_applications) / 3600 >= 7:
                        shift_applications = specific_applications.exclude(
                            pk__in=already_applications
                        )

                    clients_shift = Client.objects.filter(
                        pk__in=shift_applications.values_list(
                            'exam__coordinations__unity__client__pk', flat=True
                        ).distinct()
                    ).distinct()

                    if sync:
                        clients_shift = clients_shift.filter(
                            id_backend__isnull=False
                        )

                    for client in clients_shift:
                        applications_with_client = shift_applications.filter(
                            exam__coordinations__unity__client=client
                        ).exclude(pk__in=already_applications).order_by('date', 'start')

                        if not applications_with_client:
                            continue

                        already_applications.extend(
                            applications_with_client.values_list("pk", flat=True)
                        )

                        start = applications_with_client.aggregate(Min('start'))['start__min']

                        alternative_end = datetime.combine(timezone.now(), start)
                        
                        alternative_end = alternative_end + timedelta(seconds=calculate_total_time(applications_with_client))
                            
                        result_application = {
                            'date': str(date),
                            'start': str(start),
                            'end': str(alternative_end.time()),
                        }

                        if sync:
                            result_application["client"] = str(client.id_backend)
                            result_application["inspector"] = str(inspector.id_backend)

                        final_result.append(result_application)
                        
                        if not sync:
                            print(f'{client.name}, {inspector.name}, {date}, {result_application["start"]}, {alternative_end.time()}')

            date += timedelta(days=1)

        if not final_result:
            print('Nenhuma aplicação encontrada')
            return

        if sync:
            response = requests.post(
                settings.PRESENTIAL_BASE_URL + '/api/sincronizar-recrutamentos/',
                headers={
                    'Authorization': f'Token {settings.PRESENTIAL_AUTHORIZATION_TOKEN}',
                },
                json={
                    'recruitments': final_result,
                }
            )
            if response.status_code == 200:
                applications.update(is_presential_sync=True)


def in_intervals(time, intervals):
    for interval in intervals:
        if interval["start"] <= time["start"] and interval["end"] >= time["end"]:
            return True
            
    return False
    
def algorithm(intervals, times):
    if not intervals:
        smaller = None
        for time in times:
            if not smaller or time["start"] < smaller["start"]:
                smaller = time
        
        for time in times:
            if time["start"] >= smaller["start"] and time["start"] < smaller["end"] and time["end"] > smaller["end"]:
                smaller["end"] = time["end"]
        
        return smaller
    else:
        smaller = None
        for time in times:
            if not in_intervals(time, intervals):
                if not smaller or time["start"] < smaller["start"]:
                    smaller = time
        
        for time in times:
            if not in_intervals(time, intervals):
                if time["start"] >= smaller["start"] and time["start"] < smaller["end"] and time["end"] > smaller["end"]:
                    smaller["end"] = time["end"]
        
        return smaller

def calculate_intervals(queryset):
    times = []
    for awc in queryset:              
        start_awc = datetime.combine(timezone.now(), awc.start)
        end_awc = datetime.combine(timezone.now(), awc.end)

        times.append(
                {
                'start': start_awc,
                'end': end_awc
            },
        )

    intervals = []

    for time in times:
        result = algorithm(intervals, times)
        if result:
            intervals.append(result)

    return intervals

def calculate_total_time(queryset):
    result_time = 0
    
    for interval in calculate_intervals(queryset):
        result_time = result_time + ((interval['end']-interval['start']).total_seconds())

    return result_time