"""
messaging/permissions.py

"Secure" messaging అంటే encryption ఒక్కటే సరిపోదు -- ఎవరు ఎవరితో
చాట్ మొదలుపెట్టగలరు అనేది కూడా నియంత్రించాలి. లేకపోతే ఏ యూజర్
అయినా (login చేసిన ఏ Employee/Employer/Vendor అయినా) సైట్ లో ఉన్న
మరే ఇతర యూజర్ కైనా నేరుగా మెసేజ్ పంపి spam/harassment చేయగలరు.

ఇక్కడి రూల్ చాలా సూటిగా ఉంది -- ఇద్దరి మధ్యా ఇప్పటికే ఏదో ఒక
నిజమైన వ్యాపార సంబంధం (job application లేదా order) ఉంటేనే
చాట్ చేసుకోగలరు:

  1. Candidate ⇄ Employer  : ఆ candidate ఆ employer యొక్క ఏదైనా job
                             కి apply చేసి ఉంటేనే.
  2. Employer  ⇄ Vendor    : ఆ employer ఆ vendor దగ్గర ఏదైనా order
                             పెట్టి ఉంటేనే.
  3. Candidate ⇄ Vendor    : ప్రస్తుతం ఈ ఇద్దరి మధ్యా నేరుగా ఏ
                             వ్యాపార సంబంధమూ లేదు కాబట్టి, అనుమతి లేదు.

ఇప్పటికే ఉన్న conversation ని open చేయడానికి మాత్రం ఈ చెక్ అవసరం
లేదు (Conversation.is_participant() మాత్రమే చాలు) -- ఇది కేవలం
*కొత్త* conversation ఎవరితో మొదలుపెట్టొచ్చో నిర్ణయించడానికే.
"""
from accounts.models import EmployerProfile
from candidates.models import CandidateProfile
from jobs.models import JobApplication
from shopping.models import Order
from vendor.models import VendorProfile


def _role_of(user):
    """(role_string, profile) ని రిటర్న్ చేస్తుంది."""
    if hasattr(user, "candidate_profile"):
        return "candidate", user.candidate_profile
    if hasattr(user, "employer_profile"):
        return "employer", user.employer_profile
    if hasattr(user, "vendor_profile"):
        return "vendor", user.vendor_profile
    return None, None


def avatar_url_for(user):
    """చాట్ UI లో (sidebar list, header, message bubbles) చూపించడానికి
    ఈ యూజర్ యొక్క ప్రొఫైల్ ఫోటో URL -- ఫోటో లేకపోతే None (అప్పుడు
    టెంప్లేట్/JS initials-fallback వాడతాయి).

    గమనిక: Candidate కి రెండు వేర్వేరు photo ఫీల్డ్‌లు ఉన్నాయి
    (accounts.EmployeeProfile.profile_photo మరియు
    candidates.CandidateProfile.profile_photo) -- candidate dashboard
    అంతటా (సైడ్‌బార్, టాప్‌నావ్, ప్రొఫైల్ కార్డ్) EmployeeProfile
    దానినే canonical అవతార్ గా వాడుతుంది, కాబట్టి చాట్‌లో కూడా
    consistency కోసం అదే ఫీల్డ్ వాడతాం. Employer కి ఏ ఫోటో ఫీల్డ్ లేదు
    (accounts.EmployerProfile లో లేదు) కాబట్టి ఎప్పుడూ None -- initials
    మాత్రమే చూపిస్తుంది."""
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    if hasattr(user, "employee_profile") and user.employee_profile.profile_photo:
        return user.employee_profile.profile_photo.url
    if hasattr(user, "vendor_profile") and user.vendor_profile.shop_photo:
        return user.vendor_profile.shop_photo.url
    return None


def can_message(user_a, user_b) -> bool:
    if user_a.id == user_b.id:
        return False

    role_a, profile_a = _role_of(user_a)
    role_b, profile_b = _role_of(user_b)
    if role_a is None or role_b is None:
        return False

    pair = {role_a, role_b}

    if pair == {"candidate", "employer"}:
        candidate = profile_a if role_a == "candidate" else profile_b
        employer = profile_a if role_a == "employer" else profile_b
        if JobApplication.objects.filter(candidate=candidate, job__employer=employer).exists():
            return True
        # HireRequest: candidate ఎప్పుడూ apply చేయకపోయినా, Employer
        # candidate-search ద్వారా ఆ candidate ని నేరుగా సంప్రదించి
        # ఉంటే (headhunting), అది కూడా ఒక చెల్లుబాటు అయ్యే వ్యాపార
        # సంబంధమే -- employers/views.py: CandidateDetailView /
        # SendHireRequestView చూడండి.
        from employers.models import HireRequest
        return HireRequest.objects.filter(candidate=candidate, employer=employer).exists()

    if pair == {"employer", "vendor"}:
        employer = profile_a if role_a == "employer" else profile_b
        vendor = profile_a if role_a == "vendor" else profile_b
        return Order.objects.filter(buyer=employer, vendor=vendor).exists()

    # candidate ⇄ vendor, లేదా అదే రోల్ యిద్దరూ (candidate⇄candidate
    # వంటివి) -- ప్రస్తుతం అనుమతించడం లేదు.
    return False


