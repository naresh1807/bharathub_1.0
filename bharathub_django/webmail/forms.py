from django import forms
from django.core.exceptions import ValidationError

from .models import Email, MailAddress, MAIL_DOMAIN


class MailAddressSetupForm(forms.Form):
    """మొదటిసారి Mail యాప్ తెరిచినప్పుడు -- సజెస్ట్ చేసిన 3
    అడ్రస్‌లలో ఒకటి ఎంచుకోవచ్చు, లేదా 'custom_local_part' లో సొంతంగా
    టైప్ చేయొచ్చు. రెండూ ఖాళీగా వస్తే ఏం చేయాలో తెలియదు కాబట్టి
    clean() లో చెక్ చేస్తాం."""

    chosen_suggestion = forms.CharField(required=False)
    custom_local_part = forms.CharField(required=False, max_length=30)

    def clean(self):
        cleaned = super().clean()
        local_part = (cleaned.get("custom_local_part") or cleaned.get("chosen_suggestion") or "").strip().lower()

        if not local_part:
            raise ValidationError("దయచేసి ఒక Mail ID ఎంచుకోండి లేదా టైప్ చేయండి.")

        temp = MailAddress(local_part=local_part)
        try:
            temp.full_clean(exclude=["user"])
        except ValidationError as e:
            raise ValidationError(e.messages[0])

        if MailAddress.objects.filter(local_part=local_part).exists():
            raise ValidationError(f"'{local_part}@{MAIL_DOMAIN}' ఇప్పటికే వాడుకలో ఉంది -- వేరే ఐడి ప్రయత్నించండి.")

        cleaned["local_part"] = local_part
        return cleaned


class ComposeForm(forms.Form):
    """కొత్త మెయిల్ / రిప్లై / డ్రాఫ్ట్ -- మూడూ ఒకే ఫారమ్. 'to' ఇక్కడ
    పూర్తి అడ్రస్ (yourname@bharathub.com) లేదా కేవలం local_part అయినా
    ఓకే -- clean_to() రెండిటినీ యాక్సెప్ట్ చేస్తుంది."""

    to = forms.CharField(max_length=150, required=False)
    subject = forms.CharField(max_length=255, required=False)
    body = forms.CharField(widget=forms.Textarea, required=False)

    def clean_to(self):
        raw = (self.cleaned_data.get("to") or "").strip().lower()
        return raw

    def resolve_recipient(self):
        """draft save చేసేటప్పుడు 'to' ఖాళీగా ఉండొచ్చు (recipient=None) --
        కానీ 'send' చేసేటప్పుడు మాత్రం ఇది ఒక చెల్లుబాటు అయ్యే
        రిజిస్టర్డ్ bharathub.com అడ్రస్ నే అవ్వాలి, లేకపోతే None
        రిటర్న్ చేస్తుంది (view దాన్ని ఎర్రర్ గా చూపిస్తుంది)."""
        raw = self.cleaned_data.get("to") or ""
        local_part = raw.split("@")[0].strip().lower()
        if not local_part:
            return None
        return MailAddress.objects.filter(local_part=local_part).select_related("user").first()
