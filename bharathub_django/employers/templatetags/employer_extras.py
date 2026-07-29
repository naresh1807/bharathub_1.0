"""
employers/templatetags/employer_extras.py

employers/_nav.html అనేది 5 వేర్వేరు పేజీల్లో (employer_dashboard,
jobs:applications, shopping:shop, shopping:my_orders,
messaging:employer_messages) షేర్ అవుతుంది -- కానీ వాటిలో
employer_dashboard.html యొక్క వ్యూ మాత్రమే "total_applications_count"
ని context లో పెడుతుంది. మిగతా 4 పేజీల్లో ఆ context var ఉండదు కాబట్టి,
nav లోని "Applications" బ్యాడ్జ్ ఆ పేజీల్లో ఖాళీగా కనిపించేది (లేదా
ఇంతకుముందు లాగా హార్డ్‌కోడ్ చేసిన "8" ఎప్పుడూ కనిపించేది).

దీన్ని ప్రతి వ్యూ లోనూ విడివిడిగా కంప్యూట్ చేయించే బదులు, ఇక్కడ ఒక్క
ఫిల్టర్‌గా పెట్టి, ఎక్కడైనా (ఏ వ్యూ context provide చేసినా చేయకపోయినా)
request.user నుండి నేరుగా లెక్కించేలా చేశాం -- nav ఎప్పుడూ సరైన
నంబర్ చూపిస్తుంది.
"""
from django import template

register = template.Library()


@register.simple_tag
def new_applications_count(user):
    """ఈ employer యొక్క jobs మీద ఇంకా సమీక్షించని (status=NEW)
    అప్లికేషన్ల సంఖ్య -- nav బ్యాడ్జ్ కోసం. Employer కాని యూజర్
    (లేదా లాగిన్ కాని యూజర్) కి 0."""
    employer_profile = getattr(user, "employer_profile", None)
    if employer_profile is None:
        return 0
    from jobs.models import JobApplication
    return JobApplication.objects.filter(
        job__employer=employer_profile, status=JobApplication.Status.NEW,
    ).count()


@register.simple_tag
def pending_orders_count(user):
    """"My Orders" నావ్ బ్యాడ్జ్ -- ఇంతకుముందు ఇది ఎప్పుడూ hardcoded "0"
    గా ఉండేది (buyer_shopping.js లోని fake JS-only allOrders array మీద
    ఆధారపడేది, అది shop.html/my_orders.html కాకుండా మిగతా ఏ పేజీలోనూ
    లోడ్ అయ్యేది కూడా కాదు). ఇప్పుడు నిజంగా status=NEW/PROCESSING లో ఉన్న
    ఆర్డర్ల సంఖ్యని DB నుండే చూపిస్తుంది."""
    employer_profile = getattr(user, "employer_profile", None)
    if employer_profile is None:
        return 0
    from shopping.models import Order
    return Order.objects.filter(
        buyer=employer_profile, status__in=[Order.Status.NEW, Order.Status.PROCESSING],
    ).count()


@register.simple_tag
def pending_resignations_count(user):
    """"My Hires" నావ్ బ్యాడ్జ్ -- ఈ employer దగ్గర resignation
    accept/decline కోసం ఎదురుచూస్తున్న Employment రికార్డుల సంఖ్య."""
    employer_profile = getattr(user, "employer_profile", None)
    if employer_profile is None:
        return 0
    from jobs.models import Employment
    return Employment.objects.filter(
        application__job__employer=employer_profile,
        status=Employment.Status.RESIGNATION_REQUESTED,
    ).count()
