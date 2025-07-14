from django.contrib import admin
from django.urls import reverse
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.students.models import Student, StudentSisuCourse
from django.http import HttpResponseRedirect
@admin.register(StudentSisuCourse)
class StudentSisuCourseAdmin(admin.ModelAdmin):
	'''Admin View for StudentSisuCourse'''
	autocomplete_fields = ['student']

class StudentSchoolClassInline(admin.TabularInline):
	model = Student.classes.through
	extra = 1
	show_change_link = True
	verbose_name = "Turma"
	autocomplete_fields = ('schoolclass', )
	verbose_name_plural = "Turmas"
	autocomplete_fields = ('schoolclass', )

	def formfield_for_foreignkey(self, db_field, request, **kwargs):

		if db_field.name == 'schoolclass':
			student = Student.objects.get(pk=request.resolver_match.kwargs['object_id'])

			kwargs['queryset'] = SchoolClass.objects.filter(coordination__unity__client=student.client)

		return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
	list_display = ('name', 'client', 'enrollment_number', 'email',)
	list_filter = ('client',)
	search_fields = ('name', 'email', 'enrollment_number', ) 
	autocomplete_fields = ('client', 'user', )
	change_form_template = 'admin/change_form_student.html'
	inlines = [StudentSchoolClassInline]

	def response_post_save_change(self, request, obj):
		if '_reset_password' in request.POST:

			obj.user.set_password(obj.enrollment_number)
			obj.user.save()

			# Get its admin url
			opts = self.model._meta
			info =  opts.app_label, opts.model_name
			route = 'admin:{}_{}_change'.format(*info)
			post_url = reverse(route, args=(obj.pk,))

			# And redirect
			return HttpResponseRedirect(post_url)
		else:
			# Otherwise, use default behavior
			return super().response_post_save_change(request, obj)