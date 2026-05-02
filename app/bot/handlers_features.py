"""
Handlers Features Module - جميع المعالجات الجديدة
الملف الرئيسي للبوت مع جميع الميزات
"""
import os
import io
import csv
from typing import Optional
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, Update
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.dispatcher.handler import Handler

from app.database import SessionLocal
from app.services.user_service import UserService
from app.services.book_service import BookService
from app.services.category_service import CategoryService
from app.services.author_service import AuthorService
from app.services.channel_service import ChannelService
from app.services.points_service import PointsService
from app.services.search_service import SearchService
from app.services.ai_service import ai_service
from app.models.book import BookStatus
from app.models.user import UserStatus
from app.models.points import TransactionType
from config.settings import get_settings
from app.bot.keyboards import (
    get_main_menu_keyboard,
    get_main_menu_enhanced_keyboard,
    get_category_keyboard,
    get_book_keyboard,
    get_rating_keyboard,
    get_books_list_keyboard,
    get_user_profile_keyboard,
    get_settings_keyboard,
    get_admin_keyboard,
    get_admin_keyboard_enhanced,
    get_admin_categories_keyboard,
    get_admin_authors_keyboard,
    get_admin_channels_keyboard,
    get_admin_users_keyboard,
    get_admin_book_actions_keyboard,
    get_confirm_keyboard,
    get_back_to_admin_keyboard,
    get_search_type_keyboard,
    get_back_keyboard
)
from app.utils.helpers import format_book_info, format_user_profile, truncate_text

settings = get_settings()
router = Router()

# ==========================================
# Middleware للاشتراك الإجباري
# ==========================================

class ForceJoinMiddleware(BaseMiddleware):
    """ميدلوير لفحص الاشتراك الإجباري"""

    async def __call__(self, handler: Handler, event: Update, data: dict) -> any:
        # استثناء الأوامر الإدارية والبوت
        if isinstance(event, Message):
            if event.text and event.text.startswith('/'):
                # الأوامر العامة فقط تحتاج فحص
                if event.text not in ['/start', '/help', '/cancel']:
                    return await handler(event, data)

            # فحص الاشتراك
            db = SessionLocal()
            try:
                channel_service = ChannelService(db)
                bot = data.get('bot')

                if bot:
                    is_subscribed, not_subscribed = await channel_service.check_all_subscriptions(
                        bot, event.from_user.id
                    )

                    if not is_subscribed:
                        # بناء رسالة الاشتراك
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
                        for channel in not_subscribed:
                            if channel.channel_link:
                                keyboard.inline_keyboard.append([
                                    InlineKeyboardButton(
                                        text=f"📢 الانضمام لـ {channel.channel_name or channel.channel_id}",
                                        url=channel.channel_link
                                    )
                                ])
                        keyboard.inline_keyboard.append([
                            InlineKeyboardButton(
                                text="✅ تم الاشتراك",
                                callback_data="check_subscription"
                            )
                        ])

                        await event.answer(
                            "⚠️ يجب الاشتراك بالقنوات التالية أولاً:",
                            reply_markup=keyboard
                        )
                        return
            finally:
                db.close()

        return await handler(event, data)


# ==========================================
# States Groups
# ==========================================

class UserStates(StatesGroup):
    """حالات المستخدم"""
    main = State()
    browsing = State()
    searching = State()
    profile = State()


class AdminStates(StatesGroup):
    """حالات الإدارة"""
    waiting_category_name = State()
    waiting_category_edit = State()
    waiting_author_name = State()
    waiting_channel_id = State()
    waiting_channel_link = State()
    waiting_user_id = State()
    waiting_broadcast = State()
    waiting_search = State()
    waiting_book_title = State()
    waiting_book_author = State()
    waiting_book_description = State()
    waiting_book_file = State()
    waiting_book_category = State()
    waiting_reject_reason = State()
    waiting_message_user = State()
    waiting_ai_question = State()


# ==========================================
# Helper Functions
# ==========================================

def is_owner(telegram_id: int) -> bool:
    """التحقق من أن المستخدم هو المالك"""
    return settings.is_owner(telegram_id)


def get_user_from_event(event) -> Optional[dict]:
    """الحصول على بيانات المستخدم من الحدث"""
    if hasattr(event, 'from_user'):
        return {
            'telegram_id': event.from_user.id,
            'username': event.from_user.username,
            'first_name': event.from_user.first_name,
            'last_name': event.from_user.last_name
        }
    return None


