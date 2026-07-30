import random
import re

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models as db_models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from messaging.permissions import _role_of
from .forms import ComposeForm, MailAddressSetupForm
from .models import (
    ATTACHMENT_MAX_MB, Email, EmailAttachment, MailAddress, MAIL_DOMAIN,
    attachment_extension_validator,
)

# ============================================================================
# webmail/views.py
#
# Gmail తరహా మెయిల్ యాప్ -- Candidate/Employer/Vendor మూడు
# డాష్‌బోర్డుల్లోనూ ఇదే బ్యాకెండ్ (messaging యాప్ architecture నే
# ఇక్కడా వాడాం: ఒక్కో రోల్ కి ఒక్కో URL/View/Template, కానీ మూడూ ఒకే
# _RoleMailMixin నుండి context తీసుకుంటాయి). ఇది నిజమైన SMTP మెయిల్
# కాదు -- BharatHub లో రిజిస్టర్ అయిన వాళ్ళ మధ్యే పనిచేసే internal
# మెయిల్ సిస్టమ్ (@bharathub.com అడ్రస్‌లతో).
# ============================================================================


def _redirect_name_for(user) -> str:
    role, _ = _role_of(user)
    return {
        "candidate": "webmail:candidate_mail",
        "employer": "webmail:employer_mail",
        "vendor": "webmail:vendor_mail",
    }.get(role, "home:bharathub_home")


def _display_name_for(user) -> str:
    role, profile = _role_of(user)
    if role == "employer":
        return profile.company_name
    if role == "vendor":
        return profile.shop_name
    return user.first_name or user.username


def unread_mail_count_for(user) -> int:
    """topnav '📧 Mail' ట్యాబ్ పైన badge కోసం -- MailAddress లేని
    యూజర్ కి (ఇంకా Mail సెటప్ చేసుకోలేదు) ఎప్పుడూ 0."""
    mail_address = getattr(user, "mail_address", None)
    if mail_address is None:
        return 0
    return Email.objects.filter(
        recipient=mail_address, is_draft=False,
        recipient_trashed=False, is_read=False,
    ).count()


def _suggest_local_parts(user) -> list:
    """Gmail సైన్అప్ లో లాగే 3 సజెషన్స్ -- పేరు ఆధారంగా, ఇప్పటికే
    వాడుకలో లేని వాటినే సజెస్ట్ చేస్తాం."""
    base = re.sub(r"[^a-z0-9]", "", _display_name_for(user).lower()) or "user"
    base = base[:20] or "user"

    candidates_list = [base, f"{base}{user.id}"]
    while len(candidates_list) < 6:  # extra అభ్యర్థులు -- కొన్ని collide అయితే
        candidates_list.append(f"{base}{random.randint(100, 9999)}")

    suggestions, seen = [], set()
    existing = set(MailAddress.objects.values_list("local_part", flat=True))
    for cand in candidates_list:
        cand = cand[:30]
        if cand not in seen and cand not in existing:
            suggestions.append(cand)
            seen.add(cand)
        if len(suggestions) == 3:
            break
    return suggestions


