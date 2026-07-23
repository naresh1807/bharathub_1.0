from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Job, HireRequest

# ============================================================================
# employers/forms.py
# ఎందుకు ModelForm (accounts/forms.py లో plain forms.Form వాడాం, కానీ
# ఇక్కడ ModelForm): అక్కడ ఒక్క ఫారమ్ డేటా రెండు మోడల్స్ (User +
# Profile) లోకి వెళ్ళింది కాబట్టి plain Form వాడాల్సి వచ్చింది.
# ఇక్కడ మొత్తం డేటా ఒక్క Job మోడల్ లోకే వెళ్తుంది కాబట్టి, ModelForm
# వాడితే జాబ్ మోడల్ లో ఇప్పటికే రాసిన max_length / choices / null వంటి
# రూల్స్ అన్నీ ఆటోమేటిక్‌గా ఫారమ్ కి కూడా వర్తిస్తాయి (DRY -- Don't
# Repeat Yourself, ఒకే రూల్ ని రెండుసార్లు రాయక్కర్లేదు).
# ============================================================================


class JobPostForm(forms.ModelForm):
    class Meta:
        model = Job
        # employer, status, created_at, updated_at ఉద్దేశపూర్వకంగా ఇక్కడ
        # లేవు -- ఇవి యూజర్ టైప్ చేసేవి కావు, views.py లోనే సర్వర్-సైడ్
        # లో సెట్ చేస్తాం (employer = ప్రస్తుతం లాగిన్ అయిన కంపెనీ,
        # status = ఏ బటన్ నొక్కారో దాన్ని బట్టి). యూజర్ ఇన్‌పుట్ లోంచి
        # నేరుగా "ఏ కంపెనీ కి ఈ జాబ్" అని తీసుకుంటే, ఎవరైనా browser dev
        # tools తో fields మార్చి వేరే కంపెనీ పేరు మీద జాబ్ పోస్ట్ చేసే
        # అవకాశం ఉంటుంది (ఇది ఒక భద్రతా రంధ్రం -- ఎప్పుడూ "ఎవరు
        # చేస్తున్నారు" అనేది request.user నుండే తీసుకోవాలి, ఫారమ్
        # డేటా నుండి కాదు).
        fields = [
            "title", "department", "job_type", "experience_level",
            "location", "salary_min", "salary_max", "description",
            "skills_required", "application_deadline", "openings_count",
            "qualification",
        ]
        # widgets: ప్రతి ఫీల్డ్ కి ఇంతకుముందు employer_dashboard.html లో
        # హార్డ్‌కోడ్ చేసిన అదే CSS క్లాస్ (form-input / form-select /
        # form-textarea) ఇక్కడ ఇస్తున్నాం -- తద్వారా {{ form.title }}
        # అని రెండర్ చేసినా, పేజీ లుక్ ఇంతకుముందు లాగే కనిపిస్తుంది
        # (ఒక్క పిక్సెల్ కూడా మారదు), కానీ ఇప్పుడు ఇది నిజమైన,
        # సర్వర్-సైడ్ వాలిడేట్ అయ్యే ఫారమ్.
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Python Developer, React Engineer...",
            }),
            "department": forms.Select(attrs={"class": "form-select"}),
            "job_type": forms.Select(attrs={"class": "form-select"}),
            "experience_level": forms.Select(attrs={"class": "form-select"}),
            "location": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Hyderabad, Bangalore, Remote...",
            }),
            "salary_min": forms.NumberInput(attrs={
                "class": "form-input", "placeholder": "Min", "min": 0,
            }),
            "salary_max": forms.NumberInput(attrs={
                "class": "form-input", "placeholder": "Max", "min": 0,
            }),
            "description": forms.Textarea(attrs={
                "class": "form-textarea", "rows": 5,
                "placeholder": "Job responsibilities, requirements, company culture...",
            }),
            # id="skillTagInput" ఇంతకుముందు JS (addSkillTag/removeSkillTag)
            # వాడే అదే id -- ఆ JS స్కిల్ ట్యాగ్స్ ని విజువల్‌గా
            # <span> చిప్స్ గా చూపిస్తుంది, కానీ అసలైన value ఈ దాచిన
            # (hidden) ఫీల్డ్ లోనే ఉంటుంది, అదే సర్వర్ కి POST అవుతుంది.
            "skills_required": forms.TextInput(attrs={
                "class": "form-input", "id": "skillsRequiredField",
                "style": "display:none;",
            }),
            "application_deadline": forms.DateInput(attrs={
                "class": "form-input", "type": "date",
            }),
            "openings_count": forms.NumberInput(attrs={
                "class": "form-input", "placeholder": "5", "min": 1,
            }),
            "qualification": forms.Select(attrs={"class": "form-select"}),
        }

    # ------------------------------------------------------------------
    # clean_<field>: ప్రతి ఫీల్డ్ కి సర్వర్-సైడ్ వాలిడేషన్. JS వాలిడేషన్
    # ని ఎవరైనా బ్రౌజర్ dev tools లో ఆపేయొచ్చు / bypass చేయొచ్చు కాబట్టి,
    # అసలైన, నమ్మదగ్గ వాలిడేషన్ ఎప్పుడూ సర్వర్ సైడ్ లోనే ఉండాలి.
    # ------------------------------------------------------------------
    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if len(title) < 3:
            raise ValidationError("ఉద్యోగం పేరు కనీసం 3 అక్షరాలు ఉండాలి.")
        return title

    def clean_description(self):
        description = self.cleaned_data["description"].strip()
        if len(description) < 20:
            raise ValidationError(
                "జాబ్ డిస్క్రిప్షన్ చాలా చిన్నదిగా ఉంది -- కనీసం 20 "
                "అక్షరాలైనా ఇవ్వండి (responsibilities/requirements)."
            )
        return description

    def clean_skills_required(self):
        # "Python, , Django,,MySQL" లాంటి చెత్త ఇన్‌పుట్ ని కూడా
        # శుభ్రంగా "Python, Django, MySQL" గా మారుస్తుంది -- ఖాళీ
        # ఎంట్రీలు, డూప్లికేట్ కామాలు తీసేస్తుంది.
        raw = self.cleaned_data.get("skills_required", "").strip()
        skills = [s.strip() for s in raw.split(",") if s.strip()]
        if not skills:
            raise ValidationError("కనీసం ఒక్క స్కిల్ అయినా ఇవ్వండి.")
        if len(skills) > 25:
            raise ValidationError("25 స్కిల్స్ కన్నా ఎక్కువ ఇవ్వకండి.")
        return ", ".join(skills)

    def clean_application_deadline(self):
        deadline = self.cleaned_data.get("application_deadline")
        # గతంలో (past) తేదీ ని డెడ్‌లైన్ గా పెట్టనివ్వకూడదు -- ఇది
        # <input type="date" min="..."> అనే HTML అట్రిబ్యూట్ తో కూడా
        # ఆపొచ్చు, కానీ అది కూడా క్లయింట్-సైడ్ చెక్ మాత్రమే, కాబట్టి
        # ఇక్కడ మళ్ళీ (సర్వర్ సైడ్) చెక్ చేస్తున్నాం.
        if deadline and deadline < timezone.now().date():
            raise ValidationError("డెడ్‌లైన్ గతంలో ఉండకూడదు -- భవిష్యత్ తేదీ ఇవ్వండి.")
        return deadline

    def clean_openings_count(self):
        count = self.cleaned_data.get("openings_count")
        if count is not None and count < 1:
            raise ValidationError("ఖాళీల సంఖ్య కనీసం 1 అయినా ఉండాలి.")
        if count is not None and count > 10000:
            # అసంబద్ధంగా పెద్ద సంఖ్య (ఉదా: ఎవరైనా బరితెగించి "999999999999"
            # అని పంపితే) DB లో అస్తవ్యస్తమైన డేటా / integer overflow
            # రాకుండా ఇక్కడే ఒక సహేతుకమైన గరిష్ట పరిమితి పెడుతున్నాం.
            raise ValidationError("ఖాళీల సంఖ్య చాలా ఎక్కువగా ఉంది.")
        return count

    # clean() (ఫీల్డ్ లేకుండా): రెండు ఫీల్డ్స్ ని కలిపి చెక్ చేయాలంటే
    # (ఇక్కడ salary_min <= salary_max) ఈ మెథడ్ వాడతాం.
    def clean(self):
        cleaned_data = super().clean()
        salary_min = cleaned_data.get("salary_min")
        salary_max = cleaned_data.get("salary_max")
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            self.add_error(
                "salary_max", "గరిష్ట జీతం (max) కనిష్ట జీతం (min) కన్నా ఎక్కువ ఉండాలి.",
            )
        return cleaned_data


