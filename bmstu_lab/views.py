from django.shortcuts import render, redirect
from django.conf import settings
from urllib.parse import urljoin

# Функция для генерации URL MinIO
def get_minio_url(filename):
    """Генерирует полный URL к файлу в MinIO"""
    return urljoin(settings.MINIO_STATIC_URL, filename)

# Коллекция линз (без БД)
lenses = [
    {"id": 101, "name": "r+h EyeDrive ES 1.50 Nano S UV Plus линзы для вождения", "price": 23520,
     "description": "Сферические линзы для ожидания с защитой от ультрафиолета.",
     "image_url": get_minio_url("card1.jpg")},
    {"id": 102, "name": "Tokai 1.60 Transitions 7 PGC фотохромные линзы", "price": 14280,
     "description": "Сферические традиционные (пластик).",
     "image_url": get_minio_url("card2.jpg")},
    {"id": 103, "name": "Tokai Lutina 1.60 AS PGC P-UV очковые линзы", "price": 6980,
     "description": "Очковые линзы с высоким индексом преломления.",
     "image_url": get_minio_url("card3.jpg")},
    {"id": 104, "name": "Tokai 1.50 E50 HMC очковые линзы", "price": 1260,
     "description": "Очистные линзы для повседневного использования.",
     "image_url": get_minio_url("card4.jpg")},
    {"id": 105, "name": "Tokai 1.60 E60 HMC очковые линзы", "price": 1680,
     "description": "Очковые линзы с улучшенной защитой.",
     "image_url": get_minio_url("card5.jpg")}
]

# Корзина (словарь с id товаров)
cart = {}

def get_cart_total():
    """Возвращает общую стоимость корзины"""
    return sum(item["price"] for item in cart.values())

def home(request):
    """Главная страница с фильтрацией и корзиной"""
    search_query = request.GET.get("search", "").strip().lower()
    filter_by = request.GET.get("filter_by", "all")

    filtered_lenses = lenses
    if search_query:
        filtered_lenses = [l for l in lenses if
                         search_query in l["name"].lower() or search_query in str(l["price"])]

    if filter_by == "price":
        filtered_lenses = sorted(filtered_lenses, key=lambda x: x["price"])
    elif filter_by == "date":
        filtered_lenses = sorted(filtered_lenses, key=lambda x: x["date"])

    return render(request, "lenses_list.html", {
        "lenses": filtered_lenses,
        "cart_count": len(cart),
        "total_price": get_cart_total(),
        "search_query": search_query,
        "filter_by": filter_by,
        "LOGO_URL": settings.LOGO_URL
    })

def lenses_detail(request, lens_id):
    """Страница с подробной информацией о линзе"""
    item = next((l for l in lenses if l["id"] == lens_id), None)
    return render(request, "lenses_detail.html", {
        "lens": item,
        "cart_count": len(cart),
        "total_price": get_cart_total(),
        "LOGO_URL": settings.LOGO_URL
    })

def cart_detail(request):
    """Страница корзины"""
    return render(request, "cart_detail.html", {
        "cart": cart,
        "cart_count": len(cart),
        "total_price": get_cart_total(),
        "LOGO_URL": settings.LOGO_URL
    })

def add_to_cart(request, lens_id):
    """Добавление линзы в корзину через отдельный URL"""
    global cart
    if request.method == "POST":
        lens = next((l for l in lenses if l["id"] == lens_id), None)
        if lens:
            cart[lens_id] = lens  # Добавляем линзу в корзину

    # Возвращаем пользователя обратно на главную страницу
    return redirect("home")

def remove_from_cart(request, lens_id):
    """Удаление линзы из корзины"""
    global cart
    if lens_id in cart:
        del cart[lens_id]
    return redirect('cart_detail')