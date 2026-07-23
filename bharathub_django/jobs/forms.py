from django import forms

from .models import JobApplication


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
                "placeholder": "ఈ ఉద్యోగానికి మీరు ఎందుకు సరిపోతారో క్లుప్తంగా రాయండి (ఐచ్ఛికం)...",
            }),
        }
        labels = {"cover_note": "Cover Note (optional)"}
