from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from fiscallizeon.inspectors.models import Inspector, TeacherSubject, InspectorCoordination

class InspectorCoordinationInline(admin.TabularInline):
    model = InspectorCoordination
    extra = 1
    show_change_link = True
    autocomplete_fields = ('coordination', )

class  TeacherSubjectInline(admin.TabularInline):
    model = TeacherSubject
    extra = 1
    show_change_link = True
    autocomplete_fields = ('teacher', 'subject', 'classes')
    readonly_fields = ('cadernos', )
    
    def cadernos(self, obj):
        return obj.examteachersubject_set.all().count()
    
class InspectorUserFilter(SimpleListFilter):
    title = 'Usuário'
    parameter_name = 'with_user'

    def lookups(self, request, model_admin):
        return (
            (True, "Com usuário"),
            (False, "Sem usuário"),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user__isnull=self.value() != "True")
        
        return queryset

@admin.register(Inspector)
class InspectorAdmin(admin.ModelAdmin):
    search_fields = ['name', 'email', 'pk']
    list_display = ('name', 'email', 'user', 'created_at',)
    fieldsets = (
        (
            None,
            {
                'fields': (
                    'user',
                    'name',
                    'email',
                    'id_backend',
                    'inspector_type',
                    'enable_integration_superpro_via_file',
                    'enable_integration_superpro',
                    'already_integrated_with_superpro',
                    'superpro_data',
                    'has_ia_creation',
                    'has_new_teacher_experience',
                    'is_inspector_ia',
                    'show_questions_bank_tutorial',
                    'can_access_coordinator_profile'
                )
            },
        ),
        (
            'Permissões',
            {
                'fields': (
                    'can_viewed',
                    'can_approve',
                    'can_fail',
                    'can_update_note',
                    'can_suggest_correction',
                    'can_elaborate_questions',
                    'can_response_wrongs',
                )
            },
        ),
        ('Configurações', {'fields': ('is_abstract',)}),
    )
    inlines = [InspectorCoordinationInline, TeacherSubjectInline,  ]
    autocomplete_fields = ('user', )
    list_filter = (InspectorUserFilter, 'coordinations__unity__client')
    


@admin.register(TeacherSubject)
class TeacherSubjectAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'subject', 'school_year', 'active')
    search_fields = ['teacher__name', 'teacher__email', 'subject__name', ]
    readonly_fields = ['created_at', ]
    autocomplete_fields = ('teacher', 'subject', 'classes')
    list_editable = ('active', )


    def render_change_form(self, request, context, *args, **kwargs):
        context['adminform'].form.fields['teacher'].queryset = Inspector.objects.filter(
            inspector_type=Inspector.TEACHER
        )
        return super(TeacherSubjectAdmin, self).render_change_form(request, context, *args, **kwargs)