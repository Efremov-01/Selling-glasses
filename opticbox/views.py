from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import Lens, Request, RequestService, RequestStatus
from .serializers import LensSerializer, RequestSerializer, RequestServiceSerializer, UserSerializer
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from opticbox.minio import upload_file_to_minio, delete_file_from_minio
import uuid
from django.contrib.auth import authenticate, login, logout
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


def get_current_user():
    return User.objects.get(username="acer")


# --------- ЛИНЗЫ (5 запросов) ----------
class LensListView(APIView):
    def get(self, request):
        lenses = Lens.objects.filter(is_deleted=False)
        user = get_current_user()
        draft = Request.objects.filter(creator=user, status=RequestStatus.DRAFT).first()

        serializer = LensSerializer(lenses, many=True)
        return Response({
            'draft_id': draft.id if draft else None,
            'items_in_draft': RequestService.objects.filter(request=draft).count() if draft else 0,
            'lenses': serializer.data
        })

    def post(self, request):
        serializer = LensSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LensDetailView(APIView):
    def get(self, request, pk):
        try:
            lens = Lens.objects.get(pk=pk, is_deleted=False)
            serializer = LensSerializer(lens)
            return Response(serializer.data)
        except Lens.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        try:
            lens = Lens.objects.get(pk=pk, is_deleted=False)
            serializer = LensSerializer(lens, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Lens.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        try:
            lens = Lens.objects.get(pk=pk, is_deleted=False)
            lens.is_deleted = True
            if lens.image_url:
                old_object_name = '/'.join(lens.image_url.split('/')[-2:])
                delete_file_from_minio(old_object_name)
                lens.image_url = None
            lens.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Lens.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class LensImageUploadView(APIView):
    def post(self, request, pk):
        try:
            lens = Lens.objects.get(pk=pk, is_deleted=False)
            file = request.FILES.get('image')
            if not file:
                return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)

            if lens.image_url:
                old_object_name = '/'.join(lens.image_url.split('/')[-2:])
                delete_file_from_minio(old_object_name)

            filename = f"{uuid.uuid4().hex}_{file.name}"
            object_name = f"lenses/{lens.id}/{filename}"
            minio_url = upload_file_to_minio(file, object_name)

            lens.image_url = minio_url
            lens.save()
            return Response({'status': 'image uploaded', 'url': minio_url})
        except Lens.DoesNotExist:
            return Response({"error": "Lens not found"}, status=status.HTTP_404_NOT_FOUND)


class LensAddToDraftView(APIView):
    def post(self, request, pk):
        try:
            lens = Lens.objects.get(pk=pk, is_deleted=False)
            user = get_current_user()
            draft, _ = Request.objects.get_or_create(
                creator=user,
                status=RequestStatus.DRAFT,
                defaults={'address': '', 'full_name': ''}
            )
            RequestService.objects.get_or_create(request=draft, lens=lens)
            return Response({'status': 'added to cart'})
        except Lens.DoesNotExist:
            return Response({"error": "Lens not found"}, status=status.HTTP_404_NOT_FOUND)


# --------- ЗАЯВКИ (7 запросов) ----------
class RequestListView(APIView):
    def get(self, request):
        user = get_current_user()
        queryset = Request.objects.exclude(status__in=[RequestStatus.DELETED, RequestStatus.DRAFT])

        if status_filter := request.query_params.get('status'):
            queryset = queryset.filter(status=status_filter)
        if date_from := request.query_params.get('date_from'):
            if date_to := request.query_params.get('date_to'):
                queryset = queryset.filter(submitted_at__range=[date_from, date_to])

        serializer = RequestSerializer(queryset, many=True)
        return Response(serializer.data)


