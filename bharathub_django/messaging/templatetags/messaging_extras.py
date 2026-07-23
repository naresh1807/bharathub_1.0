"""
messaging/templatetags/messaging_extras.py

Django టెంప్లేట్‌లు ఫంక్షన్‌కి ఆర్గ్యుమెంట్ పంపి కాల్ చేయలేవు
(ఉదా: {{ avatar_url_for(member) }} పనిచేయదు) -- కాబట్టి
permissions.avatar_url_for() ని ఒక టెంప్లేట్ ఫిల్టర్‌గా ఇక్కడ
ఎక్స్‌పోజ్ చేస్తున్నాం. వాడకం: {{ some_user|avatar_url }}
"""
from django import template

from messaging.permissions import avatar_url_for

register = template.Library()


@register.filter(name="avatar_url")
def avatar_url(user):
    return avatar_url_for(user)
