import json
import math

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from shopping.models import Order
from accounts.login_throttle import (
    MAX_FAILED_ATTEMPTS, is_locked_out, record_failed_attempt, clear_attempts,
)
from accounts.notifications import send_bharathub_id_email
from messaging.views import unread_total_for
from .forms import VendorLoginForm, VendorRegistrationForm, VendorProfileCompletionForm
from .models import VendorProfile

# Vendor app: vendor registration, login & vendor dashboard/services.


class VendorRegistrationView(TemplateView):
    template_name = "vendor/vendor_registration.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", VendorRegistrationForm())
        return context

    def post(self, request, *args, **kwargs):
        # request.FILES: shop_photo ఫైల్ అప్‌లోడ్ కోసం.
        form = VendorRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user, profile = form.save()
            login(request, user)
            send_bharathub_id_email(user, profile.vendor_id, "Vendor ID")
            context = self.get_context_data(form=VendorRegistrationForm())
            context["registered_id"] = profile.vendor_id
            return self.render_to_response(context)
        return self.render_to_response(self.get_context_data(form=form))


class VendorLoginView(TemplateView):
    template_name = "vendor/vendor_login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", VendorLoginForm())
        return context

    def post(self, request, *args, **kwargs):
        form = VendorLoginForm(request.POST)
        if form.is_valid():
            login_id = form.cleaned_data["login_id"].strip()
            User = get_user_model()

            # login_id "Vendor ID" లేదా ఇమెయిల్ మాత్రమే అనుమతిస్తాం
            # (మొబైల్ నెంబర్ తో లాగిన్ ఇక పనిచేయదు -- User.username
            # గా మనం vendor_mobile నే స్టోర్ చేసినా సరే, దాన్ని
            # లాగిన్-ఐడెంటిఫయర్ గా బహిర్గతం చేయకుండా ఇక్కడే ఆపేస్తాం).
            resolved_user = None
            if login_id.upper().startswith("BHV"):
                profile = VendorProfile.objects.filter(
                    vendor_id__iexact=login_id
                ).select_related("user").first()
                if profile:
                    resolved_user = profile.user
            else:
                resolved_user = User.objects.filter(email__iexact=login_id).first()

            if resolved_user is not None and is_locked_out(resolved_user):
                messages.error(
                    request,
                    "🔒 ఈ ఖాతాలో 3 సార్లు తప్పు పాస్‌వర్డ్ ఎంటర్ చేశారు. భద్రత కోసం "
                    "ఖాతా లాక్ చేయబడింది -- కింద ఉన్న 'Forgot Password?' తో గుర్తింపు "
                    "నిర్ధారించుకుని, కొత్త పాస్‌వర్డ్ సెట్ చేసుకుంటేనే మళ్ళీ లాగిన్ అవ్వగలరు.",
                )
                return self.render_to_response(self.get_context_data(form=form))

            username = resolved_user.username if resolved_user else None
            user = authenticate(request, username=username, password=form.cleaned_data["password"]) if username else None
            if user is not None:
                clear_attempts(user)
                login(request, user)
                if not form.cleaned_data.get("remember_me"):
                    request.session.set_expiry(0)
                messages.success(request, "✅ Login successful!")
                return redirect("vendor:vendor_dashboard")

            # ఇక్కడ కూడా "ID దొరకలేదు" vs "పాస్‌వర్డ్ తప్పు" అని
            # వేరుగా చెప్పడం లేదు (user-enumeration దాడులు ఆపడానికి).
            if resolved_user is not None:
                attempts = record_failed_attempt(resolved_user)
                if attempts >= MAX_FAILED_ATTEMPTS:
                    messages.error(
                        request,
                        "🔒 3 సార్లు తప్పు పాస్‌వర్డ్ ఎంటర్ చేశారు. మీ ఖాతా భద్రత "
                        "కోసం లాక్ చేయబడింది. దయచేసి కింద ఉన్న 'Forgot Password?' "
                        "లింక్ తో మీ పాస్‌వర్డ్ ని తప్పనిసరిగా రీసెట్ చేసుకోండి.",
                    )
                else:
                    messages.error(request, "⚠️ Invalid credentials. Please try again.")
            else:
                messages.error(request, "⚠️ Invalid credentials. Please try again.")

        return self.render_to_response(self.get_context_data(form=form))


