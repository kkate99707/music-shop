from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count, Sum, F
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash, logout as auth_logout
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.core.mail import EmailMessage, send_mail
from django.conf import settings
from django.utils import timezone
import random
import json

from .models import *
from .forms import *
from .models import Photo


# ── ДЕКОРАТОРЫ ──────────────────────────────────────────────────────────────

def role_required(*roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            employee = getattr(request.user, 'employee', None)
            if employee and employee.role in roles:
                return view_func(request, *args, **kwargs)
            return render(request, 'shop/403.html', status=403)
        wrapper.__name__ = view_func.__name__
        return wrapper
    return decorator


# ── АУТЕНТИФИКАЦИЯ ───────────────────────────────────────────────────────────

def send_verification_code(request):
    if request.method == 'POST':
        email_to = request.POST.get('email')
        if not email_to:
            return JsonResponse({'status': 'error', 'message': 'Email не указан'}, status=400)
        code = str(random.randint(100000, 999999))
        request.session['verification_code'] = code
        request.session['verification_email'] = email_to
        try:
            html_content = render_to_string('shop/email/verify_code.html', {'code': code})
            email = EmailMessage(
                subject='Ваш код подтверждения MUSIC.SHOP',
                body=html_content, from_email=settings.EMAIL_HOST_USER, to=[email_to],
            )
            email.content_subtype = "html"
            email.send(fail_silently=False)
        except Exception:
            send_mail('Код подтверждения', f'Ваш код: {code}',
                      settings.EMAIL_HOST_USER, [email_to], fail_silently=False)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Неверный запрос'}, status=400)


def verify_code(request):
    if request.method == 'POST':
        user_code = request.POST.get('code')
        session_code = request.session.get('verification_code')
        if user_code and user_code == session_code:
            request.session['email_verified'] = True
            request.session['email_verified_for_password'] = True
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Неверный код'}, status=400)


def register(request):
    if request.method == 'POST':
        u_form = UserForm(request.POST)
        p_form = ProfileForm(request.POST)
        if u_form.is_valid() and p_form.is_valid():
            if not request.session.get('email_verified'):
                messages.error(request, 'Подтвердите почту перед регистрацией!')
            else:
                user = u_form.save(commit=False)
                user.set_password(u_form.cleaned_data['password'])
                user.save()
                profile = p_form.save(commit=False)
                profile.user = user
                profile.save()
                request.session.pop('email_verified', None)
                messages.success(request, 'Аккаунт создан! Войдите в систему.')
                return redirect('login')
    else:
        u_form = UserForm()
        p_form = ProfileForm()
    return render(request, 'registration/register.html', {'u_form': u_form, 'p_form': p_form})


# ── КАТАЛОГ ──────────────────────────────────────────────────────────────────

def index(request):
    promotion_products = Product.objects.filter(is_active=True).annotate(
        num_discounts=Count('discounts')
    ).filter(num_discounts__gt=0)[:8]
    popular_products = Product.objects.filter(is_active=True, quantity__gt=0).order_by('-id')[:8]
    return render(request, 'shop/index.html', {
        'promotion_products': promotion_products, 'popular_products': popular_products
    })


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.filter(parent=None)
    products = Product.objects.filter(is_active=True)
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(category__name__icontains=query) | Q(description__icontains=query)
        ).distinct()
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(Q(category=category) | Q(category__parent=category))
    min_p = request.GET.get('min_price')
    max_p = request.GET.get('max_price')
    try:
        if min_p: products = products.filter(price__gte=float(min_p))
        if max_p: products = products.filter(price__lte=float(max_p))
    except ValueError:
        pass
    sort = request.GET.get('sort')
    sort_map = {'price_asc': 'price', 'price_desc': '-price', 'newest': '-id'}
    if sort in sort_map:
        products = products.order_by(sort_map[sort])
    return render(request, 'shop/product_list.html', {
        'category': category, 'categories': categories, 'products': products
    })


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # Показываем только одобренные отзывы (если поле существует), иначе все
    try:
        reviews = product.reviews.filter(is_approved=True).order_by('-created_at')
    except Exception:
        reviews = product.reviews.all().order_by('-created_at')

    can_leave_review = False
    user_already_reviewed = False
    if request.user.is_authenticated:
        can_leave_review = Order_Item.objects.filter(
            order__user=request.user, product=product, order__order_status='completed'
        ).exists()
        user_already_reviewed = Review.objects.filter(user=request.user, product=product).exists()

    if request.method == 'POST' and can_leave_review and not user_already_reviewed:
        form = ReviewForm(request.POST)
        if form.is_valid():
            Review.objects.create(
                user=request.user,
                product=product,
                rating=form.cleaned_data['rating'],
                text=form.cleaned_data.get('text', ''),
                is_approved=False,
            )
            messages.success(request, 'Отзыв отправлен на модерацию.')
            return redirect('shop:product_detail', pk=product.pk)
    else:
        form = ReviewForm()

    recommendations = Product.objects.filter(
        category=product.category
    ).exclude(id=product.id).order_by('?')[:3]

    return render(request, 'shop/product_detail.html', {
        'product': product, 'reviews': reviews, 'form': form,
        'can_leave_review': can_leave_review,
        'user_already_reviewed': user_already_reviewed,
        'recommendations': recommendations,
    })


