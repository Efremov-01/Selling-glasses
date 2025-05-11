from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Lens, Request, RequestService

# Сериализатор Линзы
class LensSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lens
        fields = ['id', 'name', 'description', 'price', 'image_url']

# Сериализатор Заявки
class RequestSerializer(serializers.ModelSerializer):
    creator = serializers.StringRelatedField(read_only=True)  # только username создателя
    moderator = serializers.StringRelatedField(read_only=True)  # только username модератора

    class Meta:
        model = Request
        fields = [
            'id', 'creator', 'status',
            'created_at', 'submitted_at', 'completed_at',
            'moderator', 'address', 'full_name'
        ]
        read_only_fields = ['id', 'creator', 'status', 'created_at', 'moderator', 'submitted_at', 'completed_at']

# Сериализатор Услуги в Заявке
class RequestServiceSerializer(serializers.ModelSerializer):
    lens = LensSerializer(read_only=True)  # Линзу сразу отображать полностью
    lens_id = serializers.PrimaryKeyRelatedField(
        queryset=Lens.objects.all(),
        source='lens',
        write_only=True
    )

    class Meta:
        model = RequestService
        fields = ['id', 'request', 'lens', 'lens_id', 'comment']

# Сериализатор Пользователя
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'confirm_password']

    def validate(self, data):
        """
        Проверка на совпадение пароля и подтверждения пароля
        """
        if 'confirm_password' in data and data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        """
        Создание пользователя
        """
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        """
        Обновление профиля пользователя
        """
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance
