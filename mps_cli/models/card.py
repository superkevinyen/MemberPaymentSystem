from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from decimal import Decimal
from .base import BaseModel, StatusMixin, TimestampMixin
from config.constants import CARD_TYPES, CARD_STATUS, BIND_ROLES

@dataclass
class Card(BaseModel, StatusMixin, TimestampMixin):
    """卡片模型"""
    
    card_no: Optional[str] = None
    card_type: Optional[str] = None
    owner_member_id: Optional[str] = None
    name: Optional[str] = None
    balance: Optional[float] = None
    points: Optional[int] = None
    level: Optional[int] = None
    discount_rate: Optional[float] = None
    fixed_discount: Optional[float] = None
    binding_password_hash: Optional[str] = None
    expires_at: Optional[str] = None
    
    def get_display_name(self) -> str:
        """獲取顯示名稱"""
        if self.name:
            return self.name
        elif self.card_no:
            return self.card_no
        else:
            return super().get_display_name()
    
    def get_card_type_display(self) -> str:
        """獲取卡片類型顯示"""
        return CARD_TYPES.get(self.card_type, self.card_type or "未知")
    
    def get_status_display(self) -> str:
        """獲取狀態顯示"""
        return super().get_status_display(CARD_STATUS)
    
    def display_info(self) -> str:
        """顯示卡片信息"""
        from utils.formatters import Formatter
        
        card_type_name = self.get_card_type_display()
        status_name = self.get_status_display()
        balance_str = Formatter.format_currency(self.balance or 0)
        
        return f"{self.card_no} ({card_type_name}) - 餘額: {balance_str} - {status_name}"
    
    def can_recharge(self) -> bool:
        """檢查是否可以充值"""
        return (self.card_type == 'standard' and 
                self.status == 'active')
    
    def can_share(self) -> bool:
        """檢查是否可以共享"""
        return self.card_type == 'corporate'
    
    def can_generate_qr(self) -> bool:
        """檢查是否可以生成 QR 碼"""
        return self.status == 'active'
    
    def can_pay(self) -> bool:
        """檢查是否可以支付"""
        return (self.status == 'active' and 
                (self.balance or 0) > 0)
    
    def is_expired(self) -> bool:
        """檢查是否過期"""
        if not self.expires_at:
            return False
        
        from datetime import datetime
        try:
            if self.expires_at.endswith('Z'):
                expire_time_str = self.expires_at[:-1] + '+00:00'
            else:
                expire_time_str = self.expires_at
            
            expire_time = datetime.fromisoformat(expire_time_str)
            return datetime.now(expire_time.tzinfo) > expire_time
        except ValueError:
            return False
    
    def get_level_display(self) -> str:
        """獲取等級顯示"""
        from utils.formatters import Formatter
        return Formatter.format_level(self.level or 0)
    
    def get_discount_display(self) -> str:
        """獲取折扣顯示"""
        from utils.formatters import Formatter
        
        if self.fixed_discount is not None:
            return Formatter.format_discount(self.fixed_discount)
        elif self.discount_rate is not None:
            return Formatter.format_discount(self.discount_rate)
        else:
            return "無折扣"
    
    def to_display_dict(self) -> Dict[str, str]:
        """轉換為顯示字典"""
        from utils.formatters import Formatter
        
        return {
            "卡號": self.card_no or "",
            "類型": self.get_card_type_display(),
            "餘額": Formatter.format_currency(self.balance or 0),
            "積分": Formatter.format_points(self.points or 0),
            "等級": self.get_level_display(),
            "折扣": self.get_discount_display(),
            "狀態": self.get_status_display(),
            "過期時間": self.format_datetime("expires_at") if self.expires_at else "永久有效"
        }

@dataclass
class CardBinding(BaseModel, TimestampMixin):
    """卡片綁定模型"""
    
    card_id: Optional[str] = None
    member_id: Optional[str] = None
    role: Optional[str] = None
    
    def get_role_display(self) -> str:
        """獲取角色顯示"""
        return BIND_ROLES.get(self.role, self.role or "未知")
    
    def is_owner(self) -> bool:
        """檢查是否是擁有者"""
        return self.role == "owner"
    
    def is_admin(self) -> bool:
        """檢查是否是管理員"""
        return self.role == "admin"
    
    def can_manage(self) -> bool:
        """檢查是否可以管理"""
        return self.role in ["owner", "admin"]
    
    def can_view_only(self) -> bool:
        """檢查是否只能查看"""
        return self.role == "viewer"

