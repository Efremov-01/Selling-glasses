from django.db import models
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes, action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Lens, Request, RequestService, RequestStatus, CustomUser
from .permissions import IsAdmin, IsManager
from .serializers import LensSerializer, RequestSerializer, RequestServiceSerializer, UserSerializer
from opticbox.minio import upload_file_to_minio, delete_file_from_minio
from django.contrib.auth import authenticate, login, logout
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated
from django.views.decorators.csrf import csrf_exempt

from django.http import HttpResponse
import uuid
import redis
from django.conf import settings

# Connect to our Redis instance
session_storage = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)

# создаем инстанс и указываем координаты БД на локальной машине
r = redis.Redis(
    host= '127.0.0.1',
    port= '6379',
    password = 'redis',  # 🔐 обязательно указать
    decode_responses = True)

r.set('somekey', '1000-7') # сохраняем ключ 'somekey' с значением '1000-7!'
value = r.get('somekey') # получаем значение по ключу
print(value)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email', 'password'],
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING),
            'password': openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
    responses={200: 'Login successful', 401: 'Invalid credentials'}
)

@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])  # только если не используешь CSRF
def login_view(request):
    username = request.data["email"]
    password = request.data["password"]
    user = authenticate(request, email=username, password=password)
    if user is not None:
        random_key = uuid.uuid4()
        session_storage.set(str(random_key), username)

        response = HttpResponse("{'status': 'ok'}")
        response.set_cookie("session_id", str(random_key))

        return response
    else:
        return HttpResponse("{'status': 'error', 'error': 'login failed'}")


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    logout(request)
    return Response({'status': 'Success'})


class UserViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    model_class = CustomUser

    def create(self, request):
        if self.model_class.objects.filter(email=request.data['email']).exists():
            return Response({'status': 'Exist'}, status=400)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            self.model_class.objects.create_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                is_superuser=serializer.validated_data.get('is_superuser', False),
                is_staff=serializer.validated_data.get('is_staff', False)
            )
            return Response({'status': 'Success'}, status=201)
        return Response({'status': 'Error', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [AllowAny]
        elif self.action == 'list':
            permission_classes = [IsAdmin | IsManager]
        else:
            permission_classes = [IsAdmin]
        return [permission() for permission in permission_classes]


def method_permission_classes(classes):
    def decorator(func):
        def decorated_func(self, *args, **kwargs):
            self.permission_classes = classes
            self.check_permissions(self.request)
            return func(self, *args, **kwargs)
        return decorated_func
    return decorator


# --------- ЛИНЗЫ ----------
class LensListView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        lenses = Lens.objects.filter(is_deleted=False)
        user = request.user
        draft = Request.objects.filter(creator=user, status=RequestStatus.DRAFT).first()

        serializer = LensSerializer(lenses, many=True)
        return Response({
            'draft_id': draft.id if draft else None,
            'items_in_draft': RequestService.objects.filter(request=draft).count() if draft else 0,
            'lenses': serializer.data
        })

    @swagger_auto_schema(request_body=LensSerializer)
    def post(self, request):
        serializer = LensSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LensDetailView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        try:
            lens = Lens.objects.get(pk=pk, is_deleted=False)
            serializer = LensSerializer(lens)
            return Response(serializer.data)
        except Lens.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(request_body=LensSerializer)
    @method_permission_classes((IsAdmin,))
    def put(self, request, pk):
        try:
            lens = Lens.objects.get(pk=pk, is_deleted=False)
        except Lens.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = LensSerializer(lens, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            lens = Lens.objects.get(pk=pk, is_deleted=False)
            user = request.user
            draft, _ = Request.objects.get_or_create(
                creator=user,
                status=RequestStatus.DRAFT,
                defaults={'address': '', 'full_name': ''}
            )
            RequestService.objects.get_or_create(request=draft, lens=lens)
            return Response({'status': 'added to cart'})
        except Lens.DoesNotExist:
            return Response({"error": "Lens not found"}, status=status.HTTP_404_NOT_FOUND)


# --------- ЗАЯВКИ (6 запросов) ----------
class RequestListView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session_id = request.COOKIES.get('session_id')

        if not session_id or not session_storage.get(session_id):
            return Response({'error': 'Invalid session'}, status=401)

        user_email = session_storage.get(session_id).decode()
        try:
            user = CustomUser.objects.get(email=user_email)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=401)

        # Суперпользователь видит все заявки
        if user.is_superuser:
            queryset = Request.objects.all()
        # Менеджер видит все, кроме черновиков и удалённых
        elif user.is_staff:
            queryset = Request.objects.exclude(status__in=[RequestStatus.DELETED, RequestStatus.DRAFT])
        # Обычный пользователь — только свои заявки
        else:
            queryset = Request.objects.filter(creator=user).exclude(status__in=[RequestStatus.DELETED, RequestStatus.DRAFT])

        # Фильтрация по статусу
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Фильтрация по дате
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from and date_to:
            queryset = queryset.filter(submitted_at__date__range=[date_from, date_to])

        serializer = RequestSerializer(queryset, many=True)
        return Response(serializer.data)



class RequestDetailView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            # Получаем заявку по pk
            req = Request.objects.get(pk=pk)

            # 🔐 Проверка прав: если не модератор — можно смотреть только свои
            if not request.user.is_staff and req.creator != request.user:
                return Response({"error": "Нет доступа к этой заявке"}, status=status.HTTP_403_FORBIDDEN)

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
        except Request.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Только админ или создатель может редактировать
        if not (request.user.is_superuser or request.user == req.creator):
            return Response({"detail": "Нет прав на редактирование заявки"}, status=status.HTTP_403_FORBIDDEN)

        # Только черновик можно редактировать
        if req.status != RequestStatus.DRAFT:
            return Response(
                {"detail": "Можно редактировать только заявки со статусом черновик"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Исключаем запрещённые поля
        data = {
            k: v for k, v in request.data.items()
            if k not in ['status', 'creator', 'moderator', 'created_at', 'submitted_at', 'completed_at']
        }

        serializer = RequestSerializer(req, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            req = Request.objects.get(pk=pk)
            req.status = RequestStatus.DELETED
            req.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Request.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class RequestSubmitView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

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
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    """
    PUT /api/requests/{id}/complete/
    Требуемые поля:
    - action: "complete" или "decline"
    """

    def put(self, request, pk):
        # Получаем заявку по id
        req = get_object_or_404(Request, pk=pk, status=RequestStatus.FORMULATED)

        user = request.user

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


# --------- УСЛУГИ В ЗАЯВКАХ (2 запроса) ----------
class RequestServiceUpdateView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

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



