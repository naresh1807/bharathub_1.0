from django.contrib import admin

from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """Django Admin లో Job రికార్డుల్ని బ్రౌజ్/సెర్చ్/ఎడిట్ చేయడానికి.
    ఎందుకు ఇది కూడా ఒక భద్రతా ఫీచరే: /admin/ కి కేవలం is_staff=True
    యూజర్లు మాత్రమే యాక్సెస్ చేయగలరు (Django బిల్ట్-ఇన్ చెక్) --
    కంపెనీలు తప్పుడు/స్పామ్ జాబ్ పోస్ట్ చేస్తే, ఇక్కడి నుండి వేగంగా
    గుర్తించి (list_filter/search_fields తో) తీసేయొచ్చు."""

    list_display = ("title", "employer", "location", "job_type", "status", "created_at")
    list_filter = ("status", "job_type", "department", "experience_level")
    search_fields = ("title", "location", "skills_required", "employer__company_name")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