def ensure_user(telegram_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """التأكد من وجود المستخدم وإنشاؤه"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        user = user_service.get_or_create_user(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        return user
    finally:
        db.close()


# ==========================================
# Command Handlers - أوامر المالك النصية
# ==========================================

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """عرض الإحصائيات"""
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك بهذا الأمر.")
        return

    db = SessionLocal()
    try:
        book_service = BookService(db)
        user_service = UserService(db)

        book_stats = book_service.get_statistics()
        user_stats = user_service.get_statistics()

        stats_text = f"""
📊 إحصائيات المكتبة:

📚 الكتب:
• الإجمالي: {book_stats['total']}
• النشطة: {book_stats['active']}
• قيد المراجعة: {book_stats['pending']}
• المرفوضة: {book_stats['rejected']}
• إجمالي التحميلات: {book_stats['total_downloads']}
• متوسط التقييم: {book_stats['average_rating']}

👥 المستخدمين:
• الإجمالي: {user_stats['total']}
• النشطين: {user_stats['active']}
• المحظورين: {user_stats['banned']}
• إجمالي التحميلات: {user_stats['total_downloads']}
• المميزين: {user_stats['premium']}
        """
        await message.answer(stats_text)
    finally:
        db.close()


@router.message(Command("exportcsv"))
async def cmd_export_csv(message: Message):
    """تصدير بيانات الكتب كـ CSV"""
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك بهذا الأمر.")
        return

    db = SessionLocal()
    try:
        book_service = BookService(db)
        books = book_service.get_all_books(status=BookStatus.ACTIVE)

        # إنشاء ملف CSV في الذاكرة
        output = io.StringIO()
        writer = csv.writer(output)

        # كتابة Headers
        writer.writerow(['ID', 'العنوان', 'المؤلف', 'القسم', 'التحميلات', 'التقييم', 'تاريخ الإنشاء'])

        # كتابة البيانات
        for book in books:
            writer.writerow([
                book.id,
                book.title,
                book.author.name if book.author else '',
                book.category.name if book.category else '',
                book.download_count,
                book.average_rating,
                book.created_at.strftime('%Y-%m-%d')
            ])

        # إنشاء ملف
        output.seek(0)
        bytes_io = io.BytesIO(output.getvalue().encode('utf-8'))
        bytes_io.name = 'books_export.csv'

        await message.answer_document(
            document=bytes_io,
            caption="📤 تم تصدير بيانات الكتب"
        )
    finally:
        db.close()


@router.message(Command("listcategories"))
async def cmd_list_categories(message: Message):
    """عرض قائمة الأقسام"""
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك بهذا الأمر.")
        return

    db = SessionLocal()
    try:
        category_service = CategoryService(db)
        categories = category_service.list_all()

        if not categories:
            await message.answer("لا توجد أقسام حالياً.")
            return

        text = "📁 الأقسام:\n\n"
        for i, cat in enumerate(categories, 1):
            text += f"{i}. {cat.name} (ID: {cat.id})\n"

        await message.answer(text)
    finally:
        db.close()


@router.message(Command("listauthors"))
async def cmd_list_authors(message: Message):
    """عرض قائمة المؤلفين"""
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك بهذا الأمر.")
        return

    db = SessionLocal()
    try:
        author_service = AuthorService(db)
        authors = author_service.list_all()

        if not authors:
            await message.answer("لا توجد مؤلفين حالياً.")
            return

        text = "✍️ المؤلفين:\n\n"
        for i, auth in enumerate(authors, 1):
            text += f"{i}. {auth.name} (ID: {auth.id})\n"

        await message.answer(text)
    finally:
        db.close()


@router.message(Command("listchannels"))
async def cmd_list_channels(message: Message):
    """عرض قائمة قنوات الاشتراك الإجباري"""
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك بهذا الأمر.")
        return

    db = SessionLocal()
    try:
        channel_service = ChannelService(db)
        channels = channel_service.get_all_channels()

        if not channels:
            await message.answer("لا توجد قنوات اشتراك إجباري.")
            return

        text = "📡 قنوات الاشتراك الإجباري:\n\n"
        for ch in channels:
            status = "مطلوب" if ch.is_required else "اختياري"
            text += f"• {ch.channel_name or ch.channel_id}\n  الحالة: {status}\n"

        await message.answer(text)
    finally:
        db.close()


@router.message(Command("aifind"))
async def cmd_ai_find(message: Message):
    """البحث الذكي بالذكاء الاصطناعي"""
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك بهذا الأمر.")
        return

    # الحصول على نص البحث بعد الأمر
    query = message.text.replace('/aifind', '').strip()
    if not query:
        await message.answer("الاستخدام: /aifind [نص البحث]")
        return

    db = SessionLocal()
    try:
        search_service = SearchService(db)
        books, authors = search_service.text_search(query, limit=5)

        if not books and not authors:
            await message.answer(f"لم يتم العثور على نتائج لـ: {query}")
            return

        response = f"🔍 نتائج البحث عن: {query}\n\n"

        if books:
            response += "📚 الكتب:\n"
            for book in books:
                response += f"• {book.title}\n"

        if authors:
            response += "\n✍️ المؤلفين:\n"
            for auth in authors:
                response += f"• {auth.name}\n"

        await message.answer(response)
    finally:
        db.close()


# ==========================================
# Button Handlers - معالجات الأزرار
# ==========================================

@router.message(F.text == "📚 تصفح الكتب")
async def browse_books(message: Message):
    """تصفح الكتب"""
    user = ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )

    text = "📚 اختر قسمًا للتصفح:\n\n"
    keyboard = get_category_keyboard()

    await message.answer(text, reply_markup=keyboard)


@router.message(F.text == "🔍 بحث")
async def search_books(message: Message):
    """البحث عن الكتب"""
    user = ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )

    text = "🔍 كيف تريد البحث؟"
    keyboard = get_search_type_keyboard()

    await message.answer(text, reply_markup=keyboard)


@router.message(F.text == "👤 ملفي الشخصي")
async def my_profile(message: Message):
    """عرض الملف الشخصي"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        points_service = PointsService(db)

        user = user_service.get_or_create_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )

        user_points = points_service.get_user_points(user.id)
        points = user_points.current_balance if user_points else 0

        profile_text = format_user_profile(user, points)
        keyboard = get_user_profile_keyboard()

        await message.answer(profile_text, reply_markup=keyboard)
    finally:
        db.close()


