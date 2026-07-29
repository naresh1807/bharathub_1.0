from django import forms

from .models import Employment, JobApplication


class JobApplicationForm(forms.ModelForm):
    """apply చేసేటప్పుడు candidate రాసే ఐచ్ఛిక cover note కోసం ఫారమ్.
    'job' మరియు 'candidate' ఫీల్డ్స్ ఉద్దేశపూర్వకంగా Meta.fields లో
    చేర్చలేదు -- ఎవరు దేనికి apply చేస్తున్నారో ఎప్పుడూ URL/
    request.user నుండే (view లో) నిర్ణయిస్తాం, ఫారమ్ డేటా నుండి కాదు
    -- లేకపోతే ఎవరైనా వేరే candidate తరపున apply చేసే IDOR ప్రమాదం
    ఉంటుంది."""

    class Meta:
        model = JobApplication
        fields = ["cover_note"]
        widgets = {
            "cover_note": forms.Textarea(attrs={
                "class": "form-textarea",
                "rows": 4,
                "placeholder": "Briefly write why you are a good fit for this job (optional)...",
            }),
        }
        labels = {"cover_note": "Cover Note (optional)"}


class ScheduleInterviewForm(forms.ModelForm):
    """Employer 'Schedule Interview' చిన్న ఫారమ్ -- తేదీ/సమయం,
    మోడ్ (video/phone/in-person), లొకేషన్/లింక్, ఐచ్ఛిక నోట్స్.
    సబ్మిట్ అయినప్పుడు status ని కూడా 'interview' కి మార్చడం
    view లోనే (jobs/views.py::ScheduleInterviewView) జరుగుతుంది."""

    class Meta:
        model = JobApplication
        fields = ["interview_datetime", "interview_mode", "interview_location", "interview_notes"]
        widgets = {
            "interview_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "inp"},
            ),
            "interview_mode": forms.Select(attrs={"class": "sel"}),
            "interview_location": forms.TextInput(attrs={
                "class": "inp",
                "placeholder": "Video call link / phone number / office address",
            }),
            "interview_notes": forms.Textarea(attrs={
                "class": "inp", "rows": 2,
                "placeholder": "(optional) Anything the candidate should bring or know...",
            }),
        }
        labels = {
            "interview_datetime": "Interview Date & Time",
            "interview_mode": "Mode",
            "interview_location": "Location / Link",
            "interview_notes": "Notes",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["interview_datetime"].required = True
        self.fields["interview_mode"].required = True
        self.fields["interview_location"].required = True


class MarkAsHiredForm(forms.ModelForm):
    """Employer 'Mark as Hired' ఫారమ్ -- designation/joining date
    job.title/today తో ఆటోమేటిక్‌గా ప్రీఫిల్ అవుతాయి (కావాలంటే మార్చొచ్చు),
    కానీ salary_lpa తప్పనిసరిగా ఎంటర్ చేయాలి -- ఇదే 'My Hires' పేజీలోని
    ఎంప్లాయీ డైరెక్టరీలో కనిపించే జీతం వివరం (jobs/views.py:
    MarkAsHiredView, my_hires.html)."""

    class Meta:
        model = Employment
        fields = ["designation", "joining_date", "salary_lpa"]
        widgets = {
            "designation": forms.TextInput(attrs={"class": "inp"}),
            "joining_date": forms.DateInput(attrs={"type": "date", "class": "inp"}),
            "salary_lpa": forms.NumberInput(attrs={
                "class": "inp", "step": "0.1", "min": "0",
                "placeholder": "e.g. 6.5",
            }),
        }
        labels = {
            "designation": "Designation",
            "joining_date": "Date of Joining",
            "salary_lpa": "Salary Offered (LPA)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["salary_lpa"].required = True
