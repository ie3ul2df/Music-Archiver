# checkout/admin.py
from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ("plan", "quantity", "price")
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "user",
        "user_profile",
        "email",
        "order_total",
        "date",
    )
    readonly_fields = (
        "order_number",
        "date",
        "order_total",
        "stripe_pid",
        "original_basket",
    )
    inlines = (OrderItemInline,)

    search_fields = ("order_number", "email", "user__username")
    list_filter = ("date", "order_total")
