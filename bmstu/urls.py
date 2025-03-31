from django.contrib import admin
from django.urls import path
from bmstu_lab.views import home, lenses_detail, cart_detail, add_to_cart, remove_from_cart

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("lens/<int:lens_id>/", lenses_detail, name="lenses_detail"),
    path("cart/", cart_detail, name="cart_detail"),  # Обратите внимание на name="cart_detail"
    path("cart/add/<int:lens_id>/", add_to_cart, name="add_to_cart"),
    path('cart/remove/<int:lens_id>/', remove_from_cart, name='remove_from_cart'),
]