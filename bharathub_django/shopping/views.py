from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from .forms import ProductForm
from .models import Order, OrderItem, Product

# Shopping app: the B2B marketplace.
#   - Buyer (employer) side: browse products, track orders.
#   - Seller (vendor) side: manage product catalog, view/update orders.


class ShopView(LoginRequiredMixin, TemplateView):
    """Employer-facing: browse vendor products."""
    template_name = "shopping/shop.html"
    login_url = "accounts:employer_login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["products"] = Product.objects.filter(
            is_published=True, stock__gt=0,
        ).select_related("vendor")
        return context


class MyOrdersView(LoginRequiredMixin, TemplateView):
    """Employer-facing: track orders placed with vendors."""
    template_name = "shopping/my_orders.html"
    login_url = "accounts:employer_login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employer_profile = getattr(self.request.user, "employer_profile", None)
        if employer_profile is None:
            raise PermissionDenied("ఈ పేజీ Employer ఖాతాలకి మాత్రమే.")
        orders = list(
            employer_profile.orders.select_related("vendor").prefetch_related("items__product"),
        )
        context["orders"] = orders
        context["count_total"] = len(orders)
        context["count_pending"] = sum(
            1 for o in orders if o.status in (Order.Status.NEW, Order.Status.PROCESSING)
        )
        context["count_delivered"] = sum(1 for o in orders if o.status == Order.Status.DELIVERED)
        # "Total Spent" -- vendor_orders.html లో ఇప్పటికే ఉన్న
        # "month_revenue" లాగే, DELIVERED అయిన ఆర్డర్‌లు మాత్రమే
        # లెక్కిస్తాం (ఇంకా అందని ఆర్డర్ మీద డబ్బు "spent" అని చెప్పడం
        # తప్పు).
        context["total_spent"] = sum(
            o.total_amount for o in orders if o.status == Order.Status.DELIVERED
        )
        return context


