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
        subject=f"🎉 BharatHub — మీ {id_label} ఇదిగో",
        message=(
            f"నమస్కారం {user.first_name or ''},\n\n"
            "BharatHub లో మీ రిజిస్ట్రేషన్ విజయవంతమైంది!\n\n"
            f"మీ {id_label}: {id_value}\n\n"
            "లాగిన్ చేయడానికి ఈ ID ని లేదా మీ రిజిస్టర్డ్ ఇమెయిల్ ని "
            "వాడొచ్చు (పాస్‌వర్డ్ తో పాటు). దీన్ని భద్రంగా దాచుకోండి --\n"
            "ఇది మీ ఖాతా గుర్తింపు.\n\n"
            "— Team BharatHub"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
