from django.contrib import admin
from .models import Lens, Request, RequestService


@admin.register(Lens)
class LensAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "is_deleted")
    search_fields = ("name",)
    list_filter = ("is_deleted",)


class RequestServiceInline(admin.TabularInline):
    model = RequestService
    extra = 0
    can_delete = True
    fields = ("lens", "comment")


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ("id", "creator", "status", "created_at", "submitted_at", "completed_at", "moderator")
    list_filter = ("status", "created_at")
    search_fields = ('full_name', 'address', 'creator__username')
    inlines = [RequestServiceInline]


@admin.register(RequestService)
class RequestServiceAdmin(admin.ModelAdmin):
    list_display = ('request', 'lens', 'comment')
    search_fields = ("request__id", "lens__name")
