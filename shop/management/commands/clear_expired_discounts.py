from django.core.management.base import BaseCommand
from django.utils import timezone
from shop.models import Product, Discount


class Command(BaseCommand):
    help = 'Отвязывает истёкшие скидки от товаров и удаляет их'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        expired = Discount.objects.filter(end_date__lt=now)
        count = expired.count()
        expired.delete()
        self.stdout.write(f'Удалено истёкших скидок: {count}')
