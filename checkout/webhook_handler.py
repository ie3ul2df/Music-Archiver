# checkout/webhook_handler.py
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
import json
import time
import stripe

from .models import Order, OrderItem
from plans.models import Plan


class StripeWH_Handler:
    def __init__(self, request):
        self.request = request

    def handle_event(self, event):
        return HttpResponse(
            content=f"Unhandled webhook received: {event['type']}",
            status=200
        )

    def handle_payment_intent_payment_failed(self, event):
        return HttpResponse(
            content=f"Webhook received: {event['type']}",
            status=200
        )

    def handle_payment_intent_succeeded(self, event):
        intent = event.data.object
        pid = intent.id

        # Metadata
        basket_json = getattr(intent.metadata, "basket", None) or getattr(intent.metadata, "bag", "{}")
        save_info = getattr(intent.metadata, "save_info", "false") == "true"

        # Stripe charge data
        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe_charge = stripe.Charge.retrieve(intent.latest_charge)
        billing_details = stripe_charge.billing_details
        shipping_details = intent.shipping
        grand_total = Decimal(str(stripe_charge.amount)) / Decimal("100")

        # Clean up blank shipping fields
        if shipping_details and shipping_details.address:
            for field, value in shipping_details.address.items():
                if value == "":
                    shipping_details.address[field] = None

        # Try to find existing order
        order = None
        for attempt in range(5):
            try:
                order = Order.objects.get(
                    email=billing_details.email,
                    order_total=grand_total,
                    stripe_pid=pid,
                )
                return HttpResponse(
                    content=f"Webhook verified: order already exists (pid={pid})",
                    status=200,
                )
            except Order.DoesNotExist:
                time.sleep(1)

        # If no order exists, create one from basket metadata
        basket = json.loads(basket_json) if basket_json else {}
        if not order:
            order = Order.objects.create(
                full_name=billing_details.name or "",
                email=billing_details.email or "",
                stripe_pid=pid,
                original_basket=basket_json,
                order_total=grand_total,
            )
            for plan_id, qty in basket.items():
                plan = get_object_or_404(Plan, id=int(plan_id))
                OrderItem.objects.create(
                    order=order,
                    plan=plan,
                    quantity=int(qty),
                    price=plan.price,
                )

        return HttpResponse(
            content=f"Webhook created order (pid={pid})",
            status=200,
        )
