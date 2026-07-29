from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from .models import EmployeeProfile, EmployerProfile

User = get_user_model()


# భారతదేశ మొబైల్ నెంబర్ ఫార్మాట్ చెక్ చేయడానికి (10 అంకెలు, 6-9 తో మొదలవ్వాలి).
# RegexValidator ని ఒక్కసారి రాసి, ఎన్ని ఫారమ్‌లలో అయినా తిరిగి వాడొచ్చు.
mobile_validator = RegexValidator(
    regex=r"^[6-9]\d{9}$",
    message="Please enter a valid 10-digit Indian mobile number (must start with 6-9).",
)

pan_validator = RegexValidator(
    regex=r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$",
    message="Invalid PAN format. Example: ABCDE1234F",
)


# ==========================================================================
# EmployeeRegistrationForm
# ఎందుకు plain forms.Form (ModelForm కాదు): ఇక్కడ డేటా రెండు వేర్వేరు
# మోడల్స్ లోకి వెళ్తుంది -> User (username/email/password) మరియు
# EmployeeProfile (mobile/dob/gender...). ఒక్క ModelForm ఒక్క మోడల్ కే
# బైండ్ అవుతుంది కాబట్టి, ఇక్కడ మామూలు Form వాడి, save() మెథడ్ లో
# మనమే రెండు మోడల్స్ ని క్రియేట్ చేస్తున్నాం.
# ==========================================================================
class EmployeeRegistrationForm(forms.Form):
    full_name = forms.CharField(
        max_length=150, label="Full Name",
        widget=forms.TextInput(attrs={"class": "inp", "placeholder": "Your full name"}),
    )
    mobile_number = forms.CharField(
        max_length=10, validators=[mobile_validator], label="Mobile Number",
        widget=forms.TextInput(attrs={"class": "inp", "placeholder": "98765 43210", "maxlength": "10"}),
    )
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={"class": "inp", "placeholder": "your@email.com"}),
    )
    date_of_birth = forms.DateField(
        label="Date of Birth",
        widget=forms.DateInput(attrs={"class": "inp", "type": "date"}),
    )
    gender = forms.ChoiceField(
        choices=EmployeeProfile.Gender.choices,
        widget=forms.Select(attrs={"class": "sel"}),
    )
    marital_status = forms.ChoiceField(
        choices=EmployeeProfile.MaritalStatus.choices,
        widget=forms.RadioSelect, initial=EmployeeProfile.MaritalStatus.UNMARRIED,
    )
    father_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "inp", "placeholder": "Father's name"}),
    )
    profile_photo = forms.ImageField(required=False)

    # పాస్‌వర్డ్ ని ఎప్పుడూ ఒక్కసారే కాకుండా, రెండుసార్లు (confirm) అడగడం
    # -- యూజర్ టైప్ మిస్టేక్ చేస్తే, తర్వాత లాగిన్ కాలేక ఇబ్బంది పడకుండా.
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "inp", "placeholder": "Strong password"}),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"class": "inp", "placeholder": "Confirm password"}),
    )

    # ------------------------------------------------------------------
    # clean_<field> మెథడ్స్ : ఒక్కో ఫీల్డ్ కి ప్రత్యేక వాలిడేషన్.
    # Django ఫారమ్ .is_valid() కాల్ అయినప్పుడు ఇవి ఆటోమేటిక్‌గా రన్
    # అవుతాయి; ఇక్కడ ValidationError లేపితే ఆ ఎర్రర్ ఆ ఫీల్డ్ కిందే
    # టెంప్లేట్ లో కనిపిస్తుంది.
    # ------------------------------------------------------------------
    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        # ఇదే ఇమెయిల్ తో ఇంతకుముందే ఖాతా ఉందా అని DB లో చెక్ చేస్తున్నాం
        # -- డూప్లికేట్ రిజిస్ట్రేషన్‌లు ఆపడానికి.
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_mobile_number(self):
        mobile = self.cleaned_data["mobile_number"].strip()
        if EmployeeProfile.objects.filter(mobile_number=mobile).exists():
            raise ValidationError("An account with this mobile number already exists.")
        return mobile

    def clean_password1(self):
        password1 = self.cleaned_data.get("password1")
        # Django యొక్క బిల్ట్-ఇన్ password validators (settings.py లో
        # AUTH_PASSWORD_VALIDATORS లో డిఫైన్ చేసినవి -- ఉదా: కనీస పొడవు,
        # కేవలం అంకెలు మాత్రమే వద్దు, సాధారణ పాస్‌వర్డ్‌లు వద్దు)
        # ఇక్కడ రన్ చేస్తున్నాం, తద్వారా బలహీనమైన పాస్‌వర్డ్‌లు
        # ఖాతా-టేకోవర్ దాడులకి దారి తీయకుండా ఆపుతాం.
        validate_password(password1)
        return password1

    # clean() (ఫీల్డ్ లేకుండా): రెండు ఫీల్డ్స్ ని కలిపి చెక్ చేయాలంటే
    # (ఇక్కడ password1 == password2) ఈ మెథడ్ వాడతాం -- clean_<field>
    # మెథడ్స్ అన్నీ పూర్తయ్యాక ఇది చివర్లో కాల్ అవుతుంది.
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords did not match.")
        return cleaned_data

    # ------------------------------------------------------------------
    # save(): ఫారమ్ వాలిడేషన్ అంతా పాస్ అయ్యాక, view.py నుండి కాల్ చేసే
    # మెథడ్. ఇక్కడే అసలైన DB రైట్ ఆపరేషన్ జరుగుతుంది -- ముందు User ని
    # (username గా mobile_number వాడుతున్నాం, ఎందుకంటే యూజర్ ఇచ్చిన
    # ఇమెయిల్/పేరు యూనిక్ కాకపోవచ్చు), తర్వాత దానికి లింక్ అయిన
    # EmployeeProfile ని క్రియేట్ చేస్తుంది.
    # ------------------------------------------------------------------
    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["mobile_number"],
            email=data["email"],
            # set_password() లోపల Django ఆటోమేటిక్‌గా పాస్‌వర్డ్ ని hash
            # చేస్తుంది -- create_user() కాల్ చేసినప్పుడు ఇది లోపలే జరుగుతుంది.
            password=data["password1"],
            first_name=data["full_name"],
        )
        profile = EmployeeProfile.objects.create(
            user=user,
            mobile_number=data["mobile_number"],
            date_of_birth=data["date_of_birth"],
            gender=data["gender"],
            marital_status=data["marital_status"],
            father_name=data["father_name"],
            profile_photo=data.get("profile_photo"),
        )
        return user, profile