class HireRequestForm(forms.ModelForm):
    """Employer, candidate-search ఫలితం మీద నుండి పంపే 'Hire
    Request' ఫారమ్. `job` dropdown ని view.py లో ఆ employer యొక్క
    ACTIVE jobs కి మాత్రమే పరిమితం చేస్తాం (queryset ఇక్కడ ఖాళీగా
    ఉంచి, __init__ లో సెట్ చేస్తాం -- ఎందుకంటే ఏ jobs కనిపించాలో
    request.user మీద ఆధారపడి ఉంటుంది, అది ఇక్కడ తెలియదు)."""

    class Meta:
        model = HireRequest
        fields = ["job", "message"]
        widgets = {
            "job": forms.Select(attrs={"class": "form-input"}),
            "message": forms.Textarea(attrs={
                "class": "form-input", "rows": 3,
                "placeholder": "ఉదా: మీ ప్రొఫైల్ మాకు నచ్చింది, ఈ పొజిషన్ కి ఇంటర్వ్యూ కి ఆసక్తి ఉందా?",
            }),
        }

    def __init__(self, *args, employer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["job"].required = False
        self.fields["job"].empty_label = "సాధారణ ఆసక్తి (ప్రత్యేక job లేకుండా)"
        if employer is not None:
            self.fields["job"].queryset = employer.jobs.filter(status=Job.Status.ACTIVE)
