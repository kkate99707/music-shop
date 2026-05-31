from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
import datetime
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Avg

def current_year():
    return datetime.datetime.now().year


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    slug = models.SlugField(max_length=100, unique=True, null=True, verbose_name='URL-адрес')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родительская категория'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name='Категория'
        verbose_name_plural='Категории'

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('shop:product_list_by_category', args=[self.slug])
    



class Discount(models.Model):

    PERCENT = 'percent'
    FIXED = 'fixed'

    DISCOUNT_TYPE_CHOICES = [
        (PERCENT, 'Процент'),
        (FIXED, 'Фиксированная сумма'),
    ]

    type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, verbose_name='Тип')

    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Величина')

    start_date = models.DateTimeField(verbose_name='Начальная дата')
    end_date = models.DateTimeField(verbose_name='Конечная дата')

    description = models.TextField(blank=True,verbose_name='Описание')

    def __str__(self):
        return f"{self.type} {self.amount}"

    class Meta:
        verbose_name = 'Скидка'
        verbose_name_plural = 'Скидки'


class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    quantity = models.PositiveIntegerField(default=0, verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Стоимость')
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Категория'
    )
    year_manufacture = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1800),
            MaxValueValidator(current_year)
        ],
        null=True,
        blank=True, 
        verbose_name='Год выпуска'
    )
    discounts = models.ManyToManyField(
        Discount,
        related_name='products',
        blank=True,
        verbose_name='Скидки'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')


    def __str__(self):
        return self.name

    class Meta:
        verbose_name='Товар'
        verbose_name_plural='Товары'
    def get_discounted_price(self):
        from django.utils import timezone
        now = timezone.now()
        active_discounts = self.discounts.filter(start_date__lte=now, end_date__gte=now)
        if not active_discounts.exists():
            return None
        total_price = self.price
        for discount in active_discounts:
            if discount.type == 'percent':
                total_price -= (total_price * (discount.amount / 100))
            elif discount.type == 'fixed':
                total_price -= discount.amount
        return max(total_price, 0)

    def get_sale_end_date(self):
        from django.utils import timezone
        now = timezone.now()
        d = self.discounts.filter(start_date__lte=now, end_date__gte=now).order_by('end_date').first()
        return d.end_date if d else None

    def get_average_rating(self):
        from django.db.models import Avg
        try:
            avg = self.reviews.filter(is_approved=True).aggregate(Avg('rating'))['rating__avg']
        except Exception:
            avg = self.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0

    def get_reviews_count(self):
        try:
            return self.reviews.filter(is_approved=True).count()
        except Exception:
            return self.reviews.count()

class Photo(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name='Товар'
    )

    image = models.ImageField(upload_to='media/products/', verbose_name='Путь к файлу')

    is_main = models.BooleanField(default=False, verbose_name='Главная')

    def __str__(self):
        return self.image.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product'],
                condition=models.Q(is_main=True),
                name='unique_main_photo_per_product'
            )
        ]
        ordering = ['id']
        verbose_name = 'Фото'
        verbose_name_plural='Фото'


class Profile(models.Model):
    male = 'm'
    female = 'f'
    GENDERS = [
        (male, 'Мужской'),
        (female, 'Женский')
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name='Пользователь')
    surname = models.CharField(max_length=255, verbose_name='Фамилия')
    name = models.CharField(max_length=255, verbose_name='Имя')
    patronymic = models.CharField(max_length=255, null=True, blank=True, verbose_name='Отчество')
    birth_date = models.DateField(verbose_name='Дата рождения')
    gender = models.CharField(max_length=6, choices=GENDERS, verbose_name='Пол')
    phone = models.CharField(max_length = 22, unique = True, verbose_name='Номер телефона')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Дата создания')

    def __str__(self):
        return f'{self.surname} {self.name}'

    class Meta:
        verbose_name='Профиль'
        verbose_name_plural='Профили'

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee', verbose_name='Пользователь')
    ROLES = [
        ('moderator', 'Модератор'),
        ('courier', 'Курьер'), 
        ('admin', 'Администратор')
    ]
    role = models.CharField(max_length=20, choices=ROLES, verbose_name='Должность')

    def __str__(self):
        return f'{self.user.profile.surname} {self.user.profile.name} - {self.role}'

    class Meta:
        verbose_name='Сотрудник'
        verbose_name_plural='Сотрудники'


