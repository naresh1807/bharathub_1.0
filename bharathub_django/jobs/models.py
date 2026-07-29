from django.db import models

from candidates.models import CandidateProfile
from employers.models import Job

# ============================================================================
# jobs/models.py
#
# ఎందుకు: Job model (job posting) ఇప్పటికే employers app లో ఉంది --
# ఒక్క EmployerProfile చాలా Jobs పోస్ట్ చేయొచ్చు కాబట్టి అది అక్కడే
# ఉండాలి (employer.jobs.all() లాంటి natural query కోసం). ఇక్కడ jobs
# app లో మనం "ఒక candidate ఒక Job కి apply చేశాడు" అనే relationship
# ని మాత్రమే మోడల్ చేస్తున్నాం -- ఇది Job మరియు CandidateProfile
# రెండిటినీ కలిపే "join model" (many-to-many with extra fields:
# status, cover_note, applied_at).
# ============================================================================


class JobApplication(models.Model):
    """ఒక candidate, ఒక Job కి apply చేసిన రికార్డు. employer యొక్క
    'Applications Received' పేజీ, candidate యొక్క 'My Applications'
    పేజీ -- రెండూ ఇదే మోడల్ నుండి డేటా తీసుకుంటాయి (ఒక్కటే source of
    truth, డూప్లికేషన్ లేదు)."""

    class Status(models.TextChoices):
        NEW = "new", "🆕 New"
        REVIEW = "review", "👁️ Under Review"
        SHORTLISTED = "shortlisted", "✅ Shortlisted"
        INTERVIEW = "interview", "📅 Interview"
        OFFERED = "offered", "📧 Offer Sent"
        HIRED = "hired", "✅ Hired"
        REJECTED = "rejected", "❌ Rejected"

    job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="applications",
    )
    candidate = models.ForeignKey(
        CandidateProfile, on_delete=models.CASCADE, related_name="applications",
    )

    # apply చేసేటప్పుడు candidate రాసే ఐచ్ఛిక సందేశం (cover note).
    cover_note = models.TextField(max_length=1000, blank=True)

    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.NEW,
    )

    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ఇంతకుముందు "Interview" బటన్ కేవలం status ని "interview" గా
    # మార్చేది -- ఎప్పుడు, ఎలా (video/phone/in-person), ఎక్కడ అనే
    # వివరాలు ఎక్కడా నిల్వ ఉండేవి కావు, కాబట్టి candidate కి కేవలం
    # "Interview" అనే బ్యాడ్జ్ మాత్రమే కనిపించేది, తేదీ/సమయం కాదు.
    # ఇప్పుడు ఆ వివరాలు ఇక్కడ నిల్వ ఉంటాయి.
    class InterviewMode(models.TextChoices):
        VIDEO = "video", "🎥 Video Call"
        PHONE = "phone", "📞 Phone Call"
        IN_PERSON = "in_person", "🏢 In-Person"

    interview_datetime = models.DateTimeField(null=True, blank=True)
    interview_mode = models.CharField(
        max_length=15, choices=InterviewMode.choices, blank=True,
    )
    interview_location = models.CharField(
        max_length=300, blank=True,
        help_text="Video call link, phone number, or office address",
    )
    interview_notes = models.TextField(max_length=500, blank=True)

    class Meta:
        ordering = ["-applied_at"]
        # ఒక candidate అదే job కి రెండుసార్లు apply చేయకుండా DB
        # లెవెల్ లోనే ఆపుతుంది (duplicate-apply guard) -- ఇది కేవలం
        # UX సౌలభ్యం మాత్రమే కాదు, race-condition (రెండు tabs లో ఒకేసారి
        # apply నొక్కినా) నుండి కూడా కాపాడుతుంది.
        constraints = [
            models.UniqueConstraint(
                fields=["job", "candidate"], name="unique_application_per_job",
            ),
        ]

    def __str__(self):
        return f"{self.candidate} → {self.job.title} ({self.status})"


