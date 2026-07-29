from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from accounts.models import EmployeeProfile
from candidates.models import CandidateProfile
from jobs.models import JobApplication
from messaging.views import unread_total_for
from videos.forms import VideoUploadForm
from videos.models import Video
from videos.utils import published_videos_for
from .forms import HireRequestForm, JobPostForm, EmployerLogoForm
from .models import HireRequest, Job

# ============================================================================
# employers/views.py
# ============================================================================


class EmployerDashboardView(LoginRequiredMixin, TemplateView):
    """Employer dashboard: overview + "Post a Job" + "Upload Video" tabs.

    ఎందుకు ఇలా మార్చాం:
      1. LoginRequiredMixin -- ఇంతకుముందు ఇది ఎవరైనా (లాగిన్ అవ్వకుండానే)
         URL నేరుగా టైప్ చేసి చూడగలిగే plain TemplateView. ఇది ఒక
         భద్రతా లోపం (broken access control) -- కంపెనీ డాష్‌బోర్డ్,
         దాని జాబ్ పోస్టులు లాంటివి లాగిన్ అయిన Employer లకి మాత్రమే
         కనిపించాలి. login_url సెట్ చేయడం వల్ల, లాగిన్ అవ్వని యూజర్
         ఆటోమేటిక్‌గా Employer Login పేజీ కి redirect అవుతారు.
      2. GET/POST రెండిటినీ హ్యాండిల్ చేస్తుంది -- POST వచ్చినప్పుడు
         "Post a Job" ఫారమ్ ని వాలిడేట్ చేసి, సరైతే DB లో ఒక కొత్త
         Job రికార్డ్ క్రియేట్ చేస్తుంది.
    """

    template_name = "employers/employer_dashboard.html"
    login_url = "accounts:employer_login"

    # ------------------------------------------------------------------
    # get_current_employer(): ప్రస్తుతం లాగిన్ అయిన యూజర్ కి సంబంధించిన
    # EmployerProfile ని సురక్షితంగా తీసుకువస్తుంది.
    # ఎందుకు ఇలా చేయాలి: LoginRequiredMixin కేవలం "యూజర్ లాగిన్
    # అయ్యాడా లేదా" అని మాత్రమే చెక్ చేస్తుంది -- కానీ లాగిన్ అయిన
    # ప్రతి యూజర్ కి EmployerProfile ఉంటుందని గ్యారంటీ లేదు (ఉదా:
    # ఒక Employee ఖాతా తో లాగిన్ అయి, నేరుగా ఈ URL కి వస్తే). అలాంటప్పుడు
    # request.user.employer_profile యాక్సెస్ చేయడం Django యొక్క
    # RelatedObjectDoesNotExist ఎర్రర్ తో సర్వర్ క్రాష్ అవుతుంది --
    # దాన్ని ఇక్కడే పట్టుకుని, స్పష్టమైన 403 Forbidden ఇస్తున్నాం
    # (ఇదే "broken access control" ని ఆపే భద్రతా పద్ధతి).
    # ------------------------------------------------------------------
    def get_current_employer(self):
        employer_profile = getattr(self.request.user, "employer_profile", None)
        if employer_profile is None:
            raise PermissionDenied("This page is for Employer accounts only.")
        return employer_profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employer = self.get_current_employer()

        # "Post a Job" ఫారమ్ -- ఇంతకుముందు దీన్ని context లో పెట్టకపోతే
        # (అంటే GET రిక్వెస్ట్ అయితే), ఖాళీ ఫారమ్ చూపిస్తాం.
        context.setdefault("form", JobPostForm())

        # "Active Job Posts" కార్డ్ లో ఇంతకుముందు హార్డ్‌కోడ్ చేసిన
        # 3 జాబ్స్ బదులు, ఇప్పుడు ఈ కంపెనీ నిజంగా పోస్ట్ చేసిన Job
        # రికార్డుల్ని (కేవలం ACTIVE స్టేటస్ లో ఉన్నవి, కొత్తవి ముందు
        # కనిపించేలా -- models.py లోని Meta.ordering ఇప్పటికే
        # "-created_at" గా ఉంది) DB నుండి తీసుకువస్తున్నాం.
        context["jobs"] = employer.jobs.filter(status=Job.Status.ACTIVE)
        context["employer"] = employer

        # STAT CARDS: ఇంతకుముందు ఇక్కడ "148" / "24" / "7" / "4" అనే
        # హార్డ్‌కోడ్ నంబర్లు ఉండేవి -- jobs/views.py:ApplicationsView
        # లో ఇప్పటికే ఈ లెక్కలన్నీ నిజమైన JobApplication డేటా నుండి
        # సరిగ్గా కంప్యూట్ చేస్తున్నారు, కానీ dashboard హోమ్ పేజీ
        # (ఈ వ్యూ) వాటిని వాడలేదు -- ఇక్కడ కూడా అదే క్వెరీలు అప్లై
        # చేస్తున్నాం, తద్వారా dashboard మీద కనిపించే నంబర్లు
        # /jobs/applications.html పేజీ లో కనిపించే నంబర్లతో ఎప్పుడూ
        # సరిపోతాయి (ఒకే source of truth).
        all_applications = JobApplication.objects.filter(job__employer=employer)
        context["total_applications_count"] = all_applications.count()
        context["shortlisted_count"] = all_applications.filter(
            status=JobApplication.Status.SHORTLISTED,
        ).count()
        context["interview_count"] = all_applications.filter(
            status=JobApplication.Status.INTERVIEW,
        ).count()

        # RECENT ACTIVITY: ఇంతకుముందు 5 పూర్తిగా కల్పిత (fake candidate
        # పేర్లు, fake టైమ్‌స్టాంప్‌లు) ఎంట్రీలు ఉండేవి. ఇప్పుడు ఈ
        # employer యొక్క jobs మీద ఇటీవల modify అయిన (కొత్తగా apply
        # అయినా, స్టేటస్ మారినా updated_at మారుతుంది కాబట్టి) 5
        # అప్లికేషన్లని చూపిస్తాం -- నిజమైన activity feed.
        context["recent_applications"] = (
            all_applications.select_related("candidate__user", "job")
            .order_by("-updated_at")[:5]
        )

        context["unread_message_count"] = unread_total_for(self.request.user)

        # 🎥 VIDEOS TAB: videos యాప్ కి కనెక్ట్ చేశాం -- ఖాళీ
        # VideoUploadForm + ఈ కంపెనీ సొంతంగా అప్‌లోడ్ చేసిన వీడియోలు
        # (my_videos) + అందరి కంపెనీల ఫీడ్ కూడా (videos/_upload_panel.html
        # లో దిగువన {% include "videos/_feed.html" %}).
        context.setdefault("video_form", VideoUploadForm())
        context["my_videos"] = Video.objects.filter(employer=employer).order_by("-created_at")
        context["feed_videos"] = published_videos_for(self.request.user)

        # ACTIVE SECTION: ఇంతకుముందు Home / Post a Job / Upload Video
        # నావిగేషన్ లింకులు మూడూ ఒకే URL (?section= ఏ పారామీటర్
        # లేకుండా) కి పాయింట్ చేసేవి -- కాబట్టి "Upload Video" ఎక్కడి
        # నుండి క్లిక్ చేసినా (ఉదా: Applications పేజీ నుండి తిరిగి
        # dashboard కి వచ్చినప్పుడు) ఎప్పుడూ Home ట్యాబే తెరుచుకునేది.
        # ఇప్పుడు ఆ లింకులు ?section=postjob / ?section=videos పంపుతాయి
        # (employers/_nav.html చూడండి), దాన్ని ఇక్కడ చదివి సరైన
        # సెక్షన్ ని active గా సెట్ చేస్తాం. ఫారమ్ ఎర్రర్స్ ఉంటే మాత్రం
        # (POST invalid అయితే) అది ఎప్పుడూ ప్రాధాన్యత తీసుకుంటుంది --
        # యూజర్ ఏ ట్యాబ్ లో ఉన్నా, ఎర్రర్ ఉన్న ఫారమ్ నే చూపించాలి.
        valid_sections = {"home", "postjob", "videos"}
        requested_section = self.request.GET.get("section", "")
        if context["form"].errors:
            context["active_section"] = "postjob"
        elif requested_section in valid_sections:
            context["active_section"] = requested_section
        else:
            context["active_section"] = "home"

        return context

    def post(self, request, *args, **kwargs):
        employer = self.get_current_employer()
        form = JobPostForm(request.POST)

        if form.is_valid():
            # commit=False: ముందు మెమరీ లో మాత్రమే Job ఆబ్జెక్ట్ ని
            # తయారు చేసి, employer ని సెట్ చేసి, తర్వాతే DB లో save()
            # చేస్తాం. ఇది ముఖ్యం ఎందుకంటే "employer" ఫీల్డ్ ఫారమ్
            # లో లేదు (Meta.fields లో ఉద్దేశపూర్వకంగా చేర్చలేదు) --
            # ఎవరు పోస్ట్ చేస్తున్నారో ఎప్పుడూ request.user నుండే
            # (ఫారమ్ డేటా నుండి కాదు) నిర్ణయించాలి, లేకపోతే ఎవరైనా
            # వేరే కంపెనీ పేరు మీద జాబ్ పోస్ట్ చేసే ప్రమాదం ఉంటుంది.
            job = form.save(commit=False)
            job.employer = employer

            # "Post Job Now" vs "Save as Draft" -- రెండు వేర్వేరు
            # <button type="submit" name="action" value="..."> ల
            # ద్వారా ఏ బటన్ నొక్కారో ఇక్కడ తెలుసుకుంటాం.
            action = request.POST.get("action", "publish")
            job.status = Job.Status.DRAFT if action == "draft" else Job.Status.ACTIVE
            job.save()

            if job.status == Job.Status.DRAFT:
                messages.success(request, f"💾 '{job.title}' saved as draft.")
            else:
                messages.success(
                    request,
                    f"🎉 '{job.title}' posted successfully! It will be visible to matching candidates.",
                )
            # POST/Redirect/Get pattern -- యూజర్ పేజీ రిఫ్రెష్ చేసినా
            # జాబ్ మళ్ళీ డూప్లికేట్‌గా పోస్ట్ కాకుండా.
            return redirect("employers:employer_dashboard")

        # ఫారమ్ ఇన్వాలిడ్ అయితే, ఎర్రర్స్ తో మళ్ళీ అదే పేజీ (postjob
        # సెక్షన్ ని JS active గా చూపించేలా -- టెంప్లేట్ లో
        # form.errors ఉంటే section-postjob నే active చేస్తాం).
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