def product_search_autocomplete(request):
    query = request.GET.get('q', '').strip()
    if len(query) > 1:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(category__name__icontains=query), is_active=True
        ).distinct()[:6]
        results = [{'name': p.name, 'category': p.category.name, 'url': f"/product/{p.id}/"} for p in products]
        return JsonResponse({'results': results})
    return JsonResponse({'results': []})


# ── КОРЗИНА ──────────────────────────────────────────────────────────────────

@login_required
def basket_detail(request):
    if _is_employee(request.user):
        return redirect('shop:index')
    basket = Basket.objects.filter(customer=request.user).first()
    # Уведомления о скидках (только если поле discount_notified существует)
    if basket:
        try:
            for item in basket.basket_items.select_related('product').all():
                if not item.discount_notified and item.product.get_discounted_price() is not None:
                    Notification.objects.create(
                        user=request.user,
                        title='Скидка на товар в корзине!',
                        message=f'На товар «{item.product.name}» появилась скидка. '
                                f'Новая цена: {item.product.get_discounted_price():.0f} BYN.',
                        notification_type='discount',
                    )
                    item.discount_notified = True
                    item.save(update_fields=['discount_notified'])
        except Exception:
            pass  # поле ещё не создано — пропускаем
    return render(request, 'shop/basket_detail.html', {'basket': basket})


@login_required
def add_to_basket(request, product_id):
    if _is_employee(request.user):
        return redirect('shop:product_detail', pk=product_id)
    product = get_object_or_404(Product, id=product_id)
    basket, _ = Basket.objects.get_or_create(customer=request.user)
    item, created = Basket_Item.objects.get_or_create(basket=basket, product=product)
    if not created:
        item.quantity += 1
        item.save()
    return redirect(request.META.get('HTTP_REFERER', 'shop:product_list'))


@login_required
def update_basket(request, item_id):
    item = get_object_or_404(Basket_Item, id=item_id, basket__customer=request.user)
    action = request.POST.get('action')
    if action == 'plus':
        item.quantity += 1
    elif action == 'minus' and item.quantity > 1:
        item.quantity -= 1
    item.save()
    return redirect('shop:basket_detail')


@login_required
def remove_from_basket(request, item_id):
    item = get_object_or_404(Basket_Item, id=item_id, basket__customer=request.user)
    item.delete()
    return redirect('shop:basket_detail')


# ── ЗАКАЗЫ ────────────────────────────────────────────────────────────────────

@login_required
def order_create(request):
    if _is_employee(request.user):
        return redirect('shop:index')
    basket = Basket.objects.filter(customer=request.user).first()
    if not basket or not basket.basket_items.exists():
        return redirect('shop:product_list')
    user_addresses = Address.objects.filter(user=request.user)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            address_id = request.POST.get('address_selection')
            if address_id:
                addr_obj = get_object_or_404(Address, id=address_id, user=request.user)
                final_address = f"{addr_obj.index}, {addr_obj.city}, {addr_obj.street}, {addr_obj.building}"
            else:
                final_address = form.cleaned_data.get('address', 'Адрес не указан')
            try:
                with transaction.atomic():
                    total_sum = sum(
                        item.product.price * item.quantity
                        for item in basket.basket_items.all()
                    )
                    new_order = Order.objects.create(
                        user=request.user,
                        address=final_address,
                        payment_method=form.cleaned_data['payment_method'],
                        payment_status='pending',
                        order_status='new',
                        total_price=total_sum,
                    )
                    for item in basket.basket_items.all():
                        Order_Item.objects.create(
                            order=new_order, product=item.product,
                            quantity=item.quantity, price_at_order=item.product.price,
                        )
                    basket.basket_items.all().delete()
                return redirect('shop:order_success', order_id=new_order.id)
            except Exception as e:
                messages.error(request, f"Ошибка при создании заказа: {e}")
    else:
        form = OrderCreateForm()
    return render(request, 'shop/order_create.html', {
        'basket': basket, 'user_addresses': user_addresses, 'form': form
    })


