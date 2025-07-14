from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from fiscallizeon.applications.models import Application

# @receiver(m2m_changed, sender=Application.students.through)
# def call_update_hook(sender, instance, action, **kwargs):
#     if action == "post_add" and instance.students.using('default').count() > 0:
#         instance.create_students_rooms()