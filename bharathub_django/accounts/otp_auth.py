"""
accounts/otp_auth.py

Login మరియు Registration రెండిటికీ OTP వెరిఫికేషన్ తప్పనిసరి చేసే
షేర్డ్ బ్యాకెండ్ లాజిక్ -- accounts/password_reset.py లో ఇప్పటికే
స్థాపించిన అదే నమూనా (session-based, 6-అంకెల OTP) ఇక్కడ కూడా
అనుసరిస్తున్నాం, తద్వారా కోడ్‌బేస్ మొత్తం ఒకే పద్ధతిలో స్థిరంగా
ఉంటుంది.

రెండు వేర్వేరు స్టేట్‌లు (session keys):
  1. LOGIN: పాస్‌వర్డ్ సరైనదైన తర్వాత, login() కాల్ చేయకముందే OTP
     పంపుతాం -- send_login_otp(). verify_login_otp() సక్సెస్ అయితేనే
     అసలైన django.contrib.auth.login() ఇక్కడే జరుగుతుంది.
  2. REGISTRATION: ఫారమ్ వాలిడ్ అయిన వెంటనే .save() పిలవం -- బదులుగా
     send_registration_otp() తో ఆ ఫారమ్ యొక్క raw POST డేటాని (ఇంకా
     ఏ User/Profile రో క్రియేట్ కాకుండానే) session లో పెట్టి OTP
     పంపుతాం. verify_registration_otp() సక్సెస్ అయితేనే ఆ POST
     డేటాతో ఫారమ్ ని మళ్ళీ నిర్మించి (view.py లోనే) .save() పిలుస్తాం.

గమనిక: EmployeeRegistrationForm లోని ఐచ్ఛిక profile_photo (ఫైల్
అప్‌లోడ్) ఈ OTP-గేటెడ్ ఫ్లో లో సపోర్ట్ చేయం (ఫైల్ అప్‌లోడ్‌లని
session/JSON లో పెట్టడం సురక్షితం/సులభం కాదు) -- ఇది ఐచ్ఛికమే, యూజర్
దీన్ని లాగిన్ అయిన తర్వాత "Complete Your Profile" లో జోడించుకోగలరు.

═══════════════════════════════════════════════════════════════════
⚠️ బ్రూట్-ఫోర్స్ హార్డెనింగ్ (ఈ నాలుగు స్థిరాంకాలే కీలకం):
═══════════════════════════════════════════════════════════════════
1. OTP_VALID_MINUTES = 5 (10 నుండి తగ్గించాం) -- చాలా బ్యాంకులు/UPI
   యాప్‌లు 3-5 నిమిషాలే వాడతాయి. విండో ఎంత చిన్నదైతే, ఆ సమయంలో ఎన్ని
   ప్రయత్నాలు చేయగలరో అంత తక్కువ.

2. MAX_OTP_ATTEMPTS = 5 -- ఆ తర్వాత కోడ్ శాశ్వతంగా చెల్లదు. 6-అంకెల
   కోడ్ కి (10 లక్షల అవకాశాలు) 5 ప్రయత్నాలు అంటే విజయావకాశం 0.0005%.

3. ⚠️⚠️ అసలైన బగ్ ఫిక్స్: ఇంతకుముందు "Resend Code" నొక్కిన ప్రతిసారీ
   attempts కౌంటర్ 0 కి రీసెట్ అయ్యేది -- అంటే 4 సార్లు తప్పు గెస్
   చేసి (5 దాటకుండా ఆగి), Resend నొక్కి, మళ్ళీ 4 సార్లు ప్రయత్నించి...
   ఇలా చేస్తే 5-ప్రయత్నాల పరిమితి ఏమాత్రం అడ్డు రాకుండా అపరిమిత
   ప్రయత్నాలు చేయగలిగే వాళ్ళు. ఇప్పుడు 'attempts' resend చేసినా
   చెరిగిపోదు -- మొత్తం ప్రయత్నానికి (అన్ని resend లు కలిపి) 5 తప్పు
   ప్రయత్నాలు దాటితే పూర్తిగా ఆగిపోవాలి (మళ్ళీ పాస్‌వర్డ్/ఫారమ్
   దగ్గరనుండి మొదలుపెట్టాల్సిందే).

4. Resend పరిమితులు -- "Resend Code" ని కూడా అపరిమితంగా నొక్కి కొత్త
   కోడ్‌లు జనరేట్ చేయించుకుంటూ ఉండలేరు:
     - RESEND_COOLDOWN_SECONDS = 45 (ప్రతి resend కి మధ్య కనీసం ఇంత గ్యాప్)
     - MAX_RESENDS = 3 (మొత్తం ఒక ప్రయత్నానికి ఇన్ని resend లు మాత్రమే,
       ఆ తర్వాత పూర్తిగా మొదటినుండి మొదలుపెట్టాలి)
"""
import random
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