@login_required
def user_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    active_orders = orders.filter(
        order_status__in=['new', 'confirmed', 'assembling', 'ready', 'sent', 'delivered']
    )
    completed_orders = orders.filter(order_status__in=['completed', 'canceled', 'returned'])
    return render(request, 'shop/order_list.html', {
        'active_orders': active_orders, 'completed_orders': completed_orders
    })


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('order_items__product'),
        id=order_id, user=request.user
    )
    return render(request, 'shop/order_detail.html', {'order': order})


@login_required
def order_success(request, order_id):
    return render(request, 'shop/order_success.html', {'order_id': order_id})


@login_required
def order_ask_question(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == 'POST':
        messages.success(request, "Ваш вопрос отправлен поддержке.")
        return redirect('shop:order_detail', order_id=order.id)
    return render(request, 'shop/order_detail.html', {'order': order})


# ── ПРОФИЛЬ ───────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    user = request.user
    employee = getattr(user, 'employee', None)
    return render(request, 'shop/profile.html', {
        'user': user,
        'profile': getattr(user, 'profile', None),
        'employee': employee,
        'addresses': user.addresses.all() if not employee else None,
    })


@login_required
def profile_settings(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        if 'save_fio' in request.POST:
            profile.surname = request.POST.get('surname')
            profile.name = request.POST.get('name')
            profile.patronymic = request.POST.get('patronymic')
        elif 'save_phone' in request.POST:
            profile.phone = request.POST.get('phone')
        profile.save()
        return redirect('shop:profile_settings')
    return render(request, 'shop/profile_settings.html', {'profile': profile})


@login_required
def address_create(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return redirect('shop:profile')
    else:
        form = AddressForm()
    return render(request, 'shop/address_form.html', {'form': form})


@login_required
def address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.delete()
    return redirect('shop:profile')


@login_required
def password_change_settings(request):
    if request.method == 'POST':
        if not request.session.get('email_verified_for_password'):
            return JsonResponse({'status': 'error', 'message': 'Подтвердите почту'}, status=403)
        p1 = request.POST.get('password')
        p2 = request.POST.get('password_confirm')
        if p1 and p1 == p2:
            user = request.user
            user.set_password(p1)
            user.save()
            update_session_auth_hash(request, user)
            del request.session['email_verified_for_password']
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Ошибка данных'}, status=400)


@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        auth_logout(request)
        user.delete()
        return redirect('shop:index')
    return redirect('shop:profile_settings')


# ── УВЕДОМЛЕНИЯ ───────────────────────────────────────────────────────────────

@login_required
def notifications_page(request):
    try:
        notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    except Exception:
        notifs = []
    return render(request, 'shop/notifications.html', {'notifications': notifs})


@login_required
def mark_notification_read(request, notif_id):
    try:
        notif = get_object_or_404(Notification, id=notif_id, user=request.user)
        notif.is_read = True
        notif.save()
    except Exception:
        pass
    return JsonResponse({'status': 'ok'})


@login_required
def mark_all_notifications_read(request):
    try:
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    except Exception:
        pass
    return JsonResponse({'status': 'ok'})


# ── ИИ-ПОМОЩНИК ───────────────────────────────────────────────────────────────

@login_required
def ai_assistant(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)
    import urllib.request as urlreq

    body = json.loads(request.body)
    user_message = body.get('message', '').strip()
    history = body.get('history', [])
    if not user_message:
        return JsonResponse({'error': 'Пустое сообщение'}, status=400)

    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        return JsonResponse({'reply': 'ИИ-помощник временно недоступен — API-ключ не настроен.'})

    categories = list(Category.objects.values_list('name', flat=True))
    sample = Product.objects.filter(is_active=True).order_by('?')[:8]
    products_info = '\n'.join(
        f"- {p.name} ({p.category.name}), {p.price} BYN"
        + (f" → {p.get_discounted_price():.0f} BYN со скидкой" if p.get_discounted_price() else "")
        for p in sample
    )
    system_prompt = (
        "Ты — ИИ-помощник интернет-магазина музыкальных инструментов MUSIC.SHOP (Беларусь). "
        "Помогай подобрать инструмент: спрашивай жанр, уровень, бюджет. Отвечай кратко, по-русски.\n"
        f"Категории: {', '.join(categories)}.\nПримеры товаров:\n{products_info}"
    )

    gemini_contents = []
    for msg in history[-10:]:
        role = 'user' if msg['role'] == 'user' else 'model'
        gemini_contents.append({'role': role, 'parts': [{'text': msg['content']}]})
    gemini_contents.append({'role': 'user', 'parts': [{'text': user_message}]})

    payload = json.dumps({
        'system_instruction': {'parts': [{'text': system_prompt}]},
        'contents': gemini_contents,
        'generationConfig': {'maxOutputTokens': 600, 'temperature': 0.7},
    }).encode()

    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}'
    req = urlreq.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urlreq.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            reply = data['candidates'][0]['content']['parts'][0]['text']
            return JsonResponse({'reply': reply})
    except Exception:
        return JsonResponse({'reply': 'Ошибка при обращении к ИИ. Попробуйте позже.'})


# ── ПОДДЕРЖКА ─────────────────────────────────────────────────────────────────

@login_required
def ticket_list(request):
    tickets = Support_Ticket.objects.filter(user=request.user).order_by('-updated_at')
    return render(request, 'shop/ticket_list.html', {'tickets': tickets})


@login_required
def ticket_create(request):
    if request.method == 'POST':
        subject = request.POST.get('subject')
        text = request.POST.get('text', '').strip()
        if subject and text:
            ticket = Support_Ticket.objects.create(
                user=request.user, status='new', subject=subject
            )
            Support_Message.objects.create(sender=request.user, ticket=ticket, text=text)
            return redirect('shop:ticket_chat', ticket_id=ticket.id)
    return render(request, 'shop/ticket_create.html', {
        'categories': Support_Ticket.CATEGORY_CHOICES
    })


@login_required
def ticket_chat(request, ticket_id):
    ticket = get_object_or_404(Support_Ticket, id=ticket_id)
    employee = getattr(request.user, 'employee', None)
    if ticket.user != request.user and not employee:
        return render(request, 'shop/403.html', status=403)
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            Support_Message.objects.create(sender=request.user, ticket=ticket, text=text)
            if employee:
                ticket.status = 'in_progress'
                ticket.save()
        return redirect('shop:ticket_chat', ticket_id=ticket.id)
    return render(request, 'shop/ticket_chat.html', {
        'ticket': ticket, 'messages': ticket.messages.all()
    })


# ── МОДЕРАТОР ─────────────────────────────────────────────────────────────────

@role_required('moderator', 'admin')
def moderator_reviews(request):
    pending = Review.objects.filter(is_approved=False).select_related('user', 'product').order_by('-created_at')
    approved = Review.objects.filter(is_approved=True).select_related('user', 'product').order_by('-created_at')[:20]
    return render(request, 'shop/moderator_reviews.html', {'pending': pending, 'approved': approved})


@role_required('moderator', 'admin')
def moderator_approve_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.is_approved = True
    review.save()
    try:
        Notification.objects.create(
            user=review.user,
            title='Ваш отзыв опубликован',
            message=f'Отзыв на «{review.product.name}» прошёл модерацию.',
            notification_type='review_approved',
        )
    except Exception:
        pass
    messages.success(request, 'Отзыв одобрен.')
    return redirect('shop:moderator_reviews')


@role_required('moderator', 'admin')
def moderator_delete_review(request, review_id):
    get_object_or_404(Review, id=review_id).delete()
    messages.success(request, 'Отзыв удалён.')
    return redirect('shop:moderator_reviews')


@role_required('moderator', 'admin')
def moderator_support(request):
    tickets = Support_Ticket.objects.exclude(status='closed').select_related('user').order_by('-updated_at')
    return render(request, 'shop/moderator_support.html', {'tickets': tickets})


@role_required('moderator', 'admin')
def moderator_ticket(request, ticket_id):
    ticket = get_object_or_404(Support_Ticket, id=ticket_id)
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        new_status = request.POST.get('status')
        if text:
            Support_Message.objects.create(sender=request.user, ticket=ticket, text=text)
        if new_status and new_status in dict(Support_Ticket.STATUS):
            ticket.status = new_status
            ticket.save()
        return redirect('shop:moderator_ticket', ticket_id=ticket.id)
    return render(request, 'shop/moderator_ticket.html', {
        'ticket': ticket, 'messages': ticket.messages.all(), 'statuses': Support_Ticket.STATUS
    })


# ── КУРЬЕР ────────────────────────────────────────────────────────────────────

@role_required('courier')
def courier_tasks(request):
    employee = request.user.employee
    available = Order.objects.filter(
        courier__isnull=True, order_status__in=['new', 'ready', 'confirmed', 'assembling']
    ).order_by('-created_at')
    my_orders = Order.objects.filter(courier=employee).exclude(
        order_status__in=['delivered', 'completed', 'canceled', 'returned']
    ).order_by('-created_at')
    return render(request, 'shop/courier_tasks.html', {
        'available': available, 'my_orders': my_orders
    })


@role_required('courier')
def courier_take_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, courier__isnull=True)
    order.courier = request.user.employee
    order.save()
    messages.success(request, f'Заказ №{order.id} принят.')
    return redirect('shop:courier_tasks')


@role_required('courier')
def courier_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, courier=request.user.employee)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['sent', 'delivered', 'completed']:
            order.order_status = new_status
            order.save()
            messages.success(request, 'Статус обновлён.')
        return redirect('shop:courier_order_detail', order_id=order.id)
    return render(request, 'shop/courier_order.html', {'order': order})