@router.message(F.text == "🎁 نقاطي")
async def my_points(message: Message):
    """عرض نقاطي"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        points_service = PointsService(db)

        user = user_service.get_or_create_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )

        user_points = points_service.get_or_create_user_points(user.id)
        transactions = points_service.get_transactions(user.id, limit=10)

        text = f"""
🎁 نقاطي

💰 الرصيد الحالي: {user_points.current_balance}
📊 إجمالي المكتسب: {user_points.lifetime_earned}
📈 المستوى: {user.level}

📋 آخر المعاملات:
"""

        for trans in transactions:
            trans_type_text = {
                TransactionType.REFERRAL: "إحالة",
                TransactionType.DOWNLOAD: "تحميل",
                TransactionType.REVIEW: "تقييم",
                TransactionType.PURCHASE: "شراء",
                TransactionType.DEDUCTION: "خصم",
                TransactionType.COUPON: "كوبون",
                TransactionType.GIFT: "هدية"
            }.get(trans.transaction_type, str(trans.transaction_type))

            sign = "+" if trans.amount > 0 else ""
            text += f"• {trans_type_text}: {sign}{trans.amount}\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 لوحة المتصدرين", callback_data="points_leaderboard")]
        ])

        await message.answer(text, reply_markup=keyboard)
    finally:
        db.close()


@router.message(F.text == "❤️ المفضلة")
async def my_favorites(message: Message):
    """عرض المفضلة"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        book_service = BookService(db)

        user = user_service.get_or_create_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )

        favorites = user_service.get_user_favorites(message.from_user.id)

        if not favorites:
            await message.answer("📭 لا توجد كتب في المفضلة لديك.")
            return

        text = "❤️ كتبك المفضلة:\n\n"
        books = []
        for fav in favorites:
            book = book_service.get_book(fav.book_id)
            if book:
                books.append(book)
                text += f"📖 {truncate_text(book.title, 40)}\n"

        keyboard = get_books_list_keyboard(books[:10]) if books else None

        await message.answer(text, reply_markup=keyboard)
    finally:
        db.close()


