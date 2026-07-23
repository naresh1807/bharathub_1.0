"""
messaging/fields.py

EncryptedTextField — DB లో ఒక TEXT కాలమ్ లో plaintext బదులు,
encrypted ciphertext store చేసే custom Django field.

ఎలా పనిచేస్తుంది:
  - save() చేసేటప్పుడు  -> get_prep_value() ప్లెయిన్ టెక్స్ట్ ని
    Fernet (AES-128-CBC + HMAC, authenticated encryption) తో encrypt
    చేసి, ఆ ciphertext నే DB కి పంపుతుంది.
  - DB నుండి చదివేటప్పుడు -> from_db_value() ciphertext ని decrypt
    చేసి, view/template కి ఎప్పుడూ plaintext నే ఇస్తుంది.

అంటే: ఎవరైనా DB ఫైల్ ని (db.sqlite3) నేరుగా దొంగతనం చేసినా,
DB backup ఎక్కడైనా లీక్ అయినా, లేదా ఎవరైనా SQL query నేరుగా DB మీద
run చేసినా -- సందేశాల టెక్స్ట్ చదవలేరు, ఎందుకంటే అక్కడ ఉన్నది
ciphertext మాత్రమే. అప్లికేషన్ లాగిన్ అయిన సరైన యూజర్ కే plaintext
కనిపిస్తుంది (view లో authorization చెక్ తర్వాతే).

ఇది "encryption at rest" (డేటాబేస్ లో encrypted గా నిల్వ) -- ఇది
"end-to-end encryption" (E2EE, WhatsApp లో లాగా సర్వర్ కూడా చదవలేని
స్థాయి) కాదు. ఈ తేడా ఎందుకు ముఖ్యమో, ఏది ఎంచుకోవాలో చాట్ లో
వివరంగా రాశాను.
"""
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _fernet() -> Fernet:
    key = settings.MESSAGE_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode("utf-8")
    return Fernet(key)


class EncryptedTextField(models.TextField):
    """settings.MESSAGE_ENCRYPTION_KEY తో transparent గా encrypt/decrypt
    అయ్యే TextField. NOTE: encrypted విలువ మీద .filter(body__icontains=...)
    లాంటి DB-level టెక్స్ట్ సెర్చ్ పనిచేయదు (ciphertext ప్రతిసారీ
    వేరుగా ఉంటుంది) -- ఇది ఉద్దేశపూర్వకమైన trade-off, ఎందుకంటే అలాంటి
    సెర్చ్ సాధ్యం కావాలంటే content ఏదో ఒక రూపంలో ప్లెయిన్‌గా ఉండాలి."""

    def get_prep_value(self, value):
        if value is None or value == "":
            return value
        value = str(value)
        return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        try:
            return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            # తప్పు/పాత encryption key తో decrypt కావట్లేదంటే అర్థం --
            # ఖచ్చితంగా క్రాష్ కాకుండా, ఇది కనిపించేలా చూపిస్తాం.
            return "⚠️ [ఈ సందేశం డీక్రిప్ట్ చేయలేకపోయాం]"

    def to_python(self, value):
        return value
