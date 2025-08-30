import stripe
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .forms import OrderForm
from .models import Order, OrderItem
from plans.models import Plan

def checkout(request):
    basket = request.session.get("basket", {})
    if not basket:
        messages.error(request, "Your basket is empty")
        return redirect("plan_list")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    total = sum(get_object_or_404(Plan, id=pid).price for pid in basket.keys())
    intent = stripe.PaymentIntent.create(
        amount=int(total * 100),
        currency="gbp",
    )

    if request.method == "POST":
        form = OrderForm(request.POST)
        # print("CHECKOUT POST REACHED 🚀", request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.stripe_pid = request.POST.get("payment_intent_id")
            if request.user.is_authenticated:
                order.user = request.user
            order.save()

            for plan_id in basket.keys():
                plan = get_object_or_404(Plan, id=plan_id)
                OrderItem.objects.create(order=order, plan=plan, price=plan.price)

            # ✅ redirect to success page
            return redirect("checkout_success", order_number=order.order_number)
        else:
            messages.error(request, "There was an issue with your order. Please try again.")
    else:
        form = OrderForm()

    context = {
        "form": form,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
        "client_secret": intent.client_secret,
        "total": total,
    }
    return render(request, "checkout/checkout.html", context)


def checkout_success(request, order_number):
    """
    Handle successful checkouts
    """
    order = get_object_or_404(Order, order_number=order_number)

    messages.success(
        request,
        f"Order successfully processed! "
        f"Your order number is {order_number}. "
        f"A confirmation email will be sent to {order.email}."
    )

    # clear basket
    if 'basket' in request.session:
        del request.session['basket']

    context = {"order": order}
    return render(request, "checkout/checkout_success.html", context)
