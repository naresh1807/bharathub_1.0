from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from accounts.models import EmployeeProfile
from employers.models import HireRequest, Job
from jobs.models import Employment, JobApplication
from messaging.views import unread_total_for
from videos.utils import published_videos_for
from .forms import CandidateEducationForm, CandidateProfileForm
from .pdf_documents import (
    generate_appointment_letter_pdf, generate_employment_letter_pdf,
    generate_offer_letter_pdf, generate_resume_pdf,
)
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
                "⚠️ This account has no Employee profile. Please log in with an Employee "
                "account, or register first.",
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
        # candidate ఇప్పుడు HIRED అయితే కొత్త job offers చూపించం (ఇప్పటికే
        # ఏదో ఒక కంపెనీలో పని చేస్తున్నారు కాబట్టి) -- బదులుగా
        # "Currently Employed" కార్డు + Resign బటన్ చూపిస్తాం (దిగువ
        # current_employment చూడండి). resign చేసి, employer ఆ resignation
        # accept చేశాకే candidate.hire_status మళ్ళీ AVAILABLE అవుతుంది,
        # అప్పుడే ఇక్కడ recommended_jobs మళ్ళీ కనిపించడం మొదలవుతుంది
        # (jobs/views.py: ResignationRespondView చూడండి).
        if candidate_profile.hire_status == CandidateProfile.HireStatus.HIRED:
            recommended_jobs = Job.objects.none()
        else:
            recommended_jobs = (
                Job.objects.filter(status=Job.Status.ACTIVE)
                .exclude(pk__in=applied_job_ids)
                .select_related("employer")
                .order_by("-created_at")[:3]
            )

        current_employment = Employment.objects.filter(
            candidate=candidate_profile,
            status__in=[Employment.Status.ACTIVE, Employment.Status.RESIGNATION_REQUESTED],
        ).select_related("application__job__employer").first()

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
            "current_employment": current_employment,
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
                messages.success(request, "✅ Education details added.")
                return redirect("candidates:candidate_profile_edit")
        else:
            profile_form = CandidateProfileForm(
                request.POST, request.FILES, instance=profile,
            )
            education_form = CandidateEducationForm()
            if profile_form.is_valid():
                profile_form.save()

                # BUG FIX: ఈ ఫారమ్ CandidateProfile.profile_photo కి
                # మాత్రమే సేవ్ చేస్తుంది -- కానీ డాష్‌బోర్డ్ (సైడ్‌బార్,
                # టాప్‌నావ్, ప్రొఫైల్ కార్డ్) మరియు మెసేజింగ్ యాప్
                # (avatar_url_for(), messaging/permissions.py) రెండూ
                # EmployeeProfile.profile_photo నే కానానికల్ అవతార్
                # గా చదువుతాయి -- ఆ ఫీల్డ్ ఇక్కడ ఎప్పుడూ అప్‌డేట్
                # అయ్యేది కాదు, కాబట్టి యూజర్ కొత్త ఫోటో అప్‌లోడ్
                # చేసినా అది తన సొంత డాష్‌బోర్డ్ లోనూ, చాట్ లోనూ
                # ఎక్కడా కనిపించేది కాదు. కొత్త ఫోటో అప్‌లోడ్ అయినప్పుడు
                # (ఖాళీగా ఉంచేసినప్పుడు కాదు) దాన్ని కానానికల్ ఫీల్డ్
                # లోకి కూడా కాపీ చేస్తాం -- రెండూ ఒకే ఫైల్ storage
                # (MEDIA_ROOT) వాడతాయి కాబట్టి, ఫైల్ మళ్ళీ అప్‌లోడ్
                # అవదు, కేవలం రెండో ఫీల్డ్ కూడా అదే పాత్ ని పాయింట్
                # చేస్తుంది.
                if "profile_photo" in request.FILES:
                    request.user.employee_profile.profile_photo = profile.profile_photo
                    request.user.employee_profile.save(update_fields=["profile_photo"])

                # ప్రొఫైల్ ని ఒకసారి సేవ్ చేసిన తర్వాత "పూర్తయింది" గా
                # మార్క్ చేస్తాం -- ఇక ProfileCompletionMiddleware ఈ
                # యూజర్ ని బలవంతంగా ఇక్కడికే పంపదు, డాష్‌బోర్డ్ కి
                # పూర్తి యాక్సెస్ వస్తుంది.
                request.user.employee_profile.profile_completed = True
                request.user.employee_profile.save(update_fields=["profile_completed"])
                messages.success(request, "✅ Your profile has been updated.")
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
        messages.success(request, "🗑️ Education entry deleted.")
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
            messages.success(request, "✅ Hire Request accepted. You can now chat with them.")
        elif action == "decline":
            hire_request.status = HireRequest.Status.DECLINED
            hire_request.save(update_fields=["status", "updated_at"])
            messages.info(request, "ℹ️ Hire Request declined.")
        return redirect("candidates:candidate_dashboard")


