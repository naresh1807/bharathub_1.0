from django.urls import path

from . import views

app_name = "webmail"

urlpatterns = [
    path("candidate_mail.html", views.CandidateMailView.as_view(), name="candidate_mail"),
    path("employer_mail.html", views.EmployerMailView.as_view(), name="employer_mail"),
    path("vendor_mail.html", views.VendorMailView.as_view(), name="vendor_mail"),

    path("setup/", views.MailSetupView.as_view(), name="mail_setup"),
    path("compose/", views.ComposeSendView.as_view(), name="compose_send"),

    path("<int:pk>/star/", views.ToggleStarView.as_view(), name="toggle_star"),
    path("<int:pk>/trash/", views.TrashEmailView.as_view(), name="trash_email"),
    path("<int:pk>/restore/", views.RestoreEmailView.as_view(), name="restore_email"),
    path("<int:pk>/delete-forever/", views.DeleteForeverView.as_view(), name="delete_forever"),

    path("attachment/<int:pk>/delete/", views.AttachmentDeleteView.as_view(), name="delete_attachment"),
]
