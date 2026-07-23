from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

from accounts.models import EmployerProfile

# ============================================================================
# videos/models.py
# ఎందుకు ఈ యాప్: employer_dashboard.html లో ఇంతకుముందు "🎥 Upload Video"
# సెక్షన్ కేవలం UI ప్రివ్యూ మాత్రమే (ఏదీ DB లో సేవ్ కాదు) అని ఒక కామెంట్
# స్పష్టంగా చెప్పింది -- home page లోని "Company Achievements & Culture
# Feed" లోని రెండు వీడియో కార్డులు కూడా hardcoded HTML మాత్రమే.
# ఈ యాప్ ఆ రెండిటినీ ఒకే నిజమైన Video మోడల్ తో కలుపుతుంది:
#   - Employer డాష్‌బోర్డ్ లో అప్‌లోడ్ చేసిన వీడియో ఇక్కడ save అవుతుంది.
#   - అదే వీడియో ఆటోమేటిక్‌గా (a) Home పేజీ ఫీడ్ లో, (b) Candidate
#     డాష్‌బోర్డ్ లోని "Videos" ట్యాబ్ లో, (c) ఆ Employer సొంత "Published
#     Videos" గ్రిడ్ లో -- మూడు చోట్లా ఒకే source of truth నుండి కనిపిస్తుంది.
# ============================================================================


class Video(models.Model):
    """ఒక్క కంపెనీ కల్చర్/అచీవ్‌మెంట్ వీడియో పోస్ట్ -- Facebook తరహా ఫీడ్
    పోస్ట్ లాంటిది. ప్రతి వీడియో ఒక్క EmployerProfile కి చెందుతుంది
    (ForeignKey -- ఒక కంపెనీ చాలా వీడియోలు పోస్ట్ చేయొచ్చు)."""

    class Category(models.TextChoices):
        OFFICE_CULTURE = "office_culture", "Office Culture"
        ACHIEVEMENT = "achievement", "Company Achievement"
        TEAM_HIGHLIGHTS = "team_highlights", "Team Highlights"
        CSR = "csr", "CSR Activity"
        PRODUCT_LAUNCH = "product_launch", "Product Launch"
        AWARDS = "awards", "Awards & Recognition"

    employer = models.ForeignKey(
        EmployerProfile, on_delete=models.CASCADE, related_name="videos",
    )

    title = models.CharField(max_length=200)
    caption = models.TextField(blank=True)
    category = models.CharField(
        max_length=30, choices=Category.choices, default=Category.OFFICE_CULTURE,
    )

    # వీడియో ఫైల్ -- FileExtensionValidator తో mp4/mov/avi/webm మాత్రమే
    # అనుమతిస్తాం (employer_dashboard.html లోని పాత mock dropzone లో
    # ఇదే accept="video/mp4,video/avi,video/mov" ఉంది, దానికి webm
    # జోడించాం browser compatibility కోసం).
    video_file = models.FileField(
        upload_to="company_videos/%Y/%m/",
        validators=[FileExtensionValidator(allowed_extensions=["mp4", "mov", "avi", "webm"])],
    )

    # is_published=False అంటే ఈ వీడియో ఇంకా ఫీడ్ లో కనిపించదు (future:
    # admin moderation/draft feature కోసం ఉంచాం) -- ప్రస్తుతానికి అప్‌లోడ్
    # చేసిన వెంటనే True గా సెట్ అవుతుంది (views.py చూడండి).
    is_published = models.BooleanField(default=True)

    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.employer.company_name})"

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.count()


class VideoLike(models.Model):
    """Facebook-style reaction -- ఒక యూజర్ ఒక వీడియో కి ఒక్క reaction మాత్రమే
    పెట్టగలరు (unique_together). రెండోసారి అదే reaction నొక్కితే తీసేస్తాం
    (toggle), వేరే reaction నొక్కితే మారుస్తాం -- ఇది Facebook తీరు."""

    class Reaction(models.TextChoices):
        LIKE = "like", "👍"
        LOVE = "love", "❤️"
        CLAP = "clap", "👏"
        SUPPORT = "support", "🤝"
        CELEBRATE = "celebrate", "🎉"

    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="video_likes",
    )
    reaction = models.CharField(
        max_length=10, choices=Reaction.choices, default=Reaction.LIKE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("video", "user")

    def __str__(self):
        return f"{self.user} {self.reaction} {self.video_id}"


class VideoComment(models.Model):
    """Employer లేదా Candidate ఎవరైనా (login అయిన ఏ యూజర్ అయినా) ఒక వీడియో
    కింద కామెంట్ పెట్టొచ్చు -- messaging యాప్ లో లాగే Django's built-in User
    ని నేరుగా వాడతాం, ఎందుకంటే commenter Employer/Candidate ఏదైనా కావొచ్చు."""

    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="video_comments",
    )
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user} -> video {self.video_id}: {self.text[:30]}"
