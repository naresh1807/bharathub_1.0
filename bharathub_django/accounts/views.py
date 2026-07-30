import json

from django.contrib import messages
from django.contrib.auth import authenticate, logout
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView, View

from . import otp_auth, password_reset
from .forms import (
    EmployeeRegistrationForm, EmployeeLoginForm,
    EmployerRegistrationForm, EmployerLoginForm,
    EmployerProfileCompletionForm,
)
from .login_throttle import (
    MAX_FAILED_ATTEMPTS, is_locked_out, record_failed_attempt, clear_attempts,
)
from .models import EmployeeProfile, EmployerProfile
from .notifications import send_bharathub_id_email

# Accounts app: registration, login & profile management for
# Employees (job-seekers) and Employers.
# (Vendor registration/login lives in the "vendor" app.)


# ============================================================================
# EmployeeRegistrationView
# ఎందుకు ఇలా మార్చాం: ఇంతకుముందు ఇది ఖాళీ TemplateView (కేవలం HTML
# చూపించడమే) -- ఇప్పుడు GET/POST రెండిటినీ హ్యాండిల్ చేస్తుంది.
# ============================================================================
class EmployeeRegistrationView(TemplateView):
    template_name = "accounts/employee_registration.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", EmployeeRegistrationForm())
        # RegistrationOTPView.post() (OTP సరిచూసుకున్న తర్వాత, User+
        # EmployeeProfile క్రియేట్ అయిన వెంటనే) ఇక్కడ ఒక session flag
        # పెడుతుంది -- దాన్ని ఇక్కడ చదివి (ఒక్కసారే వాడేసి తీసేసి),
        # "మీ BharatHub ID ఇది" popup చూపిస్తాం.
        registered_id = self.request.session.pop("just_registered_id", None)
        registered_role = self.request.session.pop("just_registered_role", None)
        if registered_id and registered_role == "employee":
            context["registered_id"] = registered_id
        return context

    def post(self, request, *args, **kwargs):
        # request.FILES కూడా పంపాలి -- ఫారమ్ వాలిడేషన్ కి (ఐచ్ఛిక
        # profile_photo ఫీల్డ్ ఉంది) అవసరం, కానీ OTP-గేటెడ్ ఫ్లో లో
        # ఫైల్ ని ఇక్కడే సేవ్ చేయం (కింద నోట్ చూడండి).
        form = EmployeeRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            # ⚠️ ఇప్పుడు ఇక్కడే form.save() పిలవం -- ముందు OTP పంపి,
            # OTP సరిచూసుకున్న తర్వాతే (RegistrationOTPView లో) అసలైన
            # User+EmployeeProfile క్రియేట్ అవుతుంది.
            #
            # గమనిక: ఐచ్ఛిక profile_photo ఫైల్ అప్‌లోడ్ ఈ OTP-గేటెడ్
            # ఫ్లో లో సపోర్ట్ చేయం (ఫైల్ డేటాని session లో పెట్టడం
            # సురక్షితం కాదు) -- ఫోటో పెట్టి ఉంటే ఇక్కడ స్కిప్ అవుతుంది,
            # యూజర్ దాన్ని లాగిన్ అయిన తర్వాత "Complete Your Profile"
            # లో జోడించుకోగలరు.
            form_data = request.POST.dict()
            otp_auth.send_registration_otp(
                request, email=form.cleaned_data["email"], role="employee", form_data=form_data,
            )
            return redirect("accounts:otp_register")

        # వాలిడేషన్ ఫెయిల్ అయితే, ఎర్రర్స్ తో ఫారమ్‌ని మళ్ళీ చూపిస్తాం.
        return self.render_to_response(self.get_context_data(form=form))


