"""
Channel Service - خدمة القنوات
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.channel_setting import ForceJoinChannel, ChannelSetting


class ChannelService:
    """خدمة إدارة القنوات"""

    def __init__(self, db: Session):
        self.db = db

    def add_channel(
        self,
        channel_id: str,
        channel_name: Optional[str] = None,
        channel_link: Optional[str] = None,
        is_required: bool = True
    ) -> ForceJoinChannel:
        """إضافة قناة اشتراك إجباري"""
        # التحقق من عدم وجود القناة مسبقاً
        existing = self.get_channel(channel_id)
        if existing:
            return existing

        channel = ForceJoinChannel(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_link=channel_link,
            is_required=is_required
        )
        self.db.add(channel)
        self.db.commit()
        self.db.refresh(channel)
        return channel

    def remove_channel(self, channel_id: str) -> bool:
        """حذف قناة"""
        channel = self.get_channel(channel_id)
        if not channel:
            return False

        self.db.delete(channel)
        self.db.commit()
        return True

    def get_channel(self, channel_id: str) -> Optional[ForceJoinChannel]:
        """الحصول على قناة بالمعرف"""
        return self.db.query(ForceJoinChannel).filter(
            ForceJoinChannel.channel_id == channel_id
        ).first()

    def get_all_channels(self) -> List[ForceJoinChannel]:
        """الحصول على جميع قنوات الاشتراك الإجباري"""
        return self.db.query(ForceJoinChannel).all()

    def update_channel(
        self,
        channel_id: str,
        channel_name: Optional[str] = None,
        channel_link: Optional[str] = None,
        is_required: Optional[bool] = None
    ) -> Optional[ForceJoinChannel]:
        """تحديث قناة"""
        channel = self.get_channel(channel_id)
        if not channel:
            return None

        if channel_name is not None:
            channel.channel_name = channel_name
        if channel_link is not None:
            channel.channel_link = channel_link
        if is_required is not None:
            channel.is_required = is_required

        self.db.commit()
        self.db.refresh(channel)
        return channel

    async def check_subscription(self, bot, user_id: int, channel_id: str) -> bool:
        """فحص اشتراك المستخدم في القناة"""
        try:
            chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            return chat_member.status in ['member', 'administrator', 'creator']
        except Exception:
            return False

    async def check_all_subscriptions(self, bot, user_id: int) -> tuple[bool, List[ForceJoinChannel]]:
        """فحص جميع الاشتراكات الإلزامية"""
        required_channels = self.db.query(ForceJoinChannel).filter(
            ForceJoinChannel.is_required == True
        ).all()

        not_subscribed = []
        for channel in required_channels:
            if not await self.check_subscription(bot, user_id, channel.channel_id):
                not_subscribed.append(channel)

        return len(not_subscribed) == 0, not_subscribed

    # إعدادات النشر
    def setup_auto_post(
        self,
        channel_id: str,
        channel_name: Optional[str] = None,
        auto_post: bool = False,
        post_template: Optional[str] = None
    ) -> ChannelSetting:
        """إعداد النشر التلقائي"""
        setting = self.get_setting(channel_id)
        if setting:
            setting.auto_post = auto_post
            setting.post_template = post_template
            self.db.commit()
            self.db.refresh(setting)
            return setting

        setting = ChannelSetting(
            channel_id=channel_id,
            channel_name=channel_name,
            auto_post=auto_post,
            post_template=post_template
        )
        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def get_setting(self, channel_id: str) -> Optional[ChannelSetting]:
        """الحصول على إعدادات قناة نشر"""
        return self.db.query(ChannelSetting).filter(
            ChannelSetting.channel_id == channel_id
        ).first()

    def get_all_settings(self) -> List[ChannelSetting]:
        """الحصول على جميع إعدادات النشر"""
        return self.db.query(ChannelSetting).all()

    def toggle_auto_post(self, channel_id: str) -> Optional[ChannelSetting]:
        """تبديل النشر التلقائي"""
        setting = self.get_setting(channel_id)
        if not setting:
            return None

        setting.auto_post = not setting.auto_post
        self.db.commit()
        self.db.refresh(setting)
        return setting
