from django.contrib import admin

from .models import JobApplication


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ("candidate", "job", "status", "applied_at")
    list_filter = ("status",)
    search_fields = ("candidate__user__username", "job__title")
    readonly_fields = ("applied_at", "updated_at")
