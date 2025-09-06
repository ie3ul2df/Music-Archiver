from django.db import models
from django.conf import settings

# example only — not needed for your current session basket
class SavedBasket(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, db_index=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

class SavedBasketItem(models.Model):
    basket = models.ForeignKey(SavedBasket, related_name="items", on_delete=models.CASCADE)
    plan = models.ForeignKey("plans.Plan", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = (("basket", "plan"),)