class _RoleMailMixin(LoginRequiredMixin):
    redirect_url_name = ""  # subclasses override

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        mail_address = getattr(user, "mail_address", None)
        context["mail_address"] = mail_address
        context["mail_domain"] = MAIL_DOMAIN

        # ?compose_to=<mail_address>&subject=<...>&body=<...> ఉంటే,
        # పేజీ లోడ్ అయిన వెంటనే compose ప్యానెల్ ఆ recipient/subject/
        # body తో ముందే నింపి తెరవాలి (jobs/_applications_body.html
        # లోని "✉️ Mail" బటన్, meetings/meeting_list.html లోని
        # "✉️ Email It" లింక్ ఇలా లింక్ చేస్తాయి -- ఇక్కడ నుండి వచ్చిన
        # దాన్నే వాడతాం).
        context["compose_to"] = self.request.GET.get("compose_to", "")
        context["compose_subject"] = self.request.GET.get("subject", "")
        context["compose_body"] = self.request.GET.get("body", "")

        if mail_address is None:
            # ఇది మొదటిసారి -- ఇన్‌బాక్స్ బదులు ఆన్‌బోర్డింగ్
            # (సజెషన్స్ + కస్టమ్ ఐడి) చూపిస్తాం.
            context["needs_setup"] = True
            context["suggestions"] = _suggest_local_parts(user)
            return context

        folder = self.request.GET.get("folder", "inbox")
        if folder not in ("inbox", "starred", "sent", "drafts", "trash"):
            folder = "inbox"
        context["folder"] = folder

        base_qs = Email.objects.select_related("sender__user", "recipient__user")
        if folder == "inbox":
            emails = base_qs.filter(recipient=mail_address, is_draft=False, recipient_trashed=False)
        elif folder == "starred":
            emails = base_qs.filter(recipient=mail_address, is_starred=True, recipient_trashed=False, is_draft=False)
        elif folder == "sent":
            emails = base_qs.filter(sender=mail_address, is_draft=False, sender_trashed=False)
        elif folder == "drafts":
            emails = base_qs.filter(sender=mail_address, is_draft=True)
        else:  # trash
            emails = base_qs.filter(
                db_models.Q(recipient=mail_address, recipient_trashed=True)
                | db_models.Q(sender=mail_address, sender_trashed=True, is_draft=False),
            )

        emails = list(emails)
        context["emails"] = emails
        context["unread_count"] = unread_mail_count_for(user)

        open_id = self.request.GET.get("open")
        open_email = None
        if open_id:
            open_email = next((e for e in emails if str(e.pk) == str(open_id)), None)
            if open_email is None:
                # జాబితాలో లేకున్నా (వేరే ఫోల్డర్ నుండి లింక్ వచ్చుంటే),
                # ఇద్దరిలో ఒకరు ఇతనే అయితే మాత్రమే చూపిస్తాం (IDOR గార్డ్).
                candidate = base_qs.filter(pk=open_id).first()
                if candidate and mail_address.pk in (candidate.sender_id, candidate.recipient_id):
                    open_email = candidate
            if open_email is not None and open_email.recipient_id == mail_address.pk and not open_email.is_read:
                open_email.is_read = True
                open_email.save(update_fields=["is_read"])
        context["open_email"] = open_email

        return context


def _validate_and_save_attachments(email, uploaded_files):
    """request.FILES.getlist('attachments') లోని ప్రతి ఫైల్ ని
    వాలిడేట్ చేసి, పాస్ అయినవాటిని EmailAttachment గా సేవ్ చేస్తుంది.
    ఏదైనా ఫైల్ ఫెయిల్ అయితే, దాన్ని స్కిప్ చేసి ఒక ఎర్రర్ స్ట్రింగ్
    రిటర్న్ చేస్తుంది (మిగతా చెల్లుబాటు అయ్యే ఫైళ్ళని ఆపదు) --
    రిటర్న్ విలువ: ఎర్రర్ మెసేజ్‌ల లిస్ట్ (ఖాళీ అయితే అన్నీ సరిగ్గా
    సేవ్ అయ్యాయని అర్థం).

    SECURITY: messaging/views.py:MessageAttachmentUploadView లో వాడిన
    అదే మూడు పొరల రక్షణ ఇక్కడా -- (1) సైజ్ పరిమితి, (2) extension
    allow-list, (3) "image" అని క్లెయిమ్ చేసిన ప్రతి ఫైల్ నిజంగా
    Pillow తో డీకోడ్ అవుతుందా అని ధృవీకరణ (కేవలం ఫైల్ పేరు మార్చిన
    హానికరమైన ఫైల్ ని ఆపడానికి).
    """
    errors = []
    for uploaded in uploaded_files:
        if uploaded.size > ATTACHMENT_MAX_MB * 1024 * 1024:
            errors.append(f"'{uploaded.name}' చాలా పెద్దది (గరిష్టం {ATTACHMENT_MAX_MB}MB).")
            continue
        try:
            attachment_extension_validator(uploaded)
        except ValidationError:
            errors.append(f"'{uploaded.name}' — ఈ ఫైల్ టైప్ కి అనుమతి లేదు.")
            continue

        is_image = uploaded.name.lower().rsplit(".", 1)[-1] in {"jpg", "jpeg", "png", "gif", "webp"}
        if is_image:
            from PIL import Image, UnidentifiedImageError
            try:
                uploaded.seek(0)
                Image.open(uploaded).verify()
                uploaded.seek(0)
            except (UnidentifiedImageError, OSError):
                errors.append(f"'{uploaded.name}' — చెల్లని లేదా పాడైన ఇమేజ్ ఫైల్.")
                continue

        EmailAttachment.objects.create(
            email=email, file=uploaded,
            original_filename=uploaded.name, size_bytes=uploaded.size,
        )
    return errors