# ══════════════════════════════════════════════════════════════════════
# Downloads (Resume + employment letters)
#
# candidate_dashboard.html సైడ్‌బార్ లో "Downloads" నావ్ ఐటమ్ ఇక్కడికే
# లింక్ చేస్తుంది. ఇందులో రెండు రకాల డాక్యుమెంట్లు:
#
#   1. Resume -- CandidateProfile + CandidateEducation లో ఇప్పటికే ఉన్న
#      నిజమైన డేటా తో ఆటోమేటిక్‌గా జనరేట్ అవుతుంది (ఎప్పుడూ లభ్యం).
#
#   2. Appointment Letter -- ఒక Employer, ఈ candidate కి పంపిన
#      HireRequest ని candidate Accept చేసుంటే మాత్రమే జనరేట్ అవుతుంది
#      (real record ఆధారంగా -- ఏ ఖాళీ/ఫేక్ డేటా వాడము).
#
#   3. Joining Letter / Relieving Letter / Experience Letter -- వీటికి
#      joining date, designation, CTC, relieving date లాంటి నిజమైన
#      Employment రికార్డు కావాలి, అది ప్రస్తుతం ఈ సిస్టమ్ లో ఎక్కడా
#      ట్రాక్ చేయడం లేదు (HireRequest కేవలం ఇన్విటేషన్ మాత్రమే, actual
#      hiring/joining/relieving వివరాలు కాదు). కాబట్టి వీటిని ఖాళీ లేదా
#      కల్పిత (fake) డేటాతో జనరేట్ చేయం -- బదులుగా Downloads పేజీలో
#      "Not available yet" అని స్పష్టంగా చూపిస్తాం. (నిజమైన Employment
#      రికార్డ్ ఫీచర్ యాడ్ చేయాలంటే వేరే టాస్క్ గా చేయాలి.)
# ══════════════════════════════════════════════════════════════════════


class DownloadsListView(LoginRequiredMixin, TemplateView):
    """Downloads హోమ్ పేజీ. Resume ఎప్పుడూ అందుబాటులో ఉంటుంది. Offer
    Letter -- Employer 'Mark as Hired' నొక్కిన ప్రతి Employment కీ ఒక
    కార్డ్ కనిపిస్తుంది (Pending/Accepted). Appointment Letter
    అందుబాటులో ఉండాలంటే కనీసం ఒక్క ACCEPTED HireRequest (job attached
    గా) ఉండాలి. Joining/Relieving/Experience Letter మూడూ ఒక Employment
    RELIEVED అయ్యాకే కలిసి అందుబాటులోకి వస్తాయి."""

    template_name = "candidates/downloads_list.html"
    login_url = "accounts:employee_login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        candidate_profile = get_object_or_404(CandidateProfile, user=self.request.user)
        context["candidate_profile"] = candidate_profile
        context["accepted_hire_requests"] = list(
            HireRequest.objects.filter(
                candidate=candidate_profile,
                status=HireRequest.Status.ACCEPTED,
                job__isnull=False,
            ).select_related("employer", "job").order_by("-updated_at"),
        )
        # Joining/Relieving/Experience Letter లు -- ఒక Employment RELIEVED
        # అయిన వెంటనే (jobs/views.py: ResignationRespondView, Accept
        # చర్య) మూడూ కలిసి ఇక్కడ ఆటోమేటిక్‌గా అందుబాటులోకి వస్తాయి,
        # ఇంకా ఖాళీ/కల్పిత లెటర్ల అవసరం లేకుండా -- ఇప్పుడు నిజమైన
        # joining_date + relieving_date రెండూ రికార్డు లో ఉన్నాయి కాబట్టి.
        context["relieved_employments"] = list(
            Employment.objects.filter(
                candidate=candidate_profile, status=Employment.Status.RELIEVED,
            ).select_related("application__job__employer").order_by("-relieving_date"),
        )
        # Offer Letter -- Employer 'Mark as Hired' నొక్కిన ప్రతిసారీ (ఏ
        # Employment అయినా, ప్రస్తుత ఉద్యోగం అయినా గత చరిత్ర అయినా) ఒక
        # ఆఫర్ లెటర్ కార్డ్ కనిపిస్తుంది -- Pending/Accepted స్టేటస్ తో.
        context["all_employments"] = list(
            Employment.objects.filter(candidate=candidate_profile)
            .select_related("application__job__employer").order_by("-created_at"),
        )
        return context


