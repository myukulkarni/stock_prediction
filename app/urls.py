from django.urls import path
from django.shortcuts import render
from .views import (
    RegisterView,
    PredictAPIView,
    PredictionListAPIView,
    ajax_link_telegram,
    create_checkout_session,
    stripe_webhook,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Template Views
def login_page(request):
    return render(request, "login.html")

def register_page(request):
    return render(request, "register.html")

def dashboard_page(request):
    return render(request, "dashboard.html")

def subscribe_page(request):
    return render(request, "subscribe.html")

def success_page(request):
    return render(request, "success.html")

def cancel_page(request):
    return render(request, "cancel.html")

urlpatterns = [
    # API endpoints
    path('register/', RegisterView.as_view(), name='api-register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('predict/', PredictAPIView.as_view(), name='predict'),
    path('predictions/', PredictionListAPIView.as_view(), name='prediction-list'),
    path('link-telegram/', ajax_link_telegram, name='link_telegram'),
    path("create-checkout-session/", create_checkout_session, name="create-checkout-session"),
    path("webhooks/", stripe_webhook, name="stripe_webhook"),

    # Page views
    path('login/', login_page, name='login-page'),
    path('register-page/', register_page, name='register-page'),
    path('dashboard/', dashboard_page, name='dashboard'),
    path('subscribe/', subscribe_page, name='subscribe'),  # ✅ This renders the subscribe.html page
    path('success/', success_page, name='success'),
    path('cancel/', cancel_page, name='cancel'),
]
