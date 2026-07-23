# BharatHub — Django Project

This is the original 15 static HTML pages converted into a proper Django app.
**All CSS and JavaScript have been extracted out of the HTML** into separate
files, exactly as Django convention expects.

## What changed

| Before | After |
|---|---|
| `<style>...</style>` inline in every HTML file | `core/static/core/css/<page>.css` |
| `<script>...</script>` inline in every HTML file | `core/static/core/js/<page>.js` |
| Plain `.html` files | Django templates in `core/templates/core/`, using `{% load static %}` and `{% static %}` tags |

**Nothing else was changed.** Every internal link
(`<a href="employee_login.html">`, `window.location.href='candidate_dashboard.html'`, etc.)
was left exactly as-is in the templates/JS — `core/urls.py` maps routes using
those **exact same filenames**, so every button/link on every page keeps
working with zero risk of broken navigation.

## Project structure

```
bharathub_django/
├── manage.py
├── requirements.txt
├── bharathub/                  ← Django project config
│   ├── settings.py
│   ├── urls.py                 ← includes core.urls
│   ├── wsgi.py
│   └── asgi.py
└── core/                       ← the BharatHub app
    ├── views.py                ← one TemplateView per page
    ├── urls.py                 ← routes named exactly like the old .html files
    ├── models.py                (empty — ready for your ORM models)
    ├── admin.py
    ├── templates/core/
    │   ├── bharathub_home.html
    │   ├── employee_registration.html
    │   ├── employee_login.html
    │   ├── candidate_dashboard.html
    │   ├── employer_registration.html
    │   ├── employer_login.html
    │   ├── employer_dashboard.html
    │   ├── vendor_registration.html
    │   ├── vendor_login.html
    │   ├── vendor_dashboard.html
    │   ├── about.html
    │   ├── privacy.html
    │   ├── terms.html
    │   ├── contact.html
    │   └── help.html
    └── static/core/
        ├── css/  (15 files — one per page)
        └── js/   (12 files — pages with no <script> block, e.g. about.html, don't get a .js file)
```

## Running it locally

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Then open `http://127.0.0.1:8000/` — it loads `bharathub_home.html`
(the home page), and every other page is reachable at the same path it
always was, e.g. `http://127.0.0.1:8000/employee_login.html`.

## Every template follows this pattern

```django
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
  ...
  <link rel="stylesheet" href="{% static 'core/css/employee_login.css' %}">
</head>
<body>
  ...page content, unchanged...
  <script src="{% static 'core/js/employee_login.js' %}"></script>
</body>
</html>
```

## Next steps (optional, when you're ready for a real backend)

- `core/models.py` is empty and ready for Employee / Employer / Vendor models
- `settings.py` has a commented-out MySQL `DATABASES` config ready to uncomment
- Forms currently submit via JS `alert()`/redirects only — wire them to real
  Django views + forms.py when you add the backend logic (OTP email sending,
  MySQL persistence, session-based auth, etc.)
