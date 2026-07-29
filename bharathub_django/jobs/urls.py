from django.urls import path

from . import views

app_name = "jobs"

urlpatterns = [
    # Employer side: review applications received
    path("applications.html", views.ApplicationsView.as_view(), name="applications"),
    path(
        "applications/<int:pk>/status/",
        views.ApplicationStatusUpdateView.as_view(),
        name="application_status_update",
    ),
    path(
        "applications/<int:pk>/schedule-interview/",
        views.ScheduleInterviewView.as_view(),
        name="schedule_interview",
    ),
    path(
        "applications/<int:pk>/mark-hired/",
        views.MarkAsHiredView.as_view(),
        name="mark_as_hired",
    ),

    # Employer side: hired candidates + resignation approvals
    path("my_hires.html", views.MyHiresView.as_view(), name="my_hires"),
    path(
        "my_hires/<int:pk>/resignation/respond/",
        views.ResignationRespondView.as_view(),
        name="resignation_respond",
    ),

    # Candidate side: browse jobs, view one, apply, track my applications
    path("browse.html", views.JobBrowseView.as_view(), name="job_browse"),
    path("job/<int:pk>/", views.JobDetailView.as_view(), name="job_detail"),
    path("job/<int:pk>/apply/", views.JobApplyView.as_view(), name="job_apply"),
    path("my_applications.html", views.MyApplicationsView.as_view(), name="my_applications"),
    path("resign/", views.ResignationRequestView.as_view(), name="resign"),
    path(
        "offer-letter/<int:pk>/accept/",
        views.OfferLetterAcceptView.as_view(),
        name="offer_letter_accept",
    ),
]
