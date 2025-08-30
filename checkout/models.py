import uuid
from django.db import models
from django.conf import settings
from plans.models import Plan
from django.contrib.auth.models import User

class Order(models.Model):
    order_number = models.CharField(max_length=32, null=False, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    full_name = models.CharField(max_length=50, null=False, blank=False)
    email = models.EmailField(max_length=254, null=False, blank=False)
    date = models.DateTimeField(auto_now_add=True)
    order_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stripe_pid = models.CharField(max_length=254, null=False, blank=False, default="")

    def _generate_order_number(self):
        """Generate a random unique order number"""
        return uuid.uuid4().hex.upper()

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.price = self.plan.price  # always use plan price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plan.name} (Order {self.order.order_number})"
