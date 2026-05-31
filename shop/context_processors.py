from .models import Basket


def basket_info(request):
    if request.user.is_authenticated:
        basket = Basket.objects.filter(customer=request.user).first()
        if basket:
            total_quantity = sum(item.quantity for item in basket.basket_items.all())
            return {'basket': basket, 'basket_total_quantity': total_quantity}
    return {'basket': None, 'basket_total_quantity': 0}


def notifications_info(request):
    if not request.user.is_authenticated:
        return {'unread_notifications_count': 0, 'recent_notifications': []}
    try:
        from .models import Notification
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        recent = Notification.objects.filter(
            user=request.user, is_read=False
        ).order_by('-created_at')[:5]
        return {'unread_notifications_count': unread_count, 'recent_notifications': recent}
    except Exception:
        # Таблица или поле ещё не созданы — миграция не применена
        return {'unread_notifications_count': 0, 'recent_notifications': []}
