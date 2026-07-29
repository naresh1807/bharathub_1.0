from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from candidates.models import CandidateProfile
from employers.models import Job

from .forms import JobApplicationForm, MarkAsHiredForm, ScheduleInterviewForm
from .models import Employment, JobApplication
from .notifications import send_offer_accepted_email, send_offer_letter_ready_email

# ============================================================================
# jobs/views.py -- Job browsing (candidate side) + Applications review
# (employer side). Both sides read/write the same JobApplication model
# (see jobs/models.py) so there's one source of truth for application
# status.
# ============================================================================


def _current_candidate(request):
    """లాగిన్ అయిన యూజర్ కి సంబంధించిన CandidateProfile ని సురక్షితంగా
    తీసుకువస్తుంది -- లేకపోతే (ఉదా: Employer ఖాతాతో ఈ URL కి వస్తే)
    స్పష్టమైన 403 ఇస్తుంది, సర్వర్ క్రాష్ కాదు."""
    profile = getattr(request.user, "candidate_profile", None)
    if profile is None:
        raise PermissionDenied("This page is for Candidate accounts only.")
    return profile


def _current_employer(request):
    profile = getattr(request.user, "employer_profile", None)
    if profile is None:
        raise PermissionDenied("This page is for Employer accounts only.")
    return profile


# ══════════════════════════════════════════════════════════════════════
# CANDIDATE SIDE: Browse jobs, view one job, apply, see my applications
# ══════════════════════════════════════════════════════════════════════
class JobBrowseView(LoginRequiredMixin, TemplateView):
    """అన్ని ACTIVE jobs లిస్ట్ (నిజమైన DB డేటా -- ఇంతకుముందు
    candidate_dashboard.html లో ఉన్న 'Job Matches' మాక్-అప్ లో
    hardcoded TCS/Wipro/Infosys కంపెనీలు కాదు). ?q= తో టైటిల్/స్కిల్స్/
    లొకేషన్ లో సెర్చ్ చేయొచ్చు."""
    template_name = "jobs/job_browse.html"
    login_url = "accounts:employee_login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        candidate = _current_candidate(self.request)
        query = self.request.GET.get("q", "").strip()

        jobs = Job.objects.filter(status=Job.Status.ACTIVE).select_related(
            "employer",
        )
        if query:
            jobs = jobs.filter(
                Q(title__icontains=query)
                | Q(skills_required__icontains=query)
                | Q(location__icontains=query)
            )

        applied_job_ids = set(
            candidate.applications.values_list("job_id", flat=True)
        )

        context.update({
            "jobs": jobs,
            "query": query,
            "applied_job_ids": applied_job_ids,
        })
        return context


class JobDetailView(LoginRequiredMixin, TemplateView):
    """ఒక్క jobకి పూర్తి వివరాలు + apply ఫారమ్ (ఇదివరకటి JS overlay
    మాక్-అప్ కి బదులు నిజమైన, linkable పేజీ -- URL షేర్ చేయొచ్చు,
    బ్రౌజర్ Back బటన్ సరిగ్గా పనిచేస్తుంది)."""
    template_name = "jobs/job_detail.html"
    login_url = "accounts:employee_login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        candidate = _current_candidate(self.request)
        job = get_object_or_404(
            Job, pk=kwargs["pk"], status=Job.Status.ACTIVE,
        )
        existing_application = job.applications.filter(
            candidate=candidate,
        ).first()

        context.update({
            "job": job,
            "existing_application": existing_application,
            "form": JobApplicationForm(),
        })
        return context


