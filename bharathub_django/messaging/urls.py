from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    path("employer_messages.html", views.EmployerMessagesView.as_view(), name="employer_messages"),
    path("vendor_messages.html", views.VendorMessagesView.as_view(), name="vendor_messages"),
    path("candidate_messages.html", views.CandidateMessagesView.as_view(), name="candidate_messages"),

    # ⚠️ N+1/scalability ఫిక్స్: సెర్చ్ బాక్స్ లో టైప్ చేసినప్పుడల్లా
    # AJAX ద్వారా ఇక్కడికి పిలుస్తారు -- ఇది ఇక page-load-time లో
    # contacts_for() ని (మొత్తం యూజర్ బేస్ ని లోడ్ చేసేది) పిలవాల్సిన
    # అవసరాన్ని పూర్తిగా తీసేసింది.
    path("contacts/search/", views.ContactSearchView.as_view(), name="contact_search"),

    # Fallback (no-JS) send + start-new-chat
    path("conversation/<int:pk>/send/", views.SendMessageView.as_view(), name="send_message"),
    path("start/", views.StartConversationView.as_view(), name="start_conversation"),

    # Group chat
    path("group/create/", views.CreateGroupView.as_view(), name="create_group"),
    path("group/<int:pk>/members/", views.GroupMemberUpdateView.as_view(), name="group_members"),
    path("group/<int:pk>/rename/", views.RenameGroupView.as_view(), name="rename_group"),
    path("group/<int:pk>/leave/", views.LeaveGroupView.as_view(), name="leave_group"),

    # JSON APIs used by the real-time (WebSocket) chat UI
    path("conversation/<int:pk>/history/", views.ConversationHistoryView.as_view(), name="conversation_history"),
    path("conversation/<int:pk>/search/", views.ConversationSearchView.as_view(), name="conversation_search"),
    path("attachment/upload/", views.MessageAttachmentUploadView.as_view(), name="attachment_upload"),
    path("push/subscribe/", views.SavePushSubscriptionView.as_view(), name="push_subscribe"),
]