@router.message(F.text == "📥 سجل التحميلات")
async def download_history(message: Message):
    """عرض سجل التحميلات"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        book_service = BookService(db)

        user = user_service.get_or_create_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )

        downloads = user_service.get_user_downloads(message.from_user.id, limit=20)

        if not downloads:
            await message.answer("📭 لا توجد تحميلات سابقة.")
            return

        text = "📥 سجل التحميلات:\n\n"
        books = []
        for dl in downloads:
            book = book_service.get_book(dl.book_id)
            if book:
                books.append(book)
                text += f"📖 {truncate_text(book.title, 40)}\n📅 {dl.downloaded_at.strftime('%Y-%m-%d')}\n\n"

        keyboard = get_books_list_keyboard(books) if books else None

        await message.answer(text, reply_markup=keyboard)
    finally:
        db.close()


@router.message(F.text == "⚙️ الإعدادات")
async def settings_menu(message: Message):
    """قائمة الإعدادات"""
    user = ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )

    db = SessionLocal()
    try:
        user_service = UserService(db)
        user_obj = user_service.get_user_by_telegram_id(message.from_user.id)
        language = user_obj.language if user_obj else "ar"

        text = "⚙️ الإعدادات"
        keyboard = get_settings_keyboard(language)

        await message.answer(text, reply_markup=keyboard)
    finally:
        db.close()


@router.message(F.text == "👑 لوحة تحكم المالك")
async def admin_panel(message: Message):
    """لوحة تحكم المالك"""
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك.")
        return

    text = "👑 مرحباً أيها المالك!\n\nاختر مما يلي:"
    keyboard = get_admin_keyboard_enhanced()

    await message.answer(text, reply_markup=keyboard)


@router.message(F.text == "🔙 رجوع")
async def go_back(message: Message):
    """الرجوع للقائمة الرئيسية"""
    user = ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )

    text = "🏠 القائمة الرئيسية"
    keyboard = get_main_menu_keyboard(is_owner(message.from_user.id))

    await message.answer(text, reply_markup=keyboard)


# ==========================================
# Callback Handlers - معالجات الأازرار Callback
# ==========================================

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """الرجوع للقائمة الرئيسية"""
    text = "🏠 القائمة الرئيسية"
    keyboard = get_main_menu_keyboard(is_owner(callback.from_user.id))
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("cat_"))
async def callback_category(callback: CallbackQuery):
    """عرض كتب القسم"""
    category_id = int(callback.data.split("_")[1])

    db = SessionLocal()
    try:
        book_service = BookService(db)
        category_service = CategoryService(db)

        category = category_service.get_by_id(category_id)
        if not category:
            await callback.answer("القسم غير موجود", show_alert=True)
            return

        books = book_service.get_books_by_category(category_id, limit=20)

        name = category.name_ar or category.name
        text = f"📁 {name}\n\n📚 عدد الكتب: {len(books)}\n\nاختر كتاباً:"

        keyboard = get_books_list_keyboard(books) if books else None

        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data.startswith("book_"))
async def callback_book(callback: CallbackQuery):
    """عرض تفاصيل الكتاب"""
    book_id = int(callback.data.split("_")[1])

    db = SessionLocal()
    try:
        book_service = BookService(db)
        user_service = UserService(db)

        book = book_service.get_book(book_id)
        if not book:
            await callback.answer("الكتاب غير موجود", show_alert=True)
            return

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        is_favorite = False
        if user:
            from app.models.favorite import Favorite
            fav = db.query(Favorite).filter(
                Favorite.user_id == user.id,
                Favorite.book_id == book_id
            ).first()
            is_favorite = fav is not None

        book_info = format_book_info(book)
        keyboard = get_book_keyboard(book_id, is_favorite)

        await callback.message.edit_text(book_info, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data.startswith("fav_"))
async def callback_favorite(callback: CallbackQuery):
    """إضافة/إزالة من المفضلة"""
    book_id = int(callback.data.split("_")[1])

    db = SessionLocal()
    try:
        user_service = UserService(db)
        from app.models.favorite import Favorite

        user = user_service.get_or_create_user(
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
            callback.from_user.last_name
        )

        # البحث عن المفضلة
        fav = db.query(Favorite).filter(
            Favorite.user_id == user.id,
            Favorite.book_id == book_id
        ).first()

        if fav:
            # إزالة من المفضلة
            db.delete(fav)
            db.commit()
            await callback.answer("❌Removed from favorites")
        else:
            # إضافة للمفضلة
            new_fav = Favorite(user_id=user.id, book_id=book_id)
            db.add(new_fav)
            db.commit()
            await callback.answer("✅Added to favorites")

        # تحديث عرض الكتاب
        book_service = BookService(db)
        book = book_service.get_book(book_id)

        if book:
            book_info = format_book_info(book)
            keyboard = get_book_keyboard(book_id, fav is None)
            await callback.message.edit_text(book_info, reply_markup=keyboard)

    finally:
        db.close()


@router.callback_query(F.data.startswith("rate_"))
async def callback_rating(callback: CallbackQuery):
    """تقييم الكتاب"""
    parts = callback.data.split("_")

    if len(parts) == 2:
        # طلب التقييم
        book_id = int(parts[1])
        keyboard = get_rating_keyboard(book_id)
        await callback.message.edit_text(
            "⭐ اختر تقييمك للكتاب:",
            reply_markup=keyboard
        )
    else:
        # حفظ التقييم
        rating = int(parts[1])
        book_id = int(parts[2])

        db = SessionLocal()
        try:
            book_service = BookService(db)
            points_service = PointsService(db)
            user_service = UserService(db)

            book = book_service.get_book(book_id)
            if book:
                book_service.add_rating(book_id, float(rating))

                # إضافة نقاط للتقييم
                user = user_service.get_or_create_user(
                    callback.from_user.id,
                    callback.from_user.username,
                    callback.from_user.first_name,
                    callback.from_user.last_name
                )
                points_service.add_review_points(user.id, book_id)

                await callback.answer(f"⭐ شكراً لك! تم تسجيل تقييم {rating}")

                # العودة لعرض الكتاب
                book_info = format_book_info(book)
                keyboard = get_book_keyboard(book_id, False)
                await callback.message.edit_text(book_info, reply_markup=keyboard)
        finally:
            db.close()


@router.callback_query(F.data.startswith("download_"))
async def callback_download(callback: CallbackQuery):
    """تحميل الكتاب"""
    book_id = int(callback.data.split("_")[1])

    db = SessionLocal()
    try:
        book_service = BookService(db)
        user_service = UserService(db)
        points_service = PointsService(db)

        book = book_service.get_book(book_id)
        if not book:
            await callback.answer("الكتاب غير موجود", show_alert=True)
            return

        if not book.file_path or not os.path.exists(book.file_path):
            await callback.answer("الكتاب غير متاح للتحميل حالياً", show_alert=True)
            return

        user = user_service.get_or_create_user(
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
            callback.from_user.last_name
        )

        # التحقق من النقاط
        can_download, msg = points_service.can_download(user.id)
        if not can_download:
            await callback.answer(msg, show_alert=True)
            return

        # خصم النقاط
        from config.settings import get_settings
        s = get_settings()
        points_service.deduct_points(user.id, s.points_to_deduct, f"تحميل كتاب {book.title}")

        # إضافة نقاط التحميل
        points_service.add_download_points(user.id, book_id)

        # تحديث إحصائيات الكتاب
        book_service.increment_download(book_id)
        user_service.increment_downloads(callback.from_user.id)

        # إرسال الملف
        with open(book.file_path, 'rb') as file:
            await callback.message.answer_document(
                document=file,
                caption=f"📥 {book.title}"
            )

        await callback.answer("✅ تم تحميل الكتاب بنجاح!")

        # تسجيل التحميل
        from app.models.download_history import DownloadHistory
        download = DownloadHistory(user_id=user.id, book_id=book_id)
        db.add(download)
        db.commit()

    finally:
        db.close()


# ==========================================
# Admin Callback Handlers - معالجات الإدارة
# ==========================================

@router.callback_query(F.data == "admin_menu")
async def callback_admin_menu(callback: CallbackQuery):
    """العودة للوحة التحكم"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    text = "👑 لوحة تحكم المالك"
    keyboard = get_admin_keyboard_enhanced()
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    """إحصائيات متقدمة"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        book_service = BookService(db)
        user_service = UserService(db)
        points_service = PointsService(db)

        book_stats = book_service.get_statistics()
        user_stats = user_service.get_statistics()
        top_users = points_service.get_leaderboard(limit=5)

        text = "📊 إحصائيات متقدمة:\n\n"
        text += f"📚 الكتب: {book_stats['total']} | النشطة: {book_stats['active']} | المراجعة: {book_stats['pending']}\n"
        text += f"📥 التحميلات: {book_stats['total_downloads']} | التقييم: {book_stats['average_rating']}\n\n"
        text += f"👥 المستخدمين: {user_stats['total']} | النشطين: {user_stats['active']}\n"
        text += f"🚫 المحظورين: {user_stats['banned']} | 👑 المميزين: {user_stats['premium']}\n\n"
        text += "🏆 أفضل المستخدمين:\n"

        for i, up in enumerate(top_users, 1):
            text += f"{i}. نقاط: {up.current_balance}\n"

        keyboard = get_back_to_admin_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "admin_pending_books")
async def callback_admin_pending_books(callback: CallbackQuery):
    """كتب قيد المراجعة"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        book_service = BookService(db)
        books = book_service.get_pending_books(limit=20)

        if not books:
            await callback.message.edit_text(
                "✅ لا توجد كتب قيد المراجعة",
                reply_markup=get_back_to_admin_keyboard()
            )
            return

        text = "📚 كتب قيد المراجعة:\n\n"
        for book in books:
            text += f"📖 {truncate_text(book.title, 35)}\n   ID: {book.id}\n\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for book in books[:10]:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"📖 {truncate_text(book.title, 20)}",
                    callback_data=f"admin_book_review_{book.id}"
                )
            ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu")
        ])

        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_book_review_"))
