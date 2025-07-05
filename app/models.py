from django.db import models
from django.contrib.auth.models import User

class Prediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ticker = models.CharField(max_length=10)
    predicted_price = models.FloatField()
    mse = models.FloatField(null=True, blank=True)  # ✅ allow null
    rmse = models.FloatField(null=True, blank=True)  # ✅ allow null
    r2 =models.FloatField(null=True, blank=True)  # ✅ allow null
    chart_history = models.CharField(max_length=255)
    chart_prediction = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ticker} - {self.predicted_price}"

class TelegramUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    chat_id = models.BigIntegerField(unique=True)

    def __str__(self):
        return f"{self.user.username} ↔ {self.chat_id}"

from django.contrib.auth.models import User
from django.db import models

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telegram_token = models.CharField(max_length=100, blank=True, null=True)
    is_pro = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.user.username