class Basket(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='baskets', verbose_name='Пользователь')

    class Meta:
        verbose_name='Корзина'
        verbose_name_plural='Корзины'

    def get_total_quantity(self):
        return sum(item.quantity for item in self.basket_items.all())

    def get_total_cost(self):
        return sum(item.get_total_price() for item in self.basket_items.all())
    

class Basket_Item(models.Model):
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='basket_items', verbose_name='Товар')
    basket = models.ForeignKey(Basket, on_delete=models.CASCADE, related_name='basket_items', verbose_name='Корзина')

    class Meta:
        verbose_name='Строка корзины'
        verbose_name_plural='Строки корзины'
    
    def get_total_price(self):
        return self.product.price * self.quantity
    

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь', related_name='notifications')
    title = models.CharField(max_length=255, verbose_name='Заголовок')
    message = models.TextField(verbose_name='Уведомление')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    def __str__(self):
        return f'{self.user.profile.surname} {self.user.profile.name}: уведомление "{self.title}"'

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'

class Address(models.Model):
    REGIONS = [
        ('Brest', 'Брестская'),
        ('Vitebsk', 'Витебская'),
        ('Gomel', 'Гомельская'),
        ('Grogno', 'Гродненская'),
        ('Minsk', 'Минская'),
        ('Mogilev', 'Могилёвская')
    ]
    SityStreetRegex = RegexValidator(regex = r"^[А-Яа-яЁё\s\-\.]{2,100}$")

    index = models.PositiveIntegerField(validators=[MinValueValidator(100000),MaxValueValidator(999999)],verbose_name='Индекс')
    region = models.CharField(max_length=15,choices=REGIONS, verbose_name='Область')
    district = models.CharField(max_length=100, verbose_name='Район')
    city = models.CharField(validators=[SityStreetRegex], max_length=255, verbose_name='Населённый пункт')
    street = models.CharField(validators=[SityStreetRegex], max_length=255, verbose_name='Улица')
    building = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name='Дом')
    housing = models.CharField(max_length=5, null=True, blank=True, verbose_name='Корпус')
    apartment = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(1000)], null=True, verbose_name='Квартира/Офис')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses', verbose_name='Пользователь')

    def __str__(self):
        return f'Ардекс с индексом {self.index} клиента {self.user.profile.last_name} {self.user.profile.name}'

    class Meta:
        verbose_name='Адрес'
        verbose_name_plural='Адреса'

def get_sentinel_user():
    return User.objects.get_or_create(username='deleted')[0]

class Order(models.Model):

    P_STATUS = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачено'),
        ('failed', 'Ошибка оплаты'),
        ('refunded', 'Возврат средств')
    ]

    P_METHOD = [
        ('card_online', 'Картой онлайн'),
        ('cash_on_delivery', 'Наличными при получении'),
        ('card_on_delivery', 'Картой при получении')
    ]

    O_STATUS = [
        ('new', 'Новый'),
        ('confirmed', 'Подтверждён'),
        ('assembling', 'Сборка / Настройка'),
        ('ready', 'Готов к отправке'),
        ('sent', 'В доставке'),
        ('delivered', 'Доставлен'),
        ('completed', 'Завершён'),
        ('canceled', 'Отменён'),
        ('returned', 'Возврат')
    ]


    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True, 
        default=get_sentinel_user, 
        verbose_name='Пользователь')
    payment_status = models.CharField(max_length=20, choices=P_STATUS, verbose_name='Статус оплаты')
    payment_method = models.CharField(max_length=30, choices=P_METHOD, verbose_name='Способ оплаты')
    order_status = models.CharField(
        max_length=30, 
        choices=O_STATUS,
        verbose_name='Статус заказа'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    total_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='Итоговая стоимость'
    )
    address = models.TextField(
        verbose_name='Адрес'
    )
    courier = models.ForeignKey(
        Employee, on_delete=models.SET_NULL,
        blank=True,
        null=True, 
        related_name='Orders', 
        verbose_name='Курьер'
    )

    def __str__(self):
        return f'Заказ №{self.id} пользователю {self.user.username if self.user else "Удалён"}'

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы' 

    def update_total_price(self):
        from django.db.models import F, Sum
        # Считаем сумму (цена * кол-во) по всем связанным order_items
        total = self.order_items.aggregate(
            res=Sum(F('price_at_order') * F('quantity'))
        )['res'] or 0
        
        self.total_price = total
        self.save(update_fields=['total_price'])


