"""
accounts/password_reset.py

"Forgot Password" ఫ్లో యొక్క నిజమైన బ్యాకెండ్ లాజిక్ -- ఇది Employee,
Employer, Vendor మూడు లాగిన్ పేజీల్లోని "Forgot Password?" ప్యానెల్
(ఇంతకుముందు కేవలం JS-only మాక్-అప్ -- setTimeout తో దశలు మారేవి,
దేన్నీ నిజంగా వెరిఫై చేసేవి కాదు, కొత్త పాస్‌వర్డ్ ని ఎక్కడా సేవ్
చేసేవి కాదు) కి ఉమ్మడి real backend.

మూడు స్టెప్‌లు (login_throttle.MAX_FAILED_ATTEMPTS సార్లు తప్పు
పాస్‌వర్డ్ ఇచ్చాక తప్పనిసరిగా ఇదే మార్గం):
  1. verify_identity() -- role కి తగినట్టు (email+mobile+DOB /
     email+employer_id / email+mobile+vendor_id) DB లో ఖచ్చితంగా
     సరిపోలే ప్రొఫైల్ ఉందా అని చెక్ చేస్తుంది.
  2. send_otp() + verify_otp() -- 6-అంకెల OTP generate చేసి
     (DEBUG లో console కి, production లో నిజమైన SMTP కి) ఈమెయిల్
     పంపుతుంది; session లో (10 నిమిషాలు) పెడుతుంది.
  3. set_new_password() -- verify_otp() సక్సెస్ అయిన తర్వాతే
     అనుమతించాలి (session flag తో గార్డ్ చేస్తాం); కొత్త పాస్‌వర్డ్
     సెట్ చేసి, login_throttle.clear_lock_after_reset() పిలుస్తుంది.
"""
import random
from datetime import timedelta

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .login_throttle import clear_lock_after_reset
from .models import EmployeeProfile, EmployerProfile

SESSION_KEY = "password_reset_state"
OTP_VALID_MINUTES = 10


def find_user_by_identity(role: str, data: dict):
    """role కి తగిన 2/3 ఫీల్డ్స్ అన్నీ సరిపోలితేనే User ని రిటర్న్
    చేస్తుంది -- ఏదో ఒక్కటి కూడా తప్పితే None (ఏ ఫీల్డ్ తప్పు అని
    కూడా చెప్పం, enumeration నివారించడానికి)."""
    email = (data.get("email") or "").strip()

    if role == "employee":
        mobile = (data.get("mobile") or "").strip()
        dob = (data.get("dob") or "").strip()
        if not (email and mobile and dob):
            return None
        profile = EmployeeProfile.objects.filter(
            user__email__iexact=email, mobile_number=mobile, date_of_birth=dob,
        ).select_related("user").first()
        return profile.user if profile else None

    if role == "employer":
        employer_id = (data.get("employer_id") or "").strip()
        if not (email and employer_id):
            return None
        profile = EmployerProfile.objects.filter(
            corporate_email__iexact=email, employer_id__iexact=employer_id,
        ).select_related("user").first()
        return profile.user if profile else None

    if role == "vendor":
        # ఇక్కడే దిగుమతి చేయడం ఉద్దేశపూర్వకం -- accounts app, vendor
        # app ని import చేస్తే (module లెవెల్ లో) circular-import
        # ప్రమాదం ఉంది (vendor/views.py ఇప్పటికే accounts నుండి
        # దిగుమతి చేస్తుంది).
        from vendor.models import VendorProfile
        mobile = (data.get("mobile") or "").strip()
        vendor_id = (data.get("vendor_id") or "").strip()
        if not (email and mobile and vendor_id):
            return None
        profile = VendorProfile.objects.filter(
            vendor_email__iexact=email, vendor_mobile=mobile, vendor_id__iexact=vendor_id,
        ).select_related("user").first()
        return profile.user if profile else None

    return None


def send_otp(request, user) -> None:
    otp = f"{random.randint(0, 999999):06d}"
    request.session[SESSION_KEY] = {
        "user_id": user.pk,
        "otp": otp,
        "otp_verified": False,
        "expires_at": (timezone.now() + timedelta(minutes=OTP_VALID_MINUTES)).isoformat(),
    }
    send_mail(
        subject="BharatHub — Password Reset OTP",
        message=(
            f"Your BharatHub password reset OTP: {otp}\n"
            f"This will expire in {OTP_VALID_MINUTES} minutes.\n\n"
            "If you did not request this, please ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def verify_otp(request, otp: str) -> bool:
    state = request.session.get(SESSION_KEY)
    if not state or state.get("otp") != otp:
        return False
    if timezone.now().isoformat() > state["expires_at"]:
        return False
    state["otp_verified"] = True
    request.session[SESSION_KEY] = state
    return True


def set_new_password(request, new_password: str):
    """session లో OTP ఇప్పటికే verify అయ్యిందని నిర్ధారించుకున్న
    తర్వాతే కొత్త పాస్‌వర్డ్ సెట్ చేస్తుంది. సక్సెస్ అయితే User ని,
    లేకపోతే None ని రిటర్న్ చేస్తుంది."""
    from django.contrib.auth import get_user_model
    state = request.session.get(SESSION_KEY)
    if not state or not state.get("otp_verified"):
        return None

    User = get_user_model()
    try:
        user = User.objects.get(pk=state["user_id"])
    except User.DoesNotExist:
        return None

    user.set_password(new_password)
    user.save(update_fields=["password"])
    clear_lock_after_reset(user)
    del request.session[SESSION_KEY]
    return user
