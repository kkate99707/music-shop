from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    # --- ГЛАВНАЯ И ПОИСК ---
    path('', views.index, name='index'),
    path('search-autocomplete/', views.product_search_autocomplete, name='search_autocomplete'),

    # --- КАТАЛОГ ---
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),

    # --- КОРЗИНА ---
    path('basket/', views.basket_detail, name='basket_detail'),
    path('basket/add/<int:product_id>/', views.add_to_basket, name='add_to_basket'),
    path('basket/update/<int:item_id>/', views.update_basket, name='update_basket'),
    path('basket/remove/<int:item_id>/', views.remove_from_basket, name='remove_from_basket'),

    # --- ЗАКАЗЫ ---
    path('order/create/', views.order_create, name='order_create'),
    path('order/success/<int:order_id>/', views.order_success, name='order_success'),
    path('profile/orders/', views.user_orders, name='user_orders'),
    path('profile/orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('profile/orders/<int:order_id>/ask/', views.order_ask_question, name='order_ask_question'),

    # --- УВЕДОМЛЕНИЯ ---
    path('notifications/', views.notifications_page, name='notifications'),
    path('notifications/read/<int:notif_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),

    # --- ИИ-ПОМОЩНИК ---
    path('ai-assistant/', views.ai_assistant, name='ai_assistant'),

    # --- ПРОФИЛЬ ---
    path('profile/', views.profile_view, name='profile'),
    path('profile/settings/', views.profile_settings, name='profile_settings'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    path('password-change-settings/', views.password_change_settings, name='password_change_settings'),

    # --- АДРЕСА ---
    path('profile/address/add/', views.address_create, name='address_create'),
    path('profile/address/delete/<int:pk>/', views.address_delete, name='address_delete'),

    # --- АУТЕНТИФИКАЦИЯ ---
    path('register/', views.register, name='register'),
    path('send-verification-code/', views.send_verification_code, name='send_verification_code'),
    path('verify-code/', views.verify_code, name='verify_code'),

    # --- ПОДДЕРЖКА ---
    path('support/', views.ticket_list, name='ticket_list'),
    path('support/create/', views.ticket_create, name='ticket_create'),
    path('support/<int:ticket_id>/', views.ticket_chat, name='ticket_chat'),

    # --- МОДЕРАТОР ---
    path('moderator/reviews/', views.moderator_reviews, name='moderator_reviews'),
    path('moderator/reviews/<int:review_id>/approve/', views.moderator_approve_review, name='moderator_approve_review'),
    path('moderator/reviews/<int:review_id>/delete/', views.moderator_delete_review, name='moderator_delete_review'),
    path('moderator/support/', views.moderator_support, name='moderator_support'),
    path('moderator/support/<int:ticket_id>/', views.moderator_ticket, name='moderator_ticket'),

    # --- КУРЬЕР ---
    path('courier/', views.courier_tasks, name='courier_tasks'),
    path('courier/take/<int:order_id>/', views.courier_take_order, name='courier_take_order'),
    path('courier/order/<int:order_id>/', views.courier_order_detail, name='courier_order_detail'),

    # --- АДМИНИСТРАТОР ---
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/users/<int:user_id>/block/', views.admin_toggle_block, name='admin_toggle_block'),
    path('admin-panel/users/<int:user_id>/role/', views.admin_change_role, name='admin_change_role'),
    # --- УПРАВЛЕНИЕ ТОВАРАМИ (АДМИН) ---
    path('admin-panel/products/', views.admin_product_list, name='admin_product_list'),
    path('admin-panel/products/create/', views.admin_product_create, name='admin_product_create'),
    path('admin-panel/products/<int:pk>/edit/', views.admin_product_edit, name='admin_product_edit'),
    path('admin-panel/products/<int:pk>/delete/', views.admin_product_delete, name='admin_product_delete'),

    # --- УПРАВЛЕНИЕ СКИДКАМИ (АДМИН) ---
    path('admin-panel/discounts/', views.admin_discount_list, name='admin_discount_list'),
    path('admin-panel/discounts/create/', views.admin_discount_create, name='admin_discount_create'),
    path('admin-panel/discounts/<int:pk>/edit/', views.admin_discount_edit, name='admin_discount_edit'),
    path('admin-panel/discounts/<int:pk>/delete/', views.admin_discount_delete, name='admin_discount_delete'),
]
