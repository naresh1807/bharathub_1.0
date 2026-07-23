from django.contrib import admin

from .models import EmployeeProfile, EmployerProfile, LoginSecurity


# @admin.register అనేది admin.site.register(Model, ModelAdmin) కి
# షార్ట్‌కట్ డెకరేటర్ -- దీని వల్ల ఈ మోడల్స్ డేటా Django Admin
# ప్యానెల్ (/admin/) లో కనిపించి, అడ్మిన్ వాటిని వీక్షించొచ్చు/
# ఎడిట్ చేయొచ్చు.
@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    # list_display: లిస్ట్ పేజీ లో ఏ కాలమ్స్ చూపించాలో
    list_display = ("bharathub_id", "user", "mobile_number", "gender", "created_at")
    # search_fields: అడ్మిన్ పైన ఉన్న సెర్చ్ బాక్స్ ఏ ఫీల్డ్స్ లో వెతకాలో
    search_fields = ("bharathub_id", "mobile_number", "user__email", "user__first_name")
    list_filter = ("gender", "marital_status")
    # readonly_fields: bharathub_id ని ఆటోమేటిక్‌గా జనరేట్ చేస్తాం కాబట్టి
    # అడ్మిన్ కూడా దాన్ని మాన్యువల్‌గా మార్చకుండా ఉంచుతాం.
    readonly_fields = ("bharathub_id", "created_at")


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ("employer_id", "company_name", "corporate_email", "created_at")
    search_fields = ("employer_id", "company_name", "corporate_email", "pan_number", "gst_number")
    readonly_fields = ("employer_id", "created_at")


@admin.register(LoginSecurity)
class LoginSecurityAdmin(admin.ModelAdmin):
    # ఏదైనా ఒక యూజర్ నిజంగానే తనే లాక్ అయ్యానని support కి కాల్/ఈమెయిల్
    # చేస్తే, admin ఇక్కడి నుండి must_reset_password ని మాన్యువల్‌గా
    # False చేసి, failed_attempts ని 0 కి రీసెట్ చేసి, తక్షణమే అన్‌లాక్
    # చేయొచ్చు (ఫుల్ password-reset ఫ్లో లేకుండానే).
    list_display = ("user", "failed_attempts", "must_reset_password", "updated_at")
    list_filter = ("must_reset_password",)
    search_fields = ("user__username", "user__email")
