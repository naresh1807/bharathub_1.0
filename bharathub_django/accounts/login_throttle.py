"""
accounts/login_throttle.py

లాగిన్ బ్రూట్-ఫోర్స్ ప్రొటెక్షన్ (persistent, per-account 3-strikes లాక్).

ఇది ఇంతకుముందు Django cache (IP + login_id కీ, 15 నిమిషాల auto-expiry)
వాడేది. ఆ పద్ధతిలో సమస్య: IP మారితే లేదా 15 నిమిషాలు ఆగితే, దాడి
చేసేవాడు తిరిగి 3 ప్రయత్నాలు పొందేవాడు -- ఇది నిజమైన బ్రూట్-ఫోర్స్
ప్రొటెక్షన్ కాదు.

కొత్త డిజైన్ (accounts.models.LoginSecurity మీద ఆధారపడి):
  - కౌంటర్ ఖాతా (User row) కే శాశ్వతంగా అటాచ్ అవుతుంది -- IP/browser/
    సమయం తో సంబంధం లేదు.
  - 3వ తప్పు ప్రయత్నం వద్ద must_reset_password=True అవుతుంది.
  - ఆ తర్వాత, సరైన పాస్‌వర్డ్ ఇచ్చినా సరే login view లోపలికి రానివ్వదు
    -- తప్పనిసరిగా Forgot-Password (verify identity + OTP + new
    password) ఫ్లో పూర్తి చేసుకుంటేనే clear_lock_after_reset() పిలిచి
    మళ్ళీ లాగిన్ చేయనిస్తాం.
  - ఇక్కడ ఏ TIME WINDOW గానీ, auto-expiry గానీ లేదు ఉద్దేశపూర్వకంగా.

గమనిక: ఈ ఫంక్షన్లు అన్నీ ఒక resolved Django User instance మీదే
పనిచేస్తాయి (login_id స్ట్రింగ్ మీద కాదు) -- ఎందుకంటే ఒకే యూజర్
BharatHub ID తోనూ, email తోనూ కూడా ప్రయత్నించొచ్చు; రెండు వేర్వేరు
స్ట్రింగ్‌లు అయినా, అవి ఒకే ఖాతా అయితే కౌంట్ ఒకటే గా ఉండాలి.
"""
from .models import LoginSecurity

MAX_FAILED_ATTEMPTS = 3


def _get_or_create(user):
    security, _ = LoginSecurity.objects.get_or_create(user=user)
    return security


def is_locked_out(user) -> bool:
    """True అయితే, ఈ యూజర్ ఖాతా must_reset_password స్టేట్ లో ఉంది --
    పాస్‌వర్డ్ సరైనదైనా authenticate() ని అస్సలు పిలవకుండానే ఆపేయాలి."""
    security = getattr(user, "login_security", None)
    return bool(security and security.must_reset_password)


def record_failed_attempt(user) -> int:
    """తప్పు పాస్‌వర్డ్ ప్రయత్నం అయిన ప్రతిసారీ పిలవాలి (login_id ఒక
    నిజమైన యూజర్ కి resolve అయినప్పుడు మాత్రమే -- లేని ID కి కౌంట్
    చేయడానికి ఏమీ ఉండదు). కొత్త attempt కౌంట్ ని రిటర్న్ చేస్తుంది."""
    security = _get_or_create(user)
    security.failed_attempts += 1
    if security.failed_attempts >= MAX_FAILED_ATTEMPTS:
        security.must_reset_password = True
    security.save(update_fields=["failed_attempts", "must_reset_password", "updated_at"])
    return security.failed_attempts


def clear_attempts(user) -> None:
    """సరైన పాస్‌వర్డ్ తో లాగిన్ సక్సెస్ అయిన వెంటనే పిలవాలి. గమనిక:
    ఇది failed_attempts ని మాత్రమే 0 చేస్తుంది -- must_reset_password
    ఇప్పటికే True అయి ఉంటే ఇది దాన్ని క్లియర్ చేయదు (ఆ స్టేట్ లో ఉంటే
    ఈ ఫంక్షన్ కి చేరుకోకముందే login view ఆగిపోవాలి, is_locked_out()
    ద్వారా)."""
    LoginSecurity.objects.filter(user=user).update(failed_attempts=0)


def clear_lock_after_reset(user) -> None:
    """పాస్‌వర్డ్ రీసెట్ ఫ్లో (verify identity + OTP + new password)
    పూర్తిగా సక్సెస్ అయిన తర్వాతే పిలవాలి -- ఇదొక్కటే must_reset_password
    ని మళ్ళీ False చేయగలిగే మార్గం."""
    LoginSecurity.objects.update_or_create(
        user=user, defaults={"failed_attempts": 0, "must_reset_password": False},
    )
