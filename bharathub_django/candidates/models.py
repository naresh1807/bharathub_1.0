import datetime

from django.conf import settings
from django.core.validators import (
    FileExtensionValidator, MaxValueValidator, MinValueValidator,
)
from django.db import models


# ══════════════════════════════════════════════════════════════════════
# candidates/models.py
#
# ఎందుకు ఇలా డిజైన్ చేశాం (షార్ట్ నోట్ -- accounts/models.py లో వాడిన
# పద్ధతినే ఇక్కడ కూడా అనుసరిస్తున్నాం):
#   - "లాగిన్" డేటా (username/email/password) కోసం Django బిల్ట్-ఇన్
#     User మోడల్ ని వాడతాం (settings.AUTH_USER_MODEL) -- పాస్‌వర్డ్
#     ఎప్పుడూ hash చేసే బాధ్యత Django తీసుకుంటుంది, మనం ఎప్పుడూ దాన్ని
#     ఇక్కడ మళ్ళీ implement చేయము.
#   - "candidates" యాప్ కి సంబంధించిన wob-seeker-only ఫీల్డ్స్ (స్కిల్స్,
#     రెజ్యూమ్, expected CTC, hire-status వంటివి) కోసం ఒక ప్రత్యేక
#     CandidateProfile మోడల్ (Profile pattern) -- User తో
#     OneToOneField తో లింక్ చేస్తున్నాం, తద్వారా ప్రతి యూజర్ కి
#     ఒక్కటే ప్రొఫైల్ ఉంటుంది (డూప్లికేట్ ప్రొఫైల్స్ DB లెవెల్ లోనే
#     ఆగిపోతాయి).
#   - విద్యార్హతలు (Academic History) ఒక్కో candidate కి చాలా ఉండొచ్చు
#     (SSC, Inter, Degree, PG...) కాబట్టి వాటిని వేరే మోడల్
#     (CandidateEducation) లో ForeignKey తో నిల్వ చేస్తున్నాం
#     (ఒక ప్రొఫైల్ -> చాలా ఎడ్యుకేషన్ రికార్డులు).
# ══════════════════════════════════════════════════════════════════════


def current_year():
    return datetime.date.today().year


# ఫైల్ అప్‌లోడ్స్ (రెజ్యూమ్) కోసం extension allow-list.
# సెక్యూరిటీ ఎందుకు ముఖ్యం: ఏ ఫైల్ టైప్ అయినా అప్‌లోడ్ చేయడానికి
# అనుమతిస్తే, ఎవరైనా .php/.exe/.html ఫైల్ ని రెజ్యూమ్ అని పేరు పెట్టి
# అప్‌లోడ్ చేసి, తర్వాత ఆ ఫైల్ ని ఎగ్జిక్యూట్ చేయించే ప్రయత్నం
# చేయొచ్చు (అన్‌రిస్ట్రిక్టెడ్ ఫైల్ అప్‌లోడ్ దాడి). కాబట్టి Django
# యొక్క FileExtensionValidator తో కేవలం రెజ్యూమ్ కి తగిన
# ఫార్మాట్‌లనే అనుమతిస్తున్నాం. (ఇది forms.py లోని clean_resume()
# లో సైజ్ చెక్ తో పాటు రెండో పొర రక్షణ.)
resume_extension_validator = FileExtensionValidator(
    allowed_extensions=["pdf", "doc", "docx"],
    message="Resume must be uploaded in PDF, DOC, or DOCX format only.",
)


