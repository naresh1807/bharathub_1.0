from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Every existing template link (e.g. href="employee_login.html",
    # window.location.href='vendor_dashboard.html') is a ROOT-relative
    # path, so each app's urls.py is included at "" (no prefix) --
    # this keeps every old link working with ZERO template changes.
    path("", include("home.urls")),
    path("", include("accounts.urls")),
    path("", include("candidates.urls")),
    path("", include("employers.urls")),
    path("", include("vendor.urls")),

    # New/placeholder apps -- namespaced with their own prefix since
    # they don't have existing root-level page links to preserve yet.
    path("jobs/", include("jobs.urls")),
    path("shop/", include("shopping.urls")),
    path("messages/", include("messaging.urls")),
    path("videos/", include("videos.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # DEBUG=True లో మాత్రమే మీడియా (యూజర్ అప్‌లోడ్ చేసిన రెజ్యూమ్‌లు,
    # ఫోటోలు) ఫైళ్ళని Django నేరుగా సర్వ్ చేస్తుంది -- ప్రొడక్షన్ లో
    # (DEBUG=False) వీటిని ఎప్పుడూ nginx/S3 వంటి వాటితో సర్వ్ చేయాలి.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
