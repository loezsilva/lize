from fiscallizeon.celery import app
from fiscallizeon.distribution.models import RoomDistribution
from fiscallizeon.clients.models import SchoolCoordination, Unity
from fiscallizeon.distribution.tasks.export_unity_yard_list import export_unity_yard_list


"""
DEPRECATED
"""
@app.task
def export_distribution_yard_list(room_distribution_pk, output_dir, blank_pages=False):
    try:
        room_distribution = RoomDistribution.objects.get(pk=room_distribution_pk)
        
        school_coordinations = SchoolCoordination.objects.filter(
            rooms__room_distribution__distribution=room_distribution
        ).distinct()

        unities = Unity.objects.filter(coordinations__in=school_coordinations).distinct()

        unities_generator = ((room_distribution_pk, unity.pk, output_dir, blank_pages) for unity in unities)

        chunk_size = unities.count() // 3 or unities.count()

        return export_unity_yard_list.chunks(
            unities_generator, chunk_size
        ).group()
    except Exception as e:
        print(e)