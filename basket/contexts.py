from django.shortcuts import get_object_or_404
from plans.models import Plan

def basket_contents(request):
    basket = request.session.get('basket', {})
    basket_items = []
    total = 0
    count = 0

    for plan_id, qty in basket.items():
        try:
            plan = get_object_or_404(Plan, id=plan_id)
            subtotal = plan.price * qty
            total += subtotal
            count += qty

            basket_items.append({
                "plan": plan,
                "qty": qty,
                "subtotal": subtotal,
            })
        except Plan.DoesNotExist:
            continue

    return {
        "basket_items": basket_items,   # list of {plan, qty, subtotal}
        "basket_total": total,          # grand total £
        "basket_count": count,          # total number of items (including qty)
    }
