from decimal import Decimal

from plans.models import Plan


def basket_contents(request):
    basket = request.session.get("basket", {})
    basket_items = []
    total = Decimal("0")
    count = 0

    # Bulk fetch all needed plans in one query
    ids = list(basket.keys())
    plans = Plan.objects.filter(id__in=ids).only("id", "name", "price")
    plan_map = {str(p.id): p for p in plans}

    for plan_id, qty in basket.items():
        qty = int(qty)
        plan = plan_map.get(str(plan_id))
        if not plan:
            # Stale/deleted plan left in session — just skip it
            continue

        subtotal = plan.price * qty  # Decimal * int -> Decimal
        total += subtotal
        count += qty

        basket_items.append(
            {
                "plan": plan,
                "qty": qty,
                "subtotal": subtotal,
            }
        )

    return {
        "basket_items": basket_items,
        "basket_total": total,
        "basket_count": count,
    }
