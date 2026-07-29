from django import forms

from .models import Video

# ============================================================================
# videos/forms.py
# Employer dashboard లోని "🎥 Upload Video" ఫారమ్ (Title / Category /
# Description / File) కి సరిపోలే ModelForm. `employer` ఫీల్డ్ ఉద్దేశపూర్వకంగా
# ఇక్కడ చేర్చలేదు -- Job పోస్ట్ ఫారమ్ లో లాగే, ఎవరు అప్‌లోడ్ చేస్తున్నారో
# ఎప్పుడూ views.py లోని request.user నుండే నిర్ణయిస్తాం (ఫారమ్ డేటా నుండి కాదు).
# ============================================================================


class VideoUploadForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ["title", "category", "caption", "video_file"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Office Culture Tour 2026",
            }),
            "category": forms.Select(attrs={"class": "form-select"}),
            "caption": forms.Textarea(attrs={
                "class": "form-textarea", "rows": 3,
                "placeholder": "Brief description about the video...",
            }),
            "video_file": forms.ClearableFileInput(attrs={
                "accept": "video/mp4,video/quicktime,video/x-msvideo,video/webm",
                "id": "vfVideoInput",
                "style": "display:none;",
                "onchange": "vfHandleFileSelect(this)",
            }),
        }

    def clean_video_file(self):
        video_file = self.cleaned_data["video_file"]
        # 500MB పరిమితి -- పాత mock dropzone లో చూపించిన "Max 500MB" హింట్
        # ఇప్పుడు నిజంగా ఇక్కడ అమలు (enforce) అవుతుంది.
        max_bytes = 500 * 1024 * 1024
        if video_file.size > max_bytes:
            raise forms.ValidationError("Video size must be under 500MB.")
        return video_file
