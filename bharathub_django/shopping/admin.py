from django.contrib import admin

from .models import Order, OrderItem, Product


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "category", "price", "stock", "is_published", "created_at")
    list_filter = ("category", "is_published")
    search_fields = ("name", "vendor__shop_name")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "vendor", "buyer", "status", "total_amount", "created_at")
    list_filter = ("status",)
    inlines = [OrderItemInline]