async def callback_admin_book_review(callback: CallbackQuery):
    """مراجعة كتاب"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    book_id = int(callback.data.split("_")[-1])

    db = SessionLocal()
    try:
        book_service = BookService(db)
        book = book_service.get_book(book_id)

        if not book:
            await callback.answer("الكتاب غير موجود", show_alert=True)
            return

        text = f"📖 {book.title}\n\n"
        if book.author:
            text += f"✍️ المؤلف: {book.author.name}\n"
        if book.description:
            text += f"📝 الوصف: {truncate_text(book.description, 200)}\n"
        text += f"📅 التاريخ: {book.created_at.strftime('%Y-%m-%d')}"

        keyboard = get_admin_book_actions_keyboard(book_id)
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_book_approve_"))
async def callback_admin_book_approve(callback: CallbackQuery):
    """الموافقة على كتاب"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    book_id = int(callback.data.split("_")[-1])

    db = SessionLocal()
    try:
        book_service = BookService(db)
        book_service.approve_book(book_id)
        await callback.answer("✅ تم الموافقة على الكتاب", show_alert=True)
        await callback.message.edit_text(
            "✅ تم الموافقة على الكتاب بنجاح",
            reply_markup=get_back_to_admin_keyboard()
        )
    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_book_reject_"))
async def callback_admin_book_reject(callback: CallbackQuery):
    """رفض كتاب"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    book_id = int(callback.data.split("_")[-1])
    # TODO: طلب سبب الرفض من المستخدم

    db = SessionLocal()
    try:
        book_service = BookService(db)
        book_service.reject_book(book_id, "لم يتوافق مع معايير المكتبة")
        await callback.answer("❌ تم رفض الكتاب", show_alert=True)
        await callback.message.edit_text(
            "❌ تم رفض الكتاب",
            reply_markup=get_back_to_admin_keyboard()
        )
    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_book_delete_"))
async def callback_admin_book_delete(callback: CallbackQuery):
    """حذف كتاب"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    book_id = int(callback.data.split("_")[-1])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ نعم", callback_data=f"confirm_delete_book_{book_id}")],
        [InlineKeyboardButton(text="❌ لا", callback_data="admin_menu")]
    ])

    await callback.message.edit_text(
        "⚠️ هل أنت متأكد من حذف هذا الكتاب؟",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("confirm_delete_book_"))
