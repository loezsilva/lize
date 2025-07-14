from django import forms


from fiscallizeon.bncc.models import Competence

class CompetenceForm(forms.ModelForm):
    class Meta:
        model = Competence
        fields = "__all__"
        exclude = ('created_by', 'client')

    def __init__(self, *args, **kwargs):
        super(CompetenceForm, self).__init__(*args, **kwargs)
        #self.fields['subject'].required = True