# ============================================================================
# EmployeeLoginView
# ============================================================================
class EmployeeLoginView(TemplateView):
    template_name = "accounts/employee_login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", EmployeeLoginForm())
        return context

    def post(self, request, *args, **kwargs):
        form = EmployeeLoginForm(request.POST)
        if form.is_valid():
            login_id = form.cleaned_data["login_id"].strip()

            # యూజర్ "BharatHub ID" (BH2026XXXX) లేదా "email" ఏదైనా
            # ఇవ్వొచ్చు కాబట్టి, ముందు అది ఏమిటో కనుక్కుని, దాని ఆధారంగా
            # అసలైన User instance (username = mobile_number గా
            # స్టోర్ చేశాం) ని వెతుకుతాం. లాకౌట్ ఇక ఈ *resolved User*
            # మీదే ఆధారపడుతుంది (login_throttle.py చూడండి) -- login_id
            # స్ట్రింగ్ మీద కాదు, ఎందుకంటే ఒకే ఖాతాని BH ID తోనూ email
            # తోనూ కూడా ప్రయత్నించొచ్చు.
            resolved_user = None
            if login_id.upper().startswith("BH"):
                profile = EmployeeProfile.objects.filter(
                    bharathub_id__iexact=login_id
                ).select_related("user").first()
                if profile:
                    resolved_user = profile.user
            else:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                resolved_user = User.objects.filter(email__iexact=login_id).first()

            # బ్రూట్-ఫోర్స్ గార్డ్: ఈ ఖాతా ఇప్పటికే 3 తప్పు ప్రయత్నాల
            # తర్వాత must-reset-password స్టేట్ లో ఉంటే, పాస్‌వర్డ్
            # సరైనదైనా సరే authenticate() ని అస్సలు పిలవకుండానే ఆపేస్తాం.
            if resolved_user is not None and is_locked_out(resolved_user):
                messages.error(
                    request,
                    "🔒 You have entered the wrong password 3 times on this account. For security, "
                    "the account has been locked -- please verify your identity via 'Forgot Password?' "
                    "below and set a new password to log in again.",
                )
                return self.render_to_response(self.get_context_data(form=form))

            username = resolved_user.username if resolved_user else None

            # authenticate(): username+password సరిపోలుతున్నాయా అని
            # Django యొక్క hash-verify లాజిక్ తో చెక్ చేస్తుంది (ఇది
            # ప్లెయిన్ టెక్స్ట్ పోల్చదు, హ్యాష్ ని పోలుస్తుంది).
            user = authenticate(request, username=username, password=form.cleaned_data["password"]) if username else None

            if user is not None:
                clear_attempts(user)
                # ⚠️ ఇక్కడ ఇక నేరుగా login() పిలవం -- పాస్‌వర్డ్ సరైనదని
                # తెలిశాక, ఇప్పుడు OTP పంపి, verify అయిన తర్వాతే
                # (LoginOTPView లో) అసలైన login() జరుగుతుంది.
                next_url = request.POST.get("next") or request.GET.get("next") or ""
                otp_auth.send_login_otp(
                    request, user,
                    remember_me=bool(form.cleaned_data.get("remember_me")),
                    next_url=next_url,
                    redirect_name="candidates:candidate_dashboard",
                )
                return redirect("accounts:otp_login")

            # -------------------------------------------------------------
            # భద్రతా గమనిక: "ID లేదు" vs "పాస్‌వర్డ్ తప్పు" అని వేరుగా
            # చెప్పడం లేదు -- ఇది Django/OWASP సిఫారసు చేసిన పద్ధతి.
            # ఎందుకంటే వేరుగా చెప్తే, దాడి చేసేవాళ్ళు (attacker) ఏ ఏ
            # ID లు రిజిస్టర్ అయ్యాయో ఊహించగలరు (user enumeration attack).
            # -------------------------------------------------------------
            # -------------------------------------------------------------
            # భద్రతా గమనిక: "ID లేదు" vs "పాస్‌వర్డ్ తప్పు" అని వేరుగా
            # చెప్పడం లేదు -- ఇది Django/OWASP సిఫారసు చేసిన పద్ధతి.
            # ఎందుకంటే వేరుగా చెప్తే, దాడి చేసేవాళ్ళు (attacker) ఏ ఏ
            # ID లు రిజిస్టర్ అయ్యాయో ఊహించగలరు (user enumeration attack).
            # -------------------------------------------------------------
            if resolved_user is not None:
                attempts = record_failed_attempt(resolved_user)
                if attempts >= MAX_FAILED_ATTEMPTS:
                    # 3వ తప్పు ప్రయత్నం -- ఇక్కడి నుండి ఖాతా లాక్ అయిపోయింది
                    # (login_throttle.is_locked_out ఇక True ఇస్తుంది); సాధారణ
                    # "try again" బదులు, తప్పనిసరిగా పాస్‌వర్డ్ రీసెట్
                    # చేసుకోమని స్పష్టంగా చెప్తాం.
                    messages.error(
                        request,
                        "🔒 You entered the wrong password 3 times. For your account's security, "
                        "it has been locked. Please use the 'Forgot Password?' link "
                        "below to reset your password.",
                    )
                else:
                    # భద్రతా గమనిక: ఎన్ని ప్రయత్నాలు మిగిలాయో ఖచ్చితంగా
                    # చెప్పం (అది కూడా ఒక enumeration సిగ్నల్ అవుతుంది) --
                    # కేవలం సాధారణ ఇన్వాలిడ్-క్రెడెన్షియల్స్ మెసేజ్.
                    messages.error(request, "⚠️ Invalid credentials. Please try again.")
            else:
                # login_id ఏ ఖాతాకీ సరిపోలలేదు -- దీనికి ట్రాక్ చేయడానికి
                # ఏమీ లేదు (ఏ యూజర్ రికార్డ్ కీ అటాచ్ చేయలేం), కేవలం
                # generic మెసేజ్.
                messages.error(request, "⚠️ Invalid credentials. Please try again.")

        return self.render_to_response(self.get_context_data(form=form))


