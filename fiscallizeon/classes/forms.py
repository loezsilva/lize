from django import forms

from fiscallizeon.classes.models import SchoolClass, CourseType, Stage, Course
from fiscallizeon.clients.models import SchoolCoordination

class SchoolClassForm(forms.ModelForm):
    class Meta:
        model = SchoolClass
        fields = "__all__"
        exclude = ("school_year", "class_type", "id_erp")

    def __init__(self, user, is_update=False, *args, **kwargs):
        super(SchoolClassForm, self).__init__(*args, **kwargs)
        
        if not is_update:
            self.fields['coordination'].queryset = SchoolCoordination.objects.filter(
                id__in=user.get_coordinations_cache()
            )
      
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = "__all__"     
class CourseTypeForm(forms.ModelForm):
    class Meta:
        model = CourseType
        fields = "__all__"
        
class StageForm(forms.ModelForm):
    class Meta:
        model = Stage
        fields = "__all__"