class JobApplyView(LoginRequiredMixin, View):
    """POST-only apply action. Ownership/identity ఎప్పుడూ
    request.user నుండే వస్తుంది (ఫారమ్ డేటా నుండి కాదు) -- ఎవరైనా
    వేరే candidate తరపున apply చేసే అవకాశం లేకుండా. UniqueConstraint
    (jobs/models.py) డూప్లికేట్ apply ని DB లెవెల్ లో కూడా ఆపుతుంది."""
    login_url = "accounts:employee_login"

    def post(self, request, pk, *args, **kwargs):
        candidate = _current_candidate(request)
        job = get_object_or_404(Job, pk=pk, status=Job.Status.ACTIVE)

        if candidate.hire_status == CandidateProfile.HireStatus.HIRED:
            messages.error(
                request,
                "⚠️ You're currently marked as Hired, so you can't apply to new jobs. "
                "If you'd like to look for new opportunities, resign from your current "
                "employment first (from your Downloads / employment card on the dashboard).",
            )
            return redirect("jobs:job_detail", pk=job.pk)

        if job.applications.filter(candidate=candidate).exists():
            messages.info(request, "ℹ️ You have already applied to this job.")
            return redirect("jobs:job_detail", pk=job.pk)

        form = JobApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.candidate = candidate
            application.save()
            messages.success(
                request,
                f"🎉 Your application to '{job.title}' ({job.employer.company_name}) was submitted successfully!",
            )
        else:
            messages.error(request, "⚠️ Error submitting application. Please try again.")
        return redirect("jobs:job_detail", pk=job.pk)


class MyApplicationsView(LoginRequiredMixin, TemplateView):
    """Candidate ఇప్పటివరకూ apply చేసిన jobs + వాటి స్టేటస్ (New /
    Shortlisted / Interview / Rejected)."""
    template_name = "jobs/my_applications.html"
    login_url = "accounts:employee_login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        candidate = _current_candidate(self.request)
        context["applications"] = candidate.applications.select_related(
            "job", "job__employer",
        )
        return context


# ══════════════════════════════════════════════════════════════════════
# EMPLOYER SIDE: review applications received across all of my jobs
# ══════════════════════════════════════════════════════════════════════
class ApplicationsView(LoginRequiredMixin, TemplateView):
    """The employer's "review applications" page -- ఇంతకుముందు ఇది
    148/24/7/8 అనే hardcoded స్టాటిక్ నంబర్లు + 4 hardcoded candidate
    కార్డులు చూపించే మాక్-అప్ మాత్రమే. ఇప్పుడు ఈ employer పోస్ట్
    చేసిన jobs కి వచ్చిన నిజమైన JobApplication రికార్డుల్ని చూపిస్తుంది,
    ?job=<id> మరియు ?status=<status> filters తో పాటు.
    """
    template_name = "jobs/applications.html"
    login_url = "accounts:employer_login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employer = _current_employer(self.request)

        applications = JobApplication.objects.filter(
            job__employer=employer,
        ).select_related("job", "candidate", "candidate__user")

        job_filter = self.request.GET.get("job", "")
        status_filter = self.request.GET.get("status", "")
        if job_filter:
            applications = applications.filter(job_id=job_filter)
        if status_filter:
            applications = applications.filter(status=status_filter)

        all_applications = JobApplication.objects.filter(job__employer=employer)
        context.update({
            "applications": applications,
            "jobs": employer.jobs.all(),
            "job_filter": job_filter,
            "status_filter": status_filter,
            "status_choices": JobApplication.Status.choices,
            "total_count": all_applications.count(),
            "shortlisted_count": all_applications.filter(
                status=JobApplication.Status.SHORTLISTED,
            ).count(),
            "interview_count": all_applications.filter(
                status=JobApplication.Status.INTERVIEW,
            ).count(),
            "new_count": all_applications.filter(
                status=JobApplication.Status.NEW,
            ).count(),
        })
        return context


class ApplicationStatusUpdateView(LoginRequiredMixin, View):
    """Employer 'Shortlist / Reject / Send Offer' బటన్ నొక్కినప్పుడు --
    POST-only, ఎప్పుడూ job__employer__user=request.user తో ఓనర్‌షిప్
    చెక్ చేస్తుంది (వేరే employer యొక్క application ని ఎవరూ మార్చలేరు
    -- IDOR గార్డ్).

    గమనిక: 'interview' మరియు 'hired' ఇక్కడ అనుమతించం -- రెండిటికీ
    అదనపు వివరాలు (తేదీ/సమయం/మోడ్ ... జీతం/joining date) తప్పనిసరి
    కాబట్టి, అవి వాటి సొంత ఫారమ్‌ల ద్వారానే (ScheduleInterviewView /
    MarkAsHiredView) సెట్ అవ్వాలి.
    """
    login_url = "accounts:employer_login"

    def post(self, request, pk, *args, **kwargs):
        application = get_object_or_404(
            JobApplication, pk=pk, job__employer__user=request.user,
        )
        new_status = request.POST.get("status")
        allowed = set(JobApplication.Status.values) - {
            JobApplication.Status.INTERVIEW, JobApplication.Status.HIRED,
        }
        if new_status in allowed:
            application.status = new_status
            application.save(update_fields=["status", "updated_at"])
            messages.success(
                request,
                f"✅ {application.candidate.user.get_full_name() or application.candidate.user.username} "
                f"Application status updated to '{application.get_status_display()}'.",
            )
        return redirect("jobs:applications")


