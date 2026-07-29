import random
import string

from django.conf import settings
from django.db import models
from django.utils import timezone


# ------------------------------------------------------------------------
# ఎలా డిజైన్ చేశాం (షార్ట్ నోట్):
# యూజర్ పేరు/పాస్‌వర్డ్/ఇమెయిల్ లాంటి "లాగిన్" డేటాకి Django యొక్క
# బిల్ట్-ఇన్ User మోడల్ (django.contrib.auth.models.User) వాడుతున్నాం —
# ఇది పాస్‌వర్డ్ ని ఎప్పుడూ hash చేసి (PBKDF2 అల్గోరిథం తో) స్టోర్ చేస్తుంది,
# ప్లెయిన్ టెక్స్ట్ లో ఎప్పుడూ సేవ్ చేయదు (ఇదొక ప్రధాన సెక్యూరిటీ నియమం).
# "Employee-only" లేదా "Employer-only" ఫీల్డ్స్ (మొబైల్, DOB, కంపెనీ పేరు
# లాంటివి) కోసం వేర్వేరు Profile మోడల్స్ ని User తో OneToOneField తో
# అనుసంధానం (link) చేస్తున్నాం. దీన్నే Django లో "Profile pattern" అంటారు.
# ------------------------------------------------------------------------


def generate_bharathub_id():
    """
    BharatHub ID ఫార్మాట్ (Candidate/Employee): BHEMP + YY + MM + 6-అంకెల నంబర్
      BHEMP = స్థిర ప్రిఫిక్స్ (Employee)
      YY    = రిజిస్ట్రేషన్ సంవత్సరం చివరి 2 అంకెలు (ఉదా: 2026 → "26")
      MM    = రిజిస్ట్రేషన్ నెల, 2-అంకెలు (ఏప్రిల్ అయితే "04")
      తర్వాత 6 random అంకెలు -- మొత్తం 15 అక్షరాలు (ఉదా: BHEMP2604123456)

    యూనిక్‌నెస్: 6-అంకెల భాగం random గా వస్తుంది కాబట్టి, అదే
    నెలలో ఇద్దరు వేర్వేరు అభ్యర్థులకు కాకతాళీయంగా ఒకే నంబర్ రాకుండా,
    DB లో ఇప్పటికే ఉందేమో చెక్ చేసి మళ్ళీ ప్రయత్నిస్తుంది (20 సార్ల
    వరకు -- 10 లక్షల కాంబినేషన్‌లలో collision వచ్చే అవకాశం చాలా తక్కువే
    అయినా, డేటాబేస్-లెవెల్ unique=True constraint కూడా ఒక అదనపు
    రక్షణ గా ఉంది).
    """
    prefix = f"BHEMP{timezone.now().strftime('%y%m')}"
    for _ in range(20):
        candidate = f"{prefix}{''.join(random.choices(string.digits, k=6))}"
        if not EmployeeProfile.objects.filter(bharathub_id=candidate).exists():
            return candidate
    # అత్యంత అరుదైన fallback (20 సార్లు వరుసగా collision) -- ప్రస్తుత
    # timestamp ఆధారంగా.
    return f"{prefix}{int(timezone.now().timestamp()) % 1000000:06d}"


def generate_employer_id():
    """Employer ID ఫార్మాట్: BHEMR + YY + MM + 6-అంకెల నంబర్ (పైన
    generate_bharathub_id() లో ఉన్న లాజిక్ లాగే, Employer ప్రిఫిక్స్ తో)."""
    prefix = f"BHEMR{timezone.now().strftime('%y%m')}"
    for _ in range(20):
        candidate = f"{prefix}{''.join(random.choices(string.digits, k=6))}"
        if not EmployerProfile.objects.filter(employer_id=candidate).exists():
            return candidate
    return f"{prefix}{int(timezone.now().timestamp()) % 1000000:06d}"