class CandidateMailView(_RoleMailMixin, TemplateView):
    template_name = "webmail/candidate_mail.html"
    redirect_url_name = "webmail:candidate_mail"


class EmployerMailView(_RoleMailMixin, TemplateView):
    template_name = "webmail/employer_mail.html"
    redirect_url_name = "webmail:employer_mail"


class VendorMailView(_RoleMailMixin, TemplateView):
    template_name = "webmail/vendor_mail.html"
    redirect_url_name = "webmail:vendor_mail"


class MailSetupView(LoginRequiredMixin, View):
    """ఆన్‌బోర్డింగ్ ఫారమ్ సబ్మిట్ -- MailAddress క్రియేట్ చేసి,
    సక్సెస్ అయితే నేరుగా Inbox కి తీసుకెళ్తుంది (ప్రశ్నలో అడిగిన
    'సెలెక్ట్ చేసుకుని తర్వాత డైరెక్ట్ గా ఇన్‌బాక్స్ పేజీకి వెళ్ళిపోవాలి'
    అనేది ఇక్కడే)."""

    def post(self, request, *args, **kwargs):
        redirect_name = _redirect_name_for(request.user)
        if hasattr(request.user, "mail_address"):
            return redirect(redirect_name)

        form = MailAddressSetupForm(request.POST)
        if form.is_valid():
            MailAddress.objects.create(user=request.user, local_part=form.cleaned_data["local_part"])
            messages.success(
                request,
                f"🎉 మీ BharatHub Mail ID రెడీ: {form.cleaned_data['local_part']}@{MAIL_DOMAIN}",
            )
        else:
            for error in form.errors.get("__all__", []):
                messages.error(request, f"⚠️ {error}")
        return redirect(redirect_name)


class ComposeSendView(LoginRequiredMixin, View):
    """Send / Save Draft రెండూ ఇక్కడే -- 'action' POST ఫీల్డ్ ఏది
    అని బట్టి. draft_id ఉంటే ఇప్పటికే ఉన్న డ్రాఫ్ట్ నే అప్‌డేట్
    చేస్తుంది (కొత్తది క్రియేట్ చేయదు)."""

    def post(self, request, *args, **kwargs):
        redirect_name = _redirect_name_for(request.user)
        mail_address = getattr(request.user, "mail_address", None)
        if mail_address is None:
            return redirect(redirect_name)

        form = ComposeForm(request.POST)
        if not form.is_valid():
            messages.error(request, "⚠️ మెయిల్ పంపడంలో ఎర్రర్ వచ్చింది, మళ్ళీ ప్రయత్నించండి.")
            return redirect(redirect_name)

        draft_id = request.POST.get("draft_id")
        if draft_id:
            email = get_object_or_404(Email, pk=draft_id, sender=mail_address, is_draft=True)
        else:
            email = Email(sender=mail_address, is_draft=True)

        email.to_raw = form.cleaned_data["to"]
        email.subject = form.cleaned_data["subject"]
        email.body = form.cleaned_data["body"]

        action = request.POST.get("action", "send")
        if action == "draft":
            email.recipient = form.resolve_recipient()  # ఇంకా తేలకపోతే None -- పర్వాలేదు, draft కే
            email.save()
            attach_errors = _validate_and_save_attachments(email, request.FILES.getlist("attachments"))
            for err in attach_errors:
                messages.warning(request, f"📎 {err}")
            messages.success(request, "📝 Draft saved.")
            return redirect(f"{reverse(redirect_name)}?folder=drafts")

        recipient = form.resolve_recipient()
        if recipient is None:
            messages.error(
                request,
                f"⚠️ '{form.cleaned_data['to']}' అనేది చెల్లుబాటు అయ్యే BharatHub Mail ID కాదు "
                f"(@{MAIL_DOMAIN} తో రిజిస్టర్ అయిన వాళ్ళకే పంపగలరు). Draft గా సేవ్ చేశాం.",
            )
            email.save()
            _validate_and_save_attachments(email, request.FILES.getlist("attachments"))
            return redirect(f"{reverse(redirect_name)}?folder=drafts")
        if recipient.pk == mail_address.pk:
            messages.error(request, "⚠️ మీరు మీకే మెయిల్ పంపలేరు.")
            email.save()
            _validate_and_save_attachments(email, request.FILES.getlist("attachments"))
            return redirect(f"{reverse(redirect_name)}?folder=drafts")

        email.recipient = recipient
        email.is_draft = False
        email.sent_at = timezone.now()
        email.save()
        attach_errors = _validate_and_save_attachments(email, request.FILES.getlist("attachments"))
        for err in attach_errors:
            messages.warning(request, f"📎 {err}")
        messages.success(request, f"✅ Mail sent to {recipient.address}")
        return redirect(f"{reverse(redirect_name)}?folder=sent")