# LoginRequiredMixin: లాగిన్ అవ్వని యూజర్ నేరుగా URL టైప్ చేసి
# డాష్‌బోర్డ్ చూడకుండా ఆపుతుంది -- లాగిన్ లేకపోతే automatic గా
# login page కి redirect చేస్తుంది (ఇది కూడా ఒక సెక్యూరిటీ నియమం:
# ప్రతి ప్రొటెక్టెడ్ పేజీ ని ఎప్పుడూ auth-check లేకుండా వదలొద్దు).
class VendorDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "vendor/vendor_dashboard.html"
    login_url = "vendor:vendor_login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["unread_message_count"] = unread_total_for(self.request.user)

        requested_section = self.request.GET.get("section", "")
        context["active_section"] = requested_section if requested_section in ("home", "analytics") else "home"

        vendor = getattr(self.request.user, "vendor_profile", None)
        if vendor is None:
            return context

        now = timezone.now()
        orders = vendor.orders.select_related("buyer").prefetch_related("items__product")
        this_month_orders = [o for o in orders if o.created_at.year == now.year and o.created_at.month == now.month]
        delivered = [o for o in orders if o.status == Order.Status.DELIVERED]

        context["vendor"] = vendor
        context["stat_orders_this_month"] = len(this_month_orders)
        context["stat_pending"] = sum(1 for o in orders if o.status in (Order.Status.NEW, Order.Status.PROCESSING))
        context["stat_active_products"] = vendor.products.filter(is_published=True).count()
        context["stat_revenue_this_month"] = sum(o.total_amount for o in this_month_orders if o.status == Order.Status.DELIVERED)
        context["recent_orders"] = list(orders[:3])

        # RECENT ACTIVITY: ఇంతకుముందు "New order from TCS", "Enquiry
        # received from Wipro HR" లాంటి పూర్తిగా కల్పిత entries ఉండేవి.
        # ఇప్పుడు ఈ vendor యొక్క నిజమైన ఇటీవలి ఆర్డర్లు + ఇటీవల
        # జోడించిన ప్రొడక్టుల్ని (రెండిటినీ కలిపి, తేదీ ప్రకారం
        # sort చేసి) చూపిస్తాం -- "Enquiry" అనే concept కి వెనుక ఏ
        # మోడల్ లేదు (messaging app లోని Conversation ఉంది, కానీ అది
        # వేరే స్కోప్) కాబట్టి దాన్ని తీసేశాం.
        recent_products = list(vendor.products.order_by("-created_at")[:5])
        activity_items = []
        for o in orders.order_by("-created_at")[:5]:
            activity_items.append({
                "kind": "order",
                "timestamp": o.created_at,
                "text": f"New order from {o.buyer.company_name} — ₹{o.total_amount:,}"
                        if o.status == Order.Status.NEW
                        else f"Order from {o.buyer.company_name} — {o.get_status_display()}",
                "color": "var(--success)" if o.status == Order.Status.NEW else (
                    "var(--primary)" if o.status == Order.Status.DELIVERED else "#6366f1"
                ),
                "pulse": o.status == Order.Status.NEW,
            })
        for p in recent_products:
            activity_items.append({
                "kind": "product",
                "timestamp": p.created_at,
                "text": f"{p.name} listed at ₹{p.price:,}",
                "color": "var(--accent)",
                "pulse": False,
            })
        activity_items.sort(key=lambda item: item["timestamp"], reverse=True)
        context["recent_activity"] = activity_items[:5]

        # ── REVENUE TREND (గత 6 నెలలు, ప్రతి నెలలో delivered orders మొత్తం) ──
        # (year, month) tuples గత 6 నెలలకు, calendar-safe గా వెనక్కి లెక్కిస్తాం.
        y, m = now.year, now.month
        year_months = []
        for _ in range(6):
            year_months.insert(0, (y, m))
            m -= 1
            if m == 0:
                m = 12
                y -= 1

        revenue_by_month = []
        for (yy, mm) in year_months:
            total = sum(o.total_amount for o in delivered if o.created_at.year == yy and o.created_at.month == mm)
            label = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][mm]
            revenue_by_month.append({"month": label, "val": total})
        context["revenue_chart_json"] = json.dumps(revenue_by_month)
        total_revenue = sum(r["val"] for r in revenue_by_month)
        context["revenue_total"] = total_revenue
        context["revenue_avg_month"] = total_revenue // 6 if total_revenue else 0

        # ── ORDER STATUS DONUT (delivered / processing / cancelled) ──
        total_orders = orders.count()
        counts = {
            "delivered": sum(1 for o in orders if o.status == Order.Status.DELIVERED),
            "processing": sum(1 for o in orders if o.status in (Order.Status.NEW, Order.Status.PROCESSING)),
            "cancelled": sum(1 for o in orders if o.status == Order.Status.CANCELLED),
        }
        circumference = 2 * math.pi * 60
        offset = 0
        donut = {}
        for key in ("delivered", "processing", "cancelled"):
            pct = (counts[key] / total_orders) if total_orders else 0
            arc = pct * circumference
            donut[key] = {
                "count": counts[key],
                "pct": round(pct * 100),
                "dasharray": f"{arc:.0f} {circumference - arc:.0f}",
                "dashoffset": f"-{offset:.0f}",
            }
            offset += arc
        context["donut"] = donut
        context["total_orders"] = total_orders

        # QUICK BUSINESS STATS కార్డ్ లో ఇంతకుముందు "94.2%" fulfillment
        # rate మరియు "12 Active" ప్రొడక్ట్స్ హార్డ్‌కోడ్ చేసి ఉండేవి --
        # ఇప్పుడు fulfillment rate ని (delivered/total orders) నుండి
        # నిజంగా లెక్కిస్తాం. "Product Listing Health" ఇప్పటికే పైన
        # లెక్కించిన stat_active_products నే వాడుకుంటుంది (టెంప్లేట్
        # లో నేరుగా). "Customer Satisfaction" కి వెనుక ఏ Review/Rating
        # మోడల్ ప్రాజెక్ట్ లో లేదు కాబట్టి దాన్ని real డేటాతో
        # నింపలేము -- టెంప్లేట్ లో "—" గా చూపిస్తాం (ఫీచర్ లేదని
        # స్పష్టంగా, తప్పుడు నంబర్ చూపించే బదులు).
        context["fulfillment_rate"] = (
            round(100 * counts["delivered"] / total_orders) if total_orders else 0
        )

        return context


