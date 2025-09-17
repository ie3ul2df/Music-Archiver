from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_delete
from django.db.models.deletion import ProtectedError
from django.dispatch import receiver

from .models import Album

User = get_user_model()


@receiver(post_save, sender=User)
def ensure_default_album(sender, instance, created, **kwargs):
    """Create a default album for each new user."""
    if not created:
        return
    Album.objects.get_or_create(
        owner=instance,
        is_default=True,
        defaults={"name": "Default Album"},
    )


@receiver(pre_delete, sender=Album)
def prevent_default_album_delete(sender, instance, **kwargs):
    """Block deletion attempts for default albums."""
    if instance.is_default:
        raise ProtectedError("Default albums cannot be deleted.", [instance])