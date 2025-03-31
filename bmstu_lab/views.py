from django.shortcuts import render, redirect

# MinIO URL
MINIO_URL = "http://127.0.0.1:3010/opticbox-images"

# Коллекция линз (без БД)
lenses = [
    {"id": 1, "name": "r+h EyeDrive ES 1.50 Nano S UV Plus линзы для вождения", "price": 23520,
     "description": "Сферические линзы для ожидания с защитой от ультрафиолета.",
     "image_url": f"{MINIO_URL}/lens1.jpg"},
    {"id": 2, "name": "Tokai 1.60 Transitions 7 PGC фотохромные линзы", "price": 14280,
     "description": "Сферические традиционные (пластик).",
     "image_url": f"{MINIO_URL}/lens2.jpg"},
    {"id": 3, "name": "Tokai Lutina 1.60 AS PGC P-UV очковые линзы", "price": 6980,
     "description": "Очковые линзы с высоким индексом преломления.",
     "image_url": f"{MINIO_URL}/lens3.jpg"},
    {"id": 4, "name": "Tokai 1.50 E50 HMC очковые линзы", "price": 1260,
     "description": "Очистные линзы для повседневного использования.",
     "image_url": f"{MINIO_URL}/lens4.jpg"},
    {"id": 5, "name": "Tokai 1.60 E60 HMC очковые линзы", "price": 1680,
     "description": "Очковые линзы с улучшенной защитой.",
     "image_url": f"{MINIO_URL}/lens5.jpg"}
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
        "filter_by": filter_by
    })

def lenses_detail(request, lens_id):
    """Страница с подробной информацией о линзе"""
    item = next((l for l in lenses if l["id"] == lens_id), None)
    return render(request, "lenses_detail.html", {
        "lens": item,
        "cart_count": len(cart),
        "total_price": get_cart_total()
    })

def cart_detail(request):
    """Страница корзины"""
    return render(request, "cart_detail.html", {
        "cart": cart,
        "cart_count": len(cart),
        "total_price": get_cart_total()
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