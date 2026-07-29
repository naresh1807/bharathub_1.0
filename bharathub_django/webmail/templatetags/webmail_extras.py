"""
webmail/templatetags/webmail_extras.py

employers/templatetags/employer_extras.py (new_applications_count) మరియు
vendor/templatetags/vendor_extras.py (pending_orders_count) లోని అదే
pattern -- topnav లో "📧 Mail" ట్యాబ్ పైన unread badge చూపించడానికి.
వాడకం: {% load webmail_extras %} ... {% unread_mail_count request.user as mail_badge %}
"""
from django import template

from webmail.views import unread_mail_count_for

register = template.Library()


@register.simple_tag
def unread_mail_count(user):
    return unread_mail_count_for(user)