# ============================================================================
# VendorProfileCompletionView
#
# రిజిస్ట్రేషన్ లో అడగని మొబైల్/కేటగిరీ/పనిచేసే రోజులు/షాప్ ఫోటో
# వివరాలు లాగిన్ అయిన తర్వాత ఇక్కడ నింపుకుంటారు.
# ProfileCompletionMiddleware (accounts/middleware.py) profile_completed=
# False ఉన్న ప్రతి vendor ని ఇక్కడికే బలవంతంగా పంపుతుంది.
# ============================================================================
class VendorProfileCompletionView(View):
    template_name = "vendor/vendor_profile_completion.html"

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, "vendor_profile"):
            return redirect("vendor:vendor_login")
        profile = request.user.vendor_profile
        if profile.profile_completed:
            return redirect("vendor:vendor_dashboard")
        form = VendorProfileCompletionForm(instance=profile)
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, "vendor_profile"):
            return redirect("vendor:vendor_login")
        profile = request.user.vendor_profile
        form = VendorProfileCompletionForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.profile_completed = True
            profile.save()
            messages.success(request, "✅ మీ ప్రొఫైల్ పూర్తయింది! ఇక పూర్తి యాక్సెస్ మీది.")
            return redirect("vendor:vendor_dashboard")
        return render(request, self.template_name, {"form": form})
