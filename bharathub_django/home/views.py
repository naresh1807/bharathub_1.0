from datetime import timedelta

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from accounts.models import EmployeeProfile, EmployerProfile
from employers.models import Job
from vendor.models import VendorProfile
from videos.utils import published_videos_for

from .forms import ContactForm


class BharatHubHomeView(TemplateView):
    template_name = "home/bharathub_home.html"

    # ------------------------------------------------------------------
    # ఇంతకుముందు ఈ పేజీలో "12K+ Companies", "5.8L+ Job Seekers" లాంటి
    # స్టాట్స్ HTML లో నేరుగా హార్డ్‌కోడ్ చేయబడ్డాయి. ఇప్పుడు అవి DB
    # లోని అసలైన count()లు -- ఎప్పుడు ఎంతమంది register అయితే అంత
    # accurate గా కనిపిస్తాయి.
    #
    # latest_jobs: కుడి వైపు (right-panel) "🔔 Live Job Exchange" స్క్రోలింగ్
    # టికర్ లో చూపించే జాబ్స్ -- ఇంతకుముందు ఇవి TCS/Infosys/Wipro లాంటి
    # హార్డ్‌కోడెడ్ మాక్ డేటా గా ఉండేవి; ఇప్పుడు పూర్తిగా DB (employers.Job)
    # నుండే వస్తాయి, ఇంకెక్కడా (ఎడమ వైపు feed లో) జాబ్స్ చూపించం.
    # is_new: 24 గంటల్లోపు పోస్ట్ చేసిన జాబ్ కి టెంప్లేట్ లో "NEW" బ్యాడ్జ్
    # చూపించడానికి -- ఇది DB ఫీల్డ్ కాదు, ఇక్కడే లెక్కించి instance పైన
    # పెడుతున్నాం.
    # ------------------------------------------------------------------
    # employer_chips: దిగువన ఉన్న "🏢 Joined Premium Companies" స్లయిడర్
    # లో చూపించే కంపెనీలు -- ఇంతకుముందు ఇవి TCS/Wipro/Infosys/HCL... అని
    # 10 హార్డ్‌కోడెడ్ కంపెనీలు గా ఉండేవి; ఇప్పుడు నిజంగా register అయిన
    # EmployerProfile రికార్డుల నుండే వస్తాయి. ప్రతి కంపెనీకీ ఒక రంగు
    # కావాలి కాబట్టి (DB లో logo/రంగు ఫీల్డ్ లేదు), ఇక్కడ ఒక స్థిర
    # పాలెట్ నుండి index బట్టి తిరిగి తిరిగి (cyclic) కేటాయిస్తున్నాం --
    # ఇది కేవలం విజువల్ మాత్రమే, డేటా కాదు.
    _CHIP_COLORS = [
        "#0050b3", "#4a148c", "#1b5e20", "#b71c1c", "#e65100",
        "#006064", "#37474f", "#880e4f", "#1a237e", "#004d40",
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stat_employers"] = EmployerProfile.objects.count()
        context["stat_employees"] = EmployeeProfile.objects.count()
        context["stat_vendors"] = VendorProfile.objects.count()
        context["stat_active_jobs"] = Job.objects.filter(status=Job.Status.ACTIVE).count()

        ticker_jobs = list(
            Job.objects.filter(status=Job.Status.ACTIVE)
            .select_related("employer")
            .order_by("-created_at")[:8]
        )
        new_cutoff = timezone.now() - timedelta(hours=24)
        for job in ticker_jobs:
            job.is_new = job.created_at >= new_cutoff
        context["latest_jobs"] = ticker_jobs

        context["employer_chips"] = [
            {
                "name": emp.company_name,
                "initials": emp.company_name[:2].upper(),
                "color": self._CHIP_COLORS[i % len(self._CHIP_COLORS)],
            }
            for i, emp in enumerate(EmployerProfile.objects.order_by("-id")[:10])
        ]

        # 🎬 "Company Achievements & Culture Feed" -- videos యాప్ లోని
        # నిజమైన Video రికార్డుల నుండి (ఏ కంపెనీ అయినా పబ్లిష్ చేసినవి)
        # వస్తాయి -- ఇదే హెల్పర్ ని Employer & Candidate డాష్‌బోర్డులు
        # కూడా వాడతాయి, కాబట్టి ఫీడ్ మూడు చోట్లా ఒకేలా కనిపిస్తుంది.
        context["feed_videos"] = published_videos_for(self.request.user, limit=10)
        return context


class AboutView(TemplateView):
    template_name = "home/about.html"


# ----------------------------------------------------------------------
# ContactView
# ఎందుకు ఇలా మార్చాం: ఇంతకు ముందు ఇది plain TemplateView — అంటే
# పేజీ ని GET రిక్వెస్ట్ లో చూపించడం మాత్రమే చేసేది, POST (ఫారమ్ సబ్మిట్)
# ని అస్సలు హ్యాండిల్ చేయలేదు. ఇప్పుడు GET & POST రెండిటినీ ఒకే View లో
# రాస్తున్నాం (Django లో ఇది సాధారణ పద్ధతి):
#   - GET  -> ఖాళీ ఫారమ్ తో పేజీ చూపించు
#   - POST -> యూజర్ పంపిన డేటాని వాలిడేట్ చేసి, సరైతే DB లో సేవ్ చేసి
#             మళ్ళీ అదే పేజీకి redirect చేయి (success మెసేజ్ తో)
# ----------------------------------------------------------------------
class ContactView(TemplateView):
    template_name = "home/contact.html"

    # get_context_data: టెంప్లేట్ కి ఏ డేటా పంపాలో ఇక్కడ నిర్ణయిస్తాం.
    # ఇక్కడ ఖాళీ ContactForm() ని పంపుతున్నాం, తద్వారా టెంప్లేట్ లో
    # {{ form }} అని రాస్తే Django ఆటోమేటిక్‌గా ఇన్‌పుట్ ఫీల్డ్స్ + csrf
    # రెండరింగ్ చేస్తుంది.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # form ఇప్పటికే context లో పెట్టి ఉంటే (post() లో ఎర్రర్స్ తో పంపినప్పుడు)
        # దాన్ని అలాగే ఉంచుతాం, లేకపోతే కొత్త ఖాళీ ఫారమ్ క్రియేట్ చేస్తాం.
        context.setdefault("form", ContactForm())
        return context

    # post: యూజర్ "Send Message" బటన్ నొక్కి ఫారమ్ సబ్మిట్ చేసినప్పుడు
    # ఈ మెథడ్ కాల్ అవుతుంది. request.POST లో వచ్చిన డేటాతో ContactForm
    # బైండ్ చేస్తాం.
    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST)

        # form.is_valid() -> models.py & forms.py లో రాసిన అన్ని
        # వాలిడేషన్ రూల్స్ (max_length, EmailField ఫార్మాట్, clean_message
        # లోని 10-అక్షరాల చెక్ మొదలైనవి) ఇక్కడ రన్ అవుతాయి.
        if form.is_valid():
            # form.save() -> ContactMessage(**cleaned_data) క్రియేట్ చేసి
            # DB లో ఒక్క లైన్ లో సేవ్ చేస్తుంది (ModelForm వాడటం వల్ల
            # వచ్చే అతి పెద్ద ఉపయోగం ఇదే).
            form.save()
            messages.success(
                request,
                "✅ ధన్యవాదాలు! మీ సందేశం అందింది. 24 గంటల్లో స్పందిస్తాం.",
            )
            # POST తర్వాత redirect చేయడం (PRG pattern: Post/Redirect/Get)
            # -- యూజర్ పేజీ రిఫ్రెష్ చేసినా మెసేజ్ మళ్ళీ డూప్లికేట్‌గా
            # సబ్మిట్ కాకుండా ఉండటానికి ఇది ఒక security/UX best practice.
            return redirect("home:contact")

        # ఫారమ్ ఇన్వాలిడ్ అయితే (ఏదైనా ఫీల్డ్ తప్పు) అదే పేజీని, కానీ
        # ఎర్రర్స్ తో నింపిన ఫారమ్‌ని మళ్ళీ చూపిస్తాం, తద్వారా యూజర్
        # ఏ ఫీల్డ్ తప్పు అని చూసుకోవచ్చు (డేటా మళ్ళీ టైప్ చేయాల్సిన
        # అవసరం లేదు — form అప్పటికే నింపిన విలువలతోనే వస్తుంది).
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class PrivacyView(TemplateView):
    template_name = "home/privacy.html"


class TermsView(TemplateView):
    template_name = "home/terms.html"


class HelpView(TemplateView):
    template_name = "home/help.html"
