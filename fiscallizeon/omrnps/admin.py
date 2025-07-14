from django.contrib import admin

from fiscallizeon.omrnps.models import NPSApplication, NPSAxis, NPSApplicationAxis, ClassApplication, TeacherOrder, \
    OMRNPSCategory, OMRNPSUpload, OMRNPSPage, TeacherAnswer, UnityAnswer, OMRNPSError

class NPSApplicationAxisInline(admin.TabularInline):
    model = NPSApplicationAxis
    extra = 3
    show_change_link = True
        
class ClassApplicationInline(admin.TabularInline):
    model = ClassApplication
    extra = 3
    show_change_link = True
    autocomplete_fields = ('school_class', )

class OMRNPSErrorInline(admin.TabularInline):
    model = OMRNPSError
    extra = 3
    show_change_link = True
    # autocomplete_fields = ('teacher_subject', )
    
class TeacherOrderInline(admin.TabularInline):
    model = TeacherOrder
    extra = 3
    show_change_link = True
    autocomplete_fields = ('teacher_subject', )

@admin.register(NPSApplication)
class NPSApplicationAdmin(admin.ModelAdmin):
    autocomplete_fields = ('client', )
    inlines = [
         NPSApplicationAxisInline,
         ClassApplicationInline,
    ]

@admin.register(NPSAxis)
class NPSAxisAdmin(admin.ModelAdmin):
    pass

@admin.register(OMRNPSError)
class OMRNPSErrorAdmin(admin.ModelAdmin):
    pass

@admin.register(ClassApplication)
class ClassApplicationAdmin(admin.ModelAdmin):
    search_fields = ('school_class__name', 'schooll_class__id', )
    autocomplete_fields = ('school_class', )
    readonly_fields = ('nps_application',  )
    inlines = [
        TeacherOrderInline,
    ]

@admin.register(OMRNPSCategory)
class OMRNPSCategoryAdmin(admin.ModelAdmin):
    pass

class OMRNPSPageInline(admin.TabularInline):
    model = OMRNPSPage
    extra = 0
    show_change_link = True

@admin.register(OMRNPSUpload)
class OMRNPSUploadAdmin(admin.ModelAdmin):
    autocomplete_fields = ('user', )
    search_fields = ('user__name', )
    list_display = ('created_at', 'user', 'raw_pdf', 'get_status_display')
    inlines = [
        OMRNPSErrorInline,
        OMRNPSPageInline,
    ]

@admin.register(TeacherAnswer)
class TeacherAnswerAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'nps_application_axis', 'grade')
    ordering = ('created_at', 'teacher__name', 'nps_application_axis__nps_axys__name')
    readonly_fields = ('omr_nps_page',)
    autocomplete_fields = ('created_by', )


@admin.register(UnityAnswer)
class UnityAnswerAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'grade', )
    readonly_fields = ('omr_nps_page',)
    autocomplete_fields = ('created_by', )


class TeacherAnswerInline(admin.TabularInline):
    model = TeacherAnswer
    extra = 0
    show_change_link = False
    readonly_fields = ('teacher', 'grade', 'nps_application_axis')
    ordering = ('teacher', 'nps_application_axis')
    autocomplete_fields = ('created_by', )

class UnityAnswerInline(admin.TabularInline):
    model = UnityAnswer
    extra = 0
    show_change_link = False
    readonly_fields = ('class_application', 'grade', )

@admin.register(OMRNPSPage)
class OMRNPSPageAdmin(admin.ModelAdmin):
    # list_display = ('__str__', 'grade', )
    # readonly_fields = ('omr_nps_page',)
    inlines = [
        TeacherAnswerInline,
        UnityAnswerInline
    ]

