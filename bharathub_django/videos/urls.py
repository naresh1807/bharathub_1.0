from django.urls import path

from . import views

app_name = "videos"

# NOTE: bharathub/urls.py ఈ యాప్ ని path("videos/", include("videos.urls"))
# తో include చేస్తుంది (jobs/shopping/messaging యాప్‌ల తరహాలోనే) -- కాబట్టి
# ఇక్కడ మళ్ళీ "videos/" ప్రిఫిక్స్ రాయం, ఫైనల్ URL ఇలా ఉంటుంది:
# /videos/upload/, /videos/5/like/ మొదలైనవి.
urlpatterns = [
    path("upload/", views.UploadVideoView.as_view(), name="upload_video"),
    path("<int:pk>/delete/", views.DeleteVideoView.as_view(), name="delete_video"),
    path("<int:pk>/like/", views.toggle_like, name="toggle_like"),
    path("<int:pk>/comment/", views.add_comment, name="add_comment"),
    path("feed.html", views.VideoFeedPageView.as_view(), name="video_feed_page"),
]
