
# Celery app ని Django startup టైమ్‌లోనే లోడ్ చేయడానికి
# (shared_task డెకరేటర్ సరిగ్గా పనిచేయాలంటే ఇది అవసరం).
from .celery import app as celery_app  # noqa: E402,F401

__all__ = ("celery_app",)
