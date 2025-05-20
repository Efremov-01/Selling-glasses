from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LensListView, LensDetailView, LensImageUploadView, LensAddToDraftView,
    RequestListView, RequestDetailView, RequestSubmitView, RequestCompleteView,
    RequestServiceUpdateView, login_view, logout_view, UserViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    # Линзы
    path('lenses/', LensListView.as_view(), name='lens-list'),
    path('lenses/<int:pk>/', LensDetailView.as_view(), name='lens-detail'),
    path('lenses/<int:pk>/upload-image/', LensImageUploadView.as_view(), name='lens-upload-image'),
    path('lenses/<int:pk>/add-to-draft/', LensAddToDraftView.as_view(), name='lens-add-to-draft'),

    # Заявки
    path('requests/', RequestListView.as_view(), name='request-list'),
    path('requests/<int:pk>/', RequestDetailView.as_view(), name='request-detail'),
    path('requests/<int:pk>/submit/', RequestSubmitView.as_view(), name='request-submit'),
    path('requests/<int:pk>/complete/', RequestCompleteView.as_view(), name='request-complete'),

    # Услуги
    path('request-services/', RequestServiceUpdateView.as_view(), name='request-service-update'),

    # Аутентификация
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # ViewSet — пользователи
    path('', include(router.urls)),
]