class CandidateProfile(models.Model):
    """
    ఒక్కో job-seeker (candidate) కి సంబంధించిన ప్రొఫెషనల్ ప్రొఫైల్
    వివరాలు -- candidate_dashboard.html లోని "Profile Management"
    సెక్షన్ లో చూపించే డేటా ఇక్కడి నుండే వస్తుంది.
    """

    class ExperienceLevel(models.TextChoices):
        FRESHER = "fresher", "Fresher"
        JUNIOR = "0_2", "0-2 Years"
        MID = "2_5", "2-5 Years"
        SENIOR = "5_10", "5-10 Years"
        EXPERT = "10_plus", "10+ Years"

    class HireStatus(models.TextChoices):
        AVAILABLE = "available", "🟢 For Hire"
        HIRED = "hired", "🔴 Hired"
        NOT_LOOKING = "not_looking", "⏸️ Not Looking"

    # OneToOneField: ప్రతి User కి ఒక్కటే CandidateProfile ఉండేలా DB
    # లెవెల్ లోనే హామీ ఇస్తుంది (UNIQUE constraint) -- ఇద్దరు వేర్వేరు
    # candidates ఒకే ప్రొఫైల్ రికార్డ్ ని పంచుకునే అవకాశం ఉండదు.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="candidate_profile",
    )

    headline = models.CharField(
        max_length=150, blank=True,
        help_text="e.g. Python Developer · Fresher",
    )
    location = models.CharField(max_length=100, blank=True)
    about = models.TextField(
        max_length=1000, blank=True, verbose_name="About / Bio",
    )

    # కామా-సెపరేటెడ్ స్కిల్స్ ఒకే CharField లో నిల్వ చేస్తున్నాం (సింపుల్
    # design) -- forms.py లోని clean_skills() వీటిని ట్రిమ్ చేసి,
    # డూప్లికేట్లు తీసేసి, ఒక క్రమపద్ధతిలో మళ్ళీ జాయిన్ చేస్తుంది.
    skills = models.CharField(max_length=400, blank=True)

    qualification = models.CharField(
        max_length=150, blank=True,
        help_text="Highest qualification, e.g. B.Tech CSE",
    )
    experience_level = models.CharField(
        max_length=10, choices=ExperienceLevel.choices,
        default=ExperienceLevel.FRESHER,
    )

    # CTC విలువలు -- ఐచ్ఛికం (candidate దాచిపెట్టాలనుకోవచ్చు).
    current_ctc_lpa = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True,
        verbose_name="Current CTC (LPA)",
    )
    expected_ctc_lpa = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True,
        verbose_name="Expected CTC (LPA)",
    )

    hire_status = models.CharField(
        max_length=15, choices=HireStatus.choices, default=HireStatus.AVAILABLE,
    )

    # రెజ్యూమ్ ఫైల్ -- extension allow-list వాలిడేటర్ తో పాటు, ప్రతి
    # అప్‌లోడ్ ఒక సంవత్సరం/నెల సబ్‌ఫోల్డర్ లోకి వెళ్తుంది (upload_to)
    # -- ఒకే ఫోల్డర్ లో వేల ఫైళ్ళు పేరుకుపోకుండా.
    resume = models.FileField(
        upload_to="candidate_resumes/%Y/%m/", blank=True, null=True,
        validators=[resume_extension_validator],
    )

    # ImageField (FileField కాదు) వాడటం వల్ల Django + Pillow కలిసి
    # అప్‌లోడ్ అయిన ఫైల్ నిజంగా చెల్లుబాటు అయ్యే ఇమేజ్ (బైట్-లెవెల్)
    # అవునా కాదా అని పరిశీలిస్తాయి -- కేవలం ఫైల్ పేరు మార్చి (.jpg
    # అని) వేరే హానికరమైన ఫైల్ అప్‌లోడ్ చేసే ప్రయత్నాన్ని ఇది ఆపుతుంది.
    profile_photo = models.ImageField(
        upload_to="candidate_photos/%Y/%m/", blank=True, null=True,
    )

    linkedin_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} — Candidate Profile"

    @property
    def skills_list(self):
        """టెంప్లేట్ లో స్కిల్ చిప్స్ గా చూపించడానికి సులువైన హెల్పర్."""
        return [s.strip() for s in self.skills.split(",") if s.strip()]


class CandidateEducation(models.Model):
    """
    ఒక్కో CandidateProfile కి బహుళ (multiple) విద్యార్హత రికార్డులు --
    ఫారెన్ కీ రిలేషన్ ద్వారా (ఒక ప్రొఫైల్ -> చాలా ఎడ్యుకేషన్
    ఎంట్రీలు). candidate_dashboard.html లోని "Academic History"
    కార్డు ఇక్కడి డేటా ఆధారంగానే నింపొచ్చు.
    """

    class Level(models.TextChoices):
        SSC = "ssc", "SSC / 10th"
        INTERMEDIATE = "intermediate", "Intermediate / 12th"
        GRADUATION = "graduation", "Graduation"
        POST_GRADUATION = "post_graduation", "Post Graduation"
        OTHER = "other", "Other"

    profile = models.ForeignKey(
        CandidateProfile, on_delete=models.CASCADE,
        related_name="education_entries",
    )
    level = models.CharField(max_length=20, choices=Level.choices)
    degree_title = models.CharField(
        max_length=150, verbose_name="Degree / Course Title",
        help_text="e.g. B.Tech Computer Science",
    )
    institution = models.CharField(max_length=200)

    # 1950 - ప్రస్తుత సంవత్సరం మధ్యలోనే ఉండాలి అని సర్వర్ సైడ్ లో
    # (MinValueValidator/MaxValueValidator) కూడా బలవంతం చేస్తున్నాం --
    # కేవలం HTML `max` attribute మాత్రమే ఆధారపడితే, యూజర్ దాన్ని
    # బ్రౌజర్ dev-tools తో బైపాస్ చేయొచ్చు.
    year_of_passing = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1950), MaxValueValidator(current_year)],
    )
    score = models.CharField(
        max_length=30, blank=True,
        help_text="e.g. 7.8 CGPA or 89%",
    )

    class Meta:
        ordering = ["-year_of_passing"]

    def __str__(self):
        return f"{self.degree_title} ({self.year_of_passing})"
