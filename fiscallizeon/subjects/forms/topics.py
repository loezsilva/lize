from django import forms


from fiscallizeon.subjects.models import Topic

class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = "__all__"
        exclude = ('created_by', 'client', 'theme', 'main_topic', )

    def __init__(self, *args, **kwargs):
        super(TopicForm, self).__init__(*args, **kwargs)
        self.fields['subject'].required = True