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

    # Candidate side: browse jobs, view one, apply, track my applications
    path("browse.html", views.JobBrowseView.as_view(), name="job_browse"),
    path("job/<int:pk>/", views.JobDetailView.as_view(), name="job_detail"),
    path("job/<int:pk>/apply/", views.JobApplyView.as_view(), name="job_apply"),
    path("my_applications.html", views.MyApplicationsView.as_view(), name="my_applications"),
]
