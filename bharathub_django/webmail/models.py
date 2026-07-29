import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models

# ============================================================================
# webmail/models.py
#
# ఇది Gmail క్లోన్ -- కానీ నిజమైన SMTP మెయిల్ కాదు, BharatHub లో
# రిజిస్టర్ అయిన వాళ్ళ మధ్యే పనిచేసే internal మెయిల్ సిస్టమ్ (అంటే
# ఇప్పటికే ఉన్న messaging యాప్ లాగే -- కానీ చాట్ కాకుండా, ఇన్‌బాక్స్/
# సెంట్/డ్రాఫ్ట్స్/ట్రాష్ ఉన్న "మెయిల్" UX తో). ప్రతి రిజిస్టర్డ్
# యూజర్ (Candidate/Employer/Vendor ఏ రోల్ అయినా) ఒక @bharathub.com
# అడ్రస్ ని క్రియేట్ చేసుకోగలరు (MailAddress), ఆ తర్వాత ఇతర
# bharathub.com అడ్రస్‌లకి మెయిల్ పంపొచ్చు.
# ============================================================================

# ఫైల్ అటాచ్‌మెంట్‌ల కోసం extension allow-list + సైజ్ పరిమితి --
# messaging యాప్ (messaging/views.py: ATTACHMENT_MAX_MB,
# attachment_extension_validator) లో వాడిన అదే కన్వెన్షన్‌నే ఇక్కడా
# అనుసరిస్తున్నాం, స్థిరత్వం కోసం.
ATTACHMENT_MAX_MB = 10
attachment_extension_validator = FileExtensionValidator(
    allowed_extensions=[
        "jpg", "jpeg", "png", "gif", "webp",  # images
        "pdf", "doc", "docx", "xls", "xlsx", "txt",  # documents
    ],
)

LOCAL_PART_VALIDATOR = RegexValidator(
    regex=r"^[a-z][a-z0-9._]{2,29}$",
    message=(
        "Mail ID చిన్న అక్షరం తో మొదలవ్వాలి, 3-30 అక్షరాలు ఉండాలి "
        "(చిన్న అక్షరాలు, అంకెలు, '.', '_' మాత్రమే అనుమతి)."
    ),
)

MAIL_DOMAIN = "bharathub.com"


class MailAddress(models.Model):
    """ఒక్కో యూజర్ కి ఒక్కటే BharatHub Mail ఐడెంటిటీ. local_part అంటే
    '@' కి ముందు భాగం -- మొత్తం అడ్రస్ ఎప్పుడూ local_part+'@bharathub.com'.
    యూజర్ మొదటిసారి Mail యాప్ తెరిచినప్పుడు దీన్ని క్రియేట్ చేసుకుంటారు
    (webmail/views.py లోని MailSetupView చూడండి) -- అప్పటివరకూ ఈ యూజర్
    కి MailAddress ఉండదు, అదే "మొదటిసారి తెరిచామా లేదా" అని తెలుసుకునే
    చెక్."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="mail_address",
    )
    local_part = models.CharField(
        max_length=30, unique=True, validators=[LOCAL_PART_VALIDATOR],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["local_part"]

    def __str__(self):
        return self.address

    @property
    def address(self):
        return f"{self.local_part}@{MAIL_DOMAIN}"

    def clean(self):
        self.local_part = (self.local_part or "").strip().lower()


class Email(models.Model):
    """ఒక మెయిల్ -- Gmail లో లాగే, sender-side స్టేట్ (draft/trash) మరియు
    recipient-side స్టేట్ (read/starred/trash) వేర్వేరుగా ట్రాక్ చేస్తాం
    -- ఎందుకంటే ఒకరు 'Delete' చేస్తే, అది రెండో వ్యక్తి ఇన్‌బాక్స్ లో
    కూడా మాయం కాకూడదు (ఇద్దరిదీ వేర్వేరు 'view' ఈ ఒక్క row మీదే)."""

    sender = models.ForeignKey(
        MailAddress, on_delete=models.CASCADE, related_name="sent_emails",
    )
    # recipient ఎప్పుడూ ఒక చెల్లుబాటు అయ్యే internal MailAddress నే
    # అవ్వాలి (compose ఫారమ్ దీన్ని లుకప్ చేసి validate చేస్తుంది) --
    # draft గా save అయినప్పుడు మాత్రం ఇంకా recipient తేల్చుకోకపోవచ్చు
    # కాబట్టి null=True.
    recipient = models.ForeignKey(
        MailAddress, on_delete=models.CASCADE, related_name="received_emails",
        null=True, blank=True,
    )
    # Draft లో recipient ఇంకా resolve కాకముందు యూజర్ టైప్ చేసిన raw
    # టెక్స్ట్ ని కూడా దాచుకుంటాం, తిరిగి ఎడిట్ చేసేటప్పుడు చూపించడానికి.
    to_raw = models.CharField(max_length=150, blank=True)

    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)  # draft అయితే None

    # -- sender-side స్టేట్ --
    is_draft = models.BooleanField(default=False)
    sender_trashed = models.BooleanField(default=False)

    # -- recipient-side స్టేట్ --
    is_read = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    recipient_trashed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject or '(no subject)'} — {self.sender} → {self.to_raw}"

    @property
    def snippet(self):
        text = re.sub(r"\s+", " ", self.body or "").strip()
        return (text[:110] + "…") if len(text) > 110 else text


class EmailAttachment(models.Model):
    """ఒక్క Email కి బహుళ ఫైళ్ళు అటాచ్ చేయగలగడానికి ప్రత్యేక మోడల్
    (Email మీద నేరుగా ఒక్క FileField పెడితే ఒక్క ఫైల్ మాత్రమే
    సాధ్యమయ్యేది). Draft దశలో అటాచ్ చేసిన ఫైళ్ళు కూడా ఇక్కడే ఉంటాయి --
    draft ని 'Send' చేసేటప్పుడు కొత్తగా ఏమీ చేయాల్సిన అవసరం లేదు,
    ఇవే ఫైళ్ళు ఇప్పటికే email కి attach అయ్యే ఉన్నాయి."""

    email = models.ForeignKey(
        Email, on_delete=models.CASCADE, related_name="attachments",
    )
    file = models.FileField(
        upload_to="webmail_attachments/%Y/%m/",
        validators=[attachment_extension_validator],
    )
    # అప్‌లోడ్ చేసిన ఫైల్ యొక్క అసలు పేరు విడిగా నిల్వ చేస్తాం --
    # Django, డిస్క్ మీద పేరు collision లు వచ్చినప్పుడు ఫైల్ పేరు కి
    # ఒక ప్రత్యేక suffix జోడిస్తుంది (ఉదా: "resume_a1b2c3.pdf") --
    # UI లో మాత్రం యూజర్ అప్‌లోడ్ చేసిన అసలు పేరే ("resume.pdf")
    # చూపించాలంటే ఇది అవసరం.
    original_filename = models.CharField(max_length=255)
    size_bytes = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.original_filename

    @property
    def human_size(self):
        size = self.size_bytes
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"
