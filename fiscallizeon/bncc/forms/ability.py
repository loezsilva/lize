from django import forms


from fiscallizeon.bncc.models import Abiliity

class AbilityForm(forms.ModelForm):
    class Meta:
        model = Abiliity
        fields = "__all__"
        exclude = ('created_by', 'client')

    def __init__(self, *args, **kwargs):
        super(AbilityForm, self).__init__(*args, **kwargs)
        #self.fields['subject'].required = True