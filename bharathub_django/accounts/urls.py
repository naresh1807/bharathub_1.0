from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # Employee
    path("employee_registration.html", views.EmployeeRegistrationView.as_view(), name="employee_registration"),
    path("employee_login.html", views.EmployeeLoginView.as_view(), name="employee_login"),

    # Employer
    path("employer_registration.html", views.EmployerRegistrationView.as_view(), name="employer_registration"),
    path("employer_login.html", views.EmployerLoginView.as_view(), name="employer_login"),

    # Logout -- shared by all three dashboards (employer/candidate/vendor);
    # POST-only, see LogoutView docstring in views.py.
    path("logout/", views.LogoutView.as_view(), name="logout"),

    # Forgot-Password JSON API -- shared by Employee/Employer/Vendor login
    # pages' "Forgot Password?" panel (role sent in the request body).
    path("password/forgot/verify/", views.ForgotPasswordVerifyView.as_view(), name="password_forgot_verify"),
    path("password/forgot/otp/", views.ForgotPasswordOtpVerifyView.as_view(), name="password_forgot_otp"),
    path("password/forgot/set/", views.ForgotPasswordSetView.as_view(), name="password_forgot_set"),

    # రిజిస్ట్రేషన్ తర్వాత లాగిన్ అయిన Employer, మిగిలిన కంపెనీ
    # వివరాలు (PAN/GST/CIN/HQ) పూర్తి చేసుకునే పేజీ.
    path("employer/complete-profile/", views.EmployerProfileCompletionView.as_view(), name="employer_complete_profile"),
]
