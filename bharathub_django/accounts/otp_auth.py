"""
accounts/otp_auth.py

Login మరియు Registration రెండిటికీ OTP వెరిఫికేషన్ తప్పనిసరి చేసే
షేర్డ్ బ్యాకెండ్ లాజిక్ -- accounts/password_reset.py లో ఇప్పటికే
స్థాపించిన అదే నమూనా (session-based, 6-అంకెల OTP, 10 నిమిషాల
వ్యాలిడిటీ) ఇక్కడ కూడా అనుసరిస్తున్నాం, తద్వారా కోడ్‌బేస్ మొత్తం
ఒకే పద్ధతిలో స్థిరంగా ఉంటుంది.

రెండు వేర్వేరు స్టేట్‌లు (session keys) -- ఒకేసారి login OTP మరియు
register OTP రెండూ (వేర్వేరు టాబ్‌లలో) పెండింగ్ లో ఉన్నా ఒకదాన్ని
ఒకటి ఓవర్‌రైట్ చేయకుండా):

  1. LOGIN: పాస్‌వర్డ్ సరైనదైన తర్వాత, login() కాల్ చేయకముందే OTP
     పంపుతాం -- send_login_otp(). verify_login_otp() సక్సెస్ అయితేనే
     అసలైన django.contrib.auth.login() ఇక్కడే జరుగుతుంది.

  2. REGISTRATION: ఫారమ్ వాలిడ్ అయిన వెంటనే .save() పిలవం -- బదులుగా
     send_registration_otp() తో ఆ ఫారమ్ యొక్క raw POST డేటాని (ఇంకా
     ఏ User/Profile రో క్రియేట్ కాకుండానే) session లో పెట్టి OTP
     పంపుతాం. verify_registration_otp() సక్సెస్ అయితేనే ఆ POST
     డేటాతో ఫారమ్ ని మళ్ళీ నిర్మించి (view.py లోనే, ఎందుకంటే ఏ Form
     క్లాస్ వాడాలో అక్కడికే తెలుసు) .save() పిలుస్తాం.

గమనిక: EmployeeRegistrationForm లోని ఐచ్ఛిక profile_photo (ఫైల్
అప్‌లోడ్) ఈ OTP-గేటెడ్ ఫ్లో లో సపోర్ట్ చేయం -- ఫైల్ అప్‌లోడ్‌లని
session/JSON లో పెట్టడం సురక్షితం/సులభం కాదు (session cookie సైజ్
పరిమితులు, temp-file cleanup అవసరం). ఇది ఇప్పటికే ఐచ్ఛికమే, మరియు
యూజర్ దీన్ని లాగిన్ అయిన తర్వాత "Complete Your Profile" లో
జోడించుకోగలరు కాబట్టి పెద్ద లోటు కాదు.
"""
import random
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

LOGIN_SESSION_KEY = "login_otp_state"
REGISTER_SESSION_KEY = "register_otp_state"
OTP_VALID_MINUTES = 10
MAX_OTP_ATTEMPTS = 5


def _generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def _is_expired(state: dict) -> bool:
    return timezone.now().isoformat() > state["expires_at"]


