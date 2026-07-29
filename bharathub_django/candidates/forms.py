from django import forms
from django.core.exceptions import ValidationError

from .models import CandidateEducation, CandidateProfile

# ══════════════════════════════════════════════════════════════════════
# candidates/forms.py
#
# ఇప్పుడు models.py లో నిజమైన మోడల్స్ (CandidateProfile,
# CandidateEducation) రాశాం కాబట్టి, ఇక్కడ accounts/forms.py &
# vendor/forms.py లో వాడిన అదే పద్ధతిలో ModelForm క్లాసులు రాస్తున్నాం:
#   1. widgets లో CSS క్లాస్‌లు (candidate_dashboard.css లోని
#      .form-input) ఇచ్చాం -- existing టెంప్లేట్ స్టైలింగ్ తో
#      కలిసిపోయేలా.
#   2. clean_<field>() మెథడ్స్ తో సర్వర్-సైడ్ వాలిడేషన్.
#   3. ModelForm.Meta.fields లో "user" ఫీల్డ్ ఎప్పుడూ చేర్చము --
#      దీన్ని view.py లోనే request.user నుండి సెట్ చేస్తాం (ఇలా చేయకపోతే
#      ఒక దురుద్దేశపరుడు హిడెన్ <input name="user"> ఫీల్డ్ ద్వారా
#      వేరే యూజర్ ప్రొఫైల్ ని ఓవర్‌రైట్ చేసే "mass assignment /
#      IDOR" తరహా దాడి చేయగలడు).
# ══════════════════════════════════════════════════════════════════════

# ఫైల్ అప్‌లోడ్ సైజ్ పరిమితులు (బైట్లలో) -- సర్వర్ మీద అనవసరంగా పెద్ద
# ఫైళ్ళు అప్‌లోడ్ కావడం (disk-fill / DoS తరహా దాడి) ఆపడానికి.
MAX_RESUME_SIZE_MB = 2
MAX_PHOTO_SIZE_MB = 2

INPUT_CLASS = "form-input"