# ============================================================================
# EmployerRegistrationView
# ============================================================================
class EmployerRegistrationView(TemplateView):
    template_name = "accounts/employer_registration.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", EmployerRegistrationForm())
        registered_id = self.request.session.pop("just_registered_id", None)
        registered_role = self.request.session.pop("just_registered_role", None)
        if registered_id and registered_role == "employer":
            context["registered_id"] = registered_id
        return context

    def post(self, request, *args, **kwargs):
        form = EmployerRegistrationForm(request.POST)
        if form.is_valid():
            otp_auth.send_registration_otp(
                request, email=form.cleaned_data["corporate_email"], role="employer",
                form_data=request.POST.dict(),
            )
            return redirect("accounts:otp_register")
        return self.render_to_response(self.get_context_data(form=form))


# ============================================================================
# EmployerLoginView
# ============================================================================
class EmployerLoginView(TemplateView):
    template_name = "accounts/employer_login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", EmployerLoginForm())
        return context

    def post(self, request, *args, **kwargs):
        form = EmployerLoginForm(request.POST)
        if form.is_valid():
            login_id = form.cleaned_data["login_id"].strip()

            resolved_user = None
            if login_id.upper().startswith("BHE"):
                profile = EmployerProfile.objects.filter(
                    employer_id__iexact=login_id
                ).select_related("user").first()
                if profile:
                    resolved_user = profile.user
            else:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                # ఇక్కడ username == corporate_email గా సేవ్ చేశాం
                resolved_user = User.objects.filter(username__iexact=login_id).first()

            if resolved_user is not None and is_locked_out(resolved_user):
                messages.error(
                    request,
                    "🔒 You have entered the wrong password 3 times on this account. For security, "
                    "the account has been locked -- please verify your identity via 'Forgot Password?' "
                    "below and set a new password to log in again.",
                )
                return self.render_to_response(self.get_context_data(form=form))

            username = resolved_user.username if resolved_user else None
            user = authenticate(request, username=username, password=form.cleaned_data["password"]) if username else None
            if user is not None:
                clear_attempts(user)
                otp_auth.send_login_otp(
                    request, user,
                    remember_me=bool(form.cleaned_data.get("remember_me")),
                    next_url="", redirect_name="employers:employer_dashboard",
                )
                return redirect("accounts:otp_login")

            if resolved_user is not None:
                attempts = record_failed_attempt(resolved_user)
                if attempts >= MAX_FAILED_ATTEMPTS:
                    messages.error(
                        request,
                        "🔒 You entered the wrong password 3 times. For your account's security, "
                        "it has been locked. Please use the 'Forgot Password?' link "
                        "below to reset your password.",
                    )
                else:
                    messages.error(request, "⚠️ Invalid credentials. Please try again.")
            else:
                messages.error(request, "⚠️ Invalid credentials. Please try again.")

        return self.render_to_response(self.get_context_data(form=form))


