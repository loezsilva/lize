
from django.contrib.postgres.fields import ArrayField

class ChoiceArrayField(ArrayField):
    
    def formfield(self, **kwargs):
        from django import forms
        
        defaults = {
            'form_class': forms.MultipleChoiceField,
            'choices': self.base_field.choices,
        }
        defaults.update(kwargs)
        return super(ArrayField, self).formfield(**defaults)