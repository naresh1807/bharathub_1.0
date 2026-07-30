"""
Django settings for the BharatHub project.

SECURITY NOTE FOR THE DEVELOPER:
This file is deliberately split into two modes using the DEBUG flag:
  - DEBUG = True   -> safe for local development on http://127.0.0.1
  - DEBUG = False  -> "production mode": every hardened security setting
                       below (HTTPS-only cookies, HSTS, etc.) switches ON
                       automatically. Deploy with DEBUG=False and a real
                       HTTPS certificate — never run DEBUG=True on a live
                       server, it leaks stack traces & source code to
                       anyone who can trigger an error.
"""
import os
from pathlib import Path

# BASE_DIR = the bharathub_django/ folder (project root). Every other
# path in this file (templates, static, sqlite db) is built from this.
BASE_DIR = Path(__file__).resolve().parent.parent

# ═══════════════════════════════════════════════════════════════════
# ── CORE SECURITY SWITCHES ───────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

# SECRET_KEY signs session cookies, password-reset tokens & CSRF tokens.
# If an attacker learns this key they can forge login sessions.
# Read it from an environment variable in production so it is never
# committed to git; fall back to the placeholder only for local dev.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-REPLACE-THIS-KEY-BEFORE-DEPLOYING",
)

# DEBUG must be False on any server real users can reach. Read from
# env so a deploy script can flip it without touching this file.
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

# FAIL-SAFE: ఎవరైనా పొరపాటున DJANGO_SECRET_KEY env variable సెట్
# చేయకుండానే DEBUG=False తో production కి డిప్లాయ్ చేస్తే, పైన ఉన్న
# ప్లేస్‌హోల్డర్ కీ నే వాడేస్తారు -- ఈ ప్లేస్‌హోల్డర్ ఈ కోడ్ బహిరంగంగా
# పంచుకున్న ప్రతిచోటా (git repo, ఈ చాట్ లో కూడా) ఒకేలా కనిపిస్తుంది
# కాబట్టి, ఎవరైనా attacker దీన్ని ఊహించి సెషన్/CSRF టోకెన్‌లని ఫోర్జ్
# చేయగలరు. కాబట్టి production మోడ్ లో ఈ ప్లేస్‌హోల్డర్ కనిపిస్తే,
# సర్వర్ నిశ్శబ్దంగా అసురక్షితంగా రన్ అవ్వడం కంటే, స్టార్టప్ లోనే
# స్పష్టమైన ఎర్రర్ తో ఆగిపోవడం మేలు.
if not DEBUG and SECRET_KEY == "django-insecure-REPLACE-THIS-KEY-BEFORE-DEPLOYING":
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "DJANGO_DEBUG=False తో రన్ చేస్తున్నారు కానీ DJANGO_SECRET_KEY "
        "env variable సెట్ చేయలేదు -- ఇలా placeholder secret key తో "
        "production లో రన్ చేయడం చాలా ప్రమాదకరం (సెషన్/CSRF ఫోర్జరీ). "
        "ముందు ఒక కొత్త కీ generate చేయండి: "
        "python -c \"from django.core.management.utils import get_random_secret_key; "
        "print(get_random_secret_key())\" -- ఆ విలువని DJANGO_SECRET_KEY గా సెట్ చేయండి."
    )

# ALLOWED_HOSTS: Django refuses any request whose Host header isn't in
# this list (blocks "Host header poisoning" attacks). "*" is fine only
# while DEBUG=True on your own machine; list your real domain(s) in
# production, e.g. ["www.bharathub.in", "bharathub.in"].
ALLOWED_HOSTS = (
    ["*"] if DEBUG else os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
)

