from django.db import models

from accounts.models import EmployerProfile

# ============================================================================
# employers/models.py
# ఎందుకు: employer_dashboard.html లోని "Post a Job" ఫారమ్ (ఇంతకుముందు
# JS-only మాక్ -- postJob() కేవలం alert() చూపించి, ఏదీ సేవ్ చేసేది కాదు)
# ఇప్పుడు నిజంగా DB లో save అవ్వాలంటే, ముందు ఈ డేటాకి ఒక Model కావాలి.
# ప్రతి Job ఒక EmployerProfile కి చెందుతుంది (ForeignKey) -- ఒక Employer
# చాలా Jobs పోస్ట్ చేయొచ్చు కాబట్టి ForeignKey వాడాం (OneToOne కాదు).
# ============================================================================


class Job(models.Model):
    """ఒక్క ఉద్యోగ ప్రకటన (job posting). employer_dashboard.html లోని
    "Post a Job" ఫారమ్ లో ఉన్న ప్రతి ఫీల్డ్ కీ ఇక్కడ ఒక మోడల్ ఫీల్డ్
    ఉంది -- కాబట్టి forms.py లో దీని ఆధారంగా నేరుగా ModelForm రాయొచ్చు."""

    # ------------------------------------------------------------------
    # TextChoices: డ్రాప్‌డౌన్ (<select>) ఆప్షన్స్ ని ఇక్కడ ఒక్కసారే
    # డిఫైన్ చేసి, model ఫీల్డ్ లోనూ, ModelForm లోనూ (ఆటోమేటిక్‌గా)
    # ఒకే చోటనుండి వాడతాం -- HTML లో <option> లు వేరేగా, model లో
    # choices వేరేగా రాస్తే, రెండూ sync లో లేకపోతే "invalid choice"
    # ఎర్రర్స్ వస్తాయి. TextChoices వాడితే ఆ సమస్యే ఉండదు.
    # ------------------------------------------------------------------
    class Department(models.TextChoices):
        ENGINEERING = "engineering", "Engineering / Technology"
        FINANCE = "finance", "Finance & Accounts"
        MARKETING = "marketing", "Marketing"
        HR = "hr", "HR & Recruitment"
        SALES = "sales", "Sales"
        OPERATIONS = "operations", "Operations"
        DESIGN = "design", "Design"

    class JobType(models.TextChoices):
        FULL_TIME = "full_time", "Full Time"
        PART_TIME = "part_time", "Part Time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"
        REMOTE = "remote", "Remote"
        HYBRID = "hybrid", "Hybrid"

    class ExperienceLevel(models.TextChoices):
        FRESHER = "fresher", "Fresher (0-1 year)"
        JUNIOR = "junior", "Junior (1-3 years)"
        MID = "mid", "Mid (3-5 years)"
        SENIOR = "senior", "Senior (5-8 years)"
        LEAD = "lead", "Lead (8+ years)"

    class Qualification(models.TextChoices):
        ANY_GRADUATE = "any_graduate", "Any Graduate"
        BTECH = "btech", "B.Tech / BE"
        MTECH = "mtech", "MCA / M.Tech"
        BCA_BSC = "bca_bsc", "BCA / B.Sc"
        MBA = "mba", "MBA"
        ANY_PG = "any_pg", "Any PG"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    # ఏ కంపెనీ ఈ జాబ్ పోస్ట్ చేసిందో -- ForeignKey (OneToOne కాదు),
    # ఎందుకంటే ఒక్క EmployerProfile చాలా Job లు పోస్ట్ చేయొచ్చు.
    # on_delete=CASCADE: కంపెనీ ఖాతా డిలీట్ అయితే, దాని జాబ్ పోస్టులు
    # కూడా ఆటోమేటిక్‌గా తొలగిపోతాయి (orphan రికార్డులు మిగలవు).
    employer = models.ForeignKey(
        EmployerProfile, on_delete=models.CASCADE, related_name="jobs",
    )

    title = models.CharField(max_length=150)
    department = models.CharField(
        max_length=20, choices=Department.choices, blank=True,
    )
    job_type = models.CharField(
        max_length=20, choices=JobType.choices, default=JobType.FULL_TIME,
    )
    experience_level = models.CharField(
        max_length=20, choices=ExperienceLevel.choices, blank=True,
    )
    location = models.CharField(max_length=150)

    # జీతం "min-max" గా ఇస్తారు కాబట్టి రెండు వేర్వేరు ఫీల్డ్స్
    # (ఉదా: 8 to 12 LPA). null=True + blank=True: రెండూ optional
    # (కంపెనీ జీతం బహిరంగంగా చెప్పకపోవచ్చు).
    salary_min = models.PositiveIntegerField(
        null=True, blank=True, help_text="Minimum salary in LPA",
    )
    salary_max = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum salary in LPA",
    )

    description = models.TextField()

    # స్కిల్ ట్యాగ్స్ ని (Python, Django, MySQL ...) ఒక్కో ప్రత్యేక
    # మోడల్‌గా చేయకుండా, కామా-సెపరేటెడ్ టెక్స్ట్ గా సింపుల్‌గా
    # స్టోర్ చేస్తున్నాం (ప్రస్తుతానికి ఇది సరిపోతుంది -- ప్రత్యేక Skill
    # మోడల్ + M2M వాడటం over-engineering అవుతుంది ఈ దశలో).
    skills_required = models.CharField(
        max_length=500, help_text="Comma-separated, e.g. 'Python, Django, MySQL'",
    )

    application_deadline = models.DateField(null=True, blank=True)
    openings_count = models.PositiveIntegerField(default=1)
    qualification = models.CharField(
        max_length=20, choices=Qualification.choices, blank=True,
    )

    # DRAFT గా సేవ్ చేయొచ్చు ("Save as Draft" బటన్) లేదా వెంటనే ACTIVE
    # గా పబ్లిష్ చేయొచ్చు ("Post Job Now" బటన్) -- views.py లో ఏ బటన్
    # నొక్కారో బట్టి ఈ ఫీల్డ్ సెట్ చేస్తాం.
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} @ {self.employer.company_name}"

    def skills_list(self):
        """టెంప్లేట్ లో {% for skill in job.skills_list %} అని లూప్
        చేయడానికి -- "Python, Django, MySQL" అనే స్ట్రింగ్ ని
        ['Python', 'Django', 'MySQL'] అనే లిస్ట్ గా విడగొడుతుంది."""
        return [s.strip() for s in self.skills_required.split(",") if s.strip()]

    def salary_display(self):
        """టెంప్లేట్ లో చూపించడానికి '₹8-12 LPA' లాంటి రెడీమేడ్ స్ట్రింగ్."""
        if self.salary_min and self.salary_max:
            return f"₹{self.salary_min}-{self.salary_max} LPA"
        if self.salary_min:
            return f"₹{self.salary_min}+ LPA"
        return "Not disclosed"