class _EmailActionMixin(LoginRequiredMixin):
    """Star/Trash/Restore/Delete-forever -- నాలుగింటికీ ఉమ్మడి IDOR
    గార్డ్: ఈ మెయిల్ కి sender లేదా recipient అయిన వాళ్ళే యాక్షన్
    తీసుకోగలరు."""

    def get_email_and_side(self, request, pk):
        mail_address = getattr(request.user, "mail_address", None)
        email = get_object_or_404(Email, pk=pk)
        if mail_address is None or mail_address.pk not in (email.sender_id, email.recipient_id):
            raise PermissionDenied("This mail does not belong to you.")
        side = "recipient" if email.recipient_id == mail_address.pk else "sender"
        return email, side

    def back_url(self, request, folder=None, keep_open=False):
        name = reverse(_redirect_name_for(request.user))
        folder = folder or request.POST.get("folder", "inbox")
        url = f"{name}?folder={folder}"
        if keep_open:
            open_id = request.POST.get("open")
            if open_id:
                url += f"&open={open_id}"
        return url


class ToggleStarView(_EmailActionMixin, View):
    def post(self, request, pk, *args, **kwargs):
        email, side = self.get_email_and_side(request, pk)
        if side == "recipient":  # sender-side కి star అనేది అర్థరహితం (Gmail లో కూడా Sent కి star ఉండదు)
            email.is_starred = not email.is_starred
            email.save(update_fields=["is_starred"])
        return redirect(self.back_url(request, keep_open=True))


class TrashEmailView(_EmailActionMixin, View):
    def post(self, request, pk, *args, **kwargs):
        email, side = self.get_email_and_side(request, pk)
        if side == "recipient":
            email.recipient_trashed = True
            email.save(update_fields=["recipient_trashed"])
        else:
            email.sender_trashed = True
            email.save(update_fields=["sender_trashed"])
        messages.success(request, "🗑️ Moved to Trash.")
        return redirect(self.back_url(request))


class RestoreEmailView(_EmailActionMixin, View):
    def post(self, request, pk, *args, **kwargs):
        email, side = self.get_email_and_side(request, pk)
        if side == "recipient":
            email.recipient_trashed = False
            email.save(update_fields=["recipient_trashed"])
        else:
            email.sender_trashed = False
            email.save(update_fields=["sender_trashed"])
        messages.success(request, "↩️ Restored.")
        return redirect(self.back_url(request, folder="trash"))


class DeleteForeverView(_EmailActionMixin, View):
    def post(self, request, pk, *args, **kwargs):
        email, _side = self.get_email_and_side(request, pk)
        email.delete()
        messages.success(request, "🗑️ Permanently deleted.")
        return redirect(self.back_url(request, folder="trash"))


class AttachmentDeleteView(LoginRequiredMixin, View):
    """ఇప్పటికే ఒక draft కి attach అయిన ఫైల్ ని తీసేయడానికి (కొత్తగా
    ఇంకా అప్‌లోడ్ చేయని ఫైళ్ళని client-side JS లోనే తీసేయొచ్చు --
    ఇది ఇప్పటికే DB లో సేవ్ అయిన వాటికే అవసరం).

    SECURITY:
      - ఈ attachment ఉన్న Email యొక్క sender ఈ యూజరే అయ్యుండాలి
        (IDOR గార్డ్ -- లేకపోతే ఒకరు వేరొకరి draft లోని ఫైల్ ని
        తీసేయగలరు).
      - ఆ Email ఇంకా draft (is_draft=True) గానే ఉండాలి -- పంపేసిన
        లేదా అందుకున్న మెయిల్ నుండి ఫైళ్ళని ఎప్పుడూ తీసేయకూడదు
        (అది రెండో వ్యక్తి చూసే రికార్డ్ ని మార్చేస్తుంది).
    """

    def post(self, request, pk, *args, **kwargs):
        mail_address = getattr(request.user, "mail_address", None)
        attachment = get_object_or_404(
            EmailAttachment, pk=pk, email__sender=mail_address, email__is_draft=True,
        )
        attachment.delete()
        return JsonResponse({"status": "deleted"})
