"""
Notification Model - نموذج الإشعارات
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class NotificationType(enum.Enum):
    """نوع الإشعار"""
    BOOK_ADDED = "book_added"
    BOOK_APPROVED = "book_approved"
    BOOK_REJECTED = "book_rejected"
    POINTS_EARNED = "points_earned"
    POINTS_DEDUCTED = "points_deducted"
    REFERRAL_BONUS = "referral_bonus"
    COUPON_APPLIED = "coupon_applied"
    PACK_PURCHASED = "pack_purchased"
    SYSTEM = "system"


class Notification(Base):
    """نموذج الإشعار"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    metadata = Column(Text, nullable=True)  # JSON for additional data
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", backref="notifications")

    def __repr__(self):
        return f"<Notification {self.id} to {self.user_id}>"
