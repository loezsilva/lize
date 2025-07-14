from django.urls import path
from .views import RoomAttendanceListDetailView, DistributionPatioListDetailView, RoomDistributionDetailtView, RoomCreateView, RoomDeleteView, RoomDistributionCreateView, RoomDistributionDeleteView, RoomDistributionList, RoomDistributionUpdateView, RoomListView, RoomUpdateView
from fiscallizeon.distribution.api import distribution, rooms, exams_bag

app_name = 'distribution'

urlpatterns = [
	path('', RoomDistributionList.as_view(), name='distribution_list'),
	path('criar/', RoomDistributionCreateView.as_view(), name='distribution_create'),
	path('<uuid:pk>/atualizar/', RoomDistributionUpdateView.as_view(), name='distribution_update'),
	path('<uuid:pk>/deletar/', RoomDistributionDeleteView.as_view(), name='distribution_delete'),
	path('<uuid:pk>/distribuicao/detalhe/', RoomDistributionDetailtView.as_view(), name='distribution_detail'),

	path('salas/', RoomListView.as_view(), name='room_list'),
	path('criar/sala/', RoomCreateView.as_view(), name='room_create'),
	path('<uuid:pk>/sala/atualizar/', RoomUpdateView.as_view(), name='room_update'),
	path('<uuid:pk>/sala/deletar/', RoomDeleteView.as_view(), name='room_delete'),
	
	# LISTAS
	path('<uuid:pk>/<uuid:distribution>/lista/presenca/', RoomAttendanceListDetailView.as_view(), name='room_attendance_detail'),
	path('<uuid:pk>/lista/patio/', DistributionPatioListDetailView.as_view(), name='distribution_patio_list'),


	#APIS
	path('api/list/', rooms.rooms_list, name='rooms_list'),
	path('api/ensalamentos/alunos/list/', rooms.roomdistributionstudent_list, name='api_roomdistributionstudent_list'),
	path('api/ensalamentos/list/', rooms.group_rooms_of_roomdistributions_list, name='api_group_rooms_of_roomdistributions_list'),
	
	
	# SWAPS
	path('api/ensalamentos/<uuid:pk>/<uuid:old_pk>/swap/student/', rooms.roomdistributionstudent_swap_update, name='api_roomdistributionstudent_swap_update'),
	path('api/ensalamentos/<uuid:pk>/swap/room/', rooms.roomdistributionstudent_swap_room_update, name='api_roomdistributionstudent_swap_room_update'),
	
	# ROOM DISTRIBUTION
	path('api/ensalamentos/<uuid:pk>/detail/', distribution.roomdistribution_detail, name='api_roomdistribution_detail'),
	path('api/ensalamentos/<uuid:pk>/gerar-malote/', exams_bag.export_distribution_exams_bag, name='export_distribution_exams_bag'),
	path('api/ensalamentos/<uuid:pk>/gerar-malote-alunos/', exams_bag.export_application_students_bag_view, name='export_application_students_bag'),
	path('api/ensalamentos/<uuid:pk>/status-malote/', exams_bag.get_export_distribution_exams_bag_status, name='get_export_distribution_exams_bag_status'),
	path('api/ensalamentos/<uuid:pk>/change_is_printed/', distribution.roomdistribution_update, name='api_roomdistribution_update'),
]