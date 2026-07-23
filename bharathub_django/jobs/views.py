from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from candidates.models import CandidateProfile
from employers.models import Job

from .forms import JobApplicationForm
from .models import JobApplication

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
        raise PermissionDenied("ఈ పేజీ Candidate ఖాతాలకి మాత్రమే.")
    return profile


def _current_employer(request):
    profile = getattr(request.user, "employer_profile", None)
    if profile is None:
        raise PermissionDenied("ఈ పేజీ Employer ఖాతాలకి మాత్రమే.")
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

        if job.applications.filter(candidate=candidate).exists():
            messages.info(request, "ℹ️ మీరు ఇప్పటికే ఈ ఉద్యోగానికి apply చేశారు.")
            return redirect("jobs:job_detail", pk=job.pk)

        form = JobApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.candidate = candidate
            application.save()
            messages.success(
                request,
                f"🎉 '{job.title}' ({job.employer.company_name}) కి మీ అప్లికేషన్ విజయవంతంగా సమర్పించబడింది!",
            )
        else:
            messages.error(request, "⚠️ అప్లికేషన్ సమర్పించడంలో లోపం. మళ్ళీ ప్రయత్నించండి.")
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
    """Employer 'Shortlist / Interview / Reject / Send Offer' బటన్
    నొక్కినప్పుడు -- POST-only, ఎప్పుడూ job__employer__user=request.user
    తో ఓనర్‌షిప్ చెక్ చేస్తుంది (వేరే employer యొక్క application ని
    ఎవరూ మార్చలేరు -- IDOR గార్డ్)."""
    login_url = "accounts:employer_login"

    def post(self, request, pk, *args, **kwargs):
        application = get_object_or_404(
            JobApplication, pk=pk, job__employer__user=request.user,
        )
        new_status = request.POST.get("status")
        if new_status in JobApplication.Status.values:
            application.status = new_status
            application.save(update_fields=["status", "updated_at"])
            messages.success(
                request,
                f"✅ {application.candidate.user.get_full_name() or application.candidate.user.username} "
                f"యొక్క అప్లికేషన్ స్టేటస్ '{application.get_status_display()}' గా అప్‌డేట్ అయింది.",
            )
        return redirect("jobs:applications")
