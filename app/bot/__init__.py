"""
Bot Module - وحدة البوت
"""
from aiogram import Router
from app.bot.handlers import router as old_handlers_router
from app.bot.handlers_features import router as new_features_router

# دمج الراوترات - الجديد أولاً ليأخذ الأولوية
combined_router = Router()
combined_router.include_router(new_features_router)
combined_router.include_router(old_handlers_router)

handlers_router = combined_router
