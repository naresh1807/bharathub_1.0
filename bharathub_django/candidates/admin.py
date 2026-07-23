from django.contrib import admin

from .models import CandidateEducation, CandidateProfile


# CandidateEducation ని CandidateProfile అడ్మిన్ పేజీ లోపలే (inline)
# చూపిస్తున్నాం -- ఒక్కో candidate కి ఎన్ని ఎడ్యుకేషన్ రికార్డులు
# ఉన్నాయో ప్రొఫైల్ పేజీ లోనే చూడొచ్చు/ఎడిట్ చేయొచ్చు, వేరే టాబ్ కి
# వెళ్లాల్సిన అవసరం లేదు.
class CandidateEducationInline(admin.TabularInline):
    model = CandidateEducation
    extra = 0


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "headline", "location", "experience_level", "hire_status", "updated_at")
    search_fields = ("user__username", "user__email", "headline", "skills", "location")
    list_filter = ("experience_level", "hire_status")
    readonly_fields = ("created_at", "updated_at")
    inlines = [CandidateEducationInline]


@admin.register(CandidateEducation)
class CandidateEducationAdmin(admin.ModelAdmin):
    list_display = ("degree_title", "profile", "institution", "year_of_passing", "level")
    search_fields = ("degree_title", "institution", "profile__user__username")
    list_filter = ("level",)
