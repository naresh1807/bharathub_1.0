"""
jobs/notifications.py

Offer Letter లైఫ్‌సైకిల్ కి సంబంధించిన రెండు ఇమెయిల్ నోటిఫికేషన్లు --
accounts/notifications.py లోని send_bharathub_id_email అదే
పద్ధతిని (plain send_mail, fail_silently=True) ఇక్కడ కూడా వాడాం:

  1. Employer 'Mark as Hired' నొక్కిన వెంటనే → candidate కి "మీ ఆఫర్
     లెటర్ రెడీ" ఇమెయిల్ (jobs/views.py: MarkAsHiredView).
  2. Candidate ఆఫర్ Accept చేసిన వెంటనే → employer కి "candidate offer
     accept చేశారు" ఇమెయిల్ (jobs/views.py: OfferLetterAcceptView).

DEBUG=True లో EMAIL_BACKEND కన్సోల్ కి మాత్రమే ప్రింట్ చేస్తుంది
(bharathub/settings.py చూడండి).
"""
from django.conf import settings
from django.core.mail import send_mail


def send_offer_letter_ready_email(employment) -> None:
    candidate_user = employment.candidate.user
    if not candidate_user.email:
        return
    send_mail(
        subject=f"🎉 Your Offer Letter from {employment.employer.company_name} is ready",
        message=(
            f"Hello {candidate_user.first_name or ''},\n\n"
            f"{employment.employer.company_name} has marked you as Hired for the role of "
            f"{employment.designation}, effective {employment.joining_date:%B %d, %Y}.\n\n"
            "Your offer letter is ready to view -- log in to BharatHub and open "
            "Downloads on your dashboard to review the joining details and Accept it.\n\n"
            "— Team BharatHub"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[candidate_user.email],
        fail_silently=True,
    )


def send_offer_accepted_email(employment) -> None:
    employer_user = employment.employer.user
    if not employer_user.email:
        return
    candidate_name = employment.candidate.user.get_full_name() or employment.candidate.user.username
    send_mail(
        subject=f"✅ {candidate_name} accepted your offer letter",
        message=(
            f"Hello,\n\n"
            f"{candidate_name} has accepted the offer letter for {employment.designation}, "
            f"joining on {employment.joining_date:%B %d, %Y}.\n\n"
            "You can view them anytime under My Hires on your BharatHub dashboard.\n\n"
            "— Team BharatHub"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[employer_user.email],
        fail_silently=True,
    )
