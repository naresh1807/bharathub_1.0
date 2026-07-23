from django.urls import path
from . import views

app_name = "employers"

urlpatterns = [
    path("employer_dashboard.html", views.EmployerDashboardView.as_view(), name="employer_dashboard"),

    # Candidate Search (headhunting) -- Employer dashboard కి మాత్రమే.
    path("candidates/search/", views.CandidateSearchView.as_view(), name="candidate_search"),
    path("candidates/<int:pk>/", views.CandidateDetailView.as_view(), name="candidate_detail"),
    path("candidates/<int:pk>/hire-request/", views.SendHireRequestView.as_view(), name="send_hire_request"),
    path("candidates/<int:pk>/chat/", views.StartChatWithCandidateView.as_view(), name="start_chat_with_candidate"),
]