class Order_Item(models.Model):
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        verbose_name='Заказ',
        related_name='order_items'
        )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Товар'
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        default=1,
        verbose_name='Количество')
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Стоимость на момент заказа')

    class Meta:
        verbose_name = 'Строка заказа'
        verbose_name_plural = 'Строки заказа'

    def save(self, *args, **kwargs):
        # Если цена не указана вручную, берем текущую цену товара
        if not self.price_at_order:
            self.price_at_order = self.product.price
        
        super().save(*args, **kwargs)
        # После сохранения строки, обновляем итоговую сумму в самом заказе
        self.order.update_total_price()

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.quantity > self.product.quantity:
            raise ValidationError(f'На складе всего {self.product.quantity} шт. этого товара.')
        
    def __str__(self):
        return f"{self.product.name} ({self.quantity} шт.)"
    

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews', verbose_name='Пользователь')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name='Товар')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Рейтинг'
        )
    text = models.TextField(blank=True, null=True, verbose_name='Текст')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    is_approved = models.BooleanField(default=False, verbose_name='Одобрен')
    class Meta:
        verbose_name='Отзыв'
        verbose_name_plural='Отзывы'

    # def clean(self):
    #     from .models import Order_Item
    #     # Разрешаем отзыв, если заказ 'completed' ИЛИ 'canceled'
    #     bought = Order_Item.objects.filter(
    #         order__user=self.user, 
    #         product=self.product,
    #         order__order_status__in=['completed', 'canceled'] 
    #     ).exists()

    #     if not bought:
    #         raise ValidationError(
    #             f"Вы не можете оставить отзыв, так как не заказывали этот товар или заказ еще в работе."
    #         )

    def __str__(self):
        return f'Отзыв на {self.product.name}: {self.rating} от пользователя {self.user.username}'
    

class Support_Ticket(models.Model):

    STATUS = [
        ('new','Новый'),
        ('in_progress','В работе'),
        ('pending','Ожидает ответа'),
        ('resolved','Решён'),
        ('closed','Закрыт')
    ]
    CAT_DELIVERY = 'delivery'
    CAT_DEFECT = 'defect'
    CAT_RETURN = 'return'
    CAT_PRODUCT = 'product_question'
    CAT_TECH = 'tech_issue'
    CAT_OTHER = 'other'

    CATEGORY_CHOICES = [
        (CAT_DELIVERY, 'Доставка и получение'),
        (CAT_DEFECT, 'Качество товара / Брак'),
        (CAT_RETURN, 'Возврат и отмена'),
        (CAT_PRODUCT, 'Вопрос по товару'),
        (CAT_TECH, 'Проблема с сайтом/оплатой'),
        (CAT_OTHER, 'Другое'),
    ]

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name='Клиент')
    status = models.CharField(
        max_length=30,
        choices=STATUS,
        verbose_name='Статус'
        )
    subject = models.CharField(
        max_length=100,
        choices=CATEGORY_CHOICES,
        verbose_name='Предмет обсуждения'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name='Тикет'
        verbose_name_plural='Тикеты'
        ordering = ['-updated_at']

    def __str__(self):
        return f'Чат поддержки пользователя {self.user.username} №{self.id}'
    
class Support_Message(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Отправитель'
    )
    ticket = models.ForeignKey(
        Support_Ticket,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Тикет'
    )
    text = models.TextField(verbose_name='Текст')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']
    
    def clean(self):
        # Проверяем: является ли отправитель автором тикета или сотрудником?
        is_author = self.sender == self.ticket.user
        is_staff = self.sender.is_staff or self.sender.is_superuser
        
        if not (is_author or is_staff):
            raise ValidationError("Вы не имеете доступа к этому чату.")