async def callback_confirm_delete_book(callback: CallbackQuery):
    """تأكيد حذف كتاب"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    book_id = int(callback.data.split("_")[-1])

    db = SessionLocal()
    try:
        book_service = BookService(db)
        book_service.delete_book(book_id)
        await callback.answer("🗑️ تم حذف الكتاب", show_alert=True)
        await callback.message.edit_text(
            "🗑️ تم حذف الكتاب بنجاح",
            reply_markup=get_back_to_admin_keyboard()
        )
    finally:
        db.close()


@router.callback_query(F.data == "admin_categories")
async def callback_admin_categories(callback: CallbackQuery):
    """إدارة الأقسام"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    text = "📁 إدارة الأقسام"
    keyboard = get_admin_categories_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_cat_list")
async def callback_admin_cat_list(callback: CallbackQuery):
    """عرض الأقسام"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        category_service = CategoryService(db)
        categories = category_service.list_all(active_only=False)

        if not categories:
            await callback.message.edit_text(
                "لا توجد أقسام حالياً",
                reply_markup=get_admin_categories_keyboard()
            )
            return

        text = "📁 قائمة الأقسام:\n\n"
        for cat in categories:
            status = "✅" if cat.is_active else "❌"
            text += f"{status} {cat.name} (ID: {cat.id})\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_categories")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "admin_authors")
async def callback_admin_authors(callback: CallbackQuery):
    """إدارة المؤلفين"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    text = "✍️ إدارة المؤلفين"
    keyboard = get_admin_authors_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_auth_list")
async def callback_admin_auth_list(callback: CallbackQuery):
    """عرض المؤلفين"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        author_service = AuthorService(db)
        authors = author_service.list_all()

        if not authors:
            await callback.message.edit_text(
                "لا توجد مؤلفين حالياً",
                reply_markup=get_admin_authors_keyboard()
            )
            return

        text = "✍️ قائمة المؤلفين:\n\n"
        for auth in authors:
            text += f"• {auth.name} (ID: {auth.id})\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_authors")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "admin_channels")
async def callback_admin_channels(callback: CallbackQuery):
    """إدارة القنوات"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    text = "📡 إدارة قنوات الاشتراك الإجباري"
    keyboard = get_admin_channels_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_ch_list")
async def callback_admin_ch_list(callback: CallbackQuery):
    """عرض القنوات"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        channel_service = ChannelService(db)
        channels = channel_service.get_all_channels()

        if not channels:
            await callback.message.edit_text(
                "لا توجد قنوات اشتراك إجباري",
                reply_markup=get_admin_channels_keyboard()
            )
            return

        text = "📡 قنوات الاشتراك:\n\n"
        for ch in channels:
            status = "مطلوب" if ch.is_required else "اختياري"
            text += f"📢 {ch.channel_name or ch.channel_id}\n   الحالة: {status}\n\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_channels")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "admin_users")
async def callback_admin_users(callback: CallbackQuery):
    """إدارة المستخدمين"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    text = "🚫 إدارة المستخدمين"
    keyboard = get_admin_users_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_users_list")
