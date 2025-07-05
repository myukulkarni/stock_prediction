# app/middleware.py

from django.utils.timezone import now
from datetime import timedelta
from django.http import JsonResponse
from app.models import Prediction

class QuotaLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, "profile"):
            if not request.user.profile.is_pro:
                today = now().date()
                count = Prediction.objects.filter(
                    user=request.user,
                    created_at__date=today
                ).count()
                if count >= 5:
                    return JsonResponse({"error": "Free tier: Daily quota exceeded."}, status=429)

        return self.get_response(request)
