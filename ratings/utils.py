from django.db.models import Avg, Count

def annotate_albums(qs):
    """Add rating_avg/rating_count to Album queryset."""
    return qs.annotate(
        rating_avg=Avg("ratings__stars"),
        rating_count=Count("ratings", distinct=True),
    )

def annotate_tracks(qs):
    """Add rating_avg/rating_count to Track queryset."""
    return qs.annotate(
        rating_avg=Avg("ratings__stars"),
        rating_count=Count("ratings", distinct=True),
    )
