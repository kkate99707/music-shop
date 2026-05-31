from django import forms
from django.contrib.auth.models import User
from .models import Profile
from .models import Order
from .models import Review, Address

class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        # Используем поля, которые есть в твоей модели Order
        fields = ['payment_method', 'address']
        widgets = {
            'address': forms.Textarea(attrs={
                'rows': 3, 
                'placeholder': 'г. Минск, ул. Пушкина, д. 10, кв. 5',
                'class': 'w-full p-3 border border-gray-300 focus:border-black outline-none'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'w-full p-3 border border-gray-300 focus:border-black outline-none'
            })
        }

common_attrs = {
    'class': 'w-full bg-background border border-border px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-ring focus:border-primary transition-all placeholder:text-muted-foreground'
}

class UserForm(forms.ModelForm):
    # Явно задаем поля паролей с твоими стилями
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={**common_attrs, 'id': 'password_input', 'placeholder': 'Придумайте пароль'}), 
        label="Пароль"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={**common_attrs, 'id': 'password_confirm_input', 'placeholder': 'Повторите пароль'}), 
        label="Подтвердите пароль"
    )
    username = forms.CharField(widget=forms.TextInput(attrs=common_attrs), label="Имя пользователя")
    email = forms.EmailField(widget=forms.EmailInput(attrs=common_attrs), label="Email")

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        # Валидация совпадения паролей
        if password and password_confirm and password != password_confirm:
            # Вешаем ошибку конкретно на поле подтверждения
            self.add_error('password_confirm', "Пароли не совпадают!")
        
        return cleaned_data

class ProfileForm(forms.ModelForm):
    # Делаем отчество необязательным на уровне поля
    patronymic = forms.CharField(
        required=False, 
        label="Отчество",
        widget=forms.TextInput(attrs=common_attrs)
    )

    class Meta:
        model = Profile
        fields = ['surname', 'name', 'patronymic', 'birth_date', 'gender', 'phone']
        widgets = {
            'surname': forms.TextInput(attrs=common_attrs),
            'name': forms.TextInput(attrs=common_attrs),
            'birth_date': forms.DateInput(attrs={**common_attrs, 'type': 'date'}),
            'gender': forms.Select(attrs=common_attrs),
            'phone': forms.TextInput(attrs={**common_attrs}), # Убрали placeholder, чтобы не бесил
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Убеждаемся, что всё кроме отчества — обязательно
        for field_name, field in self.fields.items():
            if field_name != 'patronymic':
                field.required = True
# shop/forms.py
class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'w-full p-3 border border-gray-200 uppercase text-xs font-bold'})
        }

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['surname', 'name', 'patronymic', 'phone', 'birth_date', 'gender']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-3 border border-gray-200'}),
            # Добавьте классы Tailwind для остальных полей аналогично
        }
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.Select(choices=[(i, str(i)) for i in range(1, 6)], attrs={'class': 'form-select'}),
            'text': forms.Textarea(attrs={'class': 'w-full p-3 border rounded', 'rows': 3, 'placeholder': 'Ваш отзыв...'}),
        }

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['index', 'region', 'district', 'city', 'street', 'building', 'housing', 'apartment']
        widgets = {
            'index': forms.NumberInput(attrs={'class': 'w-full p-2 border border-gray-200 uppercase text-xs font-bold'}),
            'region': forms.Select(attrs={'class': 'w-full p-2 border border-gray-200 uppercase text-xs font-bold'}),
            'district': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-200 uppercase text-xs font-bold'}),
            'city': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-200 uppercase text-xs font-bold'}),
            'street': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-200 uppercase text-xs font-bold'}),
            'building': forms.NumberInput(attrs={'class': 'w-full p-2 border border-gray-200 uppercase text-xs font-bold'}),
            'housing': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-200 uppercase text-xs font-bold'}),
            'apartment': forms.NumberInput(attrs={'class': 'w-full p-2 border border-gray-200 uppercase text-xs font-bold'}),
        }

# ── ФОРМЫ ДЛЯ УПРАВЛЕНИЯ ТОВАРАМИ И СКИДКАМИ (АДМИН) ─────────────────────────

from .models import Product, Category, Discount, Photo

css = 'w-full border border-border bg-background px-3 py-2 rounded-md focus:outline-none focus:ring-1 focus:ring-primary text-sm'

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'price', 'quantity', 'year_manufacture', 'is_active']
        widgets = {
            'name':             forms.TextInput(attrs={'class': css}),
            'description':      forms.Textarea(attrs={'class': css, 'rows': 4}),
            'category':         forms.Select(attrs={'class': css}),
            'price':            forms.NumberInput(attrs={'class': css, 'step': '0.01'}),
            'quantity':         forms.NumberInput(attrs={'class': css}),
            'year_manufacture': forms.NumberInput(attrs={'class': css}),
            'is_active':        forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
        }

class DiscountForm(forms.ModelForm):
    class Meta:
        model = Discount
        fields = ['type', 'amount', 'description', 'start_date', 'end_date']
        widgets = {
            'type':        forms.Select(attrs={'class': css}),
            'amount':      forms.NumberInput(attrs={'class': css, 'step': '0.01'}),
            'description': forms.TextInput(attrs={'class': css}),
            'start_date':  forms.DateTimeInput(attrs={'class': css, 'type': 'datetime-local'}),
            'end_date':    forms.DateTimeInput(attrs={'class': css, 'type': 'datetime-local'}),
        }

class PhotoUploadForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ['image', 'is_main']
        widgets = {
            'image':   forms.FileInput(attrs={'class': css}),
            'is_main': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
        }