LOGIN_SESSION_KEY = "login_otp_state"
REGISTER_SESSION_KEY = "register_otp_state"

OTP_VALID_MINUTES = 5
MAX_OTP_ATTEMPTS = 5
MAX_RESENDS = 3
RESEND_COOLDOWN_SECONDS = 45


def _generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def _is_expired(state: dict) -> bool:
    return timezone.now().isoformat() > state["expires_at"]


def _seconds_since(iso_ts: str) -> float:
    return (timezone.now() - datetime.fromisoformat(iso_ts)).total_seconds()


def _send_email(subject: str, body: str, recipient: str) -> None:
    send_mail(
        subject=subject, message=body, from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient], fail_silently=True,
    )


# ============================================================================
# LOGIN OTP
# ============================================================================
def send_login_otp(request, user, *, remember_me: bool, next_url: str, redirect_name: str) -> None:
    """పాస్‌వర్డ్ సరైనదని నిర్ధారించుకున్న తర్వాత (ఒకసారే, మొదటిసారి)
    పిలవాలి -- resend కి resend_login_otp() వాడాలి, దీన్ని కాదు
    (ఇది attempts/resend_count రెండిటినీ 0 కి రీసెట్ చేస్తుంది,
    అది మొదటిసారికి మాత్రమే సరైనది)."""
    otp = _generate_otp()
    now_iso = timezone.now().isoformat()
    request.session[LOGIN_SESSION_KEY] = {
        "user_id": user.pk,
        "otp": otp,
        "expires_at": (timezone.now() + timedelta(minutes=OTP_VALID_MINUTES)).isoformat(),
        "remember_me": bool(remember_me),
        "next": next_url or "",
        "redirect_name": redirect_name,
        "attempts": 0,
        "resend_count": 0,
        "last_sent_at": now_iso,
    }
    _send_email(
        "BharatHub — Login OTP",
        f"Your BharatHub login OTP is: {otp}\n"
        f"This will expire in {OTP_VALID_MINUTES} minutes.\n\n"
        "If this wasn't you, please ignore this email and consider "
        "resetting your password immediately.",
        user.email,
    )


