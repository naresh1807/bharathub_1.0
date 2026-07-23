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
]
