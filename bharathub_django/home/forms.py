from django import forms
from .models import ContactMessage


# ----------------------------------------------------------------------
# ContactForm
# ఎందుకు: ఇది ContactMessage మోడల్ ఆధారంగా ఆటోమేటిక్‌గా ఫారమ్ ఫీల్డ్స్
#         తయారు చేసే "ModelForm". దీని వల్ల model లో రాసిన validation
#         (max_length, EmailField ఫార్మాట్ చెక్, choices మొదలైనవి) అన్నీ
#         ఫారమ్ లెవెల్ లో కూడా ఆటోమేటిక్‌గా వర్తిస్తాయి — మనం మళ్ళీ
#         డూప్లికేట్ కోడ్ రాయాల్సిన అవసరం లేదు.
#         ఇది సర్వర్-సైడ్ వాలిడేషన్ — యూజర్ బ్రౌజర్ JavaScript ని ఆఫ్
#         చేసినా, లేదా postman/curl తో నేరుగా డేటా పంపినా, ఈ ఫారమ్
#         తప్పుడు డేటాను ఎప్పుడూ DB లోకి పోనివ్వదు (ఇదే అసలైన సెక్యూరిటీ,
#         క్లయింట్ సైడ్ JS వాలిడేషన్ కేవలం UX కోసం మాత్రమే, దానిని ఎవరైనా
#         బైపాస్ చేయగలరు).
# ----------------------------------------------------------------------
class ContactForm(forms.ModelForm):

    class Meta:
        model = ContactMessage
        # ఏ ఫీల్డ్స్ ఫారమ్ లో కనిపించాలో ఇక్కడ తెలియజేస్తున్నాం.
        # created_at, is_resolved లాంటివి యూజర్ నింపకూడదు కాబట్టి
        # ఇక్కడ చేర్చలేదు — అవి మోడల్/అడ్మిన్ లోపలే ఆటోమేటిక్‌గా సెట్ అవుతాయి.
        fields = ["name", "email", "sender_type", "subject", "message"]

        # widgets: ఇక్కడ మనం అసలు ఉన్న HTML CSS క్లాస్ నేమ్స్
        # (form-input, form-select, form-textarea) ని అలాగే అట్టిపెడుతున్నాం,
        # తద్వారా ఇప్పటికే ఉన్న contact.css స్టైలింగ్ ఏమీ మారదు —
        # కేవలం "ప్లెయిన్ HTML input" బదులు "Django బైండ్ చేసిన input"
        # అవుతుంది, కంటికి ఏమీ తేడా కనిపించదు.
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-input", "placeholder": "Full name",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-input", "placeholder": "your@email.com",
            }),
            "sender_type": forms.Select(attrs={"class": "form-select"}),
            "subject": forms.Select(attrs={"class": "form-select"}),
            "message": forms.Textarea(attrs={
                "class": "form-textarea",
                "placeholder": "Describe your query in detail...",
                "rows": 5,
            }),
        }
        labels = {
            "sender_type": "I am a",
        }

    # clean_message: ఒక ఫీల్డ్ కి కస్టమ్ వాలిడేషన్ రాయాలంటే
    # "clean_<fieldname>" అనే పేరుతో మెథడ్ రాస్తే Django ఆటోమేటిక్‌గా
    # దాన్ని కాల్ చేస్తుంది. ఇక్కడ మెసేజ్ కనీసం 10 అక్షరాలు ఉండాలి అని
    # చెక్ చేస్తున్నాం — స్పామ్ / ఖాళీ మెసేజ్‌లు ఆపడానికి.
    def clean_message(self):
        message = self.cleaned_data.get("message", "").strip()
        if len(message) < 10:
            raise forms.ValidationError(
                "Please write your message in detail, with at least 10 characters."
            )
        return message
