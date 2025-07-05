import uuid
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.contrib.auth.models import User
from .models import Prediction, TelegramUser
from .serializers import PredictionSerializer
from .utils import run_prediction

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')

        if not username or not password or not email:
            return Response({"error": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password, email=email)
        return Response({"message": "User registered successfully."}, status=status.HTTP_201_CREATED)

class PredictAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ticker = request.data.get("ticker", "").upper()

        try:
            result = run_prediction(ticker, request.user)
            serializer = PredictionSerializer(result["prediction_obj"])
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PredictionListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Prediction.objects.filter(user=request.user)
        ticker = request.query_params.get("ticker")
        if ticker:
            queryset = queryset.filter(ticker__iexact=ticker)
        serializer = PredictionSerializer(queryset, many=True)
        return Response(serializer.data)

# app/views.py
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.utils.crypto import get_random_string

# app/views.py

import uuid
import os
from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import status
from app.models import Profile

def ajax_link_telegram(request):
    """
    GET /app/v1/link-telegram/
    Requires: Authorization: Bearer <access_token>
    Returns: JSON { "url": "https://t.me/<bot_username>?start=<token>" }
    """
    jwt_auth = JWTAuthentication()
    try:
        auth = jwt_auth.authenticate(request)
        if auth is None:
            raise AuthenticationFailed()
        user, _ = auth
    except AuthenticationFailed:
        return JsonResponse({'detail': 'Authentication failed'}, status=status.HTTP_401_UNAUTHORIZED)

    # Ensure Profile exists
    profile, _ = Profile.objects.get_or_create(user=user)

    # Generate a one-time token for this user
    token = uuid.uuid4().hex
    profile.telegram_token = token
    profile.save()

    # Bot username from .env
    bot_username = os.getenv("TELEGRAM_USERNAME")
    if not bot_username:
        return JsonResponse(
            {'detail': 'Bot username not configured on server.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Build deep link
    telegram_url = f"https://t.me/{bot_username}?start={token}"

    return JsonResponse({'url': telegram_url})

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework_simplejwt.authentication import JWTAuthentication
from app.models import Profile
import stripe
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@csrf_exempt
@api_view(["POST"])
def create_checkout_session(request):
    jwt_auth = JWTAuthentication()
    user_data = jwt_auth.authenticate(request)

    if user_data is None:
        return JsonResponse({"detail": "Authentication failed"}, status=401)

    user, _ = user_data
    profile = user.profile

    if not profile.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email)
        profile.stripe_customer_id = customer.id
        profile.save()
    else:
        customer = stripe.Customer.retrieve(profile.stripe_customer_id)

    checkout_session = stripe.checkout.Session.create(
        customer=customer.id,
        payment_method_types=["card"],
        line_items=[
            {
                "price": os.getenv("STRIPE_PRICE_ID"),
                "quantity": 1,
            }
        ],
        mode="subscription",
        success_url="http://localhost:8000/app/v1/success/",
        cancel_url="http://localhost:8000/app/v1/cancel/",
    )

    return JsonResponse({"url": checkout_session.url})



# app/views.py

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import stripe
import os
from app.models import Profile

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from app.models import Profile
import stripe
import os
import json

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        return JsonResponse({"error": f"Invalid payload: {str(e)}"}, status=400)
    except stripe.error.SignatureVerificationError as e:
        return JsonResponse({"error": f"Invalid signature: {str(e)}"}, status=400)

    # ✅ When user successfully pays
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_id = session.get("customer")

        if customer_id:
            try:
                profile = Profile.objects.get(stripe_customer_id=customer_id)
                profile.is_pro = True
                profile.save()
                print(f"[✓] Upgraded {profile.user.username} to Pro.")
            except Profile.DoesNotExist:
                print(f"[!] No profile found for customer_id: {customer_id}")

    # ❌ When subscription is cancelled (auto or manually)
    elif event["type"] == "customer.subscription.deleted":
        customer_id = event["data"]["object"].get("customer")

        if customer_id:
            try:
                profile = Profile.objects.get(stripe_customer_id=customer_id)
                profile.is_pro = False
                profile.save()
                print(f"[✓] Downgraded {profile.user.username} to Free.")
            except Profile.DoesNotExist:
                print(f"[!] No profile found for cancelled customer_id: {customer_id}")

    return JsonResponse({"status": "success"})
