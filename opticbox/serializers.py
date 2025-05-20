from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Request, RequestService, Lens, CustomUser
from collections import OrderedDict

# Сериализатор для линзы
class LensSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lens
        fields = ['id', 'name', 'description', 'price', 'image_url']

        def get_fields(self):
            new_fields = OrderedDict()
            for name, field in super().get_fields().items():
                field.required = False
                new_fields[name] = field
            return new_fields

# Сериализатор для услуги в заявке
class RequestServiceSerializer(serializers.ModelSerializer):
    lens = LensSerializer(read_only=True)  # Линза будет полностью отображаться
    lens_id = serializers.PrimaryKeyRelatedField(queryset=Lens.objects.all(), source='lens', write_only=True)  # Линза через ID

    class Meta:
        model = RequestService
        fields = ['id', 'request', 'lens', 'lens_id', 'comment']

# Сериализатор для заявки с услугами
class RequestSerializer(serializers.ModelSerializer):
    creator = serializers.StringRelatedField(read_only=True)  # создатель заявки
    moderator = serializers.StringRelatedField(read_only=True)  # модератор
    services = RequestServiceSerializer(many=True, read_only=True)  # услуги в заявке

    class Meta:
        model = Request
        fields = [
            'id', 'creator', 'status', 'created_at', 'submitted_at', 'completed_at',
            'moderator', 'address', 'full_name', 'services'
        ]
        read_only_fields = ['id', 'creator', 'status', 'created_at', 'moderator', 'submitted_at', 'completed_at']


# Сериализатор Пользователя

class UserSerializer(serializers.ModelSerializer):
    is_staff = serializers.BooleanField(default=False, required=False)
    is_superuser = serializers.BooleanField(default=False, required=False)
    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'is_staff', 'is_superuser', 'is_active']