# ── АДМИНИСТРАТОР ─────────────────────────────────────────────────────────────

@role_required('admin')
def admin_dashboard(request):
    from django.db.models.functions import TruncDate
    from datetime import timedelta

    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(
        order_status__in=['completed', 'delivered']
    ).aggregate(s=Sum('total_price'))['s'] or 0
    total_users = User.objects.filter(employee__isnull=True).count()
    total_products = Product.objects.filter(is_active=True).count()

    today = timezone.now().date()
    days_30 = today - timedelta(days=29)
    orders_by_day = (
        Order.objects.filter(created_at__date__gte=days_30)
        .annotate(day=TruncDate('created_at'))
        .values('day').annotate(count=Count('id'), revenue=Sum('total_price'))
        .order_by('day')
    )
    chart_labels, chart_orders, chart_revenue = [], [], []
    day_map = {row['day']: row for row in orders_by_day}
    for i in range(30):
        d = days_30 + timedelta(days=i)
        chart_labels.append(d.strftime('%d.%m'))
        row = day_map.get(d, {})
        chart_orders.append(row.get('count', 0))
        chart_revenue.append(float(row.get('revenue') or 0))

    top_products = (
        Order_Item.objects.values('product__name')
        .annotate(total_qty=Sum('quantity')).order_by('-total_qty')[:5]
    )
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]

    return render(request, 'shop/admin_dashboard.html', {
        'total_orders': total_orders, 'total_revenue': total_revenue,
        'total_users': total_users, 'total_products': total_products,
        'chart_labels': json.dumps(chart_labels),
        'chart_orders': json.dumps(chart_orders),
        'chart_revenue': json.dumps(chart_revenue),
        'top_products': top_products, 'recent_orders': recent_orders,
    })


