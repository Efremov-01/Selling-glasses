from django.urls import path
from .views import (
    LensList, LensDetail, LensFilter, LensAddToCart, LensUploadImage,
    RequestList, RequestDetail, RequestSubmit, RequestComplete, RequestDecline,
    RequestServiceList, RequestServiceDetail, RequestServiceUpdateComment,
    RequestServiceRemove, RegisterView, ProfileUpdateView, login_view, logout_view
)

urlpatterns = [
    # Линзы
    path('lenses/', LensList.as_view(), name='lens-list'),
    path('lenses/<int:pk>/', LensDetail.as_view(), name='lens-detail'),
    path('lenses/filter/', LensFilter.as_view(), name='lens-filter'),
    path('lenses/<int:pk>/add-to-cart/', LensAddToCart.as_view(), name='lens-add-to-cart'),
    path('lenses/<int:pk>/upload-image/', LensUploadImage.as_view(), name='lens-upload-image'),

    # Заявки
    path('requests/', RequestList.as_view(), name='request-list'),
    path('requests/<int:pk>/', RequestDetail.as_view(), name='request-detail'),
    path('requests/<int:pk>/submit/', RequestSubmit.as_view(), name='request-submit'),
    path('requests/<int:pk>/complete/', RequestComplete.as_view(), name='request-complete'),
    path('requests/<int:pk>/decline/', RequestDecline.as_view(), name='request-decline'),

    # Услуги в заявках
    path('request-services/', RequestServiceList.as_view(), name='requestservice-list'),
    path('request-services/<int:pk>/', RequestServiceDetail.as_view(), name='requestservice-detail'),
    path('request-services/update-comment/', RequestServiceUpdateComment.as_view(), name='requestservice-update-comment'),
    path('request-services/remove/', RequestServiceRemove.as_view(), name='requestservice-remove'),

    # Пользователи
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileUpdateView.as_view(), name='profile'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
]