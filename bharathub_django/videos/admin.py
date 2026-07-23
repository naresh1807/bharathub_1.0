from django.contrib import admin

from .models import Video, VideoComment, VideoLike


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "employer", "category", "is_published", "view_count", "created_at")
    list_filter = ("category", "is_published")
    search_fields = ("title", "caption", "employer__company_name")


@admin.register(VideoLike)
class VideoLikeAdmin(admin.ModelAdmin):
    list_display = ("video", "user", "reaction", "created_at")
    list_filter = ("reaction",)


@admin.register(VideoComment)
class VideoCommentAdmin(admin.ModelAdmin):
    list_display = ("video", "user", "text", "created_at")
    search_fields = ("text",)
