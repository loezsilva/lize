from django.urls import path
from .views import ParentSignUpView, ChildrenApplicationsStudentListView

app_name = 'parents'

urlpatterns = [
    path('<hash>/criar/usuario/pai/', ParentSignUpView.as_view(), name="parent_signup"),
    path('<uuid:pk>/aplicacoes/', ChildrenApplicationsStudentListView.as_view(), name="children-applications-list"),
]