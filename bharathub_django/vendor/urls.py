from django.urls import path
from . import views

app_name = "vendor"

urlpatterns = [
    path("vendor_registration.html", views.VendorRegistrationView.as_view(), name="vendor_registration"),
    path("vendor_login.html", views.VendorLoginView.as_view(), name="vendor_login"),
    path("vendor_dashboard.html", views.VendorDashboardView.as_view(), name="vendor_dashboard"),
    path("complete-profile/", views.VendorProfileCompletionView.as_view(), name="vendor_complete_profile"),
]