class RequestDetailView(APIView):
    def get(self, request, pk):
        try:
            # Получаем заявку по pk
            req = Request.objects.get(pk=pk)

            # Получаем все услуги, связанные с этой заявкой
            services = RequestService.objects.filter(request=req)

            # Сериализуем заявку
            request_serializer = RequestSerializer(req)
            # Сериализуем услуги
            services_serializer = RequestServiceSerializer(services, many=True)

            # Возвращаем данные заявки и услуг
            return Response({
                'request': request_serializer.data,
                'services': services_serializer.data
            })

        except Request.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        try:
            req = Request.objects.get(pk=pk)
            data = {k: v for k, v in request.data.items() if
                    k not in ['status', 'creator', 'moderator', 'created_at', 'submitted_at', 'completed_at']}
            serializer = RequestSerializer(req, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Request.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        try:
            req = Request.objects.get(pk=pk)
            req.status = RequestStatus.DELETED
            req.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Request.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class RequestSubmitView(APIView):
    def put(self, request, pk):
        try:
            req = Request.objects.get(pk=pk, status=RequestStatus.DRAFT)
            if not req.address or not req.full_name:
                return Response({"error": "Fill required fields"}, status=status.HTTP_400_BAD_REQUEST)
            req.status = RequestStatus.FORMULATED
            req.submitted_at = timezone.now()
            req.save()
            return Response({'status': 'submitted'})
        except Request.DoesNotExist:
            return Response({"error": "Request not found"}, status=status.HTTP_404_NOT_FOUND)


class RequestCompleteView(APIView):
    """
    PUT /api/requests/{id}/complete/
    Требуемые поля:
    - action: "complete" или "decline"
    """

    def put(self, request, pk):
        # Получаем заявку по id
        req = get_object_or_404(Request, pk=pk, status=RequestStatus.FORMULATED)

        user = get_current_user()  # вместо request.user

        # Проверка на роль модератора
        if not user.is_staff:
            return Response(
                {"detail": "Только для модераторов"},
                status=status.HTTP_403_FORBIDDEN
            )

        action = request.data.get('action')

        if not action:
            return Response(
                {"detail": "Поле 'action' обязательно."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Обработка действия
        if action == 'complete':
            req.status = RequestStatus.COMPLETED
            req.moderator = user
            req.total_price = sum(
                service.lens.price
                for service in req.requestservice_set.all()
            )
        elif action == 'decline':
            req.status = RequestStatus.DECLINED
        else:
            return Response(
                {"detail": "Недопустимое действие (complete/decline)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Устанавливаем модератора и дату завершения
        req.moderator = request.user
        req.completed_at = timezone.now()
        req.save()

        # Возвращаем обновленную заявку
        return Response(RequestSerializer(req).data)


# --------- УСЛУГИ В ЗАЯВКАХ (3 запроса) ----------
class RequestServiceUpdateView(APIView):
    def put(self, request):
        try:
            service = RequestService.objects.get(
                request_id=request.data.get('request'),
                lens_id=request.data.get('lens')
            )
            if 'quantity' in request.data:
                service.quantity = request.data['quantity']
            if 'comment' in request.data:
                service.comment = request.data['comment']
            service.save()
            return Response({"status": "updated"})
        except RequestService.DoesNotExist:
            return Response({"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request):
        try:
            service = RequestService.objects.get(
                request_id=request.data.get('request'),
                lens_id=request.data.get('lens')
            )
            service.delete()
            return Response({"status": "removed"})
        except RequestService.DoesNotExist:
            return Response({"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND)


# --------- ПОЛЬЗОВАТЕЛИ ----------
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "User registered successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# PUT обновление профиля (личный кабинет)
@method_decorator(csrf_exempt, name='dispatch')
class ProfileUpdateView(APIView):
    permission_classes = [AllowAny]

    def put(self, request):
        user = get_current_user()
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profile updated successfully."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# POST аутентификация
@csrf_exempt
@permission_classes([AllowAny])
@api_view(["POST"])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return Response({"message": "Login successful"})
    else:
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

# POST деавторизация
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):
    logout(request)
    return Response({"message": "Logout successful"})