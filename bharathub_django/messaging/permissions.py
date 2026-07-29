"""
messaging/permissions.py

"Secure" messaging అంటే encryption ఒక్కటే సరిపోదు -- ఎవరు ఎవరితో
చాట్ మొదలుపెట్టగలరు అనేది కూడా ఇక్కడే నిర్ణయమవుతుంది.

గతంలో ఇక్కడి రూల్ కఠినంగా ఉండేది -- ఇద్దరి మధ్యా ఇప్పటికే ఏదో ఒక
వ్యాపార సంబంధం (job application / HireRequest / order) ఉంటేనే
చాట్ మొదలుపెట్టగలిగేవాళ్ళు. ఇప్పుడు ఆ ఆంక్ష తీసేశాం -- సైట్ లో
రిజిస్టర్ అయిన (Candidate/Employer/Vendor ఏ రోల్ అయినా) ఎవరైనా,
మరే ఇతర రిజిస్టర్డ్ యూజర్ తోనైనా నేరుగా చాట్ మొదలుపెట్టగలరు.

స్పామ్/అనుచిత మెసేజ్‌ల విషయంలో రక్షణ ఇప్పుడు accountability మీద
ఆధారపడి ఉంది, కాకుండా -- ప్రతి మెసేజ్ ఒక నిజమైన, verified ఖాతా
(mobile-verified registration) నుండే వస్తుంది, ప్రతి సంభాషణలో ఎవరు
ఎవరో (పేరు, mobile number, BharatHub ID) ఎప్పుడూ కనిపిస్తూనే
ఉంటుంది (Message.sender ఎప్పుడూ Django User కి tied), కాబట్టి ఎవరైనా
స్పామ్ చేస్తే ఆ యూజర్ ని గుర్తించడం (మరియు అవసరమైతే block/report
చేయడం) సాధ్యమే. anonymous messaging కాదు ఇది.

ఇప్పటికే ఉన్న conversation ని open చేయడానికి ఈ చెక్ అవసరం లేదు
(Conversation.is_participant() మాత్రమే చాలు) -- ఇది కేవలం *కొత్త*
conversation ఎవరితో మొదలుపెట్టొచ్చో నిర్ణయించడానికే.
"""
from django.db.models import Q

from accounts.models import EmployerProfile
from candidates.models import CandidateProfile
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
    consistency కోసం అదే ఫీల్డ్ వాడతాం (candidates/views.py లోని
    CandidateProfileEditView.post() ఫోటో అప్‌లోడ్ అయినప్పుడు దీన్ని
    సింక్ చేస్తుంది). Employer కి company_logo ఇప్పుడు ఉంది
    (accounts.EmployerProfile.company_logo)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    if hasattr(user, "employee_profile") and user.employee_profile.profile_photo:
        return user.employee_profile.profile_photo.url
    if hasattr(user, "employer_profile") and user.employer_profile.company_logo:
        return user.employer_profile.company_logo.url
    if hasattr(user, "vendor_profile") and user.vendor_profile.shop_photo:
        return user.vendor_profile.shop_photo.url
    return None


def can_message(user_a, user_b) -> bool:
    """ఇద్దరు రిజిస్టర్డ్ యూజర్ల మధ్య కొత్త చాట్ మొదలుపెట్టొచ్చా.

    ఇప్పుడు ఏకైక చెక్: ఇద్దరూ వేర్వేరు వ్యక్తులు, ఇద్దరికీ సైట్ లో ఒక
    చెల్లుబాటు అయ్యే ప్రొఫైల్ (Candidate/Employer/Vendor లో ఏదో ఒకటి)
    ఉండాలి -- అంతే. ఇద్దరి మధ్యా job application/order లాంటి వ్యాపార
    సంబంధం ఉందా లేదా అనేది ఇక చెక్ చేయడం లేదు."""
    if user_a.id == user_b.id:
        return False

    role_a, _ = _role_of(user_a)
    role_b, _ = _role_of(user_b)
    return role_a is not None and role_b is not None