@role_required('admin')
def admin_users(request):
    query = request.GET.get('q', '')
    users = User.objects.filter(employee__isnull=True).select_related('profile')
    if query:
        users = users.filter(
            Q(username__icontains=query) | Q(email__icontains=query) |
            Q(profile__surname__icontains=query) | Q(profile__name__icontains=query)
        )
    employees = User.objects.filter(employee__isnull=False).select_related('profile', 'employee')
    return render(request, 'shop/admin_users.html', {
        'users': users, 'employees': employees, 'query': query
    })


@role_required('admin')
def admin_toggle_block(request, user_id):
    target = get_object_or_404(User, id=user_id)
    profile = getattr(target, 'profile', None)
    if profile:
        try:
            profile.is_blocked = not profile.is_blocked
            profile.save()
        except Exception:
            pass
        target.is_active = not target.is_active
        target.save()
        action = 'заблокирован' if not target.is_active else 'разблокирован'
        messages.success(request, f'Пользователь {target.username} {action}.')
    return redirect('shop:admin_users')


@role_required('admin')
def admin_change_role(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role == 'client':
            Employee.objects.filter(user=target).delete()
        elif new_role in ['moderator', 'courier', 'admin']:
            emp, _ = Employee.objects.get_or_create(user=target)
            emp.role = new_role
            emp.save()
        messages.success(request, f'Роль {target.username} изменена.')
    return redirect('shop:admin_users')


# ── УПРАВЛЕНИЕ ТОВАРАМИ (АДМИН) ───────────────────────────────────────────────

def _is_employee(user):
    return hasattr(user, 'employee')


@role_required('admin')
def admin_product_list(request):
    query = request.GET.get('q', '')
    products = Product.objects.select_related('category').order_by('-id')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(category__name__icontains=query))
    return render(request, 'shop/admin_product_list.html', {
        'products': products, 'query': query
    })