class CandidateProfileForm(forms.ModelForm):
    """
    Candidate తన ప్రొఫెషనల్ ప్రొఫైల్ ని క్రియేట్/ఎడిట్ చేసుకునే ఫారమ్.
    View దీన్ని ఎప్పుడూ `CandidateProfileForm(request.POST,
    request.FILES, instance=profile)` లాగే వాడాలి -- `instance` గా
    ఎప్పుడూ request.user కి సంబంధించిన ప్రొఫైల్ మాత్రమే పంపాలి, URL లో
    వచ్చిన ఏ id నైనా కాదు (అలా చేస్తే వేరే యూజర్ ప్రొఫైల్ ని ఎడిట్
    చేసే IDOR దాడికి దారి తీస్తుంది).
    """

    class Meta:
        model = CandidateProfile
        fields = [
            "headline", "location", "about", "skills", "qualification",
            "experience_level", "current_ctc_lpa", "expected_ctc_lpa",
            "hire_status", "resume", "profile_photo",
            "linkedin_url", "portfolio_url",
        ]
        widgets = {
            "headline": forms.TextInput(attrs={
                "class": INPUT_CLASS, "placeholder": "e.g. Python Developer · Fresher",
            }),
            "location": forms.TextInput(attrs={
                "class": INPUT_CLASS, "placeholder": "e.g. Hyderabad",
            }),
            "about": forms.Textarea(attrs={
                "class": INPUT_CLASS, "rows": 4,
                "placeholder": "Write a short summary about yourself...",
            }),
            "skills": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Python, Django, MySQL, React, Git (comma separated)",
            }),
            "qualification": forms.TextInput(attrs={
                "class": INPUT_CLASS, "placeholder": "e.g. B.Tech CSE",
            }),
            "experience_level": forms.Select(attrs={"class": INPUT_CLASS}),
            "current_ctc_lpa": forms.NumberInput(attrs={
                "class": INPUT_CLASS, "step": "0.1", "min": "0", "placeholder": "e.g. 6.5",
            }),
            "expected_ctc_lpa": forms.NumberInput(attrs={
                "class": INPUT_CLASS, "step": "0.1", "min": "0", "placeholder": "e.g. 9.0",
            }),
            "hire_status": forms.Select(attrs={"class": INPUT_CLASS}),
            "resume": forms.ClearableFileInput(attrs={
                "class": INPUT_CLASS, "accept": ".pdf,.doc,.docx",
            }),
            "profile_photo": forms.ClearableFileInput(attrs={
                "class": INPUT_CLASS, "accept": "image/*",
            }),
            "linkedin_url": forms.URLInput(attrs={
                "class": INPUT_CLASS, "placeholder": "https://linkedin.com/in/...",
            }),
            "portfolio_url": forms.URLInput(attrs={
                "class": INPUT_CLASS, "placeholder": "https://your-portfolio.com",
            }),
        }

    # ------------------------------------------------------------------
    # clean_skills(): యూజర్ "Python,, Django ,MySQL,Python" లాంటివి
    # టైప్ చేసినా, ఖాళీలు తీసేసి / డూప్లికేట్లు తీసేసి / ఒక
    # శుభ్రమైన ఫార్మాట్ లో మళ్ళీ నిల్వ చేస్తాం.
    # ------------------------------------------------------------------
    def clean_skills(self):
        raw = self.cleaned_data.get("skills", "")
        seen = []
        for skill in raw.split(","):
            skill = skill.strip()
            if skill and skill.lower() not in [s.lower() for s in seen]:
                seen.append(skill)
        if len(seen) > 25:
            raise ValidationError("You can add a maximum of 25 skills.")
        return ", ".join(seen)

    # ------------------------------------------------------------------
    # clean_resume() / clean_profile_photo(): models.py లోని
    # FileExtensionValidator ఎక్స్‌టెన్షన్ ని చెక్ చేస్తుంది; ఇక్కడ
    # అదనంగా ఫైల్ సైజ్ ని కూడా చెక్ చేస్తున్నాం (Django ఫైల్ సైజ్ ని
    # ఆటోమేటిక్‌గా పరిమితం చేయదు కాబట్టి, ఇది మనమే జోడించాల్సిన
    # రక్షణ పొర).
    # ------------------------------------------------------------------
    def clean_resume(self):
        resume = self.cleaned_data.get("resume")
        if resume and hasattr(resume, "size"):
            if resume.size > MAX_RESUME_SIZE_MB * 1024 * 1024:
                raise ValidationError(f"Resume size must be under {MAX_RESUME_SIZE_MB}MB.")
        return resume

    def clean_profile_photo(self):
        photo = self.cleaned_data.get("profile_photo")
        if photo and hasattr(photo, "size"):
            if photo.size > MAX_PHOTO_SIZE_MB * 1024 * 1024:
                raise ValidationError(f"Photo size must be under {MAX_PHOTO_SIZE_MB}MB.")
        return photo

    # ------------------------------------------------------------------
    # clean(): రెండు ఫీల్డ్స్ ని కలిపి చెక్ చేయాల్సినప్పుడు (ఇక్కడ:
    # Expected CTC అనేది Current CTC కన్నా తక్కువ ఉండకూడదు అనే
    # బిజినెస్ రూల్) ఇక్కడ రాస్తాం.
    # ------------------------------------------------------------------
    def clean(self):
        cleaned_data = super().clean()
        current_ctc = cleaned_data.get("current_ctc_lpa")
        expected_ctc = cleaned_data.get("expected_ctc_lpa")
        if current_ctc is not None and expected_ctc is not None:
            if expected_ctc < current_ctc:
                self.add_error(
                    "expected_ctc_lpa",
                    "Expected CTC should not be less than Current CTC.",
                )
        return cleaned_data


class CandidateEducationForm(forms.ModelForm):
    """
    ఒక్కో విద్యార్హత ఎంట్రీ ని జోడించడానికి వాడే చిన్న ఫారమ్
    (candidate_profile_form.html లో "Academic History" విభాగంలో
    ఒక్కో కొత్త ఎంట్రీ కోసం ఇదే ఫారమ్ మళ్ళీ మళ్ళీ వాడబడుతుంది).
    ఇక్కడ కూడా "profile" ఫీల్డ్ Meta.fields లో పెట్టలేదు -- అది ఎప్పుడూ
    view.py లో request.user.candidate_profile నుండే సెట్ అవుతుంది,
    ఫారమ్ నుండి యూజర్ input గా రాదు (అలా చేస్తే ఒక candidate వేరే
    candidate ప్రొఫైల్ కి ఎడ్యుకేషన్ రికార్డ్ జోడించే IDOR దాడి
    సాధ్యమవుతుంది).
    """

    class Meta:
        model = CandidateEducation
        fields = ["level", "degree_title", "institution", "year_of_passing", "score"]
        widgets = {
            "level": forms.Select(attrs={"class": INPUT_CLASS}),
            "degree_title": forms.TextInput(attrs={
                "class": INPUT_CLASS, "placeholder": "e.g. B.Tech Computer Science",
            }),
            "institution": forms.TextInput(attrs={
                "class": INPUT_CLASS, "placeholder": "e.g. JNTU Hyderabad",
            }),
            "year_of_passing": forms.NumberInput(attrs={
                "class": INPUT_CLASS, "placeholder": "e.g. 2024",
            }),
            "score": forms.TextInput(attrs={
                "class": INPUT_CLASS, "placeholder": "e.g. 7.8 CGPA or 89%",
            }),
        }
