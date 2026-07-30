from django.urls import path

from . import views

app_name = "meetings"

urlpatterns = [
    path("room/<slug:room_code>/", views.MeetingRoomView.as_view(), name="room"),
    path("start_instant/", views.StartInstantMeetingView.as_view(), name="start_instant"),
    path("my_meetings.html", views.MeetingListView.as_view(), name="meeting_list"),
    path("my_meetings_candidate.html", views.CandidateMeetingListView.as_view(), name="candidate_meeting_list"),
    path(
        "conversation/<int:conversation_id>/call/",
        views.StartConversationCallView.as_view(), name="start_conversation_call",
    ),
    path("my_room/", views.MyPersonalRoomView.as_view(), name="my_personal_room"),
    path("send_link/", views.SendMeetingLinkView.as_view(), name="send_meeting_link"),
]
