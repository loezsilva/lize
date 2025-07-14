from django.urls import path

from fiscallizeon.analytics import views
from fiscallizeon.analytics.api import subject, questions, application, classes, analytic, tri, followup


app_name = 'analytics'

urlpatterns = [
	path('', views.analytics_detail, name='analytics_detail'),
	path('cadernos/', views.AnalyticsExamsTemplateView.as_view(), name='analytics_exams_detail'),
	path('elit/', views.AnalyticsElitTemplateView.as_view(), name='analytics_elit'),
    path('avha/', views.AnalyticsAvhaTemplateView.as_view(), name='analytics_avha'),
    path('gae/', views.AnalyticsGAETemplateView.as_view(), name='analytics_gae'),
    path('idec/', views.AnalyticsIdecTemplateView.as_view(), name='analytics_idec'),
	path('provas/', views.AnalyticsRibamarTemplateView.as_view(), name='analytics_ribamar'),
	
	path('dashboards-metabase/', views.AnalyticsMetabaseDashboardListView.as_view(), name='metabase_dashboards_list'),
	path('dashboards-metabase/<uuid:pk>/', views.AnalyticsMetabaseDashboardDetailView.as_view(), name='metabase_dashboards_detail'),
	
	path('mapa/notas/', views.GradeMapTemplateView.as_view(), name='grade_map'),
	path('dashboard-tri/', views.DashboardTRITemplateView.as_view(), name='dashboard_tri'),

	path('dashboard/acompanhamento/', views.DashboardFollowUpTemplateView.as_view(), name='dashboard_follow_up'),

	path('tri/', views.TriTemplateView.as_view(), name='enem_tri'),
	
	# APIs
	path('api/coordination_widgets', analytic.coordination_widgets, name='coordination_widgets'),
	
	path('api/coordination_applications_list', application.coordination_applications_list, name='coordination_applications_list'),
	path('api/coordination_chart_applications_summary', application.coordination_chart_applications_summary, name='coordination_chart_applications_summary'),
	
	path('api/coordination_chart_areas_performance', subject.coordination_chart_areas_performance, name='coordination_chart_areas_performance'),
	path('api/coordination_list_subjects', subject.coordination_list_subjects, name='coordination_list_subjects'),
	
	path('api/coordination_chart_classes_summary', classes.coordination_chart_classes_summary, name='coordination_chart_classes_summary'),
	
	path('api/coordination_chart_questions_summary', questions.coordination_chart_questions_summary, name='coordination_chart_questions_summary'),
	path('api/coordination_chart_questions_performance', questions.coordination_chart_questions_performance, name='coordination_chart_questions_performance'),

	# APIs Exams
	path('api/exams_widget/', analytic.ExamsWidgetsSummaryAPIWiew.as_view(), name='exams-widget'),
	path('api/teachers/', analytic.TeachersSummaryAPIWiew.as_view(), name='teachers-summary'),
	path('api/subjects/', analytic.SubjectsSummaryAPIWiew.as_view(), name='subjects-summary'),
    path('api/questiontags', analytic.QuestionTagsCountAPIView.as_view(), name='question-tags'),
    
    path('api/<uuid:pk>/students/grade/', analytic.ExamStudentsGradeRetrieveAPIView.as_view(), name='students-grade'),
    path('api/exams/export', analytic.ExamsExportSheetAPIWiew.as_view(), name='analytics_exams_export'),
    
	#TRI
	path('api/exams_tri/', tri.TriAPIView.as_view(), name='exams_tri'),
	path('api/exams_tri/csv_export/', tri.ExportTriCsvAPIView.as_view(), name='exams_tri_csv_export'),
	path('api/sisu_data/', tri.SisuDataAPIView.as_view(), name='sisu_data'),
	path('api/sisu/', tri.SisuAPIView.as_view(), name='sisu'),
	path('api/items_params/', tri.ItemsParamsAPIView.as_view(), name='items-params'),

	# follow-up API
	path('api/follow-up/', followup.FollowUpAPIView.as_view(), name='followup'),
	path('api/follow-up/get/item/quantity/', followup.FollowUpGetItemQuantityAPIView.as_view(), name='followup-get-item-quantity'),
	path('api/follow-up/get/exams/summary/', followup.FollowUpGetExamsSummaryAPIView.as_view(), name='followup-get-exams-summary'),
	path('api/follow-up/get/exam/summary/', followup.FollowUpGetExamSummaryAPIView.as_view(), name='followup-get-exam-summary'),
	path('api/follow-up/get/teacher/summary/', followup.FollowUpGetTeacherSummaryAPIView.as_view(), name='followup-get-teacher-summary'),
	path('api/follow-up/get/unity/summary/', followup.FollowUpGetUnitySummaryAPIView.as_view(), name='followup-get-unity-summary'),
	path('api/follow-up/get/teachers/summary/', followup.FollowUpGetTeachersSummaryAPIView.as_view(), name='followup-get-teachers-summary'),
	path('api/follow-up/get/classes/summary/', followup.FollowUpGetClassesSummaryAPIView.as_view(), name='followup-get-classes-summary')
]