def resend_login_otp(request):
    """'Resend Code' బటన్ కోసం -- కూల్‌డౌన్ + మొత్తం resend పరిమితి
    రెండూ చెక్ చేస్తుంది, attempts కౌంటర్ ని కొనసాగిస్తుంది (0 కి
    రీసెట్ చేయదు). రిటర్న్: (ok: bool, error_message: str|None)."""
    from django.contrib.auth import get_user_model

    state = request.session.get(LOGIN_SESSION_KEY)
    if not state:
        return False, "Session expired. Please log in again."

    elapsed = _seconds_since(state["last_sent_at"])
    if elapsed < RESEND_COOLDOWN_SECONDS:
        wait = int(RESEND_COOLDOWN_SECONDS - elapsed)
        return False, f"Please wait {wait}s before requesting another code."

    if state.get("resend_count", 0) >= MAX_RESENDS:
        del request.session[LOGIN_SESSION_KEY]
        return False, "Too many code requests. Please log in again."

    User = get_user_model()
    try:
        user = User.objects.get(pk=state["user_id"])
    except User.DoesNotExist:
        del request.session[LOGIN_SESSION_KEY]
        return False, "Session expired. Please log in again."

    otp = _generate_otp()
    now_iso = timezone.now().isoformat()
    state.update({
        "otp": otp,
        "expires_at": (timezone.now() + timedelta(minutes=OTP_VALID_MINUTES)).isoformat(),
        "resend_count": state.get("resend_count", 0) + 1,
        "last_sent_at": now_iso,
        # attempts ఉద్దేశపూర్వకంగానే ఇక్కడ మార్చడం లేదు -- పైన ఉన్న
        # మాడ్యూల్ డాక్‌స్ట్రింగ్ లోని పాయింట్ 3 చూడండి.
    })
    request.session[LOGIN_SESSION_KEY] = state
    _send_email(
        "BharatHub — Login OTP",
        f"Your BharatHub login OTP is: {otp}\n"
        f"This will expire in {OTP_VALID_MINUTES} minutes.\n\n"
        "If this wasn't you, please ignore this email and consider "
        "resetting your password immediately.",
        user.email,
    )
    return True, None


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
    """ఫారమ్ వాలిడ్ అయిన వెంటనే (కానీ .save() కి ముందే), మొదటిసారి
    మాత్రమే పిలవాలి -- resend కి resend_registration_otp() వాడాలి.
    form_data: request.POST.dict() -- plain strings మాత్రమే కాబట్టి
    session (JSON-serializable) లో సురక్షితంగా పెట్టొచ్చు."""
    otp = _generate_otp()
    now_iso = timezone.now().isoformat()
    request.session[REGISTER_SESSION_KEY] = {
        "otp": otp,
        "expires_at": (timezone.now() + timedelta(minutes=OTP_VALID_MINUTES)).isoformat(),
        "role": role,
        "form_data": form_data,
        "attempts": 0,
        "resend_count": 0,
        "last_sent_at": now_iso,
    }
    _send_email(
        "BharatHub — Registration OTP",
        f"Your BharatHub registration OTP is: {otp}\n"
        f"Enter this code to complete your registration. It expires in "
        f"{OTP_VALID_MINUTES} minutes.\n\n"
        "If you did not request this, please ignore this email.",
        email,
    )


def resend_registration_otp(request):
    """'Resend Code' బటన్ కోసం -- login flow లో లాగే కూల్‌డౌన్ + మొత్తం
    resend పరిమితి రెండూ చెక్ చేస్తుంది. రిటర్న్: (ok: bool, error: str|None)."""
    state = request.session.get(REGISTER_SESSION_KEY)
    if not state:
        return False, "Session expired. Please register again."

    elapsed = _seconds_since(state["last_sent_at"])
    if elapsed < RESEND_COOLDOWN_SECONDS:
        wait = int(RESEND_COOLDOWN_SECONDS - elapsed)
        return False, f"Please wait {wait}s before requesting another code."

    if state.get("resend_count", 0) >= MAX_RESENDS:
        del request.session[REGISTER_SESSION_KEY]
        return False, "Too many code requests. Please register again."

    email_field = {"employee": "email", "employer": "corporate_email", "vendor": "vendor_email"}[state["role"]]
    email = state["form_data"].get(email_field, "")
    if not email:
        del request.session[REGISTER_SESSION_KEY]
        return False, "Session expired. Please register again."

    otp = _generate_otp()
    now_iso = timezone.now().isoformat()
    state.update({
        "otp": otp,
        "expires_at": (timezone.now() + timedelta(minutes=OTP_VALID_MINUTES)).isoformat(),
        "resend_count": state.get("resend_count", 0) + 1,
        "last_sent_at": now_iso,
        # attempts ఇక్కడ కూడా carry-forward అవుతుంది (0 కి రీసెట్ కాదు).
    })
    request.session[REGISTER_SESSION_KEY] = state
    _send_email(
        "BharatHub — Registration OTP",
        f"Your BharatHub registration OTP is: {otp}\n"
        f"Enter this code to complete your registration. It expires in "
        f"{OTP_VALID_MINUTES} minutes.\n\n"
        "If you did not request this, please ignore this email.",
        email,
    )
    return True, None


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