# ==========================================================================
# EmployeeLoginForm
# ఎందుకు: లాగిన్ పేజీ లో "BharatHub ID లేదా ఇమెయిల్" + పాస్‌వర్డ్
# అడుగుతారు (username field కాదు) కాబట్టి ఇది కూడా ప్లెయిన్ Form.
# అసలైన authenticate() కాల్ views.py లోనే చేస్తాం, ఎందుకంటే దానికి
# HttpRequest ఆబ్జెక్ట్ కావాలి (login attempt throttling వంటి middleware
# request ఆధారంగానే పనిచేస్తుంది).
# ==========================================================================
class EmployeeLoginForm(forms.Form):
    login_id = forms.CharField(
        label="BharatHub ID / Email",
        widget=forms.TextInput(attrs={"class": "form__input", "placeholder": "BHEMP26070001234 or email@example.com"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form__input", "placeholder": "Enter your password"}),
    )
    remember_me = forms.BooleanField(required=False)


# ==========================================================================
# EmployerRegistrationForm  (accounts app లోనిది -- కంపెనీ HR లాగిన్ కోసం)
# ==========================================================================
class EmployerRegistrationForm(forms.Form):
    """
    రిజిస్ట్రేషన్ ని సింపుల్ గా ఉంచడానికి కేవలం ముఖ్యమైన ఫీల్డ్స్
    మాత్రమే ఇక్కడ అడుగుతున్నాం. PAN/GST/CIN/HQ State వంటివి ఇక
    రిజిస్ట్రేషన్ లో అడగం -- లాగిన్ అయిన తర్వాత "Complete Your
    Profile" దశలో నింపుకోవచ్చు (employers/views.py లోని
    ProfileCompletionView చూడండి).

    గమనిక: వినియోగదారు ఇచ్చిన ఫీల్డ్ లిస్ట్ లో "Email"/"Mail id" అని
    రెండుసార్లు వచ్చింది -- ఒకే ఫీల్డ్ గా (Email) తీసుకున్నాం. ఇదే
    ఇమెయిల్ లాగిన్ కి, మరియు జనరేట్ అయిన Employer ID ని పంపడానికి
    కూడా వాడతాం.
    """
    company_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "inp", "placeholder": "Company name"}),
    )
    company_type = forms.ChoiceField(
        choices=EmployerProfile.CompanyType.choices,
        widget=forms.Select(attrs={"class": "sel"}),
    )
    industry_sector = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "inp", "placeholder": "e.g. IT Services, Manufacturing, Retail..."}),
    )
    contact_person = forms.CharField(
        max_length=150, label="HR / Contact Person Name",
        widget=forms.TextInput(attrs={"class": "inp", "placeholder": "Full name"}),
    )
    mobile_number = forms.CharField(
        max_length=10, validators=[mobile_validator], label="Mobile Number",
        widget=forms.TextInput(attrs={"class": "inp", "placeholder": "98765 43210", "maxlength": "10"}),
    )
    corporate_email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "inp", "placeholder": "hr@company.com"}),
    )
    address = forms.CharField(
        label="Address",
        widget=forms.Textarea(attrs={"class": "inp", "rows": 2, "placeholder": "Registered office address"}),
    )
    other_branch_location = forms.CharField(
        max_length=300, required=False, label="Other Branch Location(s)",
        widget=forms.TextInput(attrs={"class": "inp", "placeholder": "(optional) e.g. Hyderabad, Bengaluru"}),
    )

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "inp", "placeholder": "Strong password"}),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"class": "inp", "placeholder": "Confirm password"}),
    )

    def clean_corporate_email(self):
        email = self.cleaned_data["corporate_email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_mobile_number(self):
        mobile = self.cleaned_data["mobile_number"].strip()
        if EmployerProfile.objects.filter(mobile_number=mobile).exists():
            raise ValidationError("An account with this mobile number already exists.")
        return mobile

    def clean_password1(self):
        password1 = self.cleaned_data.get("password1")
        validate_password(password1)
        return password1

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            self.add_error("password2", "The two passwords did not match.")
        return cleaned_data

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["corporate_email"],
            email=data["corporate_email"],
            password=data["password1"],
            first_name=data["company_name"],
        )
        profile = EmployerProfile.objects.create(
            user=user,
            company_name=data["company_name"],
            company_type=data["company_type"],
            industry_sector=data["industry_sector"],
            contact_person=data["contact_person"],
            mobile_number=data["mobile_number"],
            corporate_email=data["corporate_email"],
            address=data["address"],
            other_branch_location=data.get("other_branch_location", ""),
        )
        return user, profile