class HireRequest(models.Model):
    """
    ఒక Employer, candidate-search ద్వారా దొరికిన ఒక candidate ని
    (ఆ candidate ఏ job కి apply చేయకపోయినా) నేరుగా సంప్రదించి,
    "మీరు మా దగ్గర ఈ job కి పనికొస్తారు, ఆసక్తి ఉందా?" అని
    ఇన్విటేషన్ పంపడానికి ఉపయోగపడే మోడల్.

    ఇది JobApplication కి రివర్స్ -- JobApplication లో candidate
    ముందుగా apply చేస్తాడు; HireRequest లో employer ముందుగా
    సంప్రదిస్తాడు (headhunting/recruiter-search తరహా).

    ముఖ్యం: ఈ రికార్డ్ ఉందంటే, ఆ Employer-Candidate జంట మధ్య ఇక
    చాట్ చేసుకోగలరు (messaging/permissions.py: can_message() ఈ
    మోడల్ ని కూడా ఒక "చెల్లుబాటు అయ్యే వ్యాపార సంబంధం" గా
    గుర్తిస్తుంది -- JobApplication మాదిరిగానే).
    """

    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        VIEWED = "viewed", "Viewed by candidate"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    employer = models.ForeignKey(
        "accounts.EmployerProfile", on_delete=models.CASCADE, related_name="hire_requests_sent",
    )
    candidate = models.ForeignKey(
        "candidates.CandidateProfile", on_delete=models.CASCADE, related_name="hire_requests_received",
    )
    # ఏ job కోసం ఈ ఇన్విటేషన్ (ఐచ్ఛికం -- ఖాళీగా ఉంటే "సాధారణ ఆసక్తి"
    # అని అర్థం, ఏదో ఒక ప్రత్యేక job ప్రస్తావించకుండా).
    job = models.ForeignKey(
        Job, on_delete=models.SET_NULL, null=True, blank=True, related_name="hire_requests",
    )
    message = models.TextField(max_length=1000, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SENT)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        # ఒకే employer, ఒకే candidate కి, ఒకే job కోసం రెండుసార్లు
        # రిక్వెస్ట్ పంపకుండా (job=None ఉన్నవి కూడా dedupe అవుతాయి --
        # SQL లో NULL ఎప్పుడూ దేనికీ సమానం కాదు కాబట్టి, "సాధారణ
        # ఆసక్తి" రిక్వెస్ట్ ఒకటి కంటే ఎక్కువ పంపే అవకాశం ఇప్పటికీ
        # ఉంది -- అది views.py లో get_or_create తో నిరోధిస్తాం).
        constraints = [
            models.UniqueConstraint(
                fields=["employer", "candidate", "job"], name="unique_hire_request_per_job",
            ),
        ]

    def __str__(self):
        return f"{self.employer.company_name} → {self.candidate} ({self.get_status_display()})"
