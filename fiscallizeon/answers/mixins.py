from rest_framework.exceptions import ValidationError

from django.conf import settings

from fiscallizeon.applications.models import Application
class SaveRestrictionMixin():
    def is_valid(self, raise_exception=False):

        is_valid = super().is_valid(raise_exception=raise_exception)
        
        if not is_valid:
            return False

        student_application = self.validated_data.get('student_application')
        
        if student_application.application.is_time_finished:
            raise ValidationError({'message':'O tempo dessa prova já foi encerrado!', 'error': 'not_allowed'})
            
        if not student_application.application.is_happening:
            raise ValidationError({'message':'O tempo dessa prova já foi encerrado!', 'error': 'not_allowed'})

        if student_application.application_state == 'finished':
            raise ValidationError({'message':'Sua prova já foi finalizada!', 'error': 'not_allowed'})

        return is_valid


class SaveRestrictionUserMixin():
    def is_valid(self, raise_exception=False):

        is_valid = super().is_valid(raise_exception=raise_exception)
        
        if not is_valid:
            return False

        user =  self.context['request'].user
        student_application = self.validated_data.get('student_application')
        if user and not user.is_anonymous:
            if user.user_type == settings.COORDINATION or user.user_type == settings.TEACHER:
                return is_valid
        
        if not student_application.student_released_for_custom_time:
            
            if student_application.application.is_time_finished:
                raise ValidationError({'message':'O tempo dessa prova já foi encerrado!', 'error': 'not_allowed'})

            if not student_application.application.is_happening:
                raise ValidationError({'message':'O tempo dessa prova já foi encerrado!', 'error': 'not_allowed'})

        if student_application.application_state == 'finished':
            raise ValidationError({'message':'Sua prova já foi finalizada!', 'error': 'not_allowed'})

        if student_application.student.user != self.context['request'].user:
            raise ValidationError({'message':'Você não tem permissão para criar essa resposta!', 'error': 'not_allowed'})

        return is_valid