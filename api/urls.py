from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('opticbox/', include('opticbox.urls')),  # Вот так мы подключаем api/
]