def contacts_for(user):
    """ఆ యూజర్ ఇప్పటికే చాట్ మొదలుపెట్టగలిగే (లేదా ఇప్పటికే చాట్
    చేసిన) ఇతర యూజర్ల జాబితా -- 'కొత్త చాట్' మొదలుపెట్టే సెర్చ్
    బార్ కోసం. ప్రతి ఐటెమ్ ఒక dict: {user, name, identifier,
    avatar_url} -- 'identifier' లో మొబైల్ నెంబర్ + role ID రెండూ
    ఉంటాయి, తద్వారా సెర్చ్ బార్ లో పేరు తోనే కాక నెంబర్/ID తోనూ
    వెతకగలరు (WhatsApp లో లాగే 'నెంబర్ తో వెతికి చాట్ మొదలుపెట్టడం')."""
    role, profile = _role_of(user)
    contacts = {}

    if role == "candidate":
        employer_users = EmployerProfile.objects.filter(
            jobs__applications__candidate=profile,
        ).distinct().select_related("user")
        for employer in employer_users:
            contacts[employer.user_id] = {
                "user": employer.user,
                "name": employer.company_name,
                "identifier": f"{employer.mobile_number} · {employer.employer_id}".strip(" ·"),
            }
        # HireRequest ద్వారా సంప్రదించిన Employers కూడా (ఈ candidate
        # ఏ job కీ apply చేయకపోయినా) contact జాబితాలో కనిపించాలి.
        from employers.models import HireRequest
        for employer in EmployerProfile.objects.filter(
            hire_requests_sent__candidate=profile,
        ).distinct().select_related("user"):
            contacts[employer.user_id] = {
                "user": employer.user,
                "name": employer.company_name,
                "identifier": f"{employer.mobile_number} · {employer.employer_id}".strip(" ·"),
            }

    elif role == "employer":
        candidate_ids = set(JobApplication.objects.filter(
            job__employer=profile,
        ).values_list("candidate_id", flat=True).distinct())
        # HireRequest ద్వారా ఈ employer నేరుగా సంప్రదించిన
        # candidates కూడా చేర్చాలి (వాళ్ళు apply చేసి ఉండకపోయినా).
        candidate_ids |= set(profile.hire_requests_sent.values_list("candidate_id", flat=True).distinct())
        for candidate in CandidateProfile.objects.filter(
            id__in=candidate_ids,
        ).select_related("user", "user__employee_profile"):
            name = candidate.user.get_full_name() or candidate.user.username
            mobile = getattr(getattr(candidate.user, "employee_profile", None), "mobile_number", "")
            bh_id = getattr(getattr(candidate.user, "employee_profile", None), "bharathub_id", "")
            contacts[candidate.user_id] = {
                "user": candidate.user,
                "name": name,
                "identifier": f"{mobile} · {bh_id}".strip(" ·"),
            }

        vendor_ids = Order.objects.filter(
            buyer=profile,
        ).values_list("vendor_id", flat=True).distinct()
        for vendor in VendorProfile.objects.filter(
            id__in=vendor_ids,
        ).select_related("user"):
            contacts[vendor.user_id] = {
                "user": vendor.user,
                "name": vendor.shop_name,
                "identifier": f"{vendor.vendor_mobile} · {vendor.vendor_id}".strip(" ·"),
            }

    elif role == "vendor":
        employer_ids = Order.objects.filter(
            vendor=profile,
        ).values_list("buyer_id", flat=True).distinct()
        for employer in EmployerProfile.objects.filter(
            id__in=employer_ids,
        ).select_related("user"):
            contacts[employer.user_id] = {
                "user": employer.user,
                "name": employer.company_name,
                "identifier": f"{employer.mobile_number} · {employer.employer_id}".strip(" ·"),
            }

    for c in contacts.values():
        c["avatar_url"] = avatar_url_for(c["user"])
    return list(contacts.values())
