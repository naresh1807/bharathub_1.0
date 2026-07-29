"""
accounts/notifications.py

రిజిస్ట్రేషన్ పూర్తయిన వెంటనే, జనరేట్ అయిన BharatHub ID (Employee/
Employer/Vendor మూడిటికీ) ని యూజర్ రిజిస్టర్డ్ ఇమెయిల్ కి పంపే
షేర్డ్ హెల్పర్. ఇంతకుముందు ఈ ID కేవలం registration success message
లో మాత్రమే కనిపించేది (పేజీ మూసేస్తే శాశ్వతంగా పోయేది) -- ఇప్పుడు
ఇమెయిల్ లో కూడా ఒక permanent కాపీ ఉంటుంది.

DEBUG=True లో EMAIL_BACKEND కన్సోల్ కి మాత్రమే ప్రింట్ చేస్తుంది
(bharathub/settings.py చూడండి) -- production లో నిజంగా ఇమెయిల్
పంపాలంటే EMAIL_BACKEND ని SMTP కి మార్చాలి.
"""
from django.conf import settings
from django.core.mail import send_mail


def send_bharathub_id_email(user, id_value: str, id_label: str) -> None:
    if not user.email:
        return  # ఇమెయిల్ లేని యూజర్ కి పంపడానికి ఏమీ లేదు
    send_mail(
        subject=f"🎉 BharatHub — Here is your {id_label}",
        message=(
            f"Hello {user.first_name or ''},\n\n"
            "Your registration on BharatHub was successful!\n\n"
            f"Your {id_label}: {id_value}\n\n"
            "You can use this ID or your registered email to log in "
            "(along with your password). Please keep it safe --\n"
            "this is your account identifier.\n\n"
            "— Team BharatHub"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