class ResumeDocumentView(LoginRequiredMixin, TemplateView):
    """Candidate ప్రొఫైల్ డేటా తో ఆటోమేటిక్‌గా జనరేట్ అయ్యే Resume --
    ప్రింట్-ఫ్రెండ్లీ పేజీ (BharatHub లోగో + Print/Download బటన్లు).
    'Download' బటన్ కూడా బ్రౌజర్ ప్రింట్ డైలాగ్ నే తెరుస్తుంది -- అక్కడ
    'Save as PDF' ఎంచుకుంటే అదే డౌన్లోడ్ అవుతుంది (సర్వర్ సైడ్ PDF
    లైబ్రరీ ఏదీ ఇప్పుడు ఈ ప్రాజెక్ట్ లో లేదు కాబట్టి, కొత్త heavy
    dependency యాడ్ చేయకుండా, ప్రతి బ్రౌజర్ లోనూ నమ్మకంగా పనిచేసే ఈ
    పద్ధతినే వాడాం)."""

    template_name = "candidates/document_resume.html"
    login_url = "accounts:employee_login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        candidate_profile = get_object_or_404(CandidateProfile, user=self.request.user)
        context["candidate_profile"] = candidate_profile
        context["education_entries"] = candidate_profile.education_entries.all()
        context["full_name"] = self.request.user.get_full_name() or self.request.user.username
        return context


class AppointmentLetterView(LoginRequiredMixin, TemplateView):
    """ఒక Accepted HireRequest ఆధారంగా Appointment Letter చూపిస్తుంది.
    get_object_or_404(candidate__user=...) ఓనర్‌షిప్ చెక్ -- వేరే
    candidate కి పంపిన HireRequest ని ఎవరూ చూడలేరు (IDOR గార్డ్,
    HireRequestRespondView లో వాడిన పద్ధతినే ఇక్కడా వాడాం)."""

    template_name = "candidates/document_appointment_letter.html"
    login_url = "accounts:employee_login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hire_request = get_object_or_404(
            HireRequest.objects.select_related("employer", "job", "candidate__user"),
            pk=kwargs["pk"], candidate__user=self.request.user,
            status=HireRequest.Status.ACCEPTED, job__isnull=False,
        )
        context["hire_request"] = hire_request
        context["full_name"] = self.request.user.get_full_name() or self.request.user.username
        return context