# ------------------------------------------------------------------------
# EmployeeProfile మోడల్
# ఎందుకు: employee_registration.html లోని Step-1 (Personal Details)
# ఫారమ్ లో అడిగే ఫీల్డ్స్ (మొబైల్, DOB, జెండర్, మారిటల్ స్టేటస్,
# తండ్రి/జీవిత భాగస్వామి పేరు, ఫోటో) అన్నీ ఇక్కడ నిల్వ చేస్తాం.
# ఇవి Django యొక్క User మోడల్ లో లేని కస్టమ్ ఫీల్డ్స్ కాబట్టి,
# ఒక ప్రత్యేక "ProfileExtension" మోడల్ గా దీన్ని రాశాం.
# ------------------------------------------------------------------------
class EmployeeProfile(models.Model):

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    class MaritalStatus(models.TextChoices):
        UNMARRIED = "unmarried", "Unmarried"
        MARRIED = "married", "Married"

    # OneToOneField: ప్రతి Django User కి సరిగ్గా ఒక్క EmployeeProfile మాత్రమే
    # ఉంటుంది (ForeignKey వాడితే ఒకే User కి చాలా ప్రొఫైల్స్ వచ్చే ఛాన్స్
    # ఉంటుంది, అది ఇక్కడ అనవసరం). on_delete=CASCADE అంటే User ని డిలీట్
    # చేస్తే, అతని ప్రొఫైల్ కూడా ఆటోమేటిక్‌గా డిలీట్ అవుతుంది (orphan
    # రికార్డులు DB లో మిగలకుండా).
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="employee_profile",
    )

    # BharatHub యూనిక్ ఐడీ — రిజిస్ట్రేషన్ సమయంలో ఆటోమేటిక్‌గా జనరేట్
    # అవుతుంది (default=generate_bharathub_id ఫంక్షన్ కాల్ అవుతుంది).
    # unique=True అంటే రెండు యూజర్లకి ఒకే ID రాకుండా DB లెవెల్ లోనే ఆపుతుంది.
    bharathub_id = models.CharField(
        max_length=16, unique=True, default=generate_bharathub_id, editable=False,
    )

    # మొబైల్ నెంబర్ — భారతదేశ నెంబర్లు ఎప్పుడూ 10 అంకెలు కాబట్టి max_length=10.
    # unique=True: ఒకే మొబైల్ నెంబర్ తో రెండు ఖాతాలు క్రియేట్ కాకుండా ఆపుతుంది.
    mobile_number = models.CharField(max_length=10, unique=True)

    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices)
    marital_status = models.CharField(
        max_length=20, choices=MaritalStatus.choices, default=MaritalStatus.UNMARRIED,
    )

    # తండ్రి పేరు — ఇంతకుముందు మారిటల్ స్టేటస్ ని బట్టి (married అయితే
    # Spouse పేరు, unmarried అయితే Father పేరు) రెండు వేర్వేరు ఫీల్డ్స్
    # ఉండేవి. ఇప్పుడు మారిటల్ స్టేటస్ తో సంబంధం లేకుండా ఎప్పుడూ
    # Father's Name మాత్రమే అడుగుతాం కాబట్టి, spouse_name ఫీల్డ్ ని
    # తీసేసి father_name ని తప్పనిసరి (required) ఫీల్డ్ గా మార్చాం.
    father_name = models.CharField(max_length=150)

    # రిజిస్ట్రేషన్ ని సింపుల్ గా ఉంచడానికి, ప్రొఫైల్ ఫోటో ఇక్కడే
    # (సైన్-అప్ సమయంలో) అడగం -- లాగిన్ అయిన తర్వాత "Complete Your
    # Profile" దశలో నింపుకుంటారు.
    profile_photo = models.ImageField(
        upload_to="employee_photos/%Y/%m/", blank=True, null=True,
    )

    # రిజిస్ట్రేషన్ లో కేవలం ప్రాథమిక వివరాలు మాత్రమే తీసుకుంటాం --
    # స్కిల్స్, రెజ్యూమ్, విద్యార్హతలు (CandidateProfile,
    # CandidateEducation) లాంటివి లాగిన్ అయిన తర్వాతే నింపాలి. ఇది
    # False గా ఉన్నంత వరకూ, ProfileCompletionMiddleware (accounts/
    # middleware.py) డాష్‌బోర్డ్ కి బదులు "Complete Your Profile"
    # పేజీ కే యూజర్ ని పంపిస్తుంది.
    profile_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.bharathub_id})"


