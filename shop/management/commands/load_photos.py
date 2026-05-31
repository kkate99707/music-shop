"""
Автоматически скачивает фото для товаров без фотографий с Unsplash.
Использует поисковые запросы на основе названия и категории товара.

Запуск:
    python manage.py load_photos            # все товары без фото
    python manage.py load_photos --id 100  # конкретный товар
"""
import urllib.request
import urllib.parse
import json
import os
import time
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings
from shop.models import Product, Photo


# Ключевые слова для поиска по категориям
CATEGORY_KEYWORDS = {
    'Акустические гитары':   'acoustic guitar',
    'Электрогитары':         'electric guitar',
    'Бас-гитары':            'bass guitar',
    'Укулеле':               'ukulele',
    'Синтезаторы':           'synthesizer keyboard',
    'Цифровые пианино':      'digital piano',
    'MIDI-контроллеры':      'midi controller',
    'Акустические установки':'acoustic drum kit',
    'Электронные установки': 'electronic drum kit',
    'Перкуссия':             'percussion djembe',
    'Струны':                'guitar strings',
    'Медиаторы':             'guitar pick plectrum',
    'Чехлы и кейсы':         'guitar case bag',
    'Стойки и держатели':    'guitar stand',
    'Ремни':                 'guitar strap',
    'Каподастры и слайды':   'guitar capo tuner',
    'Уход за инструментами': 'guitar care maintenance',
    'Комбоусилители':        'guitar amplifier combo',
    'Педали эффектов':       'guitar effect pedal',
    'Наушники':              'studio headphones',
    'Домры и балалайки':     'balalaika folk instrument',
    'Дудки и свирели':       'flute recorder folk',
    'Народные':              'folk musical instrument',
    'Духовые':               'saxophone trumpet brass',
    'Студийное оборудование':'studio microphone audio',
    'Гитары':                'guitar',
    'Клавишные':             'piano keyboard',
    'Ударные':               'drums',
}


def get_unsplash_photo(query, product_id, api_key):
    """Скачивает фото с Unsplash по запросу."""
    url = (
        f'https://api.unsplash.com/photos/random'
        f'?query={urllib.parse.quote(query)}'
        f'&orientation=squarish'
        f'&content_filter=high'
    )
    req = urllib.request.Request(url, headers={
        'Authorization': f'Client-ID {api_key}',
        'Accept-Version': 'v1',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            img_url = data['urls']['regular']
            # Скачиваем само изображение
            with urllib.request.urlopen(img_url, timeout=30) as img_resp:
                return img_resp.read()
    except Exception as e:
        return None


def get_picsum_photo(product_id):
    """Fallback: скачивает фото с picsum.photos (без API ключа)."""
    seed = product_id * 7 + 13
    url = f'https://picsum.photos/seed/{seed}/600/600'
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read()
    except Exception:
        return None


class Command(BaseCommand):
    help = 'Загружает фото для товаров без фотографий'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, help='ID конкретного товара')
        parser.add_argument('--unsplash-key', type=str, default='',
                            help='API ключ Unsplash (опционально)')
        parser.add_argument('--overwrite', action='store_true',
                            help='Перезаписать существующие фото')

    def handle(self, *args, **options):
        product_id = options.get('id')
        api_key = options.get('unsplash_key') or getattr(settings, 'UNSPLASH_API_KEY', '')
        overwrite = options.get('overwrite', False)

        if product_id:
            products = Product.objects.filter(pk=product_id)
        elif overwrite:
            products = Product.objects.all()
        else:
            # Только товары без фото
            products = Product.objects.filter(photos__isnull=True).distinct()

        total = products.count()
        self.stdout.write(f'Товаров для обработки: {total}')

        for i, product in enumerate(products, 1):
            if overwrite:
                product.photos.all().delete()

            cat_name = product.category.name
            keyword = CATEGORY_KEYWORDS.get(cat_name)
            if not keyword:
                # Ищем по родительской категории
                parent = product.category.parent
                if parent:
                    keyword = CATEGORY_KEYWORDS.get(parent.name, 'musical instrument')
                else:
                    keyword = 'musical instrument'

            self.stdout.write(f'[{i}/{total}] {product.name} → "{keyword}"... ', ending='')

            # Пробуем Unsplash, потом picsum
            img_data = None
            if api_key:
                img_data = get_unsplash_photo(keyword, product.id, api_key)
                time.sleep(0.5)  # Unsplash rate limit

            if not img_data:
                img_data = get_picsum_photo(product.id)

            if img_data:
                fname = f'product_{product.id}.jpg'
                photo = Photo(product=product, is_main=True)
                photo.image.save(fname, ContentFile(img_data), save=True)
                self.stdout.write(self.style.SUCCESS('OK'))
            else:
                self.stdout.write(self.style.WARNING('ПРОПУЩЕН'))

            time.sleep(0.3)

        self.stdout.write(self.style.SUCCESS(f'\nГотово! Обработано: {total}'))
