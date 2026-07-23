from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from accounts.models import EmployeeProfile
from employers.models import Job
from jobs.models import JobApplication
from messaging.views import unread_total_for
from videos.utils import published_videos_for
from .forms import CandidateEducationForm, CandidateProfileForm
from .models import CandidateEducation, CandidateProfile

# Candidates app: candidate details, profile & applied-jobs info.


# ══════════════════════════════════════════════════════════════════════
# CandidateDashboardView
#
# ఇంతకుముందు ఇది ఖాళీ TemplateView (కేవలం mock/hardcoded HTML చూపించడమే,
# ఎవరైనా లాగిన్ లేకుండా కూడా చూడొచ్చు) -- ఇప్పుడు:
#   1. LoginRequiredMixin తో లాగిన్ తప్పనిసరి చేశాం (ఇది వ్యక్తిగత డేటా
#      కాబట్టి భద్రత అవసరం).
#   2. రిజిస్ట్రేషన్ సమయంలో సేవ్ అయిన EmployeeProfile (పేరు, మొబైల్,
#      ఇమెయిల్, BharatHub ID, ఫోటో) మరియు CandidateProfile (headline,
#      skills, resume, hire status) + CandidateEducation (academic
#      history) రికార్డులని request.user ఆధారంగా DB నుండి తీసుకొచ్చి
#      టెంప్లేట్ కి పంపిస్తుంది.
# ══════════════════════════════════════════════════════════════════════
class CandidateDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "candidates/candidate_dashboard.html"
    login_url = "accounts:employee_login"

    # ------------------------------------------------------------------
    # dispatch(): get_context_data() కంటే ముందు, ప్రతి request మీద ఇది
    # రన్ అవుతుంది. లాగిన్ అయిన యూజర్ కి EmployeeProfile లేకపోతే (ఉదా:
    # admin/superuser అకౌంట్ తో, లేదా Employer అకౌంట్ తో ఈ URL కి
    # నేరుగా వచ్చినప్పుడు) ఇంతకుముందు ఇది raw "Page not found (404)"
    # crash ఇచ్చేది. ఇప్పుడు దాని బదులు అతన్ని లాగ్-అవుట్ చేసి, స్పష్టమైన
    # మెసేజ్ తో తిరిగి employee login పేజీ కి పంపిస్తుంది -- ఇది candidate
    # కాని ఏ యూజర్ కైనా (employer, admin, stale test account) సురక్షితమైన,
    # అర్థమయ్యే ప్రవర్తన.
    # ------------------------------------------------------------------
    def dispatch(self, request, *args, **kwargs):
        # LoginRequiredMixin ముందుగా అన్‌అథెంటికేటెడ్ యూజర్‌లని ఇప్పటికే
        # login_url కి పంపిస్తుంది, కాబట్టి ఇక్కడికి వచ్చేసరికి is_authenticated
        # ఉంటే చాలు -- login అయిన యూజర్ కి EmployeeProfile ఉందో లేదో ఇక్కడే
        # (get_context_data() కాల్ అవ్వడానికి ముందే) చెక్ చేస్తాం.
        if request.user.is_authenticated and not hasattr(request.user, "employee_profile"):
            from django.contrib.auth import logout
            logout(request)
            messages.error(
                request,
                "⚠️ ఈ అకౌంట్ కి Employee ప్రొఫైల్ లేదు. దయచేసి Employee ఖాతాతో లాగిన్ అవ్వండి "
                "లేదా ముందు రిజిస్టర్ చేసుకోండి.",
            )
            return redirect("accounts:employee_login")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # EmployeeProfile: రిజిస్ట్రేషన్ (Step-1 Personal Details) లో
        # సేవ్ అయిన డేటా. dispatch() లోనే ఇప్పటికే ఉనికిని నిర్ధారించాం
        # కాబట్టి ఇక్కడ get_object_or_404 సురక్షితంగానే ఎప్పుడూ దొరుకుతుంది.
        employee_profile = get_object_or_404(EmployeeProfile, user=user)

        # CandidateProfile: ఐచ్ఛిక ప్రొఫెషనల్ వివరాలు (headline, skills,
        # resume...) -- candidate మొదటిసారి dashboard చూసినప్పుడు ఇది
        # ఇంకా క్రియేట్ కాకపోవచ్చు కాబట్టి get_or_create వాడతాం (ఖాళీ
        # ప్రొఫైల్ అయినా పర్వాలేదు, dashboard ఖాళీ విలువలతో చూపిస్తుంది).
        candidate_profile, _created = CandidateProfile.objects.get_or_create(user=user)
        education_entries = candidate_profile.education_entries.all()

        # ఎవాటార్ లో చూపించడానికి పేరు లో మొదటి రెండు పదాల మొదటి అక్షరాలు
        # (ఉదా: "Ravi Kumar" -> "RK"); ఫోటో అప్‌లోడ్ చేసి ఉంటే టెంప్లేట్
        # దాన్నే ఉపయోగిస్తుంది (ఇది కేవలం ఫోటో లేనప్పుడు fallback).
        full_name = user.first_name or user.username
        name_parts = full_name.split()
        initials = "".join(p[0] for p in name_parts[:2]).upper() if name_parts else "?"

        # ప్రొఫైల్ ఎంత శాతం పూర్తయిందో (Profile Strength) -- ఇంతకుముందు
        # ఇది టెంప్లేట్ లో హార్డ్‌కోడ్ చేసిన స్టాటిక్ "78%" -- ఇప్పుడు
        # candidate నిజంగా ఎన్ని ప్రొఫెషనల్ ఫీల్డ్స్ నింపారో లెక్కించి
        # డైనమిక్‌గా చూపిస్తుంది.
        completion_fields = [
            bool(employee_profile.profile_photo),
            bool(candidate_profile.headline),
            bool(candidate_profile.location),
            bool(candidate_profile.about),
            bool(candidate_profile.skills),
            bool(candidate_profile.qualification),
            bool(candidate_profile.resume),
            bool(candidate_profile.linkedin_url or candidate_profile.portfolio_url),
            education_entries.exists(),
        ]
        profile_completion = round(100 * sum(completion_fields) / len(completion_fields))

        # STAT CARDS + "Applications"/"Recommended Jobs"/"Recent Activity"
        # కార్డులు -- ఇంతకుముందు ఇక్కడ "12"/"5"/"3"/"2" లాంటి
        # హార్డ్‌కోడ్ నంబర్లు, మరియు TCS/Wipro/Infosys అనే పూర్తిగా
        # కల్పిత జాబ్ కార్డులు ఉండేవి (jobs/urls.py:job_browse,
        # my_applications పేజీలు ఇప్పటికే నిజమైన డేటాతో పని చేస్తున్నా,
        # ఈ dashboard హోమ్ పేజీ మాత్రం వాటిని వాడలేదు). ఇప్పుడు అదే
        # JobApplication మోడల్ నుండి (jobs/views.py:MyApplicationsView
        # వాడే అదే మోడల్) నిజమైన లెక్కలు తీసుకుంటాం -- రెండు పేజీల్లోనూ
        # నంబర్లు ఎప్పుడూ సరిపోతాయి (ఒకే source of truth).
        applications = candidate_profile.applications.select_related("job", "job__employer")
        applied_job_ids = set(applications.values_list("job_id", flat=True))

        # "Profile Views" కి వెనుక ఏ ట్రాకింగ్ మోడల్ ప్రాజెక్ట్ లో లేదు
        # (ఎవరు ఎప్పుడు ప్రొఫైల్ చూశారో నిల్వ చేసే మోడల్ ఇంకా బిల్డ్
        # కాలేదు) -- కాబట్టి దాన్ని నిజమైన డేటాతో నింపలేము; టెంప్లేట్
        # లో "—" గా చూపిస్తాం (తప్పుడు నంబర్ చూపించే బదులు, ఫీచర్
        # లేదని స్పష్టంగా).
        recommended_jobs = (
            Job.objects.filter(status=Job.Status.ACTIVE)
            .exclude(pk__in=applied_job_ids)
            .select_related("employer")
            .order_by("-created_at")[:3]
        )

        context.update({
            "employee_profile": employee_profile,
            "candidate_profile": candidate_profile,
            "education_entries": education_entries,
            "full_name": full_name,
            "first_name_only": name_parts[0] if name_parts else full_name,
            "avatar_initials": initials,
            "profile_completion": profile_completion,
            "unread_message_count": unread_total_for(user),
            "applications_total_count": applications.count(),
            "applications_shortlisted_count": applications.filter(
                status=JobApplication.Status.SHORTLISTED,
            ).count(),
            "recommended_jobs": recommended_jobs,
            "recent_applications": applications.order_by("-updated_at")[:4],
            # 🎥 "Videos" ట్యాబ్ -- Employer లు పోస్ట్ చేసిన కంపెనీ కల్చర్/
            # అచీవ్‌మెంట్ వీడియోల ఫీడ్, Home పేజీలో కనిపించే అదే videos యాప్
            # డేటా నుండి (ఒకే source of truth) -- candidate ఇక్కడ లైక్/
            # కామెంట్ చేయొచ్చు (ఇప్పటికే లాగిన్ అయి ఉన్నారు కాబట్టి).
            "feed_videos": published_videos_for(user),
            # 📨 Hire Requests: employers ఈ candidate ని headhunting
            # ద్వారా (ఏ job కి apply చేయకపోయినా) నేరుగా సంప్రదించి
            # ఉంటే, ఆ రిక్వెస్ట్‌లు ఇక్కడ కనిపిస్తాయి -- employers/
            # candidate_detail.html: SendHireRequestView చూడండి.
            "hire_requests_received": candidate_profile.hire_requests_received
            .select_related("employer", "job").order_by("-created_at")[:10],
        })
        return context


