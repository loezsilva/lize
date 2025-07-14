from django.contrib import admin
from fiscallizeon.corrections.models import TextCorrection, CorrectionCriterion, CorrectionTextualAnswer, CorrectionFileAnswer, CorrectionDeviation

class CorrectionCriterionInline(admin.TabularInline):
	model = CorrectionCriterion
	extra = 1
	show_change_link = True
 
class CorrectionDeviationInline(admin.TabularInline):
	model = CorrectionDeviation
	extra = 0
	show_change_link = True

@admin.register(TextCorrection)
class TextCorrectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'client')
    inlines = [CorrectionCriterionInline,]
    
@admin.register(CorrectionCriterion)
class TextCorrectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')
    inlines = [CorrectionDeviationInline]

@admin.register(CorrectionTextualAnswer)
class CorrectionTextualAnswerAdmin(admin.ModelAdmin):
    list_display = ('textual_answer_id', 'correction_criterion', 'point', )
    autocomplete_fields = ('textual_answer', )

@admin.register(CorrectionFileAnswer)
class CorrectionFileAnswerAdmin(admin.ModelAdmin):
    list_display = ('file_answer_id', 'correction_criterion', 'point', )
    autocomplete_fields = ('file_answer', )

