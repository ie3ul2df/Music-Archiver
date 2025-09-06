# checkout/admin.py
from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ("price",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "email", "order_total", "date")
    readonly_fields = ("order_number", "date", "order_total", "stripe_pid", "original_basket")
    inlines = (OrderItemInline,)