# ══════════════════════════════════════════════════════════════════════
# CandidateProfileEditView
#
# సెక్యూరిటీ పాయింట్లు:
#   1. LoginRequiredMixin -- లాగిన్ కాని ఎవరూ ఈ పేజీ ని చూడలేరు/పోస్ట్
#      చేయలేరు; login లేకుండా ప్రయత్నిస్తే Django ఆటోమేటిక్‌గా
#      login_url కి ?next= తో రీడైరెక్ట్ చేస్తుంది.
#   2. ఈ వ్యూ ఎప్పుడూ URL లో వచ్చిన ఏ profile id నైనా వాడదు -- ఎప్పుడూ
#      self.request.user ఆధారంగానే ప్రొఫైల్ ని పొందుతుంది
#      (get_or_create). దీనివల్ల ఒక candidate వేరే candidate ప్రొఫైల్
#      ని URL మార్చి ఎడిట్ చేసే IDOR (Insecure Direct Object Reference)
#      దాడి సాధ్యం కాదు.
# ══════════════════════════════════════════════════════════════════════
class CandidateProfileEditView(LoginRequiredMixin, View):
    template_name = "candidates/candidate_profile_form.html"
    login_url = "accounts:employee_login"

    def _get_profile(self, request):
        # get_or_create: మొదటిసారి candidate ఈ పేజీ కి వస్తే ఖాళీ
        # ప్రొఫైల్ ఆటోమేటిక్‌గా క్రియేట్ అవుతుంది; తర్వాత ఎప్పుడూ
        # అదే రికార్డ్ మళ్ళీ వాడబడుతుంది (OneToOneField కాబట్టి
        # డూప్లికేట్ ప్రొఫైల్స్ క్రియేట్ అయ్యే అవకాశమే లేదు).
        profile, _created = CandidateProfile.objects.get_or_create(user=request.user)
        return profile

    def get(self, request, *args, **kwargs):
        profile = self._get_profile(request)
        context = {
            "form": CandidateProfileForm(instance=profile),
            "education_form": CandidateEducationForm(),
            "education_entries": profile.education_entries.all(),
            "profile": profile,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        profile = self._get_profile(request)

        # ఈ ఒక్క పేజీ లోనే రెండు వేర్వేరు ఫారమ్‌లు ఉన్నాయి (ప్రొఫైల్
        # ఎడిట్ + కొత్త ఎడ్యుకేషన్ ఎంట్రీ జోడించడం) కాబట్టి, ఏ ఫారమ్
        # సబ్‌మిట్ అయ్యిందో submit button పేరు (name="form_type")
        # ఆధారంగా వేరు చేస్తున్నాం.
        form_type = request.POST.get("form_type")

        if form_type == "education":
            education_form = CandidateEducationForm(request.POST)
            profile_form = CandidateProfileForm(instance=profile)
            if education_form.is_valid():
                # commit=False: DB లో సేవ్ చేయడానికి ముందు profile ని
                # request.user ఆధారంగా మనమే సెట్ చేస్తాం (ఫారమ్ లో ఆ
                # ఫీల్డ్ లేదు కాబట్టి, యూజర్ input ద్వారా వేరే
                # ప్రొఫైల్ కి రికార్డ్ జోడించలేడు).
                education = education_form.save(commit=False)
                education.profile = profile
                education.save()
                messages.success(request, "✅ విద్యార్హత వివరాలు జోడించబడ్డాయి.")
                return redirect("candidates:candidate_profile_edit")
        else:
            profile_form = CandidateProfileForm(
                request.POST, request.FILES, instance=profile,
            )
            education_form = CandidateEducationForm()
            if profile_form.is_valid():
                profile_form.save()
                # ప్రొఫైల్ ని ఒకసారి సేవ్ చేసిన తర్వాత "పూర్తయింది" గా
                # మార్క్ చేస్తాం -- ఇక ProfileCompletionMiddleware ఈ
                # యూజర్ ని బలవంతంగా ఇక్కడికే పంపదు, డాష్‌బోర్డ్ కి
                # పూర్తి యాక్సెస్ వస్తుంది.
                request.user.employee_profile.profile_completed = True
                request.user.employee_profile.save(update_fields=["profile_completed"])
                messages.success(request, "✅ మీ ప్రొఫైల్ అప్‌డేట్ అయ్యింది.")
                return redirect("candidates:candidate_profile_edit")

        context = {
            "form": profile_form,
            "education_form": education_form,
            "education_entries": profile.education_entries.all(),
            "profile": profile,
        }
        return render(request, self.template_name, context)


# ══════════════════════════════════════════════════════════════════════
# CandidateEducationDeleteView
#
# POST-only (GET తో డిలీట్ చేయడం ఎప్పుడూ మంచి పద్ధతి కాదు -- ఒక
# దురుద్దేశపరుడు <img src="...delete/5/"> లాంటి లింక్ ఇచ్చి, యూజర్
# బ్రౌజర్ ఆటోమేటిక్‌గా ఆ GET రిక్వెస్ట్ పంపేలా చేసే దాడి చేయగలడు;
# POST + {% csrf_token %} ఈ రెంటినీ ఆపుతాయి).
# get_object_or_404(profile__user=request.user) -- ఇదే అసలైన
# ఓనర్‌షిప్ చెక్: ఈ education id వేరే యూజర్ దైతే 404 వస్తుంది,
# తప్ప వేరే యూజర్ డేటా కనిపించదు/డిలీట్ అవదు.
# ══════════════════════════════════════════════════════════════════════
class CandidateEducationDeleteView(LoginRequiredMixin, View):
    login_url = "accounts:employee_login"

    def post(self, request, pk, *args, **kwargs):
        education = get_object_or_404(
            CandidateEducation, pk=pk, profile__user=request.user,
        )
        education.delete()
        messages.success(request, "🗑️ విద్యార్హత ఎంట్రీ తొలగించబడింది.")
        return redirect("candidates:candidate_profile_edit")


class HireRequestRespondView(LoginRequiredMixin, View):
    """Candidate ఒక Hire Request ని Accept/Decline చేసే view.
    get_object_or_404(candidate__user=request.user) ఓనర్‌షిప్ చెక్ --
    వేరే candidate కి పంపిన రిక్వెస్ట్ ని ఎవరూ accept/decline
    చేయలేరు."""
    login_url = "accounts:employee_login"

    def post(self, request, pk, *args, **kwargs):
        from employers.models import HireRequest

        hire_request = get_object_or_404(
            HireRequest, pk=pk, candidate__user=request.user,
        )
        action = request.POST.get("action")
        if action == "accept":
            hire_request.status = HireRequest.Status.ACCEPTED
            hire_request.save(update_fields=["status", "updated_at"])
            messages.success(request, "✅ Hire Request accept చేశారు. ఇప్పుడు వాళ్ళతో చాట్ చేసుకోవచ్చు.")
        elif action == "decline":
            hire_request.status = HireRequest.Status.DECLINED
            hire_request.save(update_fields=["status", "updated_at"])
            messages.info(request, "ℹ️ Hire Request decline చేశారు.")
        return redirect("candidates:candidate_dashboard")
