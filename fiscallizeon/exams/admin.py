from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from django.contrib import messages

from fiscallizeon.exams.models import (
    Exam,
    ExamHeader,
    ExamQuestion,
    ExamTeacherSubject,
    ExamTeacherSubjectFile,
    QuestionTagStatusQuestion,
    StatusQuestion,
    Wrong,
)

admin.site.register([Wrong , QuestionTagStatusQuestion])

@admin.action(description='Gerar desempenho dos cadernos selecionados')
def generate_performances(modeladmin, request, queryset):
	for exam in queryset:
		exam.run_recalculate_task()
	messages.success(request, "Uma task celery foi gerada, em breve o calculo do desempenho será finalizado.")

@admin.action(description='Forçar o recalculo dos dados do SISU (Ignorando cache)')
def force_cache_sisu(modeladmin, request, queryset):
	for exam in queryset:
		exam.run_recalculate_sisu_tri_cache()
	messages.success(request, "Os dados serão recalculados, acompanhe o dashboard do sisu, em breve o processo será finalizado.")


class ExamQuestionInlineExam(admin.TabularInline):   
	model = ExamQuestion
	autocomplete_fields = ['question', 'exam', 'source_exam_teacher_subject', 'exam_teacher_subject']
	# readonly_fields = ['exam_teacher_subject',]
	fk_name="exam"

class ExamQuestionInlineExamTeacherSubject(admin.TabularInline):   
	model = ExamQuestion
	autocomplete_fields = ['question', 'exam', 'source_exam_teacher_subject']
	readonly_fields = ['exam_teacher_subject',]
	fk_name="exam_teacher_subject"

class ExamTeacherSubjectInline(admin.TabularInline):   
	model = ExamTeacherSubject
	autocomplete_fields = ['teacher_subject', 'reviewed_by']

@admin.register(ExamQuestion)
class ExamQuestionAdmin(SimpleHistoryAdmin):
	list_filter = ('question__category', 'exam__coordinations__unity__client')
	list_display = ['id', 'exam', 'created_at']
	search_fields = ('question__enunciation', )
	readonly_fields = ['exam', 'question', 'exam_teacher_subject']
	ordering = ('-created_at',)
	autocomplete_fields = ['question', 'exam', 'source_exam_teacher_subject']

@admin.register(Exam)
class ExamAdmin(SimpleHistoryAdmin):
	search_fields = ('name', )
	list_display = ['name', 'created_at']
	readonly_fields = ('source_exam', )
	autocomplete_fields = ('coordinations', )
	inlines = [
		ExamQuestionInlineExam,
		ExamTeacherSubjectInline
	]
	autocomplete_fields = ('created_by', 'exam_print_config', 'coordinations')
	actions = [generate_performances, force_cache_sisu]

@admin.register(ExamTeacherSubject)
class ExamTeacherSubjectAdmin(admin.ModelAdmin):
	search_fields = ('exam__name', 'teacher_subject__teacher__name')
	autocomplete_fields = ('exam', )
	readonly_fields = ('teacher_subject', )
	inlines = [
		ExamQuestionInlineExamTeacherSubject
	]

@admin.register(ExamHeader)
class ExamHeaderAdmin(admin.ModelAdmin):
	search_fields = ('name',)
	autocomplete_fields = ('user', )

@admin.register(ExamTeacherSubjectFile)
class ExamTeacherSubjectFileModelAdmin(admin.ModelAdmin):
    autocomplete_fields = ('exam_teacher_subject',)

@admin.register(StatusQuestion)
class StatusQuestionAdmin(admin.ModelAdmin):
	search_fields = ['exam_question__question__enunciation', 'exam_question__pk', 'status', 'active']
	list_display = ['user', 'exam_question', 'status', 'active', 'created_at']
	autocomplete_fields = ('exam_question', 'user', 'source_status_question', 'is_checked_by')
	date_hierarchy = 'created_at'
	ordering = ('-created_at', )