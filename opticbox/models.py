from django.db import models
from django.contrib.auth.models import User


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
    creator = models.ForeignKey(User, verbose_name="Создатель", on_delete=models.PROTECT, related_name="requests")
    status = models.CharField("Статус", max_length=20, choices=RequestStatus.choices, default=RequestStatus.DRAFT)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    submitted_at = models.DateTimeField("Дата формирования", null=True, blank=True)
    completed_at = models.DateTimeField("Дата завершения", null=True, blank=True)
    moderator = models.ForeignKey(User, verbose_name="Модератор", on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="moderated_requests")

    # Новые поля:
    address = models.CharField("Адрес", max_length=255, blank=True)
    full_name = models.CharField("ФИО получателя", max_length=255, blank=True)

    def __str__(self):
        return f"Заявка #{self.id} от {self.creator.username}"


class RequestService(models.Model):
    request = models.ForeignKey(Request, on_delete=models.PROTECT, verbose_name="Заявка")
    lens = models.ForeignKey(Lens, on_delete=models.PROTECT, verbose_name="Линза")
    comment = models.TextField("Комментарий", null=True, blank=True)  # Оставляем только комментарий

    class Meta:
        unique_together = ('request', 'lens')

    def __str__(self):
        return f"{self.lens.name} в заявке #{self.request.id}"