# ═══════════════════════════════════════════════════════════════════
# ── APPLICATIONS ─────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════
INSTALLED_APPS = [
    "django.contrib.admin",          # /admin/ backoffice
    "django.contrib.auth",           # login system, password hashing (PBKDF2)
    "django.contrib.contenttypes",   # required by auth/admin
    "django.contrib.sessions",       # server-side session storage (login state)
    "django.contrib.messages",       # one-time "flash" messages framework
    "django.contrib.staticfiles",    # collects/serves CSS, JS, images

    "channels",     # WebSocket support (ASGI) for real-time chat

    # BharatHub apps
    "home",         # Home, About, Contact, Privacy, Terms, Help
    "accounts",     # Employee & Employer registration / login
    "candidates",   # Candidate profile & dashboard
    "employers",    # Job postings & employer dashboard
    "jobs",         # Job listings & the "Applications" inbox
    "vendor",       # Vendor registration, login & dashboard
    "shopping",     # B2B marketplace: product listings, cart, orders
    "messaging",    # Chat between employer / vendor / candidate
    "webmail",      # BharatHub Mail (@bharathub.com) -- Gmail-style inbox
    "videos",       # Facebook-style company culture video feed
    "meetings",     # Zoom-style WebRTC video meeting rooms
]

# ═══════════════════════════════════════════════════════════════════
# ── MIDDLEWARE (every request passes through this list, top to    ──
# ── bottom; every response passes back through it, bottom to top) ──
# ═══════════════════════════════════════════════════════════════════
MIDDLEWARE = [
    # Adds HSTS, X-Content-Type-Options, SSL redirect, etc. — see the
    # SECURE_* settings further down that this middleware reads.
    "django.middleware.security.SecurityMiddleware",

    # Signed, httponly session cookie -> server-side session table.
    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    # Rejects any POST/PUT/DELETE/PATCH that doesn't carry a valid,
    # per-session CSRF token -> stops Cross-Site Request Forgery
    # (a malicious site silently submitting forms as a logged-in user).
    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",

    # రిజిస్ట్రేషన్ ఇప్పుడు కనీస వివరాలు మాత్రమే తీసుకుంటుంది కాబట్టి,
    # profile_completed=False ఉన్న యూజర్లను "Complete Your Profile"
    # పేజీ కే బలవంతంగా పంపుతుంది -- accounts/middleware.py చూడండి.
    # AuthenticationMiddleware తర్వాతే ఉండాలి (request.user కావాలి).
    "accounts.middleware.ProfileCompletionMiddleware",

    # Sends X-Frame-Options: DENY -> stops "clickjacking" (embedding
    # your login/payment pages inside an invisible <iframe> on an
    # attacker's site to trick users into clicking hidden buttons).
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "bharathub.urls"

# ═══════════════════════════════════════════════════════════════════
# ── LOGIN_URL: 404 బగ్ కి fix (accounts/login/ ఉనికిలో లేదు) ────────
# ═══════════════════════════════════════════════════════════════════
# BharatHub కి ఒక్క యూనివర్సల్ లాగిన్ పేజీ లేదు -- Employee/Employer/
# Vendor ప్రతి రోల్ కీ దాని సొంత లాగిన్ పేజీ ఉంది (employee_login.html,
# employer_login.html, vendor_login.html). అందుకే చాలా వరకు views లో
# LoginRequiredMixin తో పాటు login_url ని ఆ రోల్ కి తగ్గట్టుగా
# ఇప్పటికే సెట్ చేశాం (ఉదా: login_url = "accounts:employer_login").
#
# కానీ కొన్ని views (ఉదా: meetings/views.py: MeetingRoomView -- ఒక
# మీటింగ్ లింక్ Employee/Employer/Vendor ముగ్గురిలో ఎవరైనా తెరవొచ్చు,
# ఏ రోల్ దో ముందే తెలియదు) ఉద్దేశపూర్వకంగానే login_url సెట్ చేయవు.
# అలాంటప్పుడు Django తన డిఫాల్ట్ LOGIN_URL కి ("/accounts/login/")
# redirect చేస్తుంది -- కానీ ఈ ప్రాజెక్ట్ లో ఆ URL పేటర్న్ అస్సలు
# లేదు కాబట్టి, లాగిన్ కాని యూజర్ ఒక మీటింగ్ లింక్ తెరిస్తే
# "Page not found (404)" వచ్చేది (ఖచ్చితంగా ఇదే బగ్ స్క్రీన్‌షాట్
# లో కనిపించింది).
#
# దీన్ని ఫిక్స్ చేయడానికి, ఏ నిర్దిష్ట రోల్ తెలియని ప్రతి చోటికీ ఒక
# సురక్షితమైన, ఎప్పుడూ పనిచేసే ఫాల్‌బ్యాక్‌గా Home పేజీ నే
# LOGIN_URL గా సెట్ చేస్తున్నాం -- Home పేజీలో ఇప్పటికే మూడు రోల్స్
# కీ లాగిన్ లింక్‌లు (Login / "🏢 I am Employer" / "🛍️ I am Vendor")
# స్పష్టంగా కనిపిస్తాయి, కాబట్టి యూజర్ తనకి సరైన లాగిన్ పేజీ ని
# అక్కడి నుండి ఎంచుకోగలరు -- 404 బదులు.
LOGIN_URL = "home:bharathub_home"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # APP_DIRS=True auto-discovers each app's own
        # templates/<app_label>/ folder (home/templates/home/, etc.).
        # DIRS below adds ONE extra shared folder for templates that
        # don't belong to a single app -- dashboard_base.html (shared
        # by the candidate / employer / vendor dashboards) lives here.
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            # Django's template engine auto-escapes every {{ variable }}
            # by default (turns <script> into &lt;script&gt;), which is
            # the main defence against stored/reflected XSS. Never use
            # the |safe filter or {% autoescape off %} on user-entered
            # text (job descriptions, chat messages, reviews, etc).
        },
    },
]