class EmploymentLetterView(LoginRequiredMixin, TemplateView):
    """Joining / Relieving / Experience Letter -- మూడూ ఒకే వ్యూ, URL లోని
    'letter_type' బట్టి టెంప్లేట్ లో వేరే సెక్షన్ చూపిస్తాం. ఈ మూడూ ఒక
    Employment RELIEVED అయ్యాకే (candidate.employments...status=='relieved')
    అందుబాటులోకి వస్తాయి -- ఎందుకో candidates/views.py: DownloadsListView
    పైన ఉన్న కామెంట్ చూడండి. get_object_or_404(candidate__user=...,
    status=RELIEVED) ఒకేసారి ఓనర్‌షిప్ + అందుబాటు రెండిటినీ చెక్ చేస్తుంది."""

    template_name = "candidates/document_employment_letter.html"
    login_url = "accounts:employee_login"

    VALID_TYPES = {"joining", "relieving", "experience"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        letter_type = kwargs.get("letter_type")
        if letter_type not in self.VALID_TYPES:
            raise Http404("Unknown letter type.")

        employment = get_object_or_404(
            Employment.objects.select_related("application__job__employer", "candidate__user"),
            pk=kwargs["pk"], candidate__user=self.request.user,
            status=Employment.Status.RELIEVED,
        )
        context["employment"] = employment
        context["letter_type"] = letter_type
        context["full_name"] = self.request.user.get_full_name() or self.request.user.username
        return context


class OfferLetterView(LoginRequiredMixin, TemplateView):
    """Offer Letter -- Employer 'Mark as Hired' నొక్కిన వెంటనే ఆటోమేటిక్‌గా
    జనరేట్ అయ్యి ఇక్కడ కనిపిస్తుంది (jobs/views.py: MarkAsHiredView).
    ఇంకా Accept చేయకపోతే 'Accept Offer' బటన్ చూపిస్తాం (POST అవుతుంది
    jobs:offer_letter_accept కి -- OfferLetterAcceptView, అది
    ఓనర్‌షిప్ మళ్ళీ చెక్ చేస్తుంది). Accept అయ్యాక ఆ బటన్ బదులు
    '✅ Accepted' బ్యాడ్జ్ + Print/Download బటన్లు మాత్రమే కనిపిస్తాయి."""

    template_name = "candidates/document_offer_letter.html"
    login_url = "accounts:employee_login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employment = get_object_or_404(
            Employment.objects.select_related("application__job__employer", "candidate__user"),
            pk=kwargs["pk"], candidate__user=self.request.user,
        )
        context["employment"] = employment
        context["full_name"] = self.request.user.get_full_name() or self.request.user.username
        return context


# ============================================================================
# PDF Download views
#
# పైన ఉన్న ResumeDocumentView/AppointmentLetterView/EmploymentLetterView/
# OfferLetterView అన్నీ ఇంతకుముందు బ్రౌజర్ ప్రింట్ డైలాగ్ (window.print())
# మీద ఆధారపడే HTML ప్రివ్యూ పేజీలు మాత్రమే ఇచ్చేవి. ఇప్పుడు ప్రతిదానికీ
# పక్కన ఒక నిజమైన PDF డౌన్‌లోడ్ వ్యూ జోడించాం (candidates/pdf_documents.py
# ద్వారా ReportLab తో సర్వర్ లోనే జనరేట్ అవుతుంది) -- ఓనర్‌షిప్/అందుబాటు
# చెక్‌లు పైన ఉన్న ఆయా HTML వ్యూలలో ఉన్నవే, exact గా అవే మళ్ళీ ఇక్కడ.
# ============================================================================
class ResumePDFDownloadView(LoginRequiredMixin, View):
    login_url = "accounts:employee_login"

    def get(self, request, *args, **kwargs):
        candidate_profile = get_object_or_404(CandidateProfile, user=request.user)
        full_name = request.user.get_full_name() or request.user.username
        return generate_resume_pdf(
            candidate_profile, candidate_profile.education_entries.all(), full_name,
        )


class AppointmentLetterPDFDownloadView(LoginRequiredMixin, View):
    login_url = "accounts:employee_login"

    def get(self, request, pk, *args, **kwargs):
        hire_request = get_object_or_404(
            HireRequest.objects.select_related("employer", "job", "candidate__user"),
            pk=pk, candidate__user=request.user,
            status=HireRequest.Status.ACCEPTED, job__isnull=False,
        )
        full_name = request.user.get_full_name() or request.user.username
        return generate_appointment_letter_pdf(hire_request, full_name)


class EmploymentLetterPDFDownloadView(LoginRequiredMixin, View):
    login_url = "accounts:employee_login"
    VALID_TYPES = {"joining", "relieving", "experience"}

    def get(self, request, pk, letter_type, *args, **kwargs):
        if letter_type not in self.VALID_TYPES:
            raise Http404("Unknown letter type.")
        employment = get_object_or_404(
            Employment.objects.select_related("application__job__employer", "candidate__user"),
            pk=pk, candidate__user=request.user,
            status=Employment.Status.RELIEVED,
        )
        full_name = request.user.get_full_name() or request.user.username
        return generate_employment_letter_pdf(employment, letter_type, full_name)


class OfferLetterPDFDownloadView(LoginRequiredMixin, View):
    login_url = "accounts:employee_login"

    def get(self, request, pk, *args, **kwargs):
        employment = get_object_or_404(
            Employment.objects.select_related("application__job__employer", "candidate__user"),
            pk=pk, candidate__user=request.user,
        )
        full_name = request.user.get_full_name() or request.user.username
        return generate_offer_letter_pdf(employment, full_name)
