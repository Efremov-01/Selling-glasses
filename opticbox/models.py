from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.db import models
from django.conf import settings


class Lens(models.Model):
    name = models.CharField("Наименование", max_length=255)
    description = models.TextField("Описание")
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    is_deleted = models.BooleanField("Удалено", default=False)
    image_url = models.URLField("URL изображения", null=True, blank=True)

    def __str__(self):
        return self.name


class RequestStatus(models.TextChoices):
    DRAFT = 'draft', 'Черновик'
    DELETED = 'deleted', 'Удалена'
    FORMULATED = 'formulated', 'Сформирована'
    COMPLETED = 'completed', 'Завершена'
    DECLINED = 'declined', 'Отклонена'


class Request(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='requests')
    status = models.CharField("Статус", max_length=20, choices=RequestStatus.choices, default=RequestStatus.DRAFT)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    submitted_at = models.DateTimeField("Дата формирования", null=True, blank=True)
    completed_at = models.DateTimeField("Дата завершения", null=True, blank=True)
    moderator = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Модератор", on_delete=models.PROTECT, null=True, blank=True, related_name="moderated_requests")
    address = models.CharField("Адрес", max_length=255, blank=True)
    full_name = models.CharField("ФИО получателя", max_length=255, blank=True)

    def __str__(self):
        return f"Заявка #{self.id} от {self.creator.email}"


class RequestService(models.Model):
    request = models.ForeignKey(Request, on_delete=models.PROTECT, verbose_name="Заявка")
    lens = models.ForeignKey(Lens, on_delete=models.PROTECT, verbose_name="Линза")
    comment = models.TextField("Комментарий", null=True, blank=True)

    class Meta:
        unique_together = ('request', 'lens')

    def __str__(self):
        return f"{self.lens.name} в заявке #{self.request.id}"


class NewUserManager(UserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('User must have an email address')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self.db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(("email адрес"), unique=True)
    password = models.CharField(max_length=255, verbose_name="Пароль")
    is_staff = models.BooleanField(default=False, verbose_name="Является ли пользователь менеджером?")
    is_superuser = models.BooleanField(default=False, verbose_name="Является ли пользователь админом?")
    is_active = models.BooleanField(default=True, verbose_name="Активен?")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = NewUserManager()

    def __str__(self):
        return self.email
