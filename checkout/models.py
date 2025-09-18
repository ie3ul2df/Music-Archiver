# checkout/models.py
import uuid

from django.conf import settings
from django.db import models
from django_countries.fields import CountryField

from plans.models import Plan
from profile_page.models import UserProfile


class Order(models.Model):
    order_number = models.CharField(max_length=32, unique=True, editable=False)

    # link to Django User (good for admin/backoffice)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    # link to Profile (used for autofill/history)
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    # customer info
    full_name = models.CharField(max_length=50)
    email = models.EmailField(max_length=254)

    # delivery fields (optional, match Profile defaults)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    country = CountryField(blank_label="(select country)", null=True, blank=True)
    postcode = models.CharField(max_length=20, null=True, blank=True)
    town_or_city = models.CharField(max_length=40, null=True, blank=True)
    street_address1 = models.CharField(max_length=80, null=True, blank=True)
    street_address2 = models.CharField(max_length=80, null=True, blank=True)
    county = models.CharField(max_length=80, null=True, blank=True)

    date = models.DateTimeField(auto_now_add=True)

    # monetary summary + Stripe linkage
    order_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stripe_pid = models.CharField(max_length=254, default="", blank=False)
    original_basket = models.TextField(default="{}")  # store JSON snapshot

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["order_number"]),
            models.Index(fields=["-date"]),
        ]

    def __str__(self):
        return self.order_number

    def _generate_order_number(self) -> str:
        """Generate a random unique order number."""
        return uuid.uuid4().hex.upper()

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    def update_total(self):
        total = sum(item.price * item.quantity for item in self.items.all())
        self.order_total = total
        super().save(update_fields=["order_total"])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    # snapshot of the plan price at purchase time
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.plan.name} × {self.quantity} (#{self.order.order_number})"

    def save(self, *args, **kwargs):
        # Always snapshot current plan price
        self.price = self.plan.price
        super().save(*args, **kwargs)
        self.order.update_total()

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.update_total()
