from django.contrib import admin

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    # is_resolved ని లిస్ట్ పేజీ లోనే నేరుగా ఆన్/ఆఫ్ చేయగలిగేలా
    # list_editable వాడుతున్నాం -- అడ్మిన్ ప్రతి మెసేజ్ ఓపెన్ చేయకుండానే
    # "పరిష్కరించానా లేదా" అని టిక్ చేయొచ్చు.
    list_display = ("name", "email", "sender_type", "subject", "is_resolved", "created_at")
    list_editable = ("is_resolved",)
    list_filter = ("sender_type", "subject", "is_resolved")
    search_fields = ("name", "email", "message")
    readonly_fields = ("created_at",)
