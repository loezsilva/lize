from django.db import models
from django.db.models import Q
from django.contrib.postgres.aggregates import ArrayAgg



class OMRStudentsQuerySet(models.QuerySet):
    def annotate_discursive_scans(self):
        return self.annotate(
            discursive_scans=ArrayAgg(
                'omrdiscursivescan__upload_image',
                filter=Q(omrdiscursivescan__upload_image__isnull=False),
                distinct=True
            )
        )


OMRStudentsManager = models.Manager.from_queryset(OMRStudentsQuerySet)