def contacts_for(user):
    """సైట్ లో రిజిస్టర్ అయిన మిగతా ప్రతి ఒక్కరి జాబితా (ఈ యూజర్ ని
    తప్ప) -- 'కొత్త చాట్' మొదలుపెట్టే సెర్చ్ బార్ కోసం. ప్రతి ఐటెమ్
    ఒక dict: {user, name, identifier, avatar_url} -- 'identifier' లో
    మొబైల్ నెంబర్ + role ID రెండూ ఉంటాయి, తద్వారా సెర్చ్ బార్ లో పేరు
    తోనే కాక నెంబర్/ID తోనూ వెతకగలరు (WhatsApp లో లాగే 'నెంబర్ తో
    వెతికి చాట్ మొదలుపెట్టడం').

    ⚠️ పెర్ఫార్మెన్స్ ఫిక్స్ (ఇక్కడ ఇంతకుముందు ఉన్న తీవ్రమైన N+1 బగ్):
    ఇది ప్లాట్‌ఫారమ్ లోని ప్రతి యూజర్ నీ scan చేస్తుంది కాబట్టి, ప్రతి
    contact కి avatar_url_for() (hasattr చెక్‌ల ద్వారా 3 వేర్వేరు
    profile రిలేషన్‌లని తనిఖీ చేసేది) విడిగా పిలవడం వల్ల 100+ యూజర్లు
    ఉంటే వందల ఎక్స్‌ట్రా క్వెరీలు వచ్చేవి -- Messages పేజీ ప్రతిసారీ
    చాలా నెమ్మదిగా (కొన్నిసార్లు మొబైల్ లో టైమ్అవుట్ అయ్యేంత) లోడ్
    అవ్వడానికి ఇదే ప్రధాన కారణం. ఇప్పుడు avatar/name/identifier మూడూ
    ఇప్పటికే select_related() చేసిన object మీద నుండే నేరుగా చదువుతాం
    -- మొత్తం ఈ ఫంక్షన్ కి ఖచ్చితంగా 3 DB క్వెరీలు మాత్రమే (ఒక్కో
    ప్రొఫైల్ టేబుల్ కి ఒకటి), యూజర్ల సంఖ్యతో సంబంధం లేకుండా."""
    contacts = {}

    for candidate in CandidateProfile.objects.exclude(
        user_id=user.id,
    ).select_related("user", "user__employee_profile"):
        employee_profile = getattr(candidate.user, "employee_profile", None)
        name = candidate.user.get_full_name() or candidate.user.username
        mobile = getattr(employee_profile, "mobile_number", "") or ""
        bh_id = getattr(employee_profile, "bharathub_id", "") or ""
        avatar_url = (
            employee_profile.profile_photo.url
            if employee_profile and employee_profile.profile_photo else None
        )
        contacts[candidate.user_id] = {
            "user": candidate.user,
            "name": name,
            "identifier": f"{mobile} · {bh_id}".strip(" ·"),
            "avatar_url": avatar_url,
        }

    for employer in EmployerProfile.objects.exclude(
        user_id=user.id,
    ).select_related("user"):
        avatar_url = employer.company_logo.url if employer.company_logo else None
        contacts[employer.user_id] = {
            "user": employer.user,
            "name": employer.company_name,
            "identifier": f"{employer.mobile_number} · {employer.employer_id}".strip(" ·"),
            "avatar_url": avatar_url,
        }

    for vendor in VendorProfile.objects.exclude(
        user_id=user.id,
    ).select_related("user"):
        avatar_url = vendor.shop_photo.url if vendor.shop_photo else None
        contacts[vendor.user_id] = {
            "user": vendor.user,
            "name": vendor.shop_name,
            "identifier": f"{vendor.vendor_mobile} · {vendor.vendor_id}".strip(" ·"),
            "avatar_url": avatar_url,
        }

    return list(contacts.values())