# ============================================================================
# Candidate Search (Employer dashboard లోని కొత్త ఫీచర్)
#
# Employer ఒక candidate ని వాళ్ళ BharatHub ID లేదా మొబైల్ నెంబర్ తో
# నేరుగా వెతికి, పూర్తి ప్రొఫైల్ చూసి, చాట్ మొదలుపెట్టొచ్చు లేదా ఒక
# job కి "Hire Request" పంపొచ్చు -- ఆ candidate ఇంతకుముందు ఏ job కీ
# apply చేయకపోయినా (headhunting/recruiter-search తరహా ఫీచర్).
#
# ముఖ్యమైన స్కోప్ నిర్ణయం: ఇది Employer dashboard కి మాత్రమే --
# Employee/Vendor డాష్‌బోర్డుల్లో లేదు ఉద్దేశపూర్వకంగా. ఎందుకంటే ఇది
# ఒక candidate యొక్క పూర్తి వ్యక్తిగత డేటా (మొబైల్ నెంబర్, DOB,
# తండ్రి పేరు మొదలైనవి) బయటపెడుతుంది -- ఇది కేవలం చట్టబద్ధమైన
# రిక్రూటర్ (Employer) కి మాత్రమే అవసరం అయ్యే యాక్సెస్. దీన్ని
# Employee/Vendor లకి కూడా ఇస్తే, ఏ registered యూజర్ అయినా ఇతర
# job-seekers యొక్క వ్యక్తిగత డేటాని వెతికి చూడగలిగే గోప్యతా సమస్య
# వస్తుంది.
# ============================================================================
# ============================================================================
# EmployerLogoUpdateView
#
# Company logo అప్‌లోడ్ -- Home tab లోని "🏢 Company Logo" చిన్న కార్డ్
# నుండి పోస్ట్ అవుతుంది (employer_dashboard.html). ఇది EmployerDashboardView
# లో కలపలేదు (అక్కడి post() ఇప్పటికే JobPostForm కి specific గా ఉంది)
# -- వేరే URL/View గా ఉంచడం వల్ల ఏ ఫారమ్ ఏ URL కి పోస్ట్ అవుతుందో
# స్పష్టంగా ఉంటుంది, ఒక ఫారమ్ ఇన్వాలిడ్ అయితే ఇంకో ఫారమ్ డేటా పోదు.
# ============================================================================
class EmployerLogoUpdateView(LoginRequiredMixin, View):
    login_url = "accounts:employer_login"

    def post(self, request, *args, **kwargs):
        employer = getattr(request.user, "employer_profile", None)
        if employer is None:
            raise PermissionDenied("This page is for Employer accounts only.")

        form = EmployerLogoForm(request.POST, request.FILES, instance=employer)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Company logo updated.")
        else:
            for error in form.errors.get("company_logo", []):
                messages.error(request, f"⚠️ {error}")
        return redirect("employers:employer_dashboard")


