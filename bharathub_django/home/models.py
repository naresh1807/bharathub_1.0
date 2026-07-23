from django.db import models


# ----------------------------------------------------------------------
# ContactMessage మోడల్
# ఎందుకు: "Contact Us" పేజీలో యూజర్ పంపే ప్రతి మెసేజ్ ని డేటాబేస్ లో
#         శాశ్వతంగా (permanently) సేవ్ చేయడానికి ఈ మోడల్ ఉపయోగపడుతుంది.
#         ఇంతకు ముందు ఈ ఫారమ్ కేవలం JavaScript (contact.js) లో మాత్రమే
#         "success" మెసేజ్ చూపించేది — డేటా ఎక్కడికీ వెళ్లేది కాదు.
#         ఇప్పుడు ఇది నిజంగా సర్వర్ కి POST అయ్యి, DB లో స్టోర్ అవుతుంది.
# ----------------------------------------------------------------------
class ContactMessage(models.Model):

    # యూజర్ "నేను ఎవరు" అని ఎంచుకునే ఆప్షన్లు (Job Seeker / Employer / Vendor / Other)
    # choices tuple వాడటం వలన DB లో ఎప్పుడూ ఈ 4 విలువల్లో ఒకటే స్టోర్ అవుతుంది,
    # random / తప్పుడు టెక్స్ట్ రాకుండా validation జరుగుతుంది.
    class SenderType(models.TextChoices):
        EMPLOYEE = "employee", "Job Seeker / Employee"
        EMPLOYER = "employer", "Employer / HR"
        VENDOR = "vendor", "Vendor / Business"
        OTHER = "other", "Other"

    # ఫారమ్ లో ఉన్న సబ్జెక్ట్ డ్రాప్‌డౌన్ ఆప్షన్లు
    class SubjectChoice(models.TextChoices):
        REGISTRATION_HELP = "registration_help", "Account Registration Help"
        LOGIN_OTP_ISSUE = "login_otp_issue", "Login / OTP Issue"
        JOB_APPLICATION = "job_application", "Job Application Query"
        EMPLOYER_POSTING = "employer_posting", "Employer / Job Posting"
        VENDOR_MARKETPLACE = "vendor_marketplace", "Vendor / Marketplace"
        PRIVACY_REQUEST = "privacy_request", "Privacy / Data Request"
        FAKE_PROFILE = "fake_profile", "Report Fake Profile"
        OTHER = "other", "Other"

    # పంపిన వ్యక్తి పేరు — ఖాళీగా ఉండకూడదు కాబట్టి blank=False (default)
    name = models.CharField(max_length=150)

    # ఇమెయిల్ — EmailField వాడితే Django దానంతట అదే "వ్యాలిడ్ ఇమెయిల్ ఫార్మాట్"
    # (example@domain.com వంటిది) కాదా అని సర్వర్ సైడ్ లో చెక్ చేస్తుంది.
    email = models.EmailField()

    # యూజర్ టైప్ (Employee/Employer/Vendor/Other)
    sender_type = models.CharField(max_length=20, choices=SenderType.choices)

    # సబ్జెక్ట్ డ్రాప్‌డౌన్ విలువ
    subject = models.CharField(max_length=30, choices=SubjectChoice.choices)

    # అసలు మెసేజ్ టెక్స్ట్ — పొడవుగా ఉండొచ్చు కాబట్టి TextField (CharField కాదు)
    message = models.TextField()

    # ఈ మెసేజ్ ఎప్పుడు వచ్చిందో — auto_now_add=True అంటే Row create
    # అయిన క్షణంలోనే Django ఆటోమేటిక్‌గా టైమ్‌స్టాంప్ నింపేస్తుంది,
    # మనం మాన్యువల్‌గా టైమ్ పంపాల్సిన అవసరం లేదు (తప్పుడు టైమ్ పంపే ఛాన్స్ ఉండదు).
    created_at = models.DateTimeField(auto_now_add=True)

    # అడ్మిన్ ఈ మెసేజ్ ని చదివి రిప్లై ఇచ్చాడా లేదా అని ట్రాక్ చేయడానికి
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]  # కొత్త మెసేజ్‌లు ముందు కనిపించేలా

    # __str__ : Django admin లో లేదా shell లో ఈ ఆబ్జెక్ట్ ని print చేసినప్పుడు
    # "ContactMessage object (1)" అని కాకుండా అర్థమయ్యే టెక్స్ట్ చూపించడానికి.
    def __str__(self):
        return f"{self.name} <{self.email}> — {self.get_subject_display()}"
