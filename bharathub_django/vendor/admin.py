from django.contrib import admin

from .models import VendorProfile


@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    list_display = ("vendor_id", "shop_name", "vendor_email", "vendor_mobile", "created_at")
    search_fields = ("vendor_id", "shop_name", "vendor_email", "vendor_mobile", "pan_number", "gst_number")
    readonly_fields = ("vendor_id", "created_at")
