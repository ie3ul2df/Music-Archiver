from django.conf import settings
from django.db import models
from django.db.models import Q

class Follow(models.Model):
    """
    Directed follow relationship: follower -> following
    """
    follower  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name="following_relations")
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name="follower_relations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("follower", "following"),)
        constraints = [
            models.CheckConstraint(
                check=~models.Q(follower=models.F("following")),
                name="prevent_self_follow",
            )
        ]
        indexes = [
            models.Index(fields=["follower"]),
            models.Index(fields=["following"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.follower} → {self.following}"

    @staticmethod
    def is_following(user, other):
        if not user or not other:
            return False
        if user.pk == other.pk:
            return False
        return Follow.objects.filter(follower=user, following=other).exists()