async def callback_admin_users_list(callback: CallbackQuery):
    """عرض المستخدمين"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        user_service = UserService(db)
        users = user_service.get_all_users()[:30]

        text = "👥 قائمة المستخدمين:\n\n"
        for user in users:
            status_emoji = {"active": "✅", "banned": "🚫", "suspended": "⚠️"}.get(
                user.status.value, "❓"
            )
            name = user.first_name or user.username or user.telegram_id
            text += f"{status_emoji} {name}\n   ID: {user.telegram_id}\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_users")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "check_subscription")
async def callback_check_subscription(callback: CallbackQuery):
    """فحص الاشتراك"""
    db = SessionLocal()
    try:
        channel_service = ChannelService(db)
        bot = callback.bot

        is_subscribed, not_subscribed = await channel_service.check_all_subscriptions(
            bot, callback.from_user.id
        )

        if is_subscribed:
            await callback.answer("✅ تم التحقق من اشتراكك!", show_alert=True)
            await callback.message.edit_text(
                "✅ شكراً لك! تم التحقق من اشتراكك.\n\nاختر من القائمة:",
                reply_markup=get_main_menu_keyboard(is_owner(callback.from_user.id))
            )
        else:
            await callback.answer("⚠️ لازلت غير مشترك", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data == "points_leaderboard")
async def callback_points_leaderboard(callback: CallbackQuery):
    """لوحة النقاط"""
    db = SessionLocal()
    try:
        points_service = PointsService(db)
        top_users = points_service.get_leaderboard(limit=10)

        text = "🏆 لوحة المتصدرين:\n\n"
        medals = ["🥇", "🥈", "🥉"]

        for i, up in enumerate(top_users, 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            text += f"{medal} نقاط: {up.current_balance}\n"

        if not top_users:
            text = "لا توجد بيانات بعد"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="my_points")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "toggle_language")
async def callback_toggle_language(callback: CallbackQuery):
    """تبديل اللغة"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(callback.from_user.id)

        if user:
            user.language = "en" if user.language == "ar" else "ar"
            db.commit()

        await callback.answer("🌐 تم تغيير اللغة", show_alert=True)

        text = "⚙️ الإعدادات"
        keyboard = get_settings_keyboard(user.language if user else "ar")
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "search_text")
async def callback_search_text(callback: CallbackQuery, state: FSMContext):
    """البحث النصي"""
    await callback.message.edit_text("🔍 أدخل نص البحث:")
    await state.set_state(AdminStates.waiting_search)


@router.message(AdminStates.waiting_search)
async def handle_search(message: Message, state: FSMContext):
    """معالجة البحث"""
    query = message.text.strip()

    db = SessionLocal()
    try:
        search_service = SearchService(db)
        books, authors = search_service.text_search(query, limit=10)

        if not books and not authors:
            await message.answer(f"لم يتم العثور على نتائج لـ: {query}")
            return

        text = f"🔍 نتائج البحث عن: {query}\n\n"

        if books:
            text += "📚 الكتب:\n"
            for book in books[:5]:
                text += f"• {truncate_text(book.title, 40)}\n"

        if authors:
            text += "\n✍️ المؤلفين:\n"
            for auth in authors[:5]:
                text += f"• {auth.name}\n"

        keyboard = get_books_list_keyboard(books) if books else None
        await message.answer(text, reply_markup=keyboard)
    finally:
        db.close()
        await state.clear()


# ==========================================
# AI Assistant Handler
# ==========================================

@router.callback_query(F.data == "admin_ai")
async def callback_admin_ai(callback: CallbackQuery, state: FSMContext):
    """مساعد AI"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    await callback.message.edit_text(
        "🤖 مرحباً! أنا مساعد الذكاء الاصطناعي.\n\nأخبرني بما تحتاجه وسأساعدك.",
        reply_markup=get_back_to_admin_keyboard()
    )
    await state.set_state(AdminStates.waiting_ai_question)


@router.message(AdminStates.waiting_ai_question)
async def handle_ai_question(message: Message, state: FSMContext):
    """معالجة سؤال AI"""
    question = message.text

    if message.text == "🔙 رجوع":
        await state.clear()
        keyboard = get_admin_keyboard()
        await message.answer("👑 لوحة تحكم المالك", reply_markup=keyboard)
        return

    # استخدام AI للإجابة
    answer = await ai_service.answer_question(question, "أنت مساعد لمكتبة كتب عربية")

    await message.answer(f"🤖 {answer}")
    await state.clear()


# ==========================================
# New Admin Features Handlers - معالجات الميزات الجديدة للإدارة
# ==========================================

@router.callback_query(F.data == "admin_market")
async def callback_admin_market(callback: CallbackQuery):
    """إدارة السوق"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    text = "🏪 إدارة السوق"
    keyboard = get_admin_market_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_challenges")