@dataclass
class QRCode(BaseModel, TimestampMixin):
    """QR 碼模型"""
    
    card_id: Optional[str] = None
    qr_plain: Optional[str] = None
    expires_at: Optional[str] = None
    
    def is_expired(self) -> bool:
        """檢查是否過期"""
        if not self.expires_at:
            return True
        
        from datetime import datetime
        try:
            if self.expires_at.endswith('Z'):
                expire_time_str = self.expires_at[:-1] + '+00:00'
            else:
                expire_time_str = self.expires_at
            
            expire_time = datetime.fromisoformat(expire_time_str)
            return datetime.now(expire_time.tzinfo) > expire_time
        except ValueError:
            return True
    
    def get_remaining_time(self) -> str:
        """獲取剩餘時間"""
        if not self.expires_at or self.is_expired():
            return "已過期"
        
        from datetime import datetime
        try:
            if self.expires_at.endswith('Z'):
                expire_time_str = self.expires_at[:-1] + '+00:00'
            else:
                expire_time_str = self.expires_at
            
            expire_time = datetime.fromisoformat(expire_time_str)
            now = datetime.now(expire_time.tzinfo)
            
            if expire_time <= now:
                return "已過期"
            
            remaining = expire_time - now
            total_seconds = int(remaining.total_seconds())
            
            if total_seconds >= 3600:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                return f"{hours}小時{minutes}分鐘"
            elif total_seconds >= 60:
                minutes = total_seconds // 60
                return f"{minutes}分鐘"
            else:
                return f"{total_seconds}秒"
                
        except ValueError:
            return "未知"
    
    def get_display_qr(self, max_length: int = 25) -> str:
        """獲取顯示用的 QR 碼"""
        if not self.qr_plain:
            return ""
        
        from utils.formatters import Formatter
        return Formatter.truncate_text(self.qr_plain, max_length)
    
    def to_display_dict(self) -> Dict[str, str]:
        """轉換為顯示字典"""
        return {
            "QR 碼": self.get_display_qr(),
            "生成時間": self.format_datetime("created_at"),
            "過期時間": self.format_datetime("expires_at"),
            "剩餘時間": self.get_remaining_time(),
            "狀態": "有效" if not self.is_expired() else "已過期"
        }

class CardHelper:
    """卡片助手類"""
    
    @staticmethod
    def filter_cards_by_type(cards: List[Card], card_type: str) -> List[Card]:
        """按類型過濾卡片"""
        return [card for card in cards if card.card_type == card_type]
    
    @staticmethod
    def filter_active_cards(cards: List[Card]) -> List[Card]:
        """過濾激活的卡片"""
        return [card for card in cards if card.is_active()]
    
    @staticmethod
    def filter_rechargeable_cards(cards: List[Card]) -> List[Card]:
        """過濾可充值的卡片"""
        return [card for card in cards if card.can_recharge()]
    
    @staticmethod
    def sort_cards_by_balance(cards: List[Card], descending: bool = True) -> List[Card]:
        """按餘額排序卡片"""
        return sorted(cards, 
                     key=lambda x: x.balance or 0, 
                     reverse=descending)
    
    @staticmethod
    def sort_cards_by_points(cards: List[Card], descending: bool = True) -> List[Card]:
        """按積分排序卡片"""
        return sorted(cards, 
                     key=lambda x: x.points or 0, 
                     reverse=descending)
    
    @staticmethod
    def get_total_balance(cards: List[Card]) -> float:
        """獲取總餘額"""
        return sum(card.balance or 0 for card in cards)
    
    @staticmethod
    def get_total_points(cards: List[Card]) -> int:
        """獲取總積分"""
        return sum(card.points or 0 for card in cards)
    
    @staticmethod
    def format_cards_for_selection(cards: List[Card]) -> List[str]:
        """格式化卡片用於選擇"""
        return [card.display_info() for card in cards]
    
    @staticmethod
    def find_card_by_no(cards: List[Card], card_no: str) -> Optional[Card]:
        """按卡號查找卡片"""
        for card in cards:
            if card.card_no == card_no:
                return card
        return None
    
    @staticmethod
    def validate_card_data(data: Dict[str, Any]) -> List[str]:
        """驗證卡片數據"""
        errors = []
        
        # 檢查卡片類型
        card_type = data.get('card_type')
        if card_type:
            from utils.validators import Validator
            if not Validator.validate_card_type(card_type):
                errors.append("卡片類型不正確")
        
        # 檢查餘額
        balance = data.get('balance')
        if balance is not None:
            try:
                balance_val = float(balance)
                if balance_val < 0:
                    errors.append("餘額不能為負數")
            except (ValueError, TypeError):
                errors.append("餘額格式不正確")
        
        # 檢查積分
        points = data.get('points')
        if points is not None:
            from utils.validators import Validator
            if not Validator.validate_points(points):
                errors.append("積分格式不正確")
        
        return errors