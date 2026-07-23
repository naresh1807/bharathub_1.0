"""
bharathub/celery.py

Celery app bootstrap -- ఆఫ్‌లైన్ యూజర్‌కి కొత్త మెసేజ్ వచ్చినప్పుడు
ఈమెయిల్ నోటిఫికేషన్ పంపడం లాంటి "వెంటనే జరగనవసరం లేని" పనులని,
ప్రధాన request-response cycle నుండి వేరుగా, బ్యాక్‌గ్రౌండ్ లో
రన్ చేయడానికి.

ఎలా రన్ చేయాలి (production లో, terminal ప్రత్యేకంగా):
    celery -A bharathub worker -l info

Dev లో REDIS లేకపోయినా settings.CELERY_TASK_ALWAYS_EAGER=True
default గా ఉంది కాబట్టి, ప్రత్యేక worker లేకుండానే టాస్క్‌లు
అదే ప్రాసెస్ లో సింక్రొనస్‌గా రన్ అవుతాయి (కేవలం dev సౌలభ్యం కోసం).
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bharathub.settings")

app = Celery("bharathub")
# settings.py లోని CELERY_* వేరియబుల్స్ అన్నింటినీ చదువుతుంది
# (namespace="CELERY" అంటే CELERY_BROKER_URL లాంటి prefix ఉన్నవే).
app.config_from_object("django.conf:settings", namespace="CELERY")
# ప్రతి యాప్ లోని tasks.py ని ఆటోమేటిక్‌గా కనిపెడుతుంది.
app.autodiscover_tasks()
