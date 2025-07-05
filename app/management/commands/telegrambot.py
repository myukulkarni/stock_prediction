# telegrambot.py

from dotenv import load_dotenv
load_dotenv()

import os
import uuid
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from django.core.management.base import BaseCommand
from django.http import HttpResponseRedirect
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

from app.models import TelegramUser, Prediction, Profile
from app.utils import run_prediction
from django.core.cache import cache

from asgiref.sync import sync_to_async

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USERNAME = os.getenv("TELEGRAM_USERNAME")  # e.g. 'myukulkarniBot'
FREE_QUOTA = 5


def is_rate_limited(user_id):
    key = f"rate-limit:{user_id}"
    count = cache.get(key, 0)
    if count >= 10:
        return True
    cache.set(key, count + 1, timeout=60)
    return False


def link_telegram(request):
    jwt_auth = JWTAuthentication()
    try:
        user_auth_tuple = jwt_auth.authenticate(request)
        if user_auth_tuple is None:
            raise AuthenticationFailed("User not authenticated")
        user, _ = user_auth_tuple
    except Exception:
        return HttpResponseRedirect("/login/")

    token = str(uuid.uuid4())
    user.profile.telegram_token = token
    user.profile.save()
    return HttpResponseRedirect(f"https://t.me/{TELEGRAM_USERNAME}?start={token}")


class Command(BaseCommand):
    help = 'Runs the Telegram bot'

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO)
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = update.effective_chat.id
            args = context.args

            user_exists = await sync_to_async(TelegramUser.objects.filter(chat_id=chat_id).exists)()
            if user_exists:
                return await update.message.reply_text("✅ You're already linked!")

            if args:
                token = args[0]
                try:
                    profile = await sync_to_async(Profile.objects.get)(telegram_token=token)
                    user = await sync_to_async(lambda: profile.user)()
                    await sync_to_async(TelegramUser.objects.update_or_create)(
                        user=user,
                        defaults={"chat_id": chat_id}
                    )
                    profile.telegram_token = None
                    await sync_to_async(profile.save)()
                    await update.message.reply_text("✅ Telegram linked to your account!")
                except Profile.DoesNotExist:
                    await update.message.reply_text("❌ Invalid or expired token. Try again or use /link.")
            else:
                await update.message.reply_text(
                    "👋 Welcome!\nIf you have a token, use: /link <token>\n"
                    f"Or go to your dashboard and click 'Link Telegram'.",
                    parse_mode="Markdown"
                )

        async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = update.effective_chat.id
            args = context.args

            if not args:
                return await update.message.reply_text("❌ Usage: /link <token>")

            token = args[0]
            try:
                profile = await sync_to_async(Profile.objects.get)(telegram_token=token)
                user = await sync_to_async(lambda: profile.user)()
                await sync_to_async(TelegramUser.objects.update_or_create)(
                    user=user,
                    defaults={"chat_id": chat_id}
                )
                profile.telegram_token = None
                await sync_to_async(profile.save)()
                await update.message.reply_text("✅ Telegram linked to your account!")
            except Profile.DoesNotExist:
                await update.message.reply_text("❌ Invalid or expired token.")

        async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = update.effective_chat.id
            if not await sync_to_async(TelegramUser.objects.filter(chat_id=chat_id).exists)():
                return await update.message.reply_text("❌ Link your account first with /start or /link.")

            user = await sync_to_async(lambda: TelegramUser.objects.get(chat_id=chat_id).user)()

            # Check Free user quota
            profile = await sync_to_async(lambda: Profile.objects.get(user=user))()
            if not profile.is_pro:
                today_key = f"quota:{user.id}:{str(uuid.uuid4())[:6]}"
                used = cache.get(today_key, 0)
                if used >= FREE_QUOTA:
                    return await update.message.reply_text(
                        "🚫 Free tier limit reached (5/day). Upgrade to Pro for unlimited predictions:\n"
                        f"👉 https://yourdomain.com/subscribe"
                    )
                cache.set(today_key, used + 1, timeout=86400)

            if len(context.args) != 1:
                return await update.message.reply_text("❌ Usage: /predict <TICKER>")

            ticker = context.args[0].upper()
            try:
                result = await sync_to_async(run_prediction)(ticker, user)
                p = result["prediction_obj"]
                await update.message.reply_text(f"✅ {ticker} → ₹{p.predicted_price:.2f}")
                if os.path.exists(p.chart_history.path):
                    await context.bot.send_photo(chat_id=chat_id, photo=open(p.chart_history.path, 'rb'))
                if os.path.exists(p.chart_prediction.path):
                    await context.bot.send_photo(chat_id=chat_id, photo=open(p.chart_prediction.path, 'rb'))
            except Exception as e:
                await update.message.reply_text(f"❌ Prediction error: {e}")

        async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = update.effective_chat.id
            if not await sync_to_async(TelegramUser.objects.filter(chat_id=chat_id).exists)():
                return await update.message.reply_text("❌ Link your account first with /start or /link.")

            user = await sync_to_async(lambda: TelegramUser.objects.get(chat_id=chat_id).user)()
            prediction = await sync_to_async(lambda: Prediction.objects.filter(user=user).order_by('-created_at').first())()
            if not prediction:
                return await update.message.reply_text("📭 No predictions yet.")

            await update.message.reply_text(f"📊 {prediction.ticker} → ₹{prediction.predicted_price:.2f}")
            if os.path.exists(prediction.chart_history.path):
                await context.bot.send_photo(chat_id=chat_id, photo=open(prediction.chart_history.path, 'rb'))
            if os.path.exists(prediction.chart_prediction.path):
                await context.bot.send_photo(chat_id=chat_id, photo=open(prediction.chart_prediction.path, 'rb'))

        async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "/start <token> - Link account\n"
                "/link <token> - Link manually\n"
                "/predict <TICKER> - Get prediction\n"
                "/latest - Your last prediction\n"
                "/help - Show help"
            )

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("link", link))
        app.add_handler(CommandHandler("predict", predict))
        app.add_handler(CommandHandler("latest", latest))
        app.add_handler(CommandHandler("help", help_cmd))

        app.run_polling()
