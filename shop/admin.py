from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import *

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    # Автоматически заполняет slug из поля name
    prepopulated_fields = {'slug': ('name',)}
    list_display = ['name', 'parent', 'slug'] # Колонки в списке
admin.site.register(Discount)
admin.site.register(Photo)
admin.site.register(Notification)
admin.site.register(Address)

class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'quantity', 'is_active', 'category']
    list_editable = ['quantity', 'is_active'] 
    inlines = [PhotoInline]


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False

# Позволяет назначать роль сотрудника прямо на странице пользователя
class EmployeeInline(admin.StackedInline):
    model = Employee
    can_delete = False

# Переопределяем стандартную настройку пользователя
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline, EmployeeInline)

# Перерегистрируем модель User
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

class BasketItemInline(admin.TabularInline):
    model = Basket_Item
    extra = 0 # Чтобы не вылезали пустые строки для новых товаров

@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    # Выводим имя пользователя и дату в списке всех корзин
    list_display = ['customer_name', 'created_at', 'total_items']
    inlines = [BasketItemInline]

    # Метод, чтобы достать имя из связанной модели User
    def customer_name(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name} ({obj.customer.username})"
    
    # Метод, чтобы посчитать количество позиций в корзине
    def total_items(self, obj):
        return obj.basket_items.count()

    customer_name.short_description = 'Покупатель'
    total_items.short_description = 'Кол-во товаров'


class OrderItemInline(admin.TabularInline):
    model = Order_Item
    extra = 0  # Чтобы не вылезало много пустых строк
    # Поля, которые нельзя редактировать (цену на момент заказа лучше зафиксировать)
    readonly_fields = ['price_at_order'] 
    fields = ['product', 'quantity', 'price_at_order']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Что мы видим в списке всех заказов
    list_display = ['id', 'user', 'order_status', 'payment_status', 'total_price', 'created_at']
    
    # Фильтры справа
    list_filter = ['order_status', 'payment_status', 'created_at']
    
    # Поля, которые нельзя менять вручную (пусть считает система)
    readonly_fields = ['total_price', 'created_at']
    
    # Подключаем товары к заказу
    inlines = [OrderItemInline]
    
    # Группируем поля для красоты
    fieldsets = [
        ('Основная информация', {
            'fields': ('user', 'order_status', 'total_price')
        }),
        ('Оплата и Доставка', {
            'fields': ('payment_method', 'payment_status', 'address', 'courier')
        }),
        ('Служебная информация', {
            'fields': ('created_at',),
            'classes': ('collapse',) # Можно скрыть блок
        }),
    ]

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    # Что отображаем в списке
    list_display = ('product', 'user', 'rating', 'created_at')
    
    # По каким полям можно фильтровать (удобно для модерации)
    list_filter = ('rating', 'created_at', 'product')
    
    # Поиск по тексту отзыва и имени пользователя
    search_fields = ('text', 'user__username', 'product__name')
    
    # Поля, которые нельзя менять (дату создания ставит сам Django)
    readonly_fields = ('created_at',)

    # Группировка полей в форме редактирования
    fieldsets = (
        ('Основная информация', {
            'fields': ('product', 'user', 'rating')
        }),
        ('Контент', {
            'fields': ('text', 'created_at')
        }),
    )

    def save_model(self, request, obj, form, change):

        obj.full_clean()
        super().save_model(request, obj, form, change)

class MessageInline(admin.StackedInline):
    model = Support_Message
    extra = 1 # Поле для быстрого ответа модератора
    readonly_fields = ['created_at']

@admin.register(Support_Ticket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'subject', 'status', 'created_at']
    list_filter = ['status', 'subject']
    inlines = [MessageInline]