class CandidateSearchView(LoginRequiredMixin, TemplateView):
    template_name = "employers/candidate_search.html"
    login_url = "accounts:employer_login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employer = _current_employer_or_403(self.request)
        context["employer"] = employer
        context["unread_message_count"] = unread_total_for(self.request.user)

        query = self.request.GET.get("q", "").strip()
        context["query"] = query
        results = []
        if query:
            # BharatHub ID (BH...) లేదా 10-అంకెల మొబైల్ నెంబర్ --
            # రెండిటిలో దేనితోనైనా ఖచ్చితమైన మ్యాచ్ వెతుకుతాం (partial
            # మొబైల్ నెంబర్ సెర్చ్ ఉద్దేశపూర్వకంగా allow చేయడం లేదు --
            # లేకపోతే 2-3 అంకెలు టైప్ చేసినా వందల మంది candidates
            # కనిపించి, అది ఒక mass-scraping/enumeration ముప్పు
            # అవుతుంది).
            employee_qs = EmployeeProfile.objects.filter(
                models.Q(bharathub_id__iexact=query) | models.Q(mobile_number=query)
            ).select_related("user", "user__candidate_profile")
            for emp_profile in employee_qs:
                candidate = getattr(emp_profile.user, "candidate_profile", None)
                if candidate is not None:
                    results.append(candidate)
        context["results"] = results
        return context


