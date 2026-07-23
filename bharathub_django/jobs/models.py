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