class MarkAsHiredView(LoginRequiredMixin, View):
    """Employer 'Mark as Hired' పేజీ (offered status మీద మాత్రమే కనిపిస్తుంది,
    _applications_body.html చూడండి) -- designation/joining date/salary
    తీసుకుని, ఒక నిజమైన Employment రికార్డ్ క్రియేట్ చేసి,
    candidate.hire_status ని HIRED కి మారుస్తుంది. అప్పటి నుండి ఆ
    candidate కి కొత్త job offers/hire requests కనిపించవు (jobs/views.py
    JobApplyView, employers/views.py SendHireRequestView చూడండి) --
    resign చేసి, employer accept చేసేదాకా (ResignationRespondView)."""
    login_url = "accounts:employer_login"
    template_name = "jobs/mark_as_hired.html"

    def _get_application(self, request, pk):
        return get_object_or_404(
            JobApplication, pk=pk, job__employer__user=request.user,
        )

    def get(self, request, pk, *args, **kwargs):
        application = self._get_application(request, pk)
        form = MarkAsHiredForm(initial={
            "designation": application.job.title,
            "joining_date": timezone.now().date(),
        })
        return render(request, self.template_name, {"application": application, "form": form})

    def post(self, request, pk, *args, **kwargs):
        application = self._get_application(request, pk)
        candidate = application.candidate

        if candidate.hire_status == CandidateProfile.HireStatus.HIRED:
            messages.error(
                request,
                f"⚠️ {candidate.user.get_full_name() or candidate.user.username} is already "
                "marked as Hired elsewhere on BharatHub.",
            )
            return redirect("jobs:applications")

        if application.status != JobApplication.Status.OFFERED:
            messages.error(request, "⚠️ You can only mark a candidate as Hired after sending them an offer.")
            return redirect("jobs:applications")

        form = MarkAsHiredForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"application": application, "form": form})

        employment = form.save(commit=False)
        employment.application = application
        employment.candidate = candidate
        employment.save()

        application.status = JobApplication.Status.HIRED
        application.save(update_fields=["status", "updated_at"])
        candidate.hire_status = CandidateProfile.HireStatus.HIRED
        candidate.save(update_fields=["hire_status"])

        send_offer_letter_ready_email(employment)

        messages.success(
            request,
            f"🎉 {candidate.user.get_full_name() or candidate.user.username} marked as Hired! "
            "Their offer letter is ready in their Downloads, and they've been emailed about it.",
        )
        return redirect("jobs:my_hires")