WSGI_APPLICATION = "bharathub.wsgi.application"
ASGI_APPLICATION = "bharathub.asgi.application"

# ═══════════════════════════════════════════════════════════════════
# ── DATABASE ──────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════
# NOTE: Django's ORM (Model.objects.filter(...) etc.) always sends
# parameterised queries to the database, which is what prevents SQL
# injection. Never build raw SQL by string-concatenating user input;
# if you ever need .raw() or connection.cursor(), always pass values
# via the params=[...] argument, never f-strings/% formatting.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'bharathub',
#         'USER': 'root',
#         'PASSWORD': 'Thanvika@1816',
#         'HOST': 'localhost',
#         'PORT': '3306',
#     }
# }

# ═══════════════════════════════════════════════════════════════════
# ── PASSWORD STRENGTH RULES (checked on every registration/change) ─
# ═══════════════════════════════════════════════════════════════════
AUTH_PASSWORD_VALIDATORS = [
    # Blocks passwords that are too similar to the user's name/email.
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    # Minimum length (default 8 chars) -- raised to 10 below via OPTIONS.
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    # Rejects the 20,000 most common leaked passwords ("password123" etc).
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    # Rejects all-numeric passwords ("9876543210").
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Passwords are hashed with PBKDF2-SHA256 (Django's default, ~260,000
# iterations) before ever touching the database -- plaintext passwords
# are never stored. Listed explicitly here for clarity/auditability.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# ═══════════════════════════════════════════════════════════════════
# ── LOGIN BRUTE-FORCE / LOCKOUT ─────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════
# ఇది ఇక TODO కాదు -- ఇప్పటికే మన సొంత lockout సిస్టమ్ బిల్డ్ చేశాం:
# accounts/models.py::LoginSecurity (per-account, DB-persistent, 3
# తప్పు ప్రయత్నాల తర్వాత must_reset_password=True) + accounts/
# login_throttle.py (లాజిక్) + accounts/password_reset.py (అన్‌లాక్
# చేసే ఏకైక మార్గం). ఏ 3rd-party package (django-axes వంటివి) అవసరం
# లేదు.

# ═══════════════════════════════════════════════════════════════════
# ── SESSION & CSRF COOKIES ──────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════
SESSION_COOKIE_HTTPONLY = True     # JavaScript (and thus XSS) can't read the session cookie
CSRF_COOKIE_HTTPONLY = False       # must stay readable so JS can attach it to fetch()/AJAX headers
SESSION_COOKIE_SAMESITE = "Lax"    # cookie isn't sent on cross-site requests (extra CSRF defence)
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7   # auto-logout after 7 days of inactivity
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True       # refreshes the expiry timer while the user is active

# ── The following only make sense once the site is served over HTTPS.
# They're gated on `not DEBUG` so local http://127.0.0.1 development
# still works; turn DEBUG off (and put the site behind HTTPS) and every
# one of these switches on automatically.
SESSION_COOKIE_SECURE = not DEBUG   # cookie only sent over HTTPS, never plain HTTP
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG     # http:// requests get 301-redirected to https://
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000   # 1 year: tells browsers "always use HTTPS for this domain"
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# ═══════════════════════════════════════════════════════════════════
# ── BROWSER-LEVEL ATTACK PROTECTION ─────────────────────────────────
# ═══════════════════════════════════════════════════════════════════
SECURE_CONTENT_TYPE_NOSNIFF = True
# ^ sends X-Content-Type-Options: nosniff -- stops the browser from
#   "guessing" a file is HTML/JS when the server said e.g. image/png,
#   which is a common way to smuggle an XSS payload through an upload.

X_FRAME_OPTIONS = "DENY"
# ^ blocks EVERY page on this site from being embedded in an <iframe>
#   on another domain -- kills clickjacking outright.

SECURE_REFERRER_POLICY = "same-origin"
# ^ the browser only sends the Referer header to your own domain, not
#   to third-party resources (fonts.googleapis.com in our templates),
#   so URLs (which may contain tokens) aren't leaked cross-site.

SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
# ^ isolates our browser tab from other-origin tabs/popups (defence
#   against Spectre-style cross-origin data leaks).

# A basic Content-Security-Policy: only allow scripts/styles/fonts
# from our own domain plus the Google Fonts CDN already used in the
# templates. This is the single biggest defence against XSS actually
# executing even if a payload sneaks into stored data somewhere.
# (Requires `pip install django-csp` + adding
#  "csp.middleware.CSPMiddleware" to MIDDLEWARE to take effect --
#  left here as ready-to-use config once that package is installed.)
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
CSP_SCRIPT_SRC = ("'self'",)
CSP_IMG_SRC = ("'self'", "data:")

# ═══════════════════════════════════════════════════════════════════
# ── FILE UPLOAD SAFETY (resumes, company logos, chat attachments) ──
# ═══════════════════════════════════════════════════════════════════
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024     # 5 MB per file
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 200               # blocks form-field "hash flooding" DoS
FILE_UPLOAD_PERMISSIONS = 0o644
# Reminder for whoever adds the upload views: always re-validate the
# file's real content-type/extension server-side (never trust the
# browser-supplied MIME type), store uploads outside any executable
# path, and serve them back with Content-Disposition: attachment for
# untrusted file types so the browser can't execute them inline.

# ═══════════════════════════════════════════════════════════════════
# ── ADMIN ALERTS ─────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════
# When DEBUG=False, an unhandled server error is emailed here instead
# of being shown to the visitor (which would leak a stack trace).
ADMINS = [("BharatHub Admin", os.environ.get("DJANGO_ADMIN_EMAIL", "admin@example.com"))]

# ═══════════════════════════════════════════════════════════════════
# ── INTERNATIONALIZATION ────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ═══════════════════════════════════════════════════════════════════
# ── STATIC FILES (CSS, JS extracted from the original HTML) ────────
# ═══════════════════════════════════════════════════════════════════
# BUG FIX: ఇది ఇంతకుముందు "static/" (leading slash లేకుండా) గా
# ఉండేది -- అంటే {% static %} టాగ్ "static/messaging/css/chat.css"
# లాంటి *relative* href నే జనరేట్ చేసేది, "/static/..." లాంటి
# absolute path కాదు. Browser దీన్ని ప్రస్తుత పేజీ URL కి సాపేక్షంగా
# (relative) రిజాల్వ్ చేస్తుంది -- root-level పేజీలకి (home/accounts/
# candidates/employers/vendor -- bharathub/urls.py లో అన్నీ ""
# prefix తోనే mount అయ్యాయి కాబట్టి) ఇది యాదృచ్ఛికంగా సరిగ్గానే
# పనిచేసేది. కానీ URL prefix ఉన్న ఏ పేజీ అయినా (jobs/, shop/,
# messages/, videos/ -- ఇవి bharathub/urls.py లో ఒక extra path
# సెగ్మెంట్ తో mount అయ్యాయి) దీని వల్ల అన్ని CSS/JS రిక్వెస్ట్‌లూ
# తప్పు URL కి వెళ్ళి (ఉదా: /messages/candidate_messages.html పేజీ
# లో "static/..." అనేది "/messages/static/..." గా రిజాల్వ్ అయ్యేది,
# "/static/..." కాదు) 404 వచ్చేవి -- పేజీ మొత్తం అన్‌స్టైల్డ్ గా
# కనిపించేది (నావ్/సైడ్‌బార్‌తో సహా, ఎందుకంటే dashboard CSS ఫైల్ కూడా
# అదే విధంగా 404 అయ్యేది). ఇప్పుడు లీడింగ్ స్లాష్ తో, ప్రతి {% static %}
# href ఎప్పుడూ డొమైన్ రూట్ నుండే (పేజీ ఎంత లోతుగా nest అయినా సరే)
# సరిగ్గా రిజాల్వ్ అవుతుంది.
STATIC_URL = "/static/"
# Each app ships its own static/<app_label>/css|js/*.* folder
# (e.g. home/static/home/css/about.css, vendor/static/vendor/js/vendor_login.js).
# These are auto-discovered because "django.contrib.staticfiles" scans
# every installed app's static/ folder.
#
# STATICFILES_DIRS below adds ONE extra folder for assets that don't
# belong to a single app -- same idea as TEMPLATES->DIRS above for
# dashboard_base.html. Right now it holds the mobile navigation
# drawer (CSS+JS) shared by all three dashboards (candidate/employer/
# vendor) and their standalone sub-pages (Applications, Messages,
# Candidate Search, ...) that also extend dashboard_base.html.
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # used by `collectstatic` in production
# In production, serve STATIC_ROOT via nginx/whitenoise with far-future
# cache headers -- never let Django itself serve static files when
# DEBUG=False (it doesn't, by design: that's what the DEBUG check in
# bharathub/urls.py's `static()` helper is for).

# ═══════════════════════════════════════════════════════════════════
# ── MEDIA FILES (user uploads: resumes, profile photos, etc.) ──────
# ═══════════════════════════════════════════════════════════════════
# accounts.EmployeeProfile.profile_photo మరియు candidates.CandidateProfile
# (resume / profile_photo) వంటి ImageField/FileField లు వాడేందుకు ఇవి
# అవసరం. SECURITY NOTE: MEDIA_ROOT లో ఎప్పుడూ యూజర్ అప్‌లోడ్ చేసిన
# ఫైళ్ళనే ఉంచాలి, ఎప్పుడూ దాన్ని కోడ్/సోర్స్ ఫైళ్ళతో కలపకూడదు --
# అప్పుడే bharathub/urls.py లోని static() హెల్పర్ (DEBUG=True లో
# మాత్రమే) సురక్షితంగా వీటిని సర్వ్ చేయగలదు. ప్రొడక్షన్ లో (DEBUG=False)
# ఈ ఫైళ్ళని nginx/S3 వంటి వాటితో సర్వ్ చేయాలి, Django తో కాదు.
# BUG FIX: STATIC_URL లో పైన వివరించిన సమస్యే ఇక్కడ కూడా ఉండేది
# ("media/" -- leading slash లేకుండా) -- ప్రొఫైల్ ఫోటోలు, రెజ్యూమ్‌లు,
# చాట్ attachments వంటివి /messages/, /jobs/ వంటి nested పేజీలలో
# తప్పు URL కి రిజాల్వ్ అయ్యేవి. లీడింగ్ స్లాష్ తో ఫిక్స్ చేశాం.
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ═══════════════════════════════════════════════════════════════════
# ── MESSAGE ENCRYPTION (messaging app: Chat between Employee /       ─
# ── Employer / Vendor) ──────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════
# ప్రతి చాట్ సందేశం, DB లో save అయ్యే ముందు Fernet (AES-128 +
# authenticated HMAC) తో encrypt అవుతుంది -- messaging/fields.py లోని
# EncryptedTextField చూడండి. ఈ కీ పోగొట్టుకుంటే/మారితే, పాత సందేశాలు
# ఎప్పటికీ decrypt కావు -- కాబట్టి ఇది తప్పకుండా permanent env
# variable గా ఉండాలి, ప్రతి server restart కీ ఒకేలా ఉండాలి.
#
# ప్రొడక్షన్ కి కీ ఇలా ఒక్కసారి generate చేసుకోండి:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# ఆ విలువ ని DJANGO_MESSAGE_KEY env variable గా సెట్ చేయండి (git లో
# commit చేయకండి -- SECRET_KEY లాగే ఇది కూడా ఒక secret).
import base64
import hashlib

_message_key_env = os.environ.get("DJANGO_MESSAGE_KEY")
if _message_key_env:
    MESSAGE_ENCRYPTION_KEY = _message_key_env
else:
    # DEV-ONLY ఫాల్‌బ్యాక్: SECRET_KEY నుండి deterministic గా ఒక Fernet
    # కీ derive చేస్తాం, తద్వారా local dev లో restart అయినా అదే కీ
    # వస్తుంది (ప్రతి restart కి కొత్త కీ వస్తే, పాత సందేశాలన్నీ
    # అర్థం కాకుండా పోతాయి). PRODUCTION లో మాత్రం ఎప్పుడూ పైన ఉన్న
    # DJANGO_MESSAGE_KEY env variable ద్వారానే సెట్ చేయాలి -- SECRET_KEY
    # మారితే (ఉదా: లీక్ అయ్యి రొటేట్ చేస్తే) సందేశాలు కూడా పోకుండా.
    _derived = hashlib.sha256(SECRET_KEY.encode("utf-8")).digest()
    MESSAGE_ENCRYPTION_KEY = base64.urlsafe_b64encode(_derived).decode("utf-8")

# ═══════════════════════════════════════════════════════════════════
# ── REAL-TIME CHAT: Channels (WebSockets) + Redis channel layer ────
# ═══════════════════════════════════════════════════════════════════
# ASGI_APPLICATION: bharathub/asgi.py లోని ProtocolTypeRouter ని
# వాడుకుంటుంది -- HTTP రిక్వెస్ట్‌లు మామూలుగా Django views కి,
# WebSocket రిక్వెస్ట్‌లు (ws://.../ws/messaging/...) messaging/
# routing.py లోని consumers కి వెళ్తాయి.
ASGI_APPLICATION = "bharathub.asgi.application"

# REDIS_URL: ఒకటే env variable, Channels (presence/broadcast) మరియు
# Celery (task queue) రెండూ వాడతాయి.
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")


def _redis_is_reachable(url, timeout=0.2):
    """Redis నిజంగా రన్ అవుతుందో లేదో ఒక చిన్న (200ms) TCP కనెక్షన్
    చెక్ తో చూస్తాం -- ఇది Django స్టార్టప్ టైమ్‌లో ఒక్కసారే
    రన్ అవుతుంది (ప్రతి రిక్వెస్ట్ కి కాదు), కాబట్టి పెర్ఫార్మెన్స్
    మీద ప్రభావం ఉండదు.

    ⚠️ ఇదే ఫిక్స్ ఈ బగ్ కి: ఇంతకుముందు USE_REDIS_CHANNEL_LAYER అనే
    env variable డిఫాల్ట్‌గా "True" గా ఉండేది -- అంటే Redis నిజంగా
    రన్ అవుతుందో లేదో చెక్ చేయకుండానే, ఎప్పుడూ దాన్నే వాడటానికి
    ప్రయత్నించేది. లోకల్ dev మెషీన్ (Redis ఇన్‌స్టాల్ చేయని Windows
    మెషీన్ లాంటివి) మీద ఇది ప్రతిసారీ
    "ConnectionError: Error 22 connecting to 127.0.0.1:6379" తో
    పేజీ లోడ్ అవ్వకుండా క్రాష్ అయ్యేలా చేసేది (chat, meetings అన్నీ
    దీనిపైనే ఆధారపడతాయి కాబట్టి). ఇప్పుడు నిజంగా Redis reachable
    అయితేనే దాన్ని వాడతాం, లేకపోతే ఆటోమేటిక్‌గా (ఏ env variable
    సెట్ చేయాల్సిన అవసరం లేకుండానే) InMemoryChannelLayer కి
    సురక్షితంగా fallback అవుతాం."""
    import socket
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 6379
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# USE_REDIS_CHANNEL_LAYER env variable ఇచ్చి ఉంటే దాన్నే గౌరవిస్తాం
# (ఉదా: production లో REDIS_URL సెట్ చేసినా, ఏదో కారణంగా బలవంతంగా
# InMemory వాడాలంటే "False" పెట్టొచ్చు). ఏమీ ఇవ్వకపోతే, ఆటోమేటిక్‌గా
# Redis reachable అవుతుందో లేదో చెక్ చేసి నిర్ణయిస్తాం.
_use_redis_env = os.environ.get("USE_REDIS_CHANNEL_LAYER")
if _use_redis_env is not None:
    _use_redis_channel_layer = _use_redis_env == "True"
else:
    _use_redis_channel_layer = _redis_is_reachable(REDIS_URL)

if _use_redis_channel_layer:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }

# ═══════════════════════════════════════════════════════════════════
# ── CELERY (background tasks: offline chat-notification emails) ───
# ═══════════════════════════════════════════════════════════════════
# Redis నే broker గా (task queue) మరియు result backend గా వాడతాం --
# వేరే బ్రోకర్ (RabbitMQ మొదలైనవి) అవసరం లేకుండా ఒకే Redis instance
# సరిపోతుంది dev/small-scale production కి.
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Kolkata"
# TRUE అయితే .delay() కాల్ చేసిన వెంటనే, ప్రత్యేక worker process
# లేకుండానే, అదే request-response cycle లో సింక్రొనస్‌గా టాస్క్
# రన్ అవుతుంది -- ఇది కేవలం local dev సౌలభ్యం కోసమే (env var తో
# ఆఫ్ చేసి production లో నిజమైన `celery -A bharathub worker` వాడాలి).
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "True") == "True"