# ============================================================================
# LogoutView
# ఎందుకు ఇది కావాలి: మూడు dashboards (employer/candidate/vendor) లోని
# "Logout" బటన్ ఇంతకుముందు కేవలం JS లో window.location.href తో నేరుగా
# లాగిన్ పేజీకి పంపేది -- అసలు Django సెషన్ ని logout() చేసేది కాదు!
# అంటే యూజర్ "Logout" నొక్కి లాగిన్ పేజీకి వచ్చినా, సెషన్ ఇంకా
# లాగిన్ అయ్యే ఉండేది -- browser back బటన్ తో లేదా dashboard URL మళ్ళీ
# టైప్ చేస్తే నేరుగా లోపలికి వెళ్ళిపోయేవారు (session logout అవలేదు కాబట్టి).
#
# ఇది మూడు dashboards కీ ఉమ్మడిగా (shared) ఇక్కడ accounts యాప్ లో ఒకే
# చోట పెట్టాం -- django.contrib.auth.logout() ఏ రకమైన యూజర్ (employee/
# employer/vendor) కైనా ఒకేలా పనిచేస్తుంది, కాబట్టి మూడు వేర్వేరు logout
# view లు రాయాల్సిన అవసరం లేదు.
#
# POST-only గా ఎందుకు: GET లింక్ ద్వారా logout చేయడం CSRF దాడులకు
# గురయ్యే అవకాశం ఉంది (ఎవరైనా <img src="/logout/"> లాంటిది పెడితే
# తెలియకుండానే logout అయిపోవచ్చు) -- అందుకే ఇది ఎప్పుడూ ఒక POST ఫారమ్
# (csrf_token తో) నుండే కాల్ అవ్వాలి, టెంప్లేట్‌లలో అలాగే మార్చాం.
# ============================================================================
class LogoutView(View):
    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect("home:bharathub_home")


# ============================================================================
# Forgot-Password JSON API (Employee + Employer + Vendor మూడిటికీ ఉమ్మడి)
#
# ఇంతకుముందు మూడు లాగిన్ పేజీల్లోని "Forgot Password?" ప్యానెల్
# పూర్తిగా JS-only మాక్-అప్ (verifyIdentity/verifyForgotOTP/resetPassword
# JS ఫంక్షన్లు setTimeout తో దశలు మారేవి, ఏదీ నిజంగా వెరిఫై అయ్యేది
# కాదు, కొత్త పాస్‌వర్డ్ ఎక్కడా సేవ్ అయ్యేది కాదు). ఇప్పుడు ఆ మూడు JS
# ఫంక్షన్లు ఈ మూడు endpoints కి నిజమైన fetch() POST చేస్తాయి.
#
# role ప్రతి రిక్వెస్ట్ లోనూ పంపిస్తారు ("employee"/"employer"/"vendor")
# -- దాని ఆధారంగా accounts/password_reset.py లో ఏ ప్రొఫైల్ మోడల్ లో
# వెతకాలో నిర్ణయిస్తుంది.
# ============================================================================
class ForgotPasswordVerifyView(View):
    """STEP 1: identity ఫీల్డ్స్ (role కి తగినట్టు) సరిపోలితే OTP పంపుతుంది."""

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except (ValueError, TypeError):
            data = request.POST

        role = data.get("role")
        user = password_reset.find_user_by_identity(role, data)
        if user is None or not user.email:
            # ఏ ఫీల్డ్ తప్పు అని చెప్పం (enumeration నివారించడానికి) --
            # 3 ఫీల్డ్స్ లో దేనికదే విడిగా ఏది సరైనదో తప్పో చెప్పకుండా
            # ఒకే generic ఎర్రర్.
            return JsonResponse({"ok": False, "error": "Details did not match. Please check again."}, status=400)

        password_reset.send_otp(request, user)
        return JsonResponse({"ok": True})


class ForgotPasswordOtpVerifyView(View):
    """STEP 2: 6-అంకెల OTP సరిచూస్తుంది."""

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except (ValueError, TypeError):
            data = request.POST

        otp = (data.get("otp") or "").strip()
        if password_reset.verify_otp(request, otp):
            return JsonResponse({"ok": True})
        return JsonResponse({"ok": False, "error": "OTP is incorrect or has expired."}, status=400)


class ForgotPasswordSetView(View):
    """STEP 3: కొత్త పాస్‌వర్డ్ సెట్ చేస్తుంది (OTP ఇప్పటికే verify
    అయ్యి ఉంటేనే -- session state గార్డ్, password_reset.py చూడండి).
    సక్సెస్ అయితే login_throttle.clear_lock_after_reset() కూడా ఇక్కడే
    (password_reset.set_new_password లోపల) పిలవబడుతుంది."""

    def post(self, request, *args, **kwargs):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        try:
            data = json.loads(request.body)
        except (ValueError, TypeError):
            data = request.POST

        new_password = data.get("password") or ""
        confirm_password = data.get("confirm_password") or ""

        if new_password != confirm_password:
            return JsonResponse({"ok": False, "error": "Passwords did not match."}, status=400)
        try:
            validate_password(new_password)
        except ValidationError as exc:
            return JsonResponse({"ok": False, "error": " ".join(exc.messages)}, status=400)

        user = password_reset.set_new_password(request, new_password)
        if user is None:
            return JsonResponse({"ok": False, "error": "Session expired. Please start over."}, status=400)

        return JsonResponse({"ok": True})