class ScheduleInterviewView(LoginRequiredMixin, View):
    """Employer 'Schedule Interview' పేజీ -- తేదీ/సమయం/మోడ్/లొకేషన్
    తీసుకుని, సేవ్ అయిన వెంటనే status ని 'interview' కి కూడా మారుస్తుంది
    (రెండూ ఒకేసారి, ఒకే source of truth). candidate వైపు ఈ వివరాలే
    'My Applications' పేజీలో కనిపిస్తాయి (jobs/my_applications.html)."""
    login_url = "accounts:employer_login"
    template_name = "jobs/schedule_interview.html"

    def get(self, request, pk, *args, **kwargs):
        application = get_object_or_404(
            JobApplication, pk=pk, job__employer__user=request.user,
        )
        form = ScheduleInterviewForm(instance=application)
        return render(request, self.template_name, {"application": application, "form": form})

    def post(self, request, pk, *args, **kwargs):
        application = get_object_or_404(
            JobApplication, pk=pk, job__employer__user=request.user,
        )
        form = ScheduleInterviewForm(request.POST, instance=application)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.status = JobApplication.Status.INTERVIEW

            # మోడ్ = Video అయితే, మేనువల్‌గా ఎవరైనా ఏదో లింక్ పేస్ట్
            # చేయాల్సిన అవసరం లేకుండా, మన సొంత BharatHub Meet రూమ్ నే
            # ఆటోమేటిక్‌గా క్రియేట్ చేసి, దాని లింక్ నే
            # interview_location గా సేవ్ చేస్తాం (meetings/models.py
            # చూడండి -- ఇదే application కి ఇంతకుముందే ఒక మీటింగ్ ఉంటే
            # దాన్నే మళ్ళీ వాడుతుంది, ప్రతిసారీ కొత్త లింక్ క్రియేట్
            # చేయదు).
            if interview.interview_mode == JobApplication.InterviewMode.VIDEO:
                from meetings.models import Meeting
                meeting = Meeting.get_or_create_for_application(interview, host=request.user)
                if interview.interview_datetime and meeting.scheduled_at != interview.interview_datetime:
                    meeting.scheduled_at = interview.interview_datetime
                    meeting.save(update_fields=["scheduled_at"])
                interview.interview_location = request.build_absolute_uri(
                    reverse("meetings:room", kwargs={"room_code": meeting.room_code}),
                )

            interview.save()
            messages.success(
                request,
                f"📅 Interview scheduled with "
                f"{application.candidate.user.get_full_name() or application.candidate.user.username} "
                f"on {interview.interview_datetime:%d %b %Y, %I:%M %p}.",
            )
            return redirect("jobs:applications")
        return render(request, self.template_name, {"application": application, "form": form})


# ══════════════════════════════════════════════════════════════════════
# Employment lifecycle: Candidate resigns → Employer accepts/declines
#
# jobs/models.py: Employment.Status చూడండి (ACTIVE →
# RESIGNATION_REQUESTED → RELIEVED). ఇక్కడి రెండు వ్యూలే ఆ లైఫ్‌సైకిల్
# ని ముందుకు నడిపిస్తాయి.
# ══════════════════════════════════════════════════════════════════════
class ResignationRequestView(LoginRequiredMixin, View):
    """Candidate dashboard లో 'Resign' బటన్ -- ఈ candidate యొక్క ప్రస్తుత
    ACTIVE Employment ని RESIGNATION_REQUESTED కి మారుస్తుంది. ఇక్కడ
    candidate.hire_status ఇంకా HIRED గానే ఉంటుంది (కొత్త job offers
    ఇంకా రావు) -- Employer accept చేసేదాకా."""
    login_url = "accounts:employee_login"

    def post(self, request, *args, **kwargs):
        candidate = _current_candidate(request)
        employment = Employment.objects.filter(
            candidate=candidate, status=Employment.Status.ACTIVE,
        ).select_related("application__job__employer").first()

        if employment is None:
            messages.error(request, "⚠️ You don't have an active employment record to resign from.")
            return redirect("candidates:candidate_dashboard")

        employment.status = Employment.Status.RESIGNATION_REQUESTED
        employment.resignation_requested_at = timezone.now()
        employment.save(update_fields=["status", "resignation_requested_at", "updated_at"])
        messages.success(
            request,
            f"📤 Resignation request sent to {employment.employer.company_name}. "
            "You'll be marked available again once they accept it.",
        )
        return redirect("candidates:candidate_dashboard")


class MyHiresView(LoginRequiredMixin, TemplateView):
    """Employer యొక్క 'My Hires' పేజీ -- ఎంత మంది పని చేస్తున్నారు, ఏ
    డిపార్ట్‌మెంట్‌లో, ఏ జీతానికి, ఎప్పుడు జాయిన్ అయ్యారు అనేది
    స్పష్టంగా చూపించే ఎంప్లాయీ డైరెక్టరీ (ACTIVE + RESIGNATION_REQUESTED
    = ప్రస్తుత ఉద్యోగులు, RELIEVED = గత చరిత్ర). resignation requests
    accept/decline చేయడానికి ఇక్కడి నుండే."""
    template_name = "jobs/my_hires.html"
    login_url = "accounts:employer_login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employer = _current_employer(self.request)
        employments = Employment.objects.filter(
            application__job__employer=employer,
        ).select_related("candidate__user", "application__job")

        current_employees = [
            e for e in employments
            if e.status in (Employment.Status.ACTIVE, Employment.Status.RESIGNATION_REQUESTED)
        ]
        relieved_employees = [e for e in employments if e.status == Employment.Status.RELIEVED]

        # "ఎంత మంది ఏం డిపార్ట్‌మెంట్ లో పని చేస్తున్నారు" -- department
        # వారీగా ప్రస్తుత ఉద్యోగుల సంఖ్య (My Hires పేజీ టాప్ సమ్మరీ కోసం).
        department_counts = {}
        for e in current_employees:
            label = (e.job.get_department_display() if e.job else "") or "—"
            department_counts[label] = department_counts.get(label, 0) + 1

        context["employments"] = employments
        context["current_employees"] = current_employees
        context["relieved_employees"] = relieved_employees
        context["department_counts"] = sorted(department_counts.items(), key=lambda kv: -kv[1])
        context["pending_resignations"] = [
            e for e in employments if e.status == Employment.Status.RESIGNATION_REQUESTED
        ]
        return context


