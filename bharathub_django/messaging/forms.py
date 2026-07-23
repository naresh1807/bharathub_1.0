from django import forms

from .models import Message


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={
                "id": "bh-body-input",
                "class": "wa-input__box",
                "placeholder": "Type a message...",
                "rows": 1,
                "maxlength": 4000,
            }),
        }

    def clean_body(self):
        # ఖాళీ / కేవలం స్పేస్‌లు ఉన్న సందేశాలు పంపకుండా ఆపడం.
        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("సందేశం ఖాళీగా ఉండకూడదు.")
        return body


class GroupForm(forms.Form):
    """Create మరియు Rename రెండిటికీ ఇదే ఫారమ్ వాడతాం (fields ఒకటే) --
    views.py లో CreateGroupView/RenameGroupView రెండూ దీన్నే వాడతాయి."""
    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "గ్రూప్ పేరు", "maxlength": 150}),
    )
    photo = forms.ImageField(required=False)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("గ్రూప్ పేరు తప్పనిసరి.")
        return name
