def display_name_for(user):
    """మీటింగ్ రూమ్ లో (participant tiles, in-room chat) చూపించడానికి
    ఈ యూజర్ పేరు -- Candidate/Employer/Vendor ఏ రోల్ అయినా సరైన పేరు
    వచ్చేలా (messaging/permissions.py::_role_of లో వాడిన అదే
    ప్రొఫైల్ attribute లు)."""
    if hasattr(user, "employer_profile"):
        return user.employer_profile.company_name
    if hasattr(user, "vendor_profile"):
        return user.vendor_profile.shop_name
    return user.get_full_name() or user.username
