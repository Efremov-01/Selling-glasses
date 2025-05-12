from django.urls import path
from .views import (
    LensListView, LensDetailView, LensImageUploadView, LensAddToDraftView,
    RequestListView, RequestDetailView, RequestSubmitView, RequestCompleteView,
    RequestServiceUpdateView, RegisterView, ProfileUpdateView, login_view, logout_view
)

urlpatterns = [
    path('lenses/', LensListView.as_view(), name='lens-list'),
    path('lenses/<int:pk>/', LensDetailView.as_view(), name='lens-detail'),
    path('lenses/<int:pk>/upload-image/', LensImageUploadView.as_view(), name='lens-upload-image'),
    path('lenses/<int:pk>/add-to-draft/', LensAddToDraftView.as_view(), name='lens-add-to-draft'),

    path('requests/', RequestListView.as_view(), name='request-list'),
    path('requests/<int:pk>/', RequestDetailView.as_view(), name='request-detail'),
    path('requests/<int:pk>/submit/', RequestSubmitView.as_view(), name='request-submit'),
    path('requests/<int:pk>/complete/', RequestCompleteView.as_view(), name='request-complete'),

    path('request-services/', RequestServiceUpdateView.as_view(), name='request-service-update'),

    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileUpdateView.as_view(), name='profile'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
]