# ============================================================================
# EmployerProfileCompletionView
#
# రిజిస్ట్రేషన్ లో అడగని PAN/GST/CIN/HQ State వివరాలు లాగిన్ అయిన
# తర్వాత ఇక్కడ నింపుకుంటారు. ProfileCompletionMiddleware
# (accounts/middleware.py) profile_completed=False ఉన్న ప్రతి
# employer ని ఇక్కడికే బలవంతంగా పంపుతుంది -- పూర్తి చేసుకున్నాకే
# డాష్‌బోర్డ్ కి యాక్సెస్ వస్తుంది.
# ============================================================================
class EmployerProfileCompletionView(View):
    template_name = "accounts/employer_profile_completion.html"

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, "employer_profile"):
            return redirect("accounts:employer_login")
        profile = request.user.employer_profile
        if profile.profile_completed:
            return redirect("employers:employer_dashboard")
        form = EmployerProfileCompletionForm(instance=profile)
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, "employer_profile"):
            return redirect("accounts:employer_login")
        profile = request.user.employer_profile
        form = EmployerProfileCompletionForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.profile_completed = True
            profile.save()
            messages.success(request, "✅ Your profile is complete! You now have full access.")
            return redirect("employers:employer_dashboard")
        return render(request, self.template_name, {"form": form})


# ============================================================================
# OTP VERIFICATION -- Login & Registration (Employee/Employer/Vendor మూడు
# రోల్స్‌కీ ఒకే రెండు షేర్డ్ views).
#
# ఈ views.py Login OTP కి "role-agnostic" గా పనిచేస్తుంది -- session
# లో ఇప్పటికే user_id/redirect_name అన్నీ ఉన్నాయి (accounts/otp_auth.py:
# send_login_otp() చూడండి), కాబట్టి ఇక్కడ మళ్ళీ role గురించి ఆలోచించే
# అవసరం లేదు. Registration OTP కి మాత్రం, ఏ Form క్లాస్ వాడాలో role
# బట్టే నిర్ణయించాలి కాబట్టి ROLE_CONFIG dict వాడతాం.
# ============================================================================

class LoginOTPView(View):
    """Employee/Employer/Vendor మూడు లాగిన్ ఫారాలూ, పాస్‌వర్డ్ సరైన
    తర్వాత ఇక్కడికే redirect చేస్తాయి. django login() ఇక్కడ,
    verify_login_otp() సక్సెస్ అయిన తర్వాతే జరుగుతుంది."""

    def get(self, request, *args, **kwargs):
        email = otp_auth.peek_login_email(request)
        if not email:
            messages.info(request, "ℹ️ No pending login found. Please log in again.")
            return redirect("home:bharathub_home")
        return render(request, "accounts/otp_entry.html", {
            "otp_purpose": "login",
            "otp_email": email,
            "verify_url": reverse("accounts:otp_login"),
            "resend_url": reverse("accounts:otp_login_resend"),
            "cancel_url": reverse("accounts:otp_login_cancel"),
        })

    def post(self, request, *args, **kwargs):
        otp = (request.POST.get("otp") or "").strip()
        result = otp_auth.verify_login_otp(request, otp)
        if result is None:
            messages.error(request, "⚠️ OTP is incorrect or has expired. Please try again or resend.")
            return redirect("accounts:otp_login")

        messages.success(request, "✅ Login successful!")
        next_url = result.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect(result["redirect_name"])


class LoginOTPResendView(View):
    def post(self, request, *args, **kwargs):
        ok, error = otp_auth.resend_login_otp(request)
        if not ok:
            messages.error(request, f"⚠️ {error}")
            if not request.session.get(otp_auth.LOGIN_SESSION_KEY):
                return redirect("home:bharathub_home")
            return redirect("accounts:otp_login")
        messages.success(request, "📧 A new OTP has been sent.")
        return redirect("accounts:otp_login")


class LoginOTPCancelView(View):
    def get(self, request, *args, **kwargs):
        otp_auth.cancel_login_otp(request)
        return redirect("home:bharathub_home")


class RegistrationOTPView(View):
    """Employee/Employer/Vendor మూడు రిజిస్ట్రేషన్ ఫారాలూ, వాలిడ్ అయిన
    తర్వాత (form.save() కి ముందే) ఇక్కడికే redirect చేస్తాయి. OTP
    సరైతేనే అసలైన User+Profile ఇక్కడ క్రియేట్ అవుతుంది."""

    ROLE_CONFIG = {
        "employee": {
            "form_module": "accounts.forms", "form_class": "EmployeeRegistrationForm",
            "email_field": "email", "id_field": "bharathub_id", "id_label": "BharatHub ID",
            "registration_url": "accounts:employee_registration",
        },
        "employer": {
            "form_module": "accounts.forms", "form_class": "EmployerRegistrationForm",
            "email_field": "corporate_email", "id_field": "employer_id", "id_label": "Employer ID",
            "registration_url": "accounts:employer_registration",
        },
        "vendor": {
            # vendor.forms ని ఇక్కడే (function లోపల) దిగుమతి చేస్తాం --
            # module లెవెల్ లో దిగుమతి చేస్తే circular-import ప్రమాదం
            # (vendor/views.py ఇప్పటికే accounts నుండి దిగుమతి చేస్తుంది,
            # password_reset.py లో కూడా ఇదే పద్ధతి వాడాం).
            "form_module": "vendor.forms", "form_class": "VendorRegistrationForm",
            "email_field": "vendor_email", "id_field": "vendor_id", "id_label": "Vendor ID",
            "registration_url": "vendor:vendor_registration",
        },
    }

    def _get_form_class(self, role):
        import importlib
        config = self.ROLE_CONFIG[role]
        module = importlib.import_module(config["form_module"])
        return getattr(module, config["form_class"])

    def get(self, request, *args, **kwargs):
        role = otp_auth.peek_registration_role(request)
        if not role:
            messages.info(request, "ℹ️ No pending registration found. Please register again.")
            return redirect("home:bharathub_home")
        state = request.session.get(otp_auth.REGISTER_SESSION_KEY) or {}
        email_field = self.ROLE_CONFIG[role]["email_field"]
        email = (state.get("form_data") or {}).get(email_field, "")
        return render(request, "accounts/otp_entry.html", {
            "otp_purpose": "register",
            "otp_email": email,
            "verify_url": reverse("accounts:otp_register"),
            "resend_url": reverse("accounts:otp_register_resend"),
            "cancel_url": reverse("accounts:otp_register_cancel"),
        })

    def post(self, request, *args, **kwargs):
        otp = (request.POST.get("otp") or "").strip()
        role, form_data = otp_auth.verify_registration_otp(request, otp)
        if role is None:
            messages.error(request, "⚠️ OTP is incorrect or has expired. Please try again or resend.")
            return redirect("accounts:otp_register")

        config = self.ROLE_CONFIG[role]
        form_class = self._get_form_class(role)
        form = form_class(form_data)
        if not form.is_valid():
            # ఇది సాధారణంగా జరగకూడదు (ఇంతకుముందే ఒకసారి వాలిడేట్
            # అయ్యింది) -- కానీ OTP వేచి ఉన్న సమయంలో మరొకరు అదే మొబైల్/
            # ఇమెయిల్ తో వేరే ఖాతా క్రియేట్ చేసేస్తే ఇది జరగొచ్చు.
            # సురక్షితంగా విఫలం అవ్వాలి.
            messages.error(
                request,
                "⚠️ Something changed since you registered (this mobile/email may now be in "
                "use) — please register again.",
            )
            return redirect(config["registration_url"])

        user, profile = form.save()
        id_value = getattr(profile, config["id_field"])
        send_bharathub_id_email(user, id_value, config["id_label"])

        # EmployeeRegistrationView/EmployerRegistrationView/
        # VendorRegistrationView.get_context_data() ఈ రెండు session
        # flags ని చదివి "మీ ID ఇది" popup చూపిస్తుంది.
        request.session["just_registered_id"] = id_value
        request.session["just_registered_role"] = role
        return redirect(config["registration_url"])


class RegistrationOTPResendView(View):
    def post(self, request, *args, **kwargs):
        ok, error = otp_auth.resend_registration_otp(request)
        if not ok:
            messages.error(request, f"⚠️ {error}")
            if not request.session.get(otp_auth.REGISTER_SESSION_KEY):
                return redirect("home:bharathub_home")
            return redirect("accounts:otp_register")
        messages.success(request, "📧 A new OTP has been sent.")
        return redirect("accounts:otp_register")


class RegistrationOTPCancelView(View):
    def get(self, request, *args, **kwargs):
        otp_auth.cancel_registration_otp(request)
        return redirect("home:bharathub_home")
