from django.urls import path

from . import views

app_name = "candidates"

urlpatterns = [
    path(
        "candidate_dashboard.html",
        views.CandidateDashboardView.as_view(),
        name="candidate_dashboard",
    ),

    # నిజమైన Django ModelForm ద్వారా ప్రొఫైల్ ఎడిట్ చేసే పేజీ
    # (CSRF token + server-side validation + login required).
    path(
        "candidate/profile/edit/",
        views.CandidateProfileEditView.as_view(),
        name="candidate_profile_edit",
    ),
    path(
        "candidate/education/<int:pk>/delete/",
        views.CandidateEducationDeleteView.as_view(),
        name="candidate_education_delete",
    ),
    path(
        "candidate/hire-request/<int:pk>/respond/",
        views.HireRequestRespondView.as_view(),
        name="hire_request_respond",
    ),

    # ── Downloads: Resume + employment letters (candidate_dashboard.html
    # sidebar లోని కొత్త "Downloads" నావ్ ఐటమ్) ────────────────────────
    path("candidate/downloads/", views.DownloadsListView.as_view(), name="downloads_list"),
    path("candidate/downloads/resume/", views.ResumeDocumentView.as_view(), name="download_resume"),
    path(
        "candidate/downloads/appointment-letter/<int:pk>/",
        views.AppointmentLetterView.as_view(),
        name="download_appointment_letter",
    ),
    path(
        "candidate/downloads/employment-letter/<int:pk>/<str:letter_type>/",
        views.EmploymentLetterView.as_view(),
        name="download_employment_letter",
    ),
    path(
        "candidate/downloads/offer-letter/<int:pk>/",
        views.OfferLetterView.as_view(),
        name="download_offer_letter",
    ),
]
