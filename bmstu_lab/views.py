from django.shortcuts import render
from django.conf import settings
from urllib.parse import urljoin

# Функция для генерации URL MinIO
def get_minio_url(filename):
    return urljoin(settings.MINIO_STATIC_URL, filename)

# Коллекция линз (без БД)
lenses = [
    {"id": 1, "name": "r+h EyeDrive ES 1.50 Nano S UV Plus линзы для вождения", "price": 23520,
     "description": "Сферические линзы для ожидания с защитой от ультрафиолета.",
     "image_url": get_minio_url("1.jpg")},
    {"id": 2, "name": "Tokai 1.60 Transitions 7 PGC фотохромные линзы", "price": 14280,
     "description": "Сферические традиционные (пластик).",
     "image_url": get_minio_url("2.jpg")},
    {"id": 3, "name": "Tokai Lutina 1.60 AS PGC P-UV очковые линзы", "price": 6980,
     "description": "Очковые линзы с высоким индексом преломления.",
     "image_url": get_minio_url("3.jpg")},
    {"id": 4, "name": "Tokai 1.50 E50 HMC очковые линзы", "price": 1260,
     "description": "Очистные линзы для повседневного использования.",
     "image_url": get_minio_url("4.jpg")},
    {"id": 5, "name": "Tokai 1.60 E60 HMC очковые линзы", "price": 1680,
     "description": "Очковые линзы с улучшенной защитой.",
     "image_url": get_minio_url("5.jpg")}
]

# Корзина (словарь с id товаров)
cart = {
    1: {"id": 1, "name": "r+h EyeDrive ES 1.50 Nano S UV Plus линзы для вождения", "price": 23520, "image_url": get_minio_url("1.jpg"), "comment": "Левая: -1.5, Правая: -2.0"},
    3: {"id": 3, "name": "Tokai Lutina 1.60 AS PGC P-UV очковые линзы", "price": 6980, "image_url": get_minio_url("3.jpg"), "comment": "Левая: -2.25, Правая: -2.5"},
}

def get_cart_total():
    return sum(item["price"] for item in cart.values())

def home(request):
    search_query = request.GET.get("search-lenses", "").strip().lower()

    filtered_lenses = lenses
    if search_query:
        filtered_lenses = [l for l in lenses if search_query in l["name"].lower() or search_query in str(l["price"])]

    return render(request, "lenses_list.html", {
        "lenses": filtered_lenses,
        "cart_count": len(cart),
        "total_price": get_cart_total(),
        "search_query": search_query,
        "LOGO_URL": settings.LOGO_URL
    })

def lenses_detail(request, lens_id):
    item = next((l for l in lenses if l["id"] == lens_id), None)
    return render(request, "lenses_detail.html", {
        "lens": item,
        "cart_count": len(cart),
        "total_price": get_cart_total(),
        "LOGO_URL": settings.LOGO_URL
    })

def cart_detail(request):
    customer_info = {
        "name": "Корнеев Андрей Иванович",
        "ready_date": "29.04.2025"
    }
    return render(request, "cart_detail.html", {
        "cart": cart,
        "cart_count": len(cart),
        "total_price": get_cart_total(),
        "customer_info": customer_info,
        "LOGO_URL": settings.LOGO_URL
    })