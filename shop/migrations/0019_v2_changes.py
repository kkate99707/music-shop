from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('shop', '0018_alter_profile_phone')]
    operations = [
        migrations.AddField(model_name='review', name='is_approved',
            field=models.BooleanField(default=False, verbose_name='Одобрен')),
        migrations.AddField(model_name='profile', name='is_blocked',
            field=models.BooleanField(default=False, verbose_name='Заблокирован')),
        migrations.AddField(model_name='basket_item', name='discount_notified',
            field=models.BooleanField(default=False, verbose_name='Уведомлён о скидке')),
        migrations.AddField(model_name='notification', name='notification_type',
            field=models.CharField(choices=[('order_status','Статус заказа'),('review_approved','Отзыв одобрен'),('discount','Скидка на товар'),('general','Общее')], default='general', max_length=20, verbose_name='Тип')),
        migrations.AlterField(model_name='photo', name='image',
            field=models.ImageField(upload_to='products/', verbose_name='Путь к файлу')),
    ]