async def callback_admin_challenges(callback: CallbackQuery):
    """إدارة التحديات"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    text = "🏆 إدارة التحديات"
    keyboard = get_admin_challenges_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_security")
async def callback_admin_security(callback: CallbackQuery):
    """إدارة الأمان"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    text = "🔒 إدارة الأمان والتدقيق"
    keyboard = get_admin_security_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_audit_log")
async def callback_admin_audit_log(callback: CallbackQuery):
    """سجل التدقيق"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        service = SecurityService(db)
        logs = service.get_recent_logs(limit=20)

        text = "📋 سجل التدقيق:\n\n"
        for log in logs:
            text += f"📌 {log.get('action', '')}\n"
            text += f"👤 المستخدم: {log.get('user_id', 'N/A')}\n"
            text += f"📅 {log.get('timestamp', '')}\n\n"

        if not logs:
            text = "📋 لا توجد سجلات تدقيق"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_security")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "admin_security_stats")
async def callback_admin_security_stats(callback: CallbackQuery):
    """إحصائيات الأمان"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        service = SecurityService(db)
        stats = service.get_security_stats()

        text = f"""
🔒 إحصائيات الأمان:

🚨 الأحداث المشبوهة: {stats.get('suspicious_events', 0)}
🚫 المحظورين: {stats.get('blocked_users', 0)}
📊 طلبات API: {stats.get('api_requests', 0)}
⚠️ محاولات الوصول الفاشلة: {stats.get('failed_attempts', 0)}
        """

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_security")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "admin_blacklist")
async def callback_admin_blacklist(callback: CallbackQuery):
    """القائمة السوداء"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        service = SecurityService(db)
        blocked = service.get_blocked_ips(limit=20)

        text = "🚫 القائمة السوداء:\n\n"
        for ip in blocked:
            text += f"🔒 {ip.get('ip_address', '')}\n"
            text += f"   السبب: {ip.get('reason', 'غير محدد')}\n\n"

        if not blocked:
            text = "🚫 لا توجد عناوين محظورة"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ إضافة عنوان", callback_data="admin_add_blacklist")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_security")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "admin_referral")
async def callback_admin_referral(callback: CallbackQuery):
    """إدارة الإحالات"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        service = ReferralService(db)
        stats = service.get_referral_stats(0)  # Platform-wide

        text = f"""
🎯 إحصائيات الإحالة للمنصة:

👥 إجمالي المحيلين: {stats.get('total_referrals', 0)}
💰 إجمالي الأرباح الموزعة: {stats.get('total_earnings', 0)} نقطة
🎖️ الشارات الممنوحة: {stats.get('badges_count', 0)}
        """

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 لوحة أفضل المحيلين", callback_data="admin_referral_leaderboard")],
            [InlineKeyboardButton(text="⚙️ إعدادات الإحالة", callback_data="admin_referral_settings")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "admin_notifications")
async def callback_admin_notifications(callback: CallbackQuery):
    """إدارة الإشعارات"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    text = """
🔔 إدارة الإشعارات:

📨 يمكنك إرسال إشعارات للمستخدمين
📊 عرض إحصائيات الإشعارات
⚙️ إدارة قوالب الإشعارات
"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 إرسال إشعار", callback_data="admin_send_notification")],
        [InlineKeyboardButton(text="📊 إحصائيات الإشعارات", callback_data="admin_notification_stats")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_leaderboard")
async def callback_admin_leaderboard(callback: CallbackQuery):
    """لوحة المتصدرين"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        challenge_service = ChallengeService(db)
        points_service = PointsService(db)

        text = "📊 لوحات المتصدرين:\n\n"

        # Points leaderboard
        text += "💰 نقاط المستخدمين:\n"
        top_points = points_service.get_leaderboard(limit=5)
        for i, up in enumerate(top_points, 1):
            text += f"{i}. نقاط: {up.current_balance}\n"

        text += "\n🏆 التحديات:\n"
        top_challenges = challenge_service.get_leaderboard("weekly", limit=5)
        for i, entry in enumerate(top_challenges, 1):
            text += f"{i}. {entry.get('user_name', 'مستخدم')}: {entry.get('score', 0)}\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "admin_market_stats")
async def callback_admin_market_stats(callback: CallbackQuery):
    """إحصائيات السوق"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        service = MarketService(db)
        stats = service.get_platform_earnings()

        text = f"""
🏪 إحصائيات السوق:

💰 إجمالي الإيرادات: {stats.get('total_earnings', 0)} نقطة
📦 إجمالي المعاملات: {stats.get('total_transactions', 0)}
🏆 المبيعات: {stats.get('sales_count', 0)}
🔨 المزادات: {stats.get('auctions_count', 0)}
        """

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_market")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


# ==========================================
# Error Handler
# ==========================================

@router.error()
async def error_handler(event, error):
    """معالج الأخطاء"""
    from app.utils.logger import get_logger
    logger = get_logger("handlers")
    logger.error(f"Error: {error}")