class VendorProductsView(LoginRequiredMixin, View):
    """Vendor-facing: manage the product/service catalog (list + add)."""
    template_name = "shopping/vendor_products.html"
    login_url = "vendor:vendor_login"

    def get_vendor(self, request):
        vendor_profile = getattr(request.user, "vendor_profile", None)
        if vendor_profile is None:
            raise PermissionDenied("ఈ పేజీ Vendor ఖాతాలకి మాత్రమే.")
        return vendor_profile

    def get(self, request, *args, **kwargs):
        vendor = self.get_vendor(request)
        context = {
            "products": vendor.products.all(),
            "form": ProductForm(),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        vendor = self.get_vendor(request)
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.vendor = vendor
            product.is_published = request.POST.get("action") != "draft"
            product.save()
            messages.success(request, f"✅ '{product.name}' catalog కి జోడించబడింది.")
            return redirect("shopping:vendor_products")

        context = {"products": vendor.products.all(), "form": form}
        return render(request, self.template_name, context)


class VendorProductDeleteView(LoginRequiredMixin, View):
    login_url = "vendor:vendor_login"

    def post(self, request, pk, *args, **kwargs):
        product = get_object_or_404(Product, pk=pk, vendor__user=request.user)
        product.delete()
        messages.success(request, "🗑️ ప్రొడక్ట్ తొలగించబడింది.")
        return redirect("shopping:vendor_products")


class VendorOrdersView(LoginRequiredMixin, View):
    """Vendor-facing: view & update orders received from employers."""
    template_name = "shopping/vendor_orders.html"
    login_url = "vendor:vendor_login"

    def get_vendor(self, request):
        vendor_profile = getattr(request.user, "vendor_profile", None)
        if vendor_profile is None:
            raise PermissionDenied("ఈ పేజీ Vendor ఖాతాలకి మాత్రమే.")
        return vendor_profile

    def get(self, request, *args, **kwargs):
        vendor = self.get_vendor(request)
        orders = vendor.orders.select_related("buyer").prefetch_related("items__product")
        context = {
            "orders": orders,
            "new_orders": [o for o in orders if o.status == Order.Status.NEW],
            "count_new": sum(1 for o in orders if o.status == Order.Status.NEW),
            "count_processing": sum(1 for o in orders if o.status == Order.Status.PROCESSING),
            "count_delivered": sum(1 for o in orders if o.status == Order.Status.DELIVERED),
            "month_revenue": sum(o.total_amount for o in orders if o.status == Order.Status.DELIVERED),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        vendor = self.get_vendor(request)
        order = get_object_or_404(Order, pk=request.POST.get("order_id"), vendor=vendor)
        new_status = request.POST.get("status")
        if new_status in Order.Status.values:
            order.status = new_status
            order.save(update_fields=["status"])
            messages.success(request, f"✅ Order #{order.pk} స్టేటస్ అప్‌డేట్ అయ్యింది.")
        return redirect("shopping:vendor_orders")


# ============================================================================
# PlaceOrderView / EmployerOrderCancelView / EmployerOrderMarkDeliveredView
#
# ఎందుకు ఇవి కావాలి: shop.html లోని "🚀 Proceed to Checkout" ఇంతకుముందు
# పూర్తిగా JS లోనే (allOrders అనే in-memory array లో) ఒక fake ఆర్డర్ ఐడి
# తయారుచేసేది -- ఏ Order/OrderItem రికార్డూ DB లో సేవ్ అయ్యేది కాదు.
# పైగా my_orders.html పేజీ కి వెళ్ళేసరికి (అది పూర్తి పేజీ లోడ్ కాబట్టి)
# ఆ JS array ఖాళీ అయిపోయి "No Orders Yet" చూపించేది -- ఇప్పుడే పెట్టిన
# ఆర్డర్ కూడా కనిపించేది కాదు! ఇప్పుడు చెక్అవుట్ నిజంగా Order+OrderItem
# రికార్డులు సృష్టిస్తుంది, స్టాక్ తగ్గిస్తుంది, my_orders.html వాటినే
# (MyOrdersView.get_context_data లో ఇప్పటికే ఉన్న నిజమైన క్వెరీ నుండి)
# చూపిస్తుంది.
# ============================================================================
class PlaceOrderView(LoginRequiredMixin, View):
    """shop.html లోని hidden #checkoutForm ఇక్కడికే POST చేస్తుంది
    (product_id[] + qty[] జతలుగా) -- చూడండి buyer_shopping.js
    proceedCheckout(). కార్ట్ లో ఒకటి కంటే ఎక్కువ వెండర్ల ప్రొడక్ట్‌లు
    ఉంటే, ప్రతి వెండర్ కీ విడిగా ఒక Order క్రియేట్ అవుతుంది (Order.vendor
    ఒకే ఒక్క వెండర్ ని పాయింట్ చేస్తుంది కాబట్టి)."""

    login_url = "accounts:employer_login"

    def get_employer(self, request):
        employer_profile = getattr(request.user, "employer_profile", None)
        if employer_profile is None:
            raise PermissionDenied("ఈ పేజీ Employer ఖాతాలకి మాత్రమే.")
        return employer_profile

    def post(self, request, *args, **kwargs):
        employer = self.get_employer(request)
        product_ids = request.POST.getlist("product_id")
        raw_quantities = request.POST.getlist("qty")

        if not product_ids:
            messages.error(request, "⚠️ కార్ట్ ఖాళీగా ఉంది.")
            return redirect("shopping:shop")

        # ఒకే వెండర్ కి చెందిన ఐటమ్స్ ని ఒక్కచోట గుర్తుపెట్టుకుంటాం (Order
        # per vendor). స్టాక్ కన్నా ఎక్కువ కోరితే అందుబాటులో ఉన్నంతకే cap
        # చేస్తాం (ఎవరైనా ఫారమ్ ని manipulate చేసినా ఓవర్‌సెల్ కాకుండా).
        items_by_vendor = {}
        skipped_any = False
        for pid, qty_raw in zip(product_ids, raw_quantities):
            try:
                product = Product.objects.select_related("vendor").get(
                    pk=pid, is_published=True,
                )
            except (Product.DoesNotExist, ValueError, TypeError):
                skipped_any = True
                continue
            try:
                requested_qty = int(qty_raw)
            except (TypeError, ValueError):
                requested_qty = 1
            qty = max(1, min(requested_qty, product.stock))
            if qty <= 0:
                skipped_any = True
                continue
            items_by_vendor.setdefault(product.vendor_id, []).append((product, qty))

        if not items_by_vendor:
            messages.error(request, "⚠️ ఎంచుకున్న ప్రొడక్ట్‌లు ఇప్పుడు అందుబాటులో లేవు (స్టాక్ అయిపోయి ఉండొచ్చు).")
            return redirect("shopping:shop")

        created_orders = []
        with transaction.atomic():
            for product_qty_list in items_by_vendor.values():
                vendor = product_qty_list[0][0].vendor
                order = Order.objects.create(vendor=vendor, buyer=employer, total_amount=0)
                order_total = 0
                for product, qty in product_qty_list:
                    OrderItem.objects.create(
                        order=order, product=product, quantity=qty,
                        price_at_order=product.price,
                    )
                    product.stock = max(0, product.stock - qty)
                    product.save(update_fields=["stock"])
                    order_total += product.price * qty
                order.total_amount = order_total
                order.save(update_fields=["total_amount"])
                created_orders.append(order)

        if len(created_orders) == 1:
            messages.success(
                request,
                f"🎉 Order #{created_orders[0].pk} విజయవంతంగా పెట్టబడింది! మొత్తం ₹{created_orders[0].total_amount}.",
            )
        else:
            order_ids = ", ".join(f"#{o.pk}" for o in created_orders)
            messages.success(
                request,
                f"🎉 {len(created_orders)} వేర్వేరు వెండర్ల నుండి ఆర్డర్‌లు ({order_ids}) విజయవంతంగా పెట్టబడ్డాయి!",
            )
        if skipped_any:
            messages.warning(request, "⚠️ కార్ట్ లో కొన్ని ఐటమ్స్ ఇప్పుడు అందుబాటులో లేక తీసివేయబడ్డాయి.")
        return redirect("shopping:my_orders")


class EmployerOrderCancelView(LoginRequiredMixin, View):
    """my_orders.html లోని "❌ Cancel" బటన్ -- ఆర్డర్ ఇంకా NEW స్టేటస్
    లోనే ఉంటేనే (వెండర్ ఇంకా ప్రాసెస్ చేయకముందే) cancel చేయనిస్తాం,
    స్టాక్ తిరిగి జోడిస్తాం."""

    login_url = "accounts:employer_login"

    def post(self, request, pk, *args, **kwargs):
        employer_profile = getattr(request.user, "employer_profile", None)
        if employer_profile is None:
            raise PermissionDenied("ఈ పేజీ Employer ఖాతాలకి మాత్రమే.")
        order = get_object_or_404(Order, pk=pk, buyer=employer_profile)
        if order.status != Order.Status.NEW:
            messages.error(request, "⚠️ వెండర్ ఇప్పటికే ప్రాసెస్ చేయడం మొదలుపెట్టిన ఆర్డర్‌ని cancel చేయలేరు.")
            return redirect("shopping:my_orders")
        with transaction.atomic():
            for item in order.items.select_related("product"):
                item.product.stock += item.quantity
                item.product.save(update_fields=["stock"])
            order.status = Order.Status.CANCELLED
            order.save(update_fields=["status"])
        messages.success(request, f"❌ Order #{order.pk} cancel చేయబడింది.")
        return redirect("shopping:my_orders")


class EmployerOrderMarkDeliveredView(LoginRequiredMixin, View):
    """my_orders.html లోని "✅ Mark Delivered" బటన్ -- గూడ్స్ అందిన తర్వాత
    ఎంప్లాయర్ నిర్ధారిస్తారు."""

    login_url = "accounts:employer_login"

    def post(self, request, pk, *args, **kwargs):
        employer_profile = getattr(request.user, "employer_profile", None)
        if employer_profile is None:
            raise PermissionDenied("ఈ పేజీ Employer ఖాతాలకి మాత్రమే.")
        order = get_object_or_404(Order, pk=pk, buyer=employer_profile)
        if order.status in (Order.Status.DELIVERED, Order.Status.CANCELLED):
            return redirect("shopping:my_orders")
        order.status = Order.Status.DELIVERED
        order.save(update_fields=["status"])
        messages.success(request, f"✅ Order #{order.pk} delivered గా గుర్తించబడింది.")
        return redirect("shopping:my_orders")
