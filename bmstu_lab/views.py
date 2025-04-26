from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import connection
from .models import Lens, Request, RequestService, RequestStatus
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from datetime import timedelta
import json

# Главная страница — список линз с фильтром
@login_required
def home(request):
    search_query = request.GET.get("search-lenses", "").strip().lower()
    lenses = Lens.objects.filter(is_deleted=False)
    if search_query:
        lenses = lenses.filter(name__icontains=search_query)

    # Получение черновика заявки
    draft_request = Request.objects.filter(creator=request.user, status=RequestStatus.DRAFT).first()
    cart_count = RequestService.objects.filter(request=draft_request).count() if draft_request else 0
    total_price = sum(rs.lens.price for rs in RequestService.objects.filter(request=draft_request)) if draft_request else 0

    return render(request, "lenses_list.html", {
        "lenses": lenses,
        "cart_count": cart_count,
        "total_price": total_price,
        "search_query": search_query,
        "draft_request": draft_request,  # ⬅️ чтобы в шаблоне знать ID заявки
    })

# Детальная страница линзы
@login_required
def lenses_detail(request, lens_id):
    lens = get_object_or_404(Lens, pk=lens_id, is_deleted=False)
    return render(request, "lenses_detail.html", {
        "lens": lens
    })

# Добавление линзы в заявку (через ORM)
@login_required
def add_to_cart(request, lens_id):
    if request.method == "POST":
        lens = get_object_or_404(Lens, pk=lens_id, is_deleted=False)

        # Найти или создать заявку в статусе "draft"
        draft_request, created = Request.objects.get_or_create(
            creator=request.user,
            status=RequestStatus.DRAFT,
            defaults={
                'full_name': f"{request.user.last_name} {request.user.first_name}",
                'address': '',
            }
        )

        # Добавить линзу в заявку
        RequestService.objects.get_or_create(
            request=draft_request,
            lens=lens,
            defaults={"comment": ""}
        )

    return redirect("home")

# Просмотр заявки по id
@login_required
def request_detail(request, request_id):
    req = get_object_or_404(Request, id=request_id)

    # Проверка доступа: только свой заказ или модератор
    if req.creator != request.user and not request.user.is_staff:
        return redirect('home')

    items = RequestService.objects.filter(request=req)
    total_price = sum(item.lens.price for item in items)

    customer_info = {
        "name": req.full_name,
        "ready_date": req.submitted_at + timedelta(days=2) if req.submitted_at else None
    }

    return render(request, 'cart_detail.html', {
        'cart': req,
        'items': items,
        'cart_count': len(items),
        'total_price': total_price,
        'customer_info': customer_info
    })

# Логическое удаление заявки через SQL
@login_required
def delete_request_sql(request, request_id):
    if request.method == "POST":
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE bmstu_lab_request SET status = %s WHERE id = %s AND creator_id = %s",
                ['deleted', request_id, request.user.id]
            )
    return redirect("home")

# Обновление комментария к товару
@login_required
@csrf_exempt
def update_comment(request, item_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            comment = data.get('comment')
            item = RequestService.objects.get(id=item_id)
            item.comment = comment
            item.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
