"""
accounts/middleware.py

రిజిస్ట్రేషన్ ఇప్పుడు కేవలం కనీస వివరాలు మాత్రమే తీసుకుంటుంది
(accounts/forms.py, vendor/forms.py చూడండి). మిగతా వివరాలు (candidate:
స్కిల్స్/రెజ్యూమ్/విద్యార్హతలు, employer: PAN/GST/CIN/HQ, vendor:
మొబైల్/కేటగిరీ/పనిచేసే రోజులు) లాగిన్ అయిన తర్వాతే నింపుకోవాలి.

ఈ మిడిల్‌వేర్ దాన్ని బలవంతం చేస్తుంది: profile_completed=False గా
ఉన్న ఏ యూజర్ అయినా, ఏ పేజీ కి వెళ్ళాలనుకున్నా, ముందు వాళ్ళ role కి
తగిన "Complete Your Profile" పేజీ కే రీడైరెక్ట్ అవుతారు. అక్కడ
పూర్తి చేసుకున్నాకే (profile_completed=True అయ్యాకే) సైట్ లో మిగతా
అన్నిటికీ యాక్సెస్ వస్తుంది.
"""
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import resolve
from django.urls.exceptions import Resolver404

# ఈ URL పేర్లు మాత్రమే మినహాయింపు -- లేకపోతే యూజర్ ఎప్పటికీ
# "Complete Your Profile" పేజీనే మళ్ళీ మళ్ళీ లోడ్ అయ్యే infinite
# redirect loop లో చిక్కుకుంటారు.
EXEMPT_URL_NAMES = {
    "candidates:candidate_profile_edit",
    "candidates:candidate_education_delete",
    "accounts:employer_complete_profile",
    "vendor:vendor_complete_profile",
    "accounts:logout",
    "accounts:password_forgot_verify",
    "accounts:password_forgot_otp",
    "accounts:password_forgot_set",
}


class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        path = request.path_info

        # స్టాటిక్/మీడియా ఫైల్ రిక్వెస్ట్‌లు (CSS/JS/ఇమేజెస్) ఎప్పుడూ
        # దీని పరిధిలోకి రావు.
        if path.startswith("/static/") or path.startswith("/media/"):
            return self.get_response(request)

        if user is not None and user.is_authenticated and not user.is_staff:
            try:
                match = resolve(path)
                url_name = f"{match.namespace}:{match.url_name}" if match.namespace else match.url_name
            except Resolver404:
                url_name = None

            if url_name not in EXEMPT_URL_NAMES:
                employee_profile = getattr(user, "employee_profile", None)
                if employee_profile is not None and not employee_profile.profile_completed:
                    if request.method == "POST":
                        messages.warning(
                            request,
                            "⚠️ మీ ప్రొఫైల్ ఇంకా పూర్తి కాలేదు కాబట్టి ఈ యాక్షన్ సేవ్ కాలేదు -- "
                            "ముందు కింద ఇచ్చిన వివరాలు పూర్తి చేయండి.",
                        )
                    return redirect("candidates:candidate_profile_edit")

                employer_profile = getattr(user, "employer_profile", None)
                if employer_profile is not None and not employer_profile.profile_completed:
                    if request.method == "POST":
                        messages.warning(
                            request,
                            "⚠️ మీ ప్రొఫైల్ ఇంకా పూర్తి కాలేదు కాబట్టి ఈ యాక్షన్ (ఉదా: జాబ్ పోస్ట్) "
                            "సేవ్ కాలేదు -- ముందు కింద ఇచ్చిన కంపెనీ వివరాలు పూర్తి చేయండి, ఆ "
                            "తర్వాత జాబ్ ని మళ్ళీ పోస్ట్ చేయండి.",
                        )
                    return redirect("accounts:employer_complete_profile")

                vendor_profile = getattr(user, "vendor_profile", None)
                if vendor_profile is not None and not vendor_profile.profile_completed:
                    if request.method == "POST":
                        messages.warning(
                            request,
                            "⚠️ మీ ప్రొఫైల్ ఇంకా పూర్తి కాలేదు కాబట్టి ఈ యాక్షన్ సేవ్ కాలేదు -- "
                            "ముందు కింద ఇచ్చిన వివరాలు పూర్తి చేయండి.",
                        )
                    return redirect("vendor:vendor_complete_profile")

        return self.get_response(request)
