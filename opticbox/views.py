from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import Lens, Request, RequestService, RequestStatus
from .serializers import LensSerializer, RequestSerializer, RequestServiceSerializer, UserSerializer
from django.contrib.auth.models import User
from opticbox.minio import upload_file_to_minio, delete_file_from_minio
import uuid
from django.contrib.auth import authenticate, login, logout
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

def get_current_user():
    return User.objects.get(id=1)


# --------- ЛИНЗЫ ----------
class LensList(APIView):
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


class LensDetail(APIView):
    def get_object(self, pk):
        try:
            return Lens.objects.get(pk=pk, is_deleted=False)
        except Lens.DoesNotExist:
            return None

    def get(self, request, pk):
        lens = self.get_object(pk)
        if not lens:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = LensSerializer(lens)
        return Response(serializer.data)

    def put(self, request, pk):
        lens = self.get_object(pk)
        if not lens:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = LensSerializer(lens, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        lens = self.get_object(pk)
        if not lens:
            return Response(status=status.HTTP_404_NOT_FOUND)
        lens.is_deleted = True
        lens.image_url = None
        lens.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LensFilter(APIView):
    def get(self, request):
        name = request.query_params.get('name')
        queryset = Lens.objects.filter(is_deleted=False)
        if name:
            queryset = queryset.filter(name__icontains=name)
        serializer = LensSerializer(queryset, many=True)
        return Response(serializer.data)


class LensAddToCart(APIView):
    def post(self, request, pk):
        try:
            lens = Lens.objects.get(pk=pk, is_deleted=False)
        except Lens.DoesNotExist:
            return Response({"error": "Lens not found"}, status=status.HTTP_404_NOT_FOUND)

        user = get_current_user()
        draft, created = Request.objects.get_or_create(
            creator=user,
            status=RequestStatus.DRAFT,
            defaults={'address': '', 'full_name': ''}
        )
        RequestService.objects.get_or_create(request=draft, lens=lens)
        return Response({'status': 'added to cart'})


class LensUploadImage(APIView):
    def post(self, request, pk):
        try:
            lens = Lens.objects.get(pk=pk, is_deleted=False)
        except Lens.DoesNotExist:
            return Response({"error": "Lens not found"}, status=status.HTTP_404_NOT_FOUND)

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


# --------- ЗАЯВКИ ----------
class RequestList(APIView):
    def get(self, request):
        user = get_current_user()
        queryset = Request.objects.exclude(status=RequestStatus.DELETED).filter(creator=user)

        status_filter = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if date_from and date_to:
            queryset = queryset.filter(submitted_at__range=[date_from, date_to])

        serializer = RequestSerializer(queryset, many=True)
        return Response(serializer.data)


class RequestDetail(APIView):
    def get_object(self, pk):
        try:
            return Request.objects.get(pk=pk)
        except Request.DoesNotExist:
            return None

    def get(self, request, pk):
        req = self.get_object(pk)
        if not req:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = RequestSerializer(req)
        return Response(serializer.data)

    def put(self, request, pk):
        req = self.get_object(pk)
        if not req:
            return Response(status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        for field in ['status', 'creator', 'moderator', 'created_at', 'submitted_at', 'completed_at']:
            data.pop(field, None)

        serializer = RequestSerializer(req, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        req = self.get_object(pk)
        if not req:
            return Response(status=status.HTTP_404_NOT_FOUND)
        req.status = RequestStatus.DELETED
        req.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RequestSubmit(APIView):
    def put(self, request, pk):
        try:
            req = Request.objects.get(pk=pk)
        except Request.DoesNotExist:
            return Response({"error": "Request not found"}, status=status.HTTP_404_NOT_FOUND)

        if req.status != RequestStatus.DRAFT:
            return Response({"error": "Only draft can be submitted"}, status=status.HTTP_400_BAD_REQUEST)

        if not req.address or not req.full_name:
            return Response({"error": "Fill required fields"}, status=status.HTTP_400_BAD_REQUEST)

        req.status = RequestStatus.FORMULATED
        req.submitted_at = timezone.now()
        req.save()
        return Response({'status': 'submitted'})


class RequestComplete(APIView):
    def put(self, request, pk):
        try:
            req = Request.objects.get(pk=pk)
        except Request.DoesNotExist:
            return Response({"error": "Request not found"}, status=status.HTTP_404_NOT_FOUND)

        if req.status != RequestStatus.FORMULATED:
            return Response({"error": "Only formulated can be completed"}, status=status.HTTP_400_BAD_REQUEST)

        req.status = RequestStatus.COMPLETED
        req.completed_at = timezone.now()
        req.moderator = get_current_user()
        req.save()

        total_price = sum([s.lens.price for s in req.requestservice_set.all()])
        return Response({'status': 'completed', 'total_price': total_price})


class RequestDecline(APIView):
    def put(self, request, pk):
        try:
            req = Request.objects.get(pk=pk)
        except Request.DoesNotExist:
            return Response({"error": "Request not found"}, status=status.HTTP_404_NOT_FOUND)

        if req.status != RequestStatus.FORMULATED:
            return Response({"error": "Only formulated can be declined"}, status=status.HTTP_400_BAD_REQUEST)

        req.status = RequestStatus.DECLINED
        req.completed_at = timezone.now()
        req.moderator = get_current_user()
        req.save()
        return Response({'status': 'declined'})


# --------- УСЛУГИ В ЗАЯВКАХ ----------
class RequestServiceList(APIView):
    def get(self, request):
        user = get_current_user()
        services = RequestService.objects.filter(request__creator=user)

        request_id = request.query_params.get('request_id')
        if request_id:
            services = services.filter(request_id=request_id)

        serializer = RequestServiceSerializer(services, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = RequestServiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RequestServiceDetail(APIView):
    def get_object(self, pk):
        try:
            return RequestService.objects.get(pk=pk)
        except RequestService.DoesNotExist:
            return None

    def get(self, request, pk):
        service = self.get_object(pk)
        if not service:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = RequestServiceSerializer(service)
        return Response(serializer.data)

    def put(self, request, pk):
        service = self.get_object(pk)
        if not service:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = RequestServiceSerializer(service, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        service = self.get_object(pk)
        if not service:
            return Response(status=status.HTTP_404_NOT_FOUND)
        service.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RequestServiceUpdateComment(APIView):
    def put(self, request):
        req_id = request.data.get('request')
        lens_id = request.data.get('lens')
        comment = request.data.get('comment')

        try:
            service = RequestService.objects.get(request_id=req_id, lens_id=lens_id)
        except RequestService.DoesNotExist:
            return Response({"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

        service.comment = comment
        service.save()
        return Response({"status": "comment updated"})


class RequestServiceRemove(APIView):
    def delete(self, request):
        req_id = request.data.get('request')
        lens_id = request.data.get('lens')

        try:
            service = RequestService.objects.get(request_id=req_id, lens_id=lens_id)
            service.delete()
            return Response({"status": "service removed"})
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