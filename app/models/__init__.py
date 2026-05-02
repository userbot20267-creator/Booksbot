"""
Models Module - نماذج قاعدة البيانات
"""
from app.models.user import User
from app.models.book import Book, BookCategory
from app.models.author import Author
from app.models.favorite import Favorite
from app.models.download_history import DownloadHistory
from app.models.channel_setting import ForceJoinChannel, ChannelSetting
from app.models.points import UserPoints, PointsTransaction
from app.models.review import Review
from app.models.referral import Referral
from app.models.coupon import Coupon
from app.models.pack import Pack
from app.models.notification import Notification
from app.models.admin import AdminUser, AdminLog

# Marketplace Models
from app.models.market import (
    MarketListing,
    AuctionBid,
    MarketTransaction,
    Wishlist,
    PriceHistory,
)

# Recommendations Models
from app.models.recommendations import (
    UserBehavior,
    UserPreference,
    Recommendation,
    ReadingHistory,
    UserSegment,
)

# Referral System Models
from app.models.referral_system import (
    ReferralCode,
    ReferralSettings,
    ReferralEarning,
    ReferralBadge,
    ReferralLevel,
)

# Challenges Models
from app.models.challenges import (
    Challenge,
    ChallengeParticipation,
    Badge,
    Milestone,
    DailyStreak,
    Leaderboard,
)

# Smart Notifications Models
from app.models.smart_notifications import (
    NotificationTemplate,
    UserNotificationSettings,
)

# Security Models
from app.models.security import (
    AuditLog,
    SecurityEvent,
    RateLimit,
    IPBlacklist,
)

__all__ = [
    "User",
    "Book",
    "BookCategory",
    "Author",
    "Favorite",
    "DownloadHistory",
    "ForceJoinChannel",
    "ChannelSetting",
    "UserPoints",
    "PointsTransaction",
    "Review",
    "Referral",
    "Coupon",
    "Pack",
    "Notification",
    "AdminUser",
    "AdminLog",
    # Marketplace
    "MarketListing",
    "AuctionBid",
    "MarketTransaction",
    "Wishlist",
    "PriceHistory",
    # Recommendations
    "UserBehavior",
    "UserPreference",
    "Recommendation",
    "ReadingHistory",
    "UserSegment",
    # Referral System
    "ReferralCode",
    "ReferralSettings",
    "ReferralEarning",
    "ReferralBadge",
    "ReferralLevel",
    # Challenges
    "Challenge",
    "ChallengeParticipation",
    "Badge",
    "Milestone",
    "DailyStreak",
    "Leaderboard",
    # Smart Notifications
    "NotificationTemplate",
    "UserNotificationSettings",
    # Security
    "AuditLog",
    "SecurityEvent",
    "RateLimit",
    "IPBlacklist",
]
