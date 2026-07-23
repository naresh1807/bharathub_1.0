"""
vendor/templatetags/vendor_extras.py

vendor/_nav.html నాలుగు వేర్వేరు పేజీల్లో (vendor_dashboard,
shopping:vendor_products, shopping:vendor_orders,
messaging:vendor_messages) షేర్ అవుతుంది -- "Orders/Leads" బ్యాడ్జ్
ఏ పేజీ లో అయినా సరైన నంబర్ చూపించాలంటే, ఆ లెక్క ఇక్కడ ఒక్కచోటే
(request.user నుండి నేరుగా) కంప్యూట్ చేస్తాం -- prewiring ప్రతి
వ్యూ లోనూ విడివిడిగా చేసే బదులు.
"""
from django import template

register = template.Library()


@register.simple_tag
def pending_orders_count(user):
    """ఇంకా పూర్తి కాని (NEW లేదా PROCESSING స్టేటస్ లో ఉన్న) ఆర్డర్ల
    సంఖ్య -- nav బ్యాడ్జ్ కోసం. Vendor కాని యూజర్ కి 0."""
    vendor_profile = getattr(user, "vendor_profile", None)
    if vendor_profile is None:
        return 0
    from shopping.models import Order
    return vendor_profile.orders.filter(
        status__in=[Order.Status.NEW, Order.Status.PROCESSING],
    ).count()
