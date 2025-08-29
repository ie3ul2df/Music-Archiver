from plans.models import Plan

def basket_contents(request):
    basket = request.session.get('basket', {})
    plans = []
    total = 0

    for plan_id in basket.keys():
        try:
            plan = Plan.objects.get(id=plan_id)
            plans.append(plan)
            total += float(plan.price)
        except Plan.DoesNotExist:
            continue

    return {
        'basket_plans': plans,
        'basket_total': total,
        'basket_count': len(plans),
    }