@role_required('admin')
def admin_product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        photo_form = PhotoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            if request.FILES.get('image'):
                Photo.objects.create(
                    product=product,
                    image=request.FILES['image'],
                    is_main=True,
                )
            messages.success(request, f'Товар «{product.name}» создан.')
            return redirect('shop:admin_product_edit', pk=product.pk)
    else:
        form = ProductForm()
        photo_form = PhotoUploadForm()
    return render(request, 'shop/admin_product_form.html', {
        'form': form, 'photo_form': photo_form, 'title': 'Новый товар'
    })


@role_required('admin')
def admin_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        if 'delete_photo' in request.POST:
            Photo.objects.filter(pk=request.POST['delete_photo'], product=product).delete()
            return redirect('shop:admin_product_edit', pk=pk)
        if 'add_photo' in request.POST:
            if request.FILES.get('image'):
                is_main = not product.photos.filter(is_main=True).exists()
                Photo.objects.create(product=product, image=request.FILES['image'], is_main=is_main)
            return redirect('shop:admin_product_edit', pk=pk)
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Товар обновлён.')
            return redirect('shop:admin_product_edit', pk=pk)
    else:
        form = ProductForm(instance=product)
    photo_form = PhotoUploadForm()
    return render(request, 'shop/admin_product_form.html', {
        'form': form, 'photo_form': photo_form,
        'product': product, 'title': f'Редактировать: {product.name}'
    })


@role_required('admin')
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'Товар «{name}» удалён.')
        return redirect('shop:admin_product_list')
    return render(request, 'shop/admin_product_confirm_delete.html', {'product': product})


# ── УПРАВЛЕНИЕ СКИДКАМИ (АДМИН) ───────────────────────────────────────────────

@role_required('admin')
def admin_discount_list(request):
    from django.utils import timezone
    now = timezone.now()
    discounts = Discount.objects.prefetch_related('products').order_by('-end_date')
    return render(request, 'shop/admin_discount_list.html', {
        'discounts': discounts, 'now': now
    })


@role_required('admin')
def admin_discount_create(request):
    if request.method == 'POST':
        form = DiscountForm(request.POST)
        if form.is_valid():
            discount = form.save()
            # Применяем к выбранным товарам
            product_ids = request.POST.getlist('products')
            if product_ids:
                discount.products.set(product_ids)
            messages.success(request, 'Скидка создана.')
            return redirect('shop:admin_discount_list')
    else:
        form = DiscountForm()
    products = Product.objects.filter(is_active=True).order_by('category__name', 'name')
    return render(request, 'shop/admin_discount_form.html', {
        'form': form, 'products': products, 'title': 'Новая скидка'
    })


@role_required('admin')
def admin_discount_edit(request, pk):
    discount = get_object_or_404(Discount, pk=pk)
    if request.method == 'POST':
        form = DiscountForm(request.POST, instance=discount)
        if form.is_valid():
            form.save()
            product_ids = request.POST.getlist('products')
            discount.products.set(product_ids)
            messages.success(request, 'Скидка обновлена.')
            return redirect('shop:admin_discount_list')
    else:
        form = DiscountForm(instance=discount)
    products = Product.objects.filter(is_active=True).order_by('category__name', 'name')
    selected = list(discount.products.values_list('id', flat=True))
    return render(request, 'shop/admin_discount_form.html', {
        'form': form, 'products': products, 'selected': selected,
        'discount': discount, 'title': 'Редактировать скидку'
    })


@role_required('admin')
def admin_discount_delete(request, pk):
    discount = get_object_or_404(Discount, pk=pk)
    if request.method == 'POST':
        discount.delete()
        messages.success(request, 'Скидка удалена.')
    return redirect('shop:admin_discount_list')
