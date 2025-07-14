from django import forms
from .models import Room, RoomDistribution
from fiscallizeon.clients.models import SchoolCoordination
from fiscallizeon.applications.models import Application

class RoomDistributionForm(forms.ModelForm):
    rooms = forms.ModelMultipleChoiceField(queryset=Room.objects.all())
    applications = forms.ModelMultipleChoiceField(queryset=Application.objects.all())

    class Meta:
        model = RoomDistribution
        fields = ['category', 'shuffle_students', 'balance_rooms']

    def __init__(self, *args, **kwargs):
        super(RoomDistributionForm, self).__init__(*args, **kwargs)
        self.fields['category'].empty_label = None


class RoomCreateForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = '__all__'

    def __init__(self, user, *args, **kwargs):
        super(RoomCreateForm, self).__init__(*args, **kwargs)
        
        self.fields['coordination'].queryset = SchoolCoordination.objects.filter(
            unity__client__in=user.get_clients_cache()
        ).distinct()