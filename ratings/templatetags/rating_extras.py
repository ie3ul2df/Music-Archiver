"""Custom template filters for rating widgets."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django import template

register = template.Library()


@register.filter(name="coerce_float")
def coerce_float(value: Any) -> float:
    """Return ``value`` as a float when possible.

    ``ratings/_stars.html`` compares the average rating against the integer
    star positions.  In production we noticed a few contexts (e.g. annotated
    querysets or JSON sources) providing the average as a string.  Django's
    template language treats comparisons between integers and strings as
    ``False`` which means no stars are highlighted.  Converting the value to a
    float before the comparison keeps the widget resilient regardless of the
    incoming type.

    Any value that cannot be converted cleanly defaults to ``0.0`` which is the
    same behaviour as "no rating yet".
    """

    if value is None:
        return 0.0

    if isinstance(value, float):
        return value

    if isinstance(value, Decimal):
        return float(value)

    try:
        return float(value)
    except (TypeError, ValueError, InvalidOperation):
        return 0.0