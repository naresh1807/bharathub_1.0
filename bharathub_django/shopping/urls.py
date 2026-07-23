from django.urls import path
from . import views

app_name = "shopping"

urlpatterns = [
    # Buyer (employer) side
    path("shop.html", views.ShopView.as_view(), name="shop"),
    path("place_order/", views.PlaceOrderView.as_view(), name="place_order"),
    path("my_orders.html", views.MyOrdersView.as_view(), name="my_orders"),
    path("orders/<int:pk>/cancel/", views.EmployerOrderCancelView.as_view(), name="order_cancel"),
    path("orders/<int:pk>/mark_delivered/", views.EmployerOrderMarkDeliveredView.as_view(), name="order_mark_delivered"),

    # Seller (vendor) side
    path("vendor_products.html", views.VendorProductsView.as_view(), name="vendor_products"),
    path("vendor_products/<int:pk>/delete/", views.VendorProductDeleteView.as_view(), name="vendor_product_delete"),
    path("vendor_orders.html", views.VendorOrdersView.as_view(), name="vendor_orders"),
]
