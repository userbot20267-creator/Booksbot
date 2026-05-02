"""
Smart Notifications Models - نماذج الإشعارات الذكية
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.database import Base


class NotificationType(enum.Enum):
    """أنواع الإشعارات"""
    # إشعارات الكتب
    NEW_BOOK = "new_book"
    BOOK_UPDATE = "book_update"
    AUTHOR_NEW_BOOK = "author_new_book"
    CATEGORY_NEW_BOOK = "category_new_book"

    # إشعارات السوق
    PRICE_DROP = "price_drop"
    WISHLIST_AVAILABLE = "wishlist_available"
    AUCTION_ENDING = "auction_ending"
    OUTBID = "outbid"

    # إشعارات المجتمع
    NEW_REVIEW = "new_review"
    NEW_FOLLOWER = "new_follower"
    FRIEND_ACTIVITY = "friend_activity"
    CHALLENGE_INVITE = "challenge_invite"

    # إشعارات النقاط
    POINTS_EARNED = "points_earned"
    POINTS_EXPIRED = "points_expired"
    LEVEL_UP = "level_up"
    REFERRAL_SIGNUP = "referral_signup"

    # إشعارات التحديات
    CHALLENGE_AVAILABLE = "challenge_available"
    CHALLENGE_COMPLETED = "challenge_completed"
    CHALLENGE_EXPIRED = "challenge_expired"
    BADGE_EARNED = "badge_earned"
    STREAK_BONUS = "streak_bonus"

    # إشعارات النظام
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    MAINTENANCE = "maintenance"
    POLICY_UPDATE = "policy_update"

    # إشعارات شخصية
    DIRECT_MESSAGE = "direct_message"
    REPLY = "reply"
    MENTION = "mention"


class NotificationPriority(enum.Enum):
    """أولوية الإشعار"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(enum.Enum):
    """حالة الإشعار"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    DISMISSED = "dismissed"


class UserNotificationSettings(Base):
    """إعدادات إشعارات المستخدم"""
    __tablename__ = "user_notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # تفعيل/إيقاف أنواع الإشعارات
    new_book = Column(Boolean, default=True)
    author_new_book = Column(Boolean, default=True)
    category_new_book = Column(Boolean, default=False)

    price_alerts = Column(Boolean, default=True)
    wishlist_alerts = Column(Boolean, default=True)
    auction_alerts = Column(Boolean, default=True)

    social_notifications = Column(Boolean, default=True)
    challenge_notifications = Column(Boolean, default=True)

    points_notifications = Column(Boolean, default=True)
    level_notifications = Column(Boolean, default=True)

    system_notifications = Column(Boolean, default=True)
    direct_messages = Column(Boolean, default=True)

    # تفضيلات التوقيت
    quiet_hours_start = Column(String(10), default="22:00")  # 10 PM
    quiet_hours_end = Column(String(10), default="08:00")   # 8 AM
    timezone = Column(String(50), default="UTC")

    # تجميع الإشعارات
    batch_notifications = Column(Boolean, default=True)
    batch_interval_hours = Column(Integer, default=24)

    # أذونات إضافية
    email_notifications = Column(Boolean, default=False)
    push_notifications = Column(Boolean, default=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="notification_settings")

    def __repr__(self):
        return f"<UserNotificationSettings user={self.user_id}>"


class Notification(Base):
    """الإشعار"""
    __tablename__ = "smart_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    notification_type = Column(Enum(NotificationType), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)

    # محتوى الإشعار
    title = Column(String(200), nullable=False)
    title_ar = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    message_ar = Column(Text, nullable=True)

    # بيانات مرتبطة
    related_type = Column(String(50), nullable=True)  # book, user, challenge, etc.
    related_id = Column(Integer, nullable=True)

    # الأزرار والإجراءات
    action_buttons = Column(JSON, nullable=True)  # [{"text": "View", "action": "view_book", "data": "123"}]
    action_url = Column(String(500), nullable=True)

    # الوسائط
    image_url = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)

    # الحالة والتتبع
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING)
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)

    # توقيت الإرسال
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    # فشل الإرسال
    failed_at = Column(DateTime, nullable=True)
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # تجميع
    batch_id = Column(String(100), nullable=True)  # لتجميع إشعارات متشابهة
    batch_count = Column(Integer, default=1)  # عدد الإشعارات المجمعة

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="notifications")
    preferences = relationship("NotificationPreference", back_populates="notification", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Notification {self.id} type={self.notification_type}>"


class NotificationPreference(Base):
    """تفضيل المستخدم لإشعار معين"""
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("smart_notifications.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    is_enabled = Column(Boolean, default=True)
    last_interaction = Column(DateTime, nullable=True)

    # Relationships
    notification = relationship("Notification", back_populates="preferences")
    user = relationship("User")

    def __repr__(self):
        return f"<NotificationPreference notification={self.notification_id}>"


class NotificationTemplate(Base):
    """قوالب الإشعارات"""
    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_code = Column(String(100), nullable=False, unique=True)

    notification_type = Column(Enum(NotificationType), nullable=False)

    # النصوص
    title_template = Column(String(200), nullable=False)
    title_template_ar = Column(String(200), nullable=True)
    message_template = Column(Text, nullable=False)
    message_template_ar = Column(Text, nullable=True)

    # الأيقونات
    icon = Column(String(100), nullable=True)
    default_image_url = Column(String(500), nullable=True)

    # الأزرار الافتراضية
    default_buttons = Column(JSON, nullable=True)

    # الحالة
    is_active = Column(Boolean, default=True)

    # متغيرات القالب المتاحة
    available_variables = Column(JSON, nullable=True)  # ["user_name", "book_title", "points"]

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<NotificationTemplate {self.template_code}>"


class NotificationSchedule(Base):
    """جدولة الإشعارات الجماعية"""
    __tablename__ = "notification_schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)

    notification_type = Column(Enum(NotificationType), nullable=False)

    # targeting
    target_criteria = Column(JSON, nullable=True)  # {"segments": [1, 2], "countries": ["SA", "AE"]}

    # التوقيت
    scheduled_at = Column(DateTime, nullable=True)
    repeat_interval = Column(String(50), nullable=True)  # daily, weekly, monthly
    repeat_count = Column(Integer, default=1)

    # البيانات
    data = Column(JSON, nullable=True)  # البيانات المراد استخدامها في القالب

    status = Column(String(20), default="pending")  # pending, running, completed, cancelled
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<NotificationSchedule {self.name}>"


class NotificationAnalytics(Base):
    """تحليلات الإشعارات"""
    __tablename__ = "notification_analytics"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("smart_notifications.id"), nullable=False)

    # التحليلات
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    action_taken_at = Column(DateTime, nullable=True)

    # الأوقات
    time_to_deliver = Column(Integer, nullable=True)  # بالثواني
    time_to_read = Column(Integer, nullable=True)
    time_to_action = Column(Integer, nullable=True)

    # الأحداث
    action_type = Column(String(50), nullable=True)  # view, download, purchase, etc.
    action_data = Column(JSON, nullable=True)

    # Relationships
    notification = relationship("Notification", backref="analytics")

    def __repr__(self):
        return f"<NotificationAnalytics notification={self.notification_id}>"