# ==========================================================================
# EmployerLoginForm
# ==========================================================================
class EmployerLoginForm(forms.Form):
    login_id = forms.CharField(label="Employer ID / Email")
    password = forms.CharField(widget=forms.PasswordInput)
    remember_me = forms.BooleanField(required=False)


# ==========================================================================
# EmployerProfileCompletionForm
# రిజిస్ట్రేషన్ లో అడగని మిగతా కంపెనీ వివరాలు (PAN/GST/CIN/HQ State) --
# లాగిన్ అయిన తర్వాత "Complete Your Profile" పేజీలో నింపుకుంటారు.
# PAN మాత్రమే required (కంపెనీ చట్టబద్ధమైన గుర్తింపుకి కీలకం);
# GST/CIN/HQ optional (అందరు కంపెనీలకూ ఉండకపోవచ్చు).
# ==========================================================================
class EmployerProfileCompletionForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = ["pan_number", "gst_number", "cin_number", "hq_state"]
        widgets = {
            "pan_number": forms.TextInput(attrs={"class": "form__input", "placeholder": "ABCDE1234F", "style": "text-transform:uppercase"}),
            "gst_number": forms.TextInput(attrs={"class": "form__input", "placeholder": "(optional) 27AAAAA0000A1Z5", "style": "text-transform:uppercase"}),
            "cin_number": forms.TextInput(attrs={"class": "form__input", "placeholder": "(optional) L17110MH1973PLC019786", "style": "text-transform:uppercase"}),
            "hq_state": forms.TextInput(attrs={"class": "form__input", "placeholder": "(optional) e.g. Telangana"}),
        }
        labels = {"pan_number": "PAN Number", "gst_number": "GST Number", "cin_number": "CIN Number", "hq_state": "HQ State"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pan_number"].required = True
        self.fields["pan_number"].validators.append(pan_validator)
        self.fields["gst_number"].required = False
        self.fields["cin_number"].required = False
        self.fields["hq_state"].required = False

    def clean_pan_number(self):
        return self.cleaned_data["pan_number"].strip().upper()
