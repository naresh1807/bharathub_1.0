from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from .forms import VideoUploadForm
from .models import Video, VideoComment, VideoLike
from .utils import REACTION_EMOJI, display_identity, published_videos_for

# ============================================================================
# videos/views.py
# ఎందుకు ఇలా విభజించాం:
#   - UploadVideoView / DeleteVideoView -- సాధారణ HTML ఫారమ్ POST (పేజీ
#     రీలోడ్ అవుతుంది), employer_dashboard.html లోని "Post a Job" ఫారమ్
#     పద్ధతిని అనుసరిస్తాయి (POST/Redirect/Get, messages framework).
#   - toggle_like / add_comment -- ఇవి AJAX (fetch) ఎండ్‌పాయింట్లు, పేజీ
#     రీలోడ్ లేకుండా Facebook తరహాలో వెంటనే స్పందించడానికి; JSON తిరిగి
#     ఇస్తాయి, videos/static/videos/js/video_feed.js వాటిని కాల్ చేస్తుంది.
# ============================================================================


def _get_employer_profile_or_403(request):
    employer_profile = getattr(request.user, "employer_profile", None)
    if employer_profile is None:
        raise PermissionDenied("వీడియో అప్‌లోడ్/డిలీట్ చేయడం Employer ఖాతాలకి మాత్రమే.")
    return employer_profile


class UploadVideoView(View):
    """Employer డాష్‌బోర్డ్ లోని "🎥 Videos" ట్యాబ్ లో "Publish to Feed"
    బటన్ నొక్కినప్పుడు ఇక్కడికి POST అవుతుంది. GET కి అనుమతి లేదు --
    అప్‌లోడ్ ఫారమ్ ఎప్పుడూ employer_dashboard.html లోపలే కనిపిస్తుంది."""

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:employer_login")
        employer = _get_employer_profile_or_403(request)

        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.employer = employer
            video.save()
            messages.success(
                request,
                f"🎥 '{video.title}' ఫీడ్‌కి పబ్లిష్ అయింది! ఇది Home పేజీలో మరియు "
                f"Candidate డాష్‌బోర్డ్ లో కూడా వెంటనే కనిపిస్తుంది.",
            )
        else:
            error_text = " ".join(
                f"{field}: {', '.join(errs)}" for field, errs in form.errors.items()
            )
            messages.error(request, f"⚠️ వీడియో అప్‌లోడ్ విఫలమైంది — {error_text}")

        return redirect(
            reverse("employers:employer_dashboard") + "?section=videos",
        )


class DeleteVideoView(View):
    """Employer తన సొంత వీడియో మాత్రమే డిలీట్ చేయగలరు -- ఓనర్‌షిప్ చెక్
    లేకపోతే ఒక Employer వేరే కంపెనీ వీడియో ID టైప్ చేసి డిలీట్ చేసే ప్రమాదం
    ఉంటుంది (broken access control), కాబట్టి video.employer_id ని
    request.user యొక్క EmployerProfile తో సరిపోల్చాకే డిలీట్ చేస్తాం."""

    def post(self, request, pk, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:employer_login")
        employer = _get_employer_profile_or_403(request)
        video = get_object_or_404(Video, pk=pk)

        if video.employer_id != employer.id:
            raise PermissionDenied("మీరు ఈ వీడియో ని డిలీట్ చేయలేరు.")

        title = video.title
        video.delete()
        messages.success(request, f"🗑️ '{title}' తీసివేయబడింది.")
        return redirect(
            reverse("employers:employer_dashboard") + "?section=videos",
        )


@login_required
def toggle_like(request, pk):
    """AJAX: ఒకసారి నొక్కితే like అవుతుంది, అదే reaction మళ్ళీ నొక్కితే
    తీసేస్తుంది (unlike), వేరే reaction (❤️/👏/🤝/🎉) నొక్కితే మారుస్తుంది --
    సరిగ్గా Facebook రియాక్షన్ బటన్ ఎలా పనిచేస్తుందో అలాగే."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    video = get_object_or_404(Video, pk=pk, is_published=True)
    reaction = request.POST.get("reaction", VideoLike.Reaction.LIKE)
    if reaction not in VideoLike.Reaction.values:
        reaction = VideoLike.Reaction.LIKE

    existing = VideoLike.objects.filter(video=video, user=request.user).first()
    if existing is None:
        VideoLike.objects.create(video=video, user=request.user, reaction=reaction)
        liked, final_reaction = True, reaction
    elif existing.reaction == reaction:
        existing.delete()
        liked, final_reaction = False, None
    else:
        existing.reaction = reaction
        existing.save(update_fields=["reaction"])
        liked, final_reaction = True, reaction

    return JsonResponse({
        "liked": liked,
        "reaction": final_reaction,
        "reaction_emoji": REACTION_EMOJI.get(final_reaction, "👍"),
        "like_count": video.like_count,
    })


@login_required
def add_comment(request, pk):
    """AJAX: కొత్త కామెంట్ ని DB లో సేవ్ చేసి, వెంటనే ఫీడ్ లో జోడించడానికి
    అవసరమైన (పేరు/ఇనిషియల్స్/టెక్స్ట్/కొత్త కౌంట్) JSON తిరిగి ఇస్తుంది."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    video = get_object_or_404(Video, pk=pk, is_published=True)
    text = (request.POST.get("text") or "").strip()
    if not text:
        return JsonResponse({"error": "ఖాళీ కామెంట్ పోస్ట్ చేయలేరు."}, status=400)

    comment = VideoComment.objects.create(video=video, user=request.user, text=text[:500])
    name, initials = display_identity(request.user)

    return JsonResponse({
        "id": comment.id,
        "text": comment.text,
        "name": name,
        "initials": initials,
        "comment_count": video.comment_count,
    })


class VideoFeedPageView(TemplateView):
    """పూర్తి వీడియో ఫీడ్ ని ఒక స్టాండలోన్ పేజీ గా చూపించే వ్యూ -- Home
    పేజీలో "View All Videos" లాంటి లింక్ కోసం, లాగిన్ అవ్వకుండానే ఎవరైనా
    బ్రౌజ్ చేయొచ్చు (like/comment మాత్రం లాగిన్ తర్వాతే)."""

    template_name = "videos/video_feed_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["videos"] = published_videos_for(self.request.user)
        return context