# ------------------------------------------------------------------------
# EmployerProfile మోడల్
# ఎందుకు: employer_registration.html లో అడిగే కంపెనీ-సంబంధిత ఫీల్డ్స్
# (కంపెనీ పేరు, PAN, GST, CIN, ఇండస్ట్రీ సెక్టార్, HQ రాష్ట్రం) ఇక్కడ
# నిల్వ చేస్తాం.
# ------------------------------------------------------------------------
class EmployerProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="employer_profile",
    )

    employer_id = models.CharField(
        max_length=16, unique=True, default=generate_employer_id, editable=False,
    )

    company_name = models.CharField(max_length=200)

    # రిజిస్ట్రేషన్ ని సింపుల్ గా ఉంచడానికి కొత్తగా జోడించిన ఫీల్డ్స్
    # (ఇంతకుముందు ఇవి registration ఫారమ్ లో లేవు):
    class CompanyType(models.TextChoices):
        PRIVATE_LTD = "private_ltd", "Private Limited"
        PUBLIC_LTD = "public_ltd", "Public Limited"
        PARTNERSHIP = "partnership", "Partnership"
        PROPRIETORSHIP = "proprietorship", "Sole Proprietorship"
        LLP = "llp", "LLP"
        OTHER = "other", "Other"

    company_type = models.CharField(
        max_length=20, choices=CompanyType.choices, blank=True,
    )
    contact_person = models.CharField(
        max_length=150, blank=True,
        help_text="HR / primary point of contact name",
    )
    mobile_number = models.CharField(max_length=10, blank=True)
    address = models.TextField(blank=True)
    other_branch_location = models.TextField(
        blank=True, help_text="Other branch locations (if any, optional)",
    )

    # కార్పొరేట్ ఇమెయిల్ ప్రత్యేకంగా ఉంచాం (User.email తో పాటు) ఎందుకంటే
    # ఇది "కంపెనీ" కి సంబంధించిన అధికారిక ఇమెయిల్ కావొచ్చు, లాగిన్
    # ఇమెయిల్ వేరే ఉండొచ్చు.
    corporate_email = models.EmailField()

    # PAN నెంబర్ ఫార్మాట్ ఎప్పుడూ 10 క్యారెక్టర్లు (ఉదా: ABCDE1234F).
    # blank=True: ఇది ఇక రిజిస్ట్రేషన్ లో అడగం -- "Complete Your
    # Profile" దశలో నింపుకోవచ్చు.
    pan_number = models.CharField(max_length=10, blank=True)

    # GST నెంబర్ ఫార్మాట్ ఎప్పుడూ 15 క్యారెక్టర్లు
    gst_number = models.CharField(max_length=15, blank=True)

    # CIN (Corporate Identification Number) — కంపెనీలకు మాత్రమే ఉంటుంది,
    # సోల్ ప్రొప్రైటర్‌షిప్ లాంటి వాటికి ఉండకపోవచ్చు కాబట్టి blank=True.
    cin_number = models.CharField(max_length=21, blank=True)

    industry_sector = models.CharField(max_length=100, blank=True)
    hq_state = models.CharField(max_length=100, blank=True)

    # Employee (candidate) కి profile_photo, Vendor కి shop_photo ఉన్నట్టే,
    # Employer కి company logo -- messaging/permissions.py లోని
    # avatar_url_for() చాట్ UI లో ఈ కంపెనీ తరపున ఇదే చూపిస్తుంది,
    # లేకపోతే కంపెనీ పేరు మొదటి 2 అక్షరాల initials చూపిస్తుంది
    # (employers/_nav.html లో ఇప్పటికే ఉన్న fallback).
    company_logo = models.ImageField(
        upload_to="employer_logos/%Y/%m/", blank=True, null=True,
    )

    # ఇది False గా ఉన్నంత వరకూ (అంటే PAN/GST/CIN/HQ వంటి మిగతా కంపెనీ
    # వివరాలు ఇంకా నింపలేదు), ProfileCompletionMiddleware డాష్‌బోర్డ్
    # కి బదులు "Complete Your Profile" పేజీ కే పంపిస్తుంది.
    profile_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_name} ({self.employer_id})"


# ============================================================================
# LoginSecurity
#
# ఎందుకు ఇది కావాలి: ఇంతకుముందు failed-login-attempt కౌంట్ Django
# cache (accounts/login_throttle.py) లో, (IP + login_id) కీ తో
# స్టోర్ అయ్యేది -- అంటే 15 నిమిషాలు ఆగితే, లేదా వేరే IP/network
# (ఉదా: WiFi నుండి mobile data కి మారితే) కౌంట్ రీసెట్ అయిపోయేది.
# ఇది నిజమైన brute-force ప్రొటెక్షన్ కాదు -- దాడి చేసేవాడు IP మార్చుకుని
# లేదా 15 నిమిషాలు ఆగి మళ్ళీ ప్రయత్నించొచ్చు.
#
# ఇప్పుడు ఈ కౌంటర్ ఖాతా (User) కే శాశ్వతంగా (DB లో) అటాచ్ అయి ఉంటుంది --
# IP మారినా, browser మారినా, ఎన్ని నిమిషాలు ఆగినా కౌంట్ అలాగే ఉంటుంది.
# మూడు తప్పు ప్రయత్నాల తర్వాత must_reset_password=True అవుతుంది --
# ఆ తర్వాత సరైన పాస్‌వర్డ్ ఇచ్చినా కూడా లాగిన్ కానివ్వం; అకౌంట్
# పాస్‌వర్డ్ రీసెట్ (Forgot Password ఫ్లో) పూర్తి చేసుకుంటేనే
# must_reset_password మళ్ళీ False అవుతుంది (login_throttle.py లోని
# clear_lock_after_reset() చూడండి).
# ============================================================================
class LoginSecurity(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="login_security",
    )
    failed_attempts = models.PositiveSmallIntegerField(default=0)

    # True అయితే -- పాస్‌వర్డ్ సరైనదైనా సరే, login view ఈ యూజర్ ని
    # లోపలికి రానివ్వదు, తప్పనిసరిగా Forgot-Password ఫ్లో ద్వారా
    # కొత్త పాస్‌వర్డ్ సెట్ చేసుకోవాలి.
    must_reset_password = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        state = "🔒 MUST RESET" if self.must_reset_password else f"{self.failed_attempts} failed"
        return f"{self.user.username} — {state}"