# ══════════════════════════════════════════════════════════════════════
# Employment
#
# Employer, ఒక JobApplication ని "Hired" గా మార్క్ చేసినప్పుడు (అంతకుముందు
# status "offered" గా ఉండాలి) ఇక్కడ ఒక్క నిజమైన Employment రికార్డు
# క్రియేట్ అవుతుంది -- ఇదే CandidateProfile.hire_status లైఫ్‌సైకిల్ ని
# నడిపిస్తుంది:
#
#   Hired  → candidate.hire_status = HIRED (కొత్త job offers/hire
#            requests ఇక ఆగిపోతాయి -- jobs/views.py, employers/views.py
#            చూడండి)
#   Resign → candidate "Resign" నొక్కితే status = RESIGNATION_REQUESTED
#            (ఇంకా HIRED గానే ఉంటారు, employer approve చేసేదాకా)
#   Accept → Employer resignation accept చేస్తే status = RELIEVED,
#            relieving_date సెట్ అవుతుంది, candidate.hire_status మళ్ళీ
#            AVAILABLE కి మారుతుంది (ఇప్పుడు మళ్ళీ job offers కనిపిస్తాయి)
#
# ఒక్కసారి RELIEVED అయ్యాక, ఈ రికార్డులోని joining_date/relieving_date/
# designation డేటా తోనే candidates/views.py: DownloadsListView లో
# Joining/Relieving/Experience Letter లు ఆటోమేటిక్‌గా అందుబాటులోకి వస్తాయి.
# ══════════════════════════════════════════════════════════════════════
class Employment(models.Model):
    """ఒక candidate ని ఒక Employer నిజంగా hire చేసిన రికార్డు."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RESIGNATION_REQUESTED = "resignation_requested", "Resignation Requested"
        RELIEVED = "relieved", "Relieved"

    # Offer Letter -- Employer 'Mark as Hired' నొక్కిన వెంటనే ఆటోమేటిక్‌గా
    # జనరేట్ అయ్యి, candidate యొక్క Downloads లో కనిపిస్తుంది (PENDING).
    # candidate దాన్ని 'Accept Offer' నొక్కి Accept చేస్తే ACCEPTED అవుతుంది
    # -- అప్పుడు employer కి నోటిఫికేషన్ ఇమెయిల్ వెళ్తుంది (jobs/views.py:
    # OfferLetterAcceptView, jobs/notifications.py చూడండి).
    class OfferStatus(models.TextChoices):
        PENDING = "pending", "Pending Acceptance"
        ACCEPTED = "accepted", "Accepted"

    candidate = models.ForeignKey(
        CandidateProfile, on_delete=models.CASCADE, related_name="employments",
    )
    # ఏ application ద్వారా hire అయ్యారో -- దీని job/employer నుండే
    # designation/company వివరాలు తీసుకుంటాం (డూప్లికేట్ ఫీల్డ్స్
    # అవసరం లేదు). OneToOneField: ఒక్క application కి ఒక్కటే
    # Employment (డూప్లికేట్ hire రికార్డులు రాకుండా).
    application = models.OneToOneField(
        JobApplication, on_delete=models.CASCADE, related_name="employment",
    )

    designation = models.CharField(max_length=150)  # hire చేసిన సమయంలో job.title యొక్క స్నాప్‌షాట్
    joining_date = models.DateField()
    # ఈ employee కి నిజంగా ఇస్తున్న జీతం -- job.salary_min/max (పోస్టింగ్
    # రేంజ్) కాదు, ఖచ్చితమైన అంకె. Employer 'Mark as Hired' ఫారమ్‌లో
    # దీన్ని ఎంటర్ చేస్తారు (jobs/views.py: MarkAsHiredView). "My Hires"
    # పేజీలో ఎంప్లాయీ డైరెక్టరీ కోసం ఇదే వాడతాం.
    salary_lpa = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Salary (LPA)")

    status = models.CharField(max_length=25, choices=Status.choices, default=Status.ACTIVE)
    resignation_requested_at = models.DateTimeField(null=True, blank=True)
    relieving_date = models.DateField(null=True, blank=True)

    offer_status = models.CharField(
        max_length=15, choices=OfferStatus.choices, default=OfferStatus.PENDING,
    )
    offer_accepted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.candidate} @ {self.employer.company_name} ({self.status})"

    @property
    def employer(self):
        return self.application.job.employer

    @property
    def job(self):
        return self.application.job