class ResignationRespondView(LoginRequiredMixin, View):
    """Employer 'Accept'/'Decline' resignation బటన్ -- ఓనర్‌షిప్ చెక్
    (application__job__employer__user=request.user) IDOR గార్డ్.
    Accept: RELIEVED + relieving_date సెట్ + candidate.hire_status మళ్ళీ
    AVAILABLE (ఇక్కడి నుండే Downloads లో Joining/Relieving/Experience
    Letter లు ఆటోమేటిక్‌గా అందుబాటులోకి వస్తాయి -- candidates/views.py
    DownloadsListView చూడండి). Decline: ఉద్యోగం ACTIVE గానే కొనసాగుతుంది."""
    login_url = "accounts:employer_login"

    def post(self, request, pk, *args, **kwargs):
        employment = get_object_or_404(
            Employment, pk=pk, application__job__employer__user=request.user,
            status=Employment.Status.RESIGNATION_REQUESTED,
        )
        action = request.POST.get("action")
        candidate = employment.candidate

        if action == "accept":
            employment.status = Employment.Status.RELIEVED
            employment.relieving_date = timezone.now().date()
            employment.save(update_fields=["status", "relieving_date", "updated_at"])
            candidate.hire_status = CandidateProfile.HireStatus.AVAILABLE
            candidate.save(update_fields=["hire_status"])
            messages.success(
                request,
                f"✅ Relieved {candidate.user.get_full_name() or candidate.user.username}. "
                "They can now see new job offers again, and their Relieving/Experience Letters "
                "are ready in their Downloads.",
            )
        elif action == "decline":
            employment.status = Employment.Status.ACTIVE
            employment.resignation_requested_at = None
            employment.save(update_fields=["status", "resignation_requested_at", "updated_at"])
            messages.info(
                request,
                f"ℹ️ Resignation declined -- {candidate.user.get_full_name() or candidate.user.username} "
                "remains an active employee.",
            )
        return redirect("jobs:my_hires")


class OfferLetterAcceptView(LoginRequiredMixin, View):
    """Candidate 'Accept Offer' బటన్ (candidates/document_offer_letter.html
    లో) -- ఈ Employment ఓనర్‌షిప్ చెక్ (candidate=_current_candidate)
    IDOR గార్డ్. Accept అయిన వెంటనే employer కి ఇమెయిల్ నోటిఫికేషన్
    వెళ్తుంది (jobs/notifications.py: send_offer_accepted_email) --
    'అది ఏం ప్లేయర్ కి రావాలి' అనే రిక్వైర్‌మెంట్ ఇక్కడే."""
    login_url = "accounts:employee_login"

    def post(self, request, pk, *args, **kwargs):
        candidate = _current_candidate(request)
        employment = get_object_or_404(
            Employment.objects.select_related("application__job__employer__user", "candidate__user"),
            pk=pk, candidate=candidate,
        )

        if employment.offer_status != Employment.OfferStatus.ACCEPTED:
            employment.offer_status = Employment.OfferStatus.ACCEPTED
            employment.offer_accepted_at = timezone.now()
            employment.save(update_fields=["offer_status", "offer_accepted_at", "updated_at"])
            send_offer_accepted_email(employment)
            messages.success(request, "✅ Offer accepted! Your employer has been notified.")

        return redirect("candidates:download_offer_letter", pk=employment.pk)
