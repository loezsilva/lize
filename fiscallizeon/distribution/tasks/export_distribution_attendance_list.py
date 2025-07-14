from fiscallizeon.celery import app
from fiscallizeon.distribution.models import RoomDistribution, Room
from fiscallizeon.distribution.tasks.export_room_attendance_list import export_room_attendance_list


"""
DEPRECATED
"""
@app.task
def export_distribution_attendance_list(room_distribution_pk, output_dir, blank_pages=False):
    try:
        room_distribution = RoomDistribution.objects.get(pk=room_distribution_pk)
        rooms = room_distribution.get_rooms()

        rooms_generator = ((room_distribution_pk, room.pk, output_dir, blank_pages) for room in rooms)

        chunk_size = rooms.count() // 3 or rooms.count()

        return export_room_attendance_list.chunks(
            rooms_generator, chunk_size
        ).group()
    except Exception as e:
        print(e)