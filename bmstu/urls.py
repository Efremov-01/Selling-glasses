from django.contrib import admin
from django.urls import path
from bmstu_lab.views import home, lenses_detail, cart_detail

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("lens/<int:lens_id>/", lenses_detail, name="lenses_detail"),
    path("cart/", cart_detail, name="cart_detail"),  # Обратите внимание на name="cart_detail"
]