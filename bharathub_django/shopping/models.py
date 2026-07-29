from django.db import models

from accounts.models import EmployerProfile
from vendor.models import VendorProfile

# ============================================================================
# shopping/models.py
# B2B marketplace: Vendor లు Product/Service catalog పెడతారు, Employer లు
# వాటిని కొంటారు (Order పెడతారు). ఒక Order లో ఒకటి కంటే ఎక్కువ Products
# ఉండొచ్చు కాబట్టి, Order <-> Product మధ్య OrderItem (through model) వాడాం.
# ============================================================================


class Product(models.Model):
    class Category(models.TextChoices):
        HARDWARE = "hardware", "Hardware"
        SOFTWARE = "software", "Software"
        SERVICE = "service", "Service"
        OFFICE_SUPPLY = "office_supply", "Office Supply"
        TRAINING = "training", "Training"
        CATERING = "catering", "Catering"

    class Unit(models.TextChoices):
        PER_UNIT = "per_unit", "Per Unit"
        PER_HOUR = "per_hour", "Per Hour"
        PER_DAY = "per_day", "Per Day"
        PER_MONTH = "per_month", "Per Month"
        FIXED = "fixed", "Fixed"

    vendor = models.ForeignKey(
        VendorProfile, on_delete=models.CASCADE, related_name="products",
    )
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices)
    price = models.PositiveIntegerField(help_text="Price in ₹")
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.PER_UNIT)
    stock = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/%Y/%m/", blank=True, null=True)

    # "Live" (marketplace లో కనిపిస్తుంది) vs "Draft" (వెండర్ కి మాత్రమే కనిపిస్తుంది)
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.vendor.shop_name})"


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        PROCESSING = "processing", "Processing"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    vendor = models.ForeignKey(
        VendorProfile, on_delete=models.CASCADE, related_name="orders",
    )
    buyer = models.ForeignKey(
        EmployerProfile, on_delete=models.CASCADE, related_name="orders",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    total_amount = models.PositiveIntegerField(default=0)
    # చెక్‌అవుట్ సమయంలో Employer ఇచ్చిన డెలివరీ అడ్రస్ -- employer.address
    # (ప్రొఫైల్ లో నమోదు చేసినది) తో ఒకటే కానవసరం లేదు, వేరే బ్రాంచ్‌కి
    # షిప్ చేయాల్సి రావొచ్చు కాబట్టి ప్రతి ఆర్డర్ కీ విడిగా అడుగుతాం
    # (shopping/views.py: PlaceOrderView, buyer_shopping.js చెక్‌అవుట్
    # మోడల్). ఇన్వాయిస్ లో కూడా ఇదే చూపిస్తాం.
    delivery_address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} — {self.buyer.company_name} → {self.vendor.shop_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1)
    price_at_order = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

    @property
    def line_total(self):
        return self.price_at_order * self.quantity
