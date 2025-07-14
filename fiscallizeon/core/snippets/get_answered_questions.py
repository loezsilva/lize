from datetime import datetime

from django.db.models import Q
from django.utils import timezone

from fiscallizeon.questions.models import Question
from fiscallizeon.clients.models import Client
from fiscallizeon.applications.models import Application
from fiscallizeon.exams.models import Exam

startdate = datetime(year=2021, month=3, day=15, hour=3, minute=0)
enddate = datetime(year=2021, month=3, day=15, hour=15, minute=0)

startdate = timezone.make_aware(startdate)
enddate = timezone.make_aware(enddate)

lato = Client.objects.get(pk='f1a6a4e9-7b95-4045-b6dd-f720a17a14e1')

answered_questions = Question.objects.filter(
    Q(
        Q(textualanswer__created_at__range=[startdate, enddate]) |
        Q(fileanswer__created_at__range=[startdate, enddate]) |
        Q(alternatives__optionanswer__created_at__range=[startdate, enddate])
    ),
    coordinations__unity__client=lato,
).distinct()

applications = Application.objects.filter(date=startdate.date(), end__lte=enddate.time())
exams = Exam.objects.filter(
    application__in=applications,
    coordinations__unity__client=lato,
).distinct()

pedro_questions = Question.objects.filter(examquestion__exam__in=exams).distinct()

difference = answered_questions.difference(pedro_questions)