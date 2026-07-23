from django.urls import path
from . import views

app_name = "home"

urlpatterns = [
    # Root -> Home page
    path("", views.BharatHubHomeView.as_view(), name="home"),

    # NOTE: paths below intentionally match the ORIGINAL filenames
    # (e.g. "bharathub_home.html") so that every existing
    # <a href="bharathub_home.html"> / window.location.href inside the
    # templates keeps working with ZERO changes required.
    path("bharathub_home.html", views.BharatHubHomeView.as_view(), name="bharathub_home"),
    path("about.html", views.AboutView.as_view(), name="about"),
    path("contact.html", views.ContactView.as_view(), name="contact"),
    path("privacy.html", views.PrivacyView.as_view(), name="privacy"),
    path("terms.html", views.TermsView.as_view(), name="terms"),
    path("help.html", views.HelpView.as_view(), name="help"),
]
