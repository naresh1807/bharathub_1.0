from .models import Video, VideoComment, VideoLike

# ============================================================================
# videos/utils.py
# ఈ ఫీడ్ మూడు వేర్వేరు పేజీల్లో (Home, Employer Dashboard, Candidate
# Dashboard) ఒకేలా కనిపించాలి కాబట్టి, ఆ మూడు views.py ఫైళ్ళలో ఒకే క్వెరీ
# లాజిక్ కాపీ-పేస్ట్ చేయకుండా ఇక్కడ ఒక్కసారే రాశాం (DRY).
# ============================================================================

REACTION_EMOJI = dict(VideoLike.Reaction.choices)

_LOGO_COLORS = [
    "#0050b3", "#4a148c", "#1b5e20", "#b71c1c", "#e65100",
    "#006064", "#37474f", "#880e4f", "#1a237e", "#004d40",
]


def display_identity(user):
    """ఒక User కి చూపించాల్సిన పేరు + అవతార్ ఇనిషియల్స్ ని తిరిగి ఇస్తుంది.
    Employer అయితే కంపెనీ పేరు, Candidate అయితే వాళ్ళ పూర్తి పేరు వాడతాం --
    కామెంట్ల కింద ఎవరు రాశారో స్పష్టంగా తెలియడానికి."""
    employer_profile = getattr(user, "employer_profile", None)
    if employer_profile is not None:
        name = employer_profile.company_name
        return name, name[:2].upper()

    full_name = user.get_full_name() or user.username
    return full_name, full_name[:2].upper()


def logo_color_for(employer_id):
    """ఒక్కో కంపెనీ కార్డ్ లోగో కి ఒక స్థిర రంగు -- home page లోని
    employer_chips లో వాడిన అదే cyclic-palette టెక్నిక్ (DB లో రంగు ఫీల్డ్
    లేదు కాబట్టి, ఇది కేవలం విజువల్ మాత్రమే)."""
    return _LOGO_COLORS[employer_id % len(_LOGO_COLORS)]


def published_videos_for(request_user, employer=None, limit=None):
    """పబ్లిష్ అయిన వీడియోల జాబితా -- ప్రతి వీడియో మీద ప్రస్తుత యూజర్ యొక్క
    reaction (ఉంటే), లోగో రంగు, మరియు కామెంట్ల మీద commenter పేరు/ఇనిషియల్స్
    ని extra (non-DB) attributes గా జోడిస్తుంది -- home/views.py లోని
    `job.is_new` ట్రిక్ లాగే, టెంప్లేట్ లో నేరుగా వాడుకోవడానికి వీలుగా."""
    queryset = (
        Video.objects.filter(is_published=True)
        .select_related("employer")
        .prefetch_related("comments__user__employer_profile")
        .order_by("-created_at")
    )
    if employer is not None:
        queryset = queryset.filter(employer=employer)
    if limit is not None:
        queryset = queryset[:limit]

    videos = list(queryset)

    liked_map = {}
    if getattr(request_user, "is_authenticated", False):
        liked_map = {
            like.video_id: like.reaction
            for like in VideoLike.objects.filter(
                video__in=videos, user=request_user,
            )
        }

    for video in videos:
        video.employer_color = logo_color_for(video.employer_id)
        reaction_code = liked_map.get(video.id)
        video.user_reaction = reaction_code
        video.user_reaction_emoji = REACTION_EMOJI.get(reaction_code, "👍")
        for comment in video.comments.all():
            comment.display_name, comment.display_initials = display_identity(comment.user)

    return videos
