from django.contrib import admin
from django.urls import path
from bmstu_lab.views import (
    home,
    lenses_detail,
    add_to_cart,
    delete_request_sql,
    update_comment,
    request_detail
)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('lens/<int:lens_id>/', lenses_detail, name='lenses_detail'),
    path('cart/add/<int:lens_id>/', add_to_cart, name='add_to_cart'),
    path('request/delete/<int:request_id>/', delete_request_sql, name='delete_request_sql'),
    path('cart/comment/<int:item_id>/', update_comment, name='update_comment'),
    path('Glass_request/<int:request_id>/', request_detail, name='request_detail'),  # 👈 Новый путь для заявок
]
