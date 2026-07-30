import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView, View

from . import password_reset
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
        return context

    def post(self, request, *args, **kwargs):
        # request.FILES కూడా పంపాలి -- ఎందుకంటే ఫారమ్ లో ప్రొఫైల్ ఫోటో
        # (ImageField / <input type="file">) ఉంది. ఫైల్ డేటా request.POST
        # లో కాదు, request.FILES లో వేరేగా వస్తుంది.
        form = EmployeeRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user, profile = form.save()
            # ఇక్కడ auto-login చేయడం లేదు -- రిజిస్ట్రేషన్ అయిన వెంటనే
            # సెషన్ లాగిన్ చేసేస్తే, popup లోని "Continue to Login" బటన్
            # నొక్కినప్పుడు యూజర్ ఇప్పటికే authenticated గా ఉంటారు, దాంతో
            # ProfileCompletionMiddleware వెంటనే వాళ్ళని లాగిన్ పేజీ నుండి
            # నేరుగా "Complete Your Profile" ఫారమ్ కి పంపించేస్తుంది --
            # యూజర్ తన లాగిన్ ఐడీ/పాస్‌వర్డ్ తో నిజంగా లాగిన్ అవ్వకుండానే.
            # దాన్ని నివారించడానికి, రిజిస్ట్రేషన్ తర్వాత సెషన్ ని
            # అన్‌అథెంటికేటెడ్ గానే ఉంచుతాం -- "Continue to Login" నొక్కి,
            # అసలైన లాగిన్ ఫారమ్ లో ఐడీ/పాస్‌వర్డ్ ఇచ్చాకే ప్రొఫైల్
            # ఫారమ్ కి వెళ్తారు.
            send_bharathub_id_email(user, profile.bharathub_id, "BharatHub ID")
            # redirect చేయకుండా, ఇదే పేజీని (ఖాళీ ఫారమ్ తో, వెనుక) +
            # registered_id popup తో రెండరింగ్ చేస్తాం -- popup లోని
            # "Continue to Login" బటన్ నొక్కేదాకా యూజర్ ఇక్కడే ఉండి,
            # తన BharatHub ID ని చూసి, కాపీ చేసుకోగలరు.
            context = self.get_context_data(form=EmployeeRegistrationForm())
            context["registered_id"] = profile.bharathub_id
            return self.render_to_response(context)

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
                login(request, user)
                # "Remember Me" చెక్‌బాక్స్ తీసేస్తే, బ్రౌజర్ మూసేసిన
                # వెంటనే సెషన్ ముగిసేలా (0 అంటే browser-session cookie).
                if not form.cleaned_data.get("remember_me"):
                    request.session.set_expiry(0)
                messages.success(request, "✅ Login successful!")

                # ఇంతకుముందు ఇక్కడ "home:bharathub_home" కి redirect
                # అయ్యేది -- అందుకే candidate login అయ్యాక తిరిగి Home
                # పేజీ కే వెళ్ళిపోయేది (dashboard కి కాదు). ఇప్పుడు
                # నేరుగా candidate dashboard కి పంపిస్తుంది.
                #
                # "next" పరామితి: candidates dashboard వంటి
                # LoginRequiredMixin పేజీ ని లాగిన్ అవ్వకుండా నేరుగా
                # URL టైప్ చేసి తెరిస్తే, Django ఆటోమేటిక్‌గా ఇక్కడికి
                # "?next=..." పంపిస్తుంది -- login అయ్యాక అక్కడికే
                # తీసుకెళ్ళాలి. url_has_allowed_host_and_scheme() తో
                # ఈ "next" విలువ మన సైట్ లోపలిదేనా అని నిర్ధారించుకున్న
                # తర్వాతే వాడతాం (లేకపోతే ఎవరైనా
                # "?next=https://evil.com" తో phishing సైట్ కి
                # redirect చేయించే Open Redirect దాడి సాధ్యమవుతుంది).
                next_url = request.POST.get("next") or request.GET.get("next")
                if next_url and url_has_allowed_host_and_scheme(
                    url=next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
                ):
                    return redirect(next_url)
                return redirect("candidates:candidate_dashboard")

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
        return context

    def post(self, request, *args, **kwargs):
        form = EmployerRegistrationForm(request.POST)
        if form.is_valid():
            user, profile = form.save()
            # auto-login చేయడం లేదు -- కారణం EmployeeRegistrationView లో
            # ఇచ్చిన కామెంట్ చూడండి (login page bypass అవ్వకుండా).
            send_bharathub_id_email(user, profile.employer_id, "Employer ID")
            context = self.get_context_data(form=EmployerRegistrationForm())
            context["registered_id"] = profile.employer_id
            return self.render_to_response(context)
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
                login(request, user)
                if not form.cleaned_data.get("remember_me"):
                    request.session.set_expiry(0)
                messages.success(request, "✅ Login successful!")
                return redirect("employers:employer_dashboard")

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