# ఆఫ్‌లైన్ యూజర్‌కి కొత్త మెసేజ్ వచ్చినప్పుడు పంపే ఈమెయిల్ కోసం
# "from" అడ్రస్. DEBUG=True లో నిజంగా ఈమెయిల్ పంపకుండా, కేవలం
# కన్సోల్ లో ప్రింట్ చేస్తుంది (console backend) -- production లో
# EMAIL_BACKEND ని SMTP కి మార్చాలి.
# DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@bharathub.local")
# if DEBUG:
#    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'bharathubproject1@gmail.com'
EMAIL_HOST_PASSWORD = 'rjrdlzghnxwfiddo'
DEFAULT_FROM_EMAIL = 'bharathubproject1@gmail.com'

# ═══════════════════════════════════════════════════════════════════
# ── WEB PUSH NOTIFICATIONS (browser desktop notifications) ─────────
# ═══════════════════════════════════════════════════════════════════
# ఆఫ్‌లైన్‌లో ఉన్న యూజర్‌కి ఈమెయిల్ తో పాటు (లేదా బదులుగా) బ్రౌజర్
# push నోటిఫికేషన్ కూడా పంపడానికి (Web Push API + service worker,
# messaging/static/messaging/js/sw.js చూడండి). ఇది VAPID
# (Voluntary Application Server Identification) కీ జంట మీద
# ఆధారపడుతుంది -- ఒక్కసారి జనరేట్ చేసి env లో పెట్టుకోవాలి:
#
#   pip install pywebpush py-vapid --break-system-packages
#   vapid --gen  # ఇది private_key.pem / public_key.pem ఇస్తుంది
#
# లేదా పైథాన్ లో నేరుగా:
#   from py_vapid import Vapid02
#   v = Vapid02(); v.generate_keys()
#
# DEV-ONLY ఫాల్‌బ్యాక్: env వేరియబుల్స్ సెట్ చేయకపోతే push పంపడం
# నిశ్శబ్దంగా స్కిప్ అవుతుంది (tasks.py లో చెక్ చేస్తాం) -- ఈమెయిల్
# నోటిఫికేషన్ మాత్రం ఎప్పటిలాగే పనిచేస్తుంది.
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:admin@bharathub.local")

