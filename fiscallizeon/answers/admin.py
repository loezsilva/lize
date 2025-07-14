from django.contrib import admin

from fiscallizeon.answers.models import (
	OptionAnswer, TextualAnswer, FileAnswer, Attachments, RetryAnswer, ProofAnswer, SumAnswer, SumAnswerQuestionOption
)

class BaseAnswerAdmin(admin.ModelAdmin):
	def get_student(self, obj):
		return obj.student_application.student

	def get_question(self, obj):
		return str(obj.question)[:100]

	get_student.short_description = 'Aluno'
	get_question.short_description = 'Questão'


@admin.register(Attachments)
class AttachmentsAdmin(admin.ModelAdmin):

	list_display = ('id',)
	list_filter = ('id',)
	date_hierarchy = 'created_at'
	ordering = ('created_at',)


@admin.register(OptionAnswer)
class OptionAnswerAdmin(BaseAnswerAdmin):
  #  date_hierarchy = 'created_at'
	autocomplete_fields = ('question_option', 'student_application', 'created_by', )
	list_display = ('get_student', '__str__', 'created_at', )
	search_fields = ('student_application__student__name', 'student_application__pk', 'student_application__application__exam__name')
	readonly_fields = ('updated_at', 'created_at', 'question_option')


@admin.register(TextualAnswer)
class TextualAnswerAdmin(BaseAnswerAdmin):
	date_hierarchy = 'created_at'
	list_display = ('get_student', 'get_question',)
	# list_filter = ('student_application__student__client',)
	autocomplete_fields = ('question', 'student_application', )
	search_fields = ('student_application__student__name', 'student_application_id', )
	readonly_fields = ('updated_at', 'created_at', 'who_corrected', 'exam_question', )


@admin.register(FileAnswer)
class FileAnswerAdmin(BaseAnswerAdmin):
	date_hierarchy = 'created_at'
	list_display = ('get_student', 'get_question', )
	autocomplete_fields = ('question', 'student_application', )
	search_fields = ('student_application__student__name', 'student_application_id', )
	readonly_fields = ('updated_at', 'created_at', 'who_corrected', 'exam_question', )
	# list_filter = ('student_application__student__name', )


@admin.register(RetryAnswer)
class RetryAnswerAdmin(BaseAnswerAdmin):
	autocomplete_fields = ('option', 'application_student', 'exam_question')
	
@admin.register(ProofAnswer)
class ProofAnswerAdmin(BaseAnswerAdmin):
	autocomplete_fields = ('application_student', )

class SumAnswerQuestionOptionInline(admin.TabularInline):
	model = SumAnswerQuestionOption
	extra = 1
	show_change_link = True
	autocomplete_fields=('question_option', )
	list_filter = ('student_application__student__name', )
	ordering = ('question_option__index', )

@admin.register(SumAnswer)
class SumAnswerAdmin(BaseAnswerAdmin):
	list_display = ('pk', 'student_application', 'value', 'grade')
	readonly_fields = ('created_at', 'updated_at', )
	autocomplete_fields = ('student_application', 'question', 'created_by')
	inlines = [
		SumAnswerQuestionOptionInline
	]
	search_fields = ('student_application__student__name', )