def search_contacts(user, query, limit=20):
    """⚠️ ఇదే అసలైన ఫిక్స్: contacts_for() పైన ఉన్న N+1 అవతార్-లుక్అప్
    బగ్ ఇంతకుముందే ఫిక్స్ అయింది (3 క్వెరీలకే పరిమితం), కానీ అది ఇప్పటికీ
    'సైట్ లో రిజిస్టర్ అయిన ప్రతి ఒక్కరినీ' -- పది మంది ఉన్నా, పది వేల
    మంది ఉన్నా -- ప్రతి Messages పేజీ లోడ్ కీ పూర్తిగా మెమరీ లోకి
    తెచ్చి, ఆ మొత్తం జాబితానీ JSON గా పేజీ HTML లో పొందుపరిచేది. అదే
    అసలైన scalability సమస్య (view.py లో `contacts_for(user)` కాల్ చేసే
    ప్రతిచోటా). ఈ కొత్త ఫంక్షన్ దాన్ని పూర్తిగా భర్తీ చేస్తుంది --
    ఖాళీ query కి ఖాళీ లిస్ట్ (ఏమీ eager గా లోడ్ చేయదు); query ఇచ్చినప్పుడు
    మాత్రమే, ఆ query కి సరిపోలిన వాళ్ళని మాత్రమే (ఒక్కో ప్రొఫైల్ టైప్
    కి `limit` వరకూ) DB స్థాయిలోనే (icontains) ఫిల్టర్ చేసి తెస్తుంది --
    ఎంతమంది యూజర్లు రిజిస్టర్ అయినా ప్రతి కీస్ట్రోక్ కి కేవలం మూడు
    చిన్న, bounded క్వెరీలే (ఒక్కో ప్రొఫైల్ టేబుల్ కి ఒకటి, ఒక్కోటీ
    `limit` కి పరిమితం). వాడకం: messaging/views.py:ContactSearchView
    (AJAX, సెర్చ్ బాక్స్ లో టైప్ చేసినప్పుడల్లా పిలుస్తుంది)."""
    query = (query or "").strip()
    if not query:
        return []

    results = []

    candidate_matches = CandidateProfile.objects.exclude(
        user_id=user.id,
    ).filter(
        Q(user__first_name__icontains=query)
        | Q(user__last_name__icontains=query)
        | Q(user__username__icontains=query)
        | Q(user__employee_profile__mobile_number__icontains=query)
        | Q(user__employee_profile__bharathub_id__icontains=query),
    ).select_related("user", "user__employee_profile").distinct()[:limit]
    for candidate in candidate_matches:
        employee_profile = getattr(candidate.user, "employee_profile", None)
        name = candidate.user.get_full_name() or candidate.user.username
        mobile = getattr(employee_profile, "mobile_number", "") or ""
        bh_id = getattr(employee_profile, "bharathub_id", "") or ""
        avatar_url = (
            employee_profile.profile_photo.url
            if employee_profile and employee_profile.profile_photo else None
        )
        results.append({
            "user": candidate.user,
            "name": name,
            "identifier": f"{mobile} · {bh_id}".strip(" ·"),
            "avatar_url": avatar_url,
        })

    employer_matches = EmployerProfile.objects.exclude(
        user_id=user.id,
    ).filter(
        Q(company_name__icontains=query)
        | Q(mobile_number__icontains=query)
        | Q(employer_id__icontains=query),
    ).select_related("user").distinct()[:limit]
    for employer in employer_matches:
        avatar_url = employer.company_logo.url if employer.company_logo else None
        results.append({
            "user": employer.user,
            "name": employer.company_name,
            "identifier": f"{employer.mobile_number} · {employer.employer_id}".strip(" ·"),
            "avatar_url": avatar_url,
        })

    vendor_matches = VendorProfile.objects.exclude(
        user_id=user.id,
    ).filter(
        Q(shop_name__icontains=query)
        | Q(vendor_mobile__icontains=query)
        | Q(vendor_id__icontains=query),
    ).select_related("user").distinct()[:limit]
    for vendor in vendor_matches:
        avatar_url = vendor.shop_photo.url if vendor.shop_photo else None
        results.append({
            "user": vendor.user,
            "name": vendor.shop_name,
            "identifier": f"{vendor.vendor_mobile} · {vendor.vendor_id}".strip(" ·"),
            "avatar_url": avatar_url,
        })

    return results[:limit]


def valid_contact_ids(user_ids):
    """సమర్పించిన user_ids లో ఏవి నిజంగా చెల్లుబాటు అయ్యే (Candidate/
    Employer/Vendor ప్రొఫైల్ ఉన్న) యూజర్ IDs అని చెక్ చేస్తుంది --
    contacts_for() లా మొత్తం యూజర్ బేస్ ని తేకుండా, ఇన్‌పుట్ గా వచ్చిన
    IDs సంఖ్యకే (ఉదా: ఒక గ్రూప్ క్రియేట్ చేసేటప్పుడు ఎంచుకున్న 5-20
    మంది) పరిమితమైన మూడు చిన్న క్వెరీలు మాత్రమే. వాడకం:
    messaging/views.py:CreateGroupView (సమర్పించిన member_ids అన్నీ
    నిజమైన ఖాతాలేనా అని ధృవీకరించడానికి)."""
    ids = list({int(i) for i in user_ids if str(i).isdigit()})
    if not ids:
        return set()
    valid = set(CandidateProfile.objects.filter(user_id__in=ids).values_list("user_id", flat=True))
    valid |= set(EmployerProfile.objects.filter(user_id__in=ids).values_list("user_id", flat=True))
    valid |= set(VendorProfile.objects.filter(user_id__in=ids).values_list("user_id", flat=True))
    return valid