class CandidateDetailView(LoginRequiredMixin, TemplateView):
    """ఒక్క candidate యొక్క పూర్తి ప్రొఫైల్ (EmployeeProfile +
    CandidateProfile + విద్యార్హతలు) + Chat / Send Hire Request
    బటన్లు."""
    template_name = "employers/candidate_detail.html"
    login_url = "accounts:employer_login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employer = _current_employer_or_403(self.request)
        candidate = get_object_or_404(
            CandidateProfile.objects.select_related("user", "user__employee_profile"),
            pk=kwargs["pk"],
        )
        context.update({
            "employer": employer,
            "candidate": candidate,
            "education_list": candidate.education_entries.all(),
            "hire_request_form": HireRequestForm(employer=employer),
            "existing_hire_requests": HireRequest.objects.filter(
                employer=employer, candidate=candidate,
            ).select_related("job"),
            "unread_message_count": unread_total_for(self.request.user),
        })
        return context


class SendHireRequestView(LoginRequiredMixin, View):
    login_url = "accounts:employer_login"

    def post(self, request, pk, *args, **kwargs):
        employer = _current_employer_or_403(request)
        candidate = get_object_or_404(CandidateProfile, pk=pk)

        if candidate.hire_status == CandidateProfile.HireStatus.HIRED:
            messages.error(
                request,
                f"⚠️ {candidate.user.get_full_name() or candidate.user.username} is currently "
                "marked as Hired elsewhere and isn't accepting new Hire Requests.",
            )
            return redirect("employers:candidate_detail", pk=candidate.pk)

        form = HireRequestForm(request.POST, employer=employer)

        if form.is_valid():
            hire_request, created = HireRequest.objects.get_or_create(
                employer=employer, candidate=candidate, job=form.cleaned_data.get("job"),
                defaults={"message": form.cleaned_data.get("message", "")},
            )
            if created:
                messages.success(
                    request,
                    f"📨 Hire Request sent to {candidate.user.get_full_name() or candidate.user.username}.",
                )
            else:
                messages.info(request, "ℹ️ You have already sent a request to this candidate for this job.")
        else:
            messages.error(request, "⚠️ There was a problem sending the Hire Request.")

        return redirect("employers:candidate_detail", pk=candidate.pk)


class StartChatWithCandidateView(LoginRequiredMixin, View):
    """'💬 Chat' బటన్ -- ఇక్కడి నుండి క్లిక్ చేస్తే, ఈ employer ఈ
    candidate ని headhunting ద్వారా సంప్రదించినట్టు (job లేకుండా, ఒక
    'general interest' HireRequest రికార్డ్ తో) గుర్తించి, వెంటనే
    Messages యాప్ కి ఆ సంభాషణతో redirect చేస్తుంది. ఇదే
    can_message()/contacts_for() కి 'చెల్లుబాటు అయ్యే సంబంధం'
    ఏర్పరుస్తుంది (permissions.py చూడండి)."""
    login_url = "accounts:employer_login"

    def post(self, request, pk, *args, **kwargs):
        from messaging.models import Conversation

        employer = _current_employer_or_403(request)
        candidate = get_object_or_404(CandidateProfile, pk=pk)

        HireRequest.objects.get_or_create(
            employer=employer, candidate=candidate, job=None,
            defaults={"message": ""},
        )
        conversation = Conversation.get_or_create_between(request.user, candidate.user)
        return redirect(f"{reverse('messaging:employer_messages')}?c={conversation.pk}")


def _current_employer_or_403(request):
    employer_profile = getattr(request.user, "employer_profile", None)
    if employer_profile is None:
        raise PermissionDenied("This page is for Employer accounts only.")
    return employer_profile
