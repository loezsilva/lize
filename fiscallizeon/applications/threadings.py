import threading
import requests
import time
from fiscallizeon.core.utils import generate_random_string, generate_random_number
from fiscallizeon.applications.utils import handle_request_orchestrator


from django.conf import settings

class JanusVideoRoomCreateThread(threading.Thread):
    def __init__(self, students, application):
        self.students = students
        self.application = application

        threading.Thread.__init__(self)

    def generate_default_start_values(self):
        self.application.text_room_id = generate_random_number(16)
        self.application.text_room_pin = generate_random_string(10)
        self.application.video_room_id = generate_random_number(16)
        self.application.video_room_pin = generate_random_string(10)
        self.application.video_room_secret = generate_random_number(16)

        params = {
            "start_date": str(self.application.date_time_start_tz),
            "finish_date": str(self.application.date_time_end_tz),
            "participants": self.students.using('default').count(),
            "video_room_id": self.application.video_room_id,
            "video_room_secret": self.application.video_room_secret,
            "video_room_pin": self.application.video_room_pin,
            "is_development": settings.ORCHESTRATOR_IS_DEVELOPMENT,
            "rooms": []
        }

        params["rooms"].append(
            {
                "text_room_id":self.application.text_room_id, 
                "text_room_pin":self.application.text_room_pin,
            }
        )

        return params

    def run(self):
        from fiscallizeon.applications.models import ApplicationStudent
        
        if self.application.count_students() == 0:
            self.application.create_students_rooms()
            return
        
        params = {
            "rooms": []
        }

        if not self.application.orchestrator_id:
            params = self.generate_default_start_values()

        for student in self.students.using('default').filter(text_room_id__isnull=True):
            student_id = generate_random_number(16)
            pin = generate_random_string(10)
            room_id = generate_random_number(16)

            student.text_room_pin = pin
            student.text_room_id = room_id
            student.student_room_id = student_id
            student.save(skip_hooks=True)

            params["rooms"].append(
                {
                    "text_room_id": room_id,
                    "text_room_pin": pin
                }
            )
            
        if not self.application.orchestrator_id:
            response = handle_request_orchestrator(
                url='applications/',
                method='post',
                params=params
            )
            
            self.application.orchestrator_id = response.json().get('pk')
            self.application.prefix = response.json().get('server_prefix')
            self.application.save(skip_hooks=True)
        else:
            response = handle_request_orchestrator(
                url=f'applications/{self.application.orchestrator_id}/add_rooms/',
                method='post',
                params=params["rooms"]
            )

class JanusVideoRoomDeleteThread(threading.Thread):
    def __init__(self, application):
        self.application = application
        threading.Thread.__init__(self)

    def run(self):
        response = handle_request_orchestrator(
            url=f'applications/{self.application.orchestrator_id}/',
            method='delete'
        )
        
class IgnoreCacheTriDataThread(threading.Thread):
    def __init__(self, exam, token, url, year):
        self.exam = exam
        self.url = url
        self.year = year
        self.token = token
        threading.Thread.__init__(self)

    def run(self):
        
        payload = {
            "year": self.year,
            "exams": [str(self.exam.id)],
            "ignore_cache": True
        }
        
        url = self.url + f'/tri'
        
        response = requests.post(
            url=url,
            headers={"Authorization": f"Bearer {self.token}"},
            json=payload
        )
        
        print("RESPONSE DO FORCE CACHE: ", response.status_code)