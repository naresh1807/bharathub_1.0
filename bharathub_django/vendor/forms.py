from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from .models import VendorProfile

User = get_user_model()

mobile_validator = RegexValidator(
    regex=r"^[6-9]\d{9}$",
    message="దయచేసి సరైన 10-అంకెల భారతీయ మొబైల్ నెంబర్ ఇవ్వండి.",
)


# ==========================================================================
# VendorRegistrationForm
# ఎందుకు plain Form (ModelForm కాదు): accounts/forms.py లో వివరించినట్టే,
# ఇక్కడ కూడా డేటా రెండు మోడల్స్ (User + VendorProfile) లోకి వెళ్తుంది.
# ==========================================================================
class VendorRegistrationForm(forms.Form):
    """
    రిజిస్ట్రేషన్ ని సింపుల్ గా ఉంచడానికి కేవలం ముఖ్యమైన ఫీల్డ్స్
    మాత్రమే ఇక్కడ అడుగుతున్నాం. మొబైల్/కేటగిరీ/పనిచేసే రోజులు/షాప్
    ఫోటో వంటివి ఇక రిజిస్ట్రేషన్ లో అడగం -- లాగిన్ అయిన తర్వాత
    "Complete Your Profile" దశలో నింపుకోవచ్చు (vendor/views.py లోని
    ProfileCompletionView చూడండి).

    గమనిక: వినియోగదారు ఇచ్చిన ఫీల్డ్ లిస్ట్ లో ఇమెయిల్ లేదు, కానీ
    దాన్ని ఇక్కడ ఉంచాం -- ఎందుకంటే (1) లాగిన్ ఇక Email/BharatHub ID
    తోనే జరగాలని ఇంతకుముందు నిర్ణయించాం, (2) జనరేట్ అయిన Vendor ID ని
    పంపడానికి ఇమెయిల్ కావాలి. ఇమెయిల్ లేకుండా ఈ రెండూ పనిచేయవు.
    """
    shop_name = forms.CharField(
        max_length=200, label="Business / Shop Name",
        widget=forms.TextInput(attrs={"class": "inp", "placeholder": "Your shop/business name"}),
    )
    owner_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "inp", "placeholder": "Owner's full name"}),
    )
    business_type = forms.ChoiceField(
        choices=VendorProfile.BusinessType.choices,
        widget=forms.Select(attrs={"class": "sel"}),
    )
    year_established = forms.IntegerField(
        min_value=1900, max_value=2100,
        widget=forms.NumberInput(attrs={"class": "inp", "placeholder": "e.g. 2015"}),
    )
    vendor_email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "inp", "placeholder": "your@business.com"}),
    )
    gst_number = forms.CharField(
        max_length=15, required=False,
        widget=forms.TextInput(attrs={"class": "inp", "placeholder": "(optional) 27AAAAA0000A1Z5", "style": "text-transform:uppercase"}),
    )
    pan_number = forms.CharField(
        max_length=10, required=False,
        widget=forms.TextInput(attrs={"class": "inp", "placeholder": "(optional) ABCDE1234F", "style": "text-transform:uppercase"}),
    )
    address = forms.CharField(
        label="Address",
        widget=forms.Textarea(attrs={"class": "inp", "rows": 2, "placeholder": "Shop / business address"}),
    )

    password1 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "inp"}), label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "inp"}), label="Confirm Password")

    def clean_vendor_email(self):
        email = self.cleaned_data["vendor_email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("ఈ ఇమెయిల్ తో ఇప్పటికే ఒక వెండర్ ఖాతా ఉంది.")
        return email

    def clean_password1(self):
        password1 = self.cleaned_data.get("password1")
        validate_password(password1)
        return password1

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            self.add_error("password2", "పాస్‌వర్డ్‌లు రెండూ సరిపోలలేదు.")
        return cleaned_data

    # save(): వాలిడేషన్ పూర్తయ్యాక User + VendorProfile రెండిటినీ
    # ఒకేసారి క్రియేట్ చేసే మెథడ్ (view.py నుండి కాల్ అవుతుంది).
    # గమనిక: username ఇప్పుడు vendor_email (ఇంతకుముందు vendor_mobile
    # ఉండేది -- మొబైల్ ఇక రిజిస్ట్రేషన్ లో అడగం కాబట్టి).
    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["vendor_email"],
            email=data["vendor_email"],
            password=data["password1"],
            first_name=data["shop_name"],
        )
        profile = VendorProfile.objects.create(
            user=user,
            shop_name=data["shop_name"],
            owner_name=data["owner_name"],
            business_type=data["business_type"],
            year_established=data["year_established"],
            vendor_email=data["vendor_email"],
            pan_number=data.get("pan_number", "").upper(),
            gst_number=data.get("gst_number", ""),
            address=data["address"],
        )
        return user, profile


# ==========================================================================
# VendorLoginForm
# ==========================================================================
class VendorLoginForm(forms.Form):
    login_id = forms.CharField(label="Vendor ID / Email")
    password = forms.CharField(widget=forms.PasswordInput)
    remember_me = forms.BooleanField(required=False)


# ==========================================================================
# VendorProfileCompletionForm
# రిజిస్ట్రేషన్ లో అడగని మిగతా వివరాలు (మొబైల్/కేటగిరీ/పనిచేసే
# రోజులు/షాప్ ఫోటో) -- లాగిన్ అయిన తర్వాత "Complete Your Profile"
# పేజీలో నింపుకుంటారు. మొబైల్ మాత్రమే required (customer contact
# కి కీలకం); మిగతావి optional.
# ==========================================================================
class VendorProfileCompletionForm(forms.ModelForm):
    class Meta:
        model = VendorProfile
        fields = ["vendor_mobile", "category", "working_days", "shop_photo"]
        widgets = {
            "vendor_mobile": forms.TextInput(attrs={"class": "form__input", "placeholder": "98765 43210", "maxlength": "10"}),
            "category": forms.TextInput(attrs={"class": "form__input", "placeholder": "(optional) e.g. Office Supplies, Catering..."}),
            "working_days": forms.TextInput(attrs={"class": "form__input", "placeholder": "(optional) e.g. Mon-Sat"}),
        }
        labels = {"vendor_mobile": "Mobile Number", "category": "Business Category", "working_days": "Working Days"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vendor_mobile"].required = True
        self.fields["vendor_mobile"].validators.append(mobile_validator)
        self.fields["category"].required = False
        self.fields["working_days"].required = False
        self.fields["shop_photo"].required = False

    def clean_vendor_mobile(self):
        mobile = self.cleaned_data["vendor_mobile"].strip()
        if VendorProfile.objects.filter(vendor_mobile=mobile).exclude(pk=self.instance.pk).exists():
            raise ValidationError("ఈ మొబైల్ నెంబర్ తో ఇప్పటికే ఒక వెండర్ ఖాతా ఉంది.")
        return mobile