# ============================================================================
# LOGIN OTP
# ============================================================================
def send_login_otp(request, user, *, remember_me: bool, next_url: str, redirect_name: str) -> None:
    """పాస్‌వర్డ్ సరైనదని నిర్ధారించుకున్న తర్వాత పిలవాలి. login()
    ఇక్కడ ఇంకా జరగదు -- verify_login_otp() సక్సెస్ అయిన తర్వాతే."""
    otp = _generate_otp()
    request.session[LOGIN_SESSION_KEY] = {
        "user_id": user.pk,
        "otp": otp,
        "expires_at": (timezone.now() + timedelta(minutes=OTP_VALID_MINUTES)).isoformat(),
        "remember_me": bool(remember_me),
        "next": next_url or "",
        "redirect_name": redirect_name,
        "attempts": 0,
    }
    send_mail(
        subject="BharatHub — Login OTP",
        message=(
            f"Your BharatHub login OTP is: {otp}\n"
            f"This will expire in {OTP_VALID_MINUTES} minutes.\n\n"
            "If this wasn't you, please ignore this email and consider "
            "resetting your password immediately."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def peek_login_email(request):
    """OTP ఎంటర్ పేజీ లో 'we sent a code to your@email.com' లాంటి
    మెసేజ్ చూపించడానికి -- OTP ని consume చేయదు."""
    from django.contrib.auth import get_user_model
    state = request.session.get(LOGIN_SESSION_KEY)
    if not state:
        return None
    User = get_user_model()
    try:
        return User.objects.get(pk=state["user_id"]).email
    except User.DoesNotExist:
        return None


def verify_login_otp(request, otp: str):
    """సక్సెస్ అయితే ఇక్కడే django login() చేసేసి, {'next', 'redirect_name'}
    dict రిటర్న్ చేస్తుంది. తప్పు/expired/సెషన్ లేకపోతే None."""
    from django.contrib.auth import get_user_model, login as auth_login

    state = request.session.get(LOGIN_SESSION_KEY)
    if not state:
        return None
    if _is_expired(state):
        del request.session[LOGIN_SESSION_KEY]
        return None
    if state.get("otp") != otp:
        state["attempts"] = state.get("attempts", 0) + 1
        if state["attempts"] >= MAX_OTP_ATTEMPTS:
            del request.session[LOGIN_SESSION_KEY]
        else:
            request.session[LOGIN_SESSION_KEY] = state
        return None

    User = get_user_model()
    try:
        user = User.objects.get(pk=state["user_id"])
    except User.DoesNotExist:
        del request.session[LOGIN_SESSION_KEY]
        return None

    auth_login(request, user)
    if not state.get("remember_me"):
        request.session.set_expiry(0)

    result = {"next": state.get("next") or "", "redirect_name": state.get("redirect_name")}
    del request.session[LOGIN_SESSION_KEY]
    return result


def cancel_login_otp(request) -> None:
    request.session.pop(LOGIN_SESSION_KEY, None)


# ============================================================================
# REGISTRATION OTP
# ============================================================================
def send_registration_otp(request, *, email: str, role: str, form_data: dict) -> None:
    """ఫారమ్ వాలిడ్ అయిన వెంటనే (కానీ .save() కి ముందే) పిలవాలి.
    form_data: request.POST.dict() -- plain strings మాత్రమే కాబట్టి
    session (JSON-serializable) లో సురక్షితంగా పెట్టొచ్చు."""
    otp = _generate_otp()
    request.session[REGISTER_SESSION_KEY] = {
        "otp": otp,
        "expires_at": (timezone.now() + timedelta(minutes=OTP_VALID_MINUTES)).isoformat(),
        "role": role,
        "form_data": form_data,
        "attempts": 0,
    }
    send_mail(
        subject="BharatHub — Registration OTP",
        message=(
            f"Your BharatHub registration OTP is: {otp}\n"
            f"Enter this code to complete your registration. It expires in "
            f"{OTP_VALID_MINUTES} minutes.\n\n"
            "If you did not request this, please ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=True,
    )


def peek_registration_role(request):
    state = request.session.get(REGISTER_SESSION_KEY)
    return state.get("role") if state else None


def verify_registration_otp(request, otp: str):
    """సక్సెస్ అయితే (role, form_data) tuple రిటర్న్ చేస్తుంది -- ఆ
    role కి తగిన Form క్లాస్ ని view.py లోనే reconstruct చేసి .save()
    పిలవాలి. తప్పు/expired అయితే (None, None)."""
    state = request.session.get(REGISTER_SESSION_KEY)
    if not state:
        return None, None
    if _is_expired(state):
        del request.session[REGISTER_SESSION_KEY]
        return None, None
    if state.get("otp") != otp:
        state["attempts"] = state.get("attempts", 0) + 1
        if state["attempts"] >= MAX_OTP_ATTEMPTS:
            del request.session[REGISTER_SESSION_KEY]
        else:
            request.session[REGISTER_SESSION_KEY] = state
        return None, None

    role, form_data = state["role"], state["form_data"]
    del request.session[REGISTER_SESSION_KEY]
    return role, form_data


def cancel_registration_otp(request) -> None:
    request.session.pop(REGISTER_SESSION_KEY, None)
