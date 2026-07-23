import random
import string

from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_vendor_id():
    """
    Vendor ID ఫార్మాట్: BHVND + YY + MM + 6-అంకెల నంబర్
      BHVND = స్థిర ప్రిఫిక్స్ (Vendor)
      YY    = రిజిస్ట్రేషన్ సంవత్సరం చివరి 2 అంకెలు
      MM    = రిజిస్ట్రేషన్ నెల, 2-అంకెలు
      తర్వాత 6 random అంకెలు -- మొత్తం 15 అక్షరాలు (ఉదా: BHVND2604123456)

    (accounts/models.py లోని generate_bharathub_id() లో ఉన్న అదే
    యూనిక్‌నెస్-రిట్రై లాజిక్.)
    """
    prefix = f"BHVND{timezone.now().strftime('%y%m')}"
    for _ in range(20):
        candidate = f"{prefix}{''.join(random.choices(string.digits, k=6))}"
        if not VendorProfile.objects.filter(vendor_id=candidate).exists():
            return candidate
    return f"{prefix}{int(timezone.now().timestamp()) % 1000000:06d}"


# ----------------------------------------------------------------------
# VendorProfile మోడల్
# ఎందుకు: vendor_registration.html లో అడిగే షాప్/వెండర్ వివరాలు
# (షాప్ పేరు, మొబైల్, ఇమెయిల్, PAN, GST, కేటగిరీ, పనిచేసే రోజులు,
# షాప్ ఫోటో) ఇక్కడ నిల్వ చేస్తాం. accounts app లో EmployeeProfile /
# EmployerProfile చేసిన విధంగానే ఇక్కడ కూడా Django యొక్క User మోడల్
# ని (లాగిన్ + hashed password కోసం) OneToOneField తో వాడుతున్నాం.
# ----------------------------------------------------------------------
class VendorProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="vendor_profile",
    )

    vendor_id = models.CharField(
        max_length=16, unique=True, default=generate_vendor_id, editable=False,
    )

    shop_name = models.CharField(max_length=200)
    vendor_email = models.EmailField()

    # రిజిస్ట్రేషన్ ని సింపుల్ గా ఉంచడానికి మొబైల్ ని ఇక్కడ optional
    # చేశాం (null=True కూడా పెట్టాం -- ఎందుకంటే unique=True తో పాటు
    # blank='' వాడితే, ఇద్దరు వెండర్లు మొబైల్ నింపకపోతే ఇద్దరికీ ఖాళీ
    # స్ట్రింగ్ వచ్చి UNIQUE constraint విరిగిపోతుంది; NULL మాత్రం
    # SQLite/Postgres రెండిటిలోనూ ఎప్పుడూ ఇతర NULL లతో సరిపోలదు).
    # "Complete Your Profile" దశలో నింపుకోవచ్చు.
    vendor_mobile = models.CharField(max_length=10, unique=True, blank=True, null=True)

    # రిజిస్ట్రేషన్ లో కొత్తగా జోడించిన ఫీల్డ్స్:
    owner_name = models.CharField(max_length=150, blank=True)

    class BusinessType(models.TextChoices):
        RETAIL = "retail", "Retail"
        WHOLESALE = "wholesale", "Wholesale"
        SERVICE = "service", "Service Provider"
        MANUFACTURING = "manufacturing", "Manufacturing"
        OTHER = "other", "Other"

    business_type = models.CharField(
        max_length=20, choices=BusinessType.choices, blank=True,
    )
    year_established = models.PositiveIntegerField(null=True, blank=True)
    address = models.TextField(blank=True)

    pan_number = models.CharField(max_length=10, blank=True)
    gst_number = models.CharField(max_length=15, blank=True)

    category = models.CharField(max_length=100, blank=True)

    # ఇది False గా ఉన్నంత వరకూ (మొబైల్, కేటగిరీ, పనిచేసే రోజులు,
    # షాప్ ఫోటో వంటివి ఇంకా నింపలేదు), ప్రొఫైల్ కంప్లీషన్ గేట్
    # (ProfileCompletionMiddleware) డాష్‌బోర్డ్ కి బదులు "Complete
    # Your Profile" పేజీ కే పంపిస్తుంది.
    profile_completed = models.BooleanField(default=False)

    # "పనిచేసే రోజులు" -- ఉదా: "Mon-Sat" లేదా "Mon,Tue,Wed" లాంటి కామా
    # సెపరేటెడ్ టెక్స్ట్ గా సింపుల్ గా స్టోర్ చేస్తున్నాం (ప్రస్తుతానికి
    # ప్రత్యేక Day మోడల్ అవసరం లేదు, అది over-engineering అవుతుంది).
    working_days = models.CharField(max_length=100, blank=True)

    shop_photo = models.ImageField(upload_to="vendor_photos/%Y/%m/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.shop_name} ({self.vendor_id})"
