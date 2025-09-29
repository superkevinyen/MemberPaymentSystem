from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from .base import BaseModel, StatusMixin, TimestampMixin
from config.constants import MEMBER_STATUS

@dataclass
class Member(BaseModel, StatusMixin, TimestampMixin):
    """會員模型"""
    
    member_no: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    binding_user_org: Optional[str] = None
    binding_org_id: Optional[str] = None
    role: Optional[str] = None
    owner_info: Optional[Dict[str, Any]] = None
    
    def get_display_name(self) -> str:
        """獲取顯示名稱"""
        if self.name:
            return self.name
        elif self.member_no:
            return self.member_no
        elif self.phone:
            return self.phone
        else:
            return super().get_display_name()
    
    def get_status_display(self) -> str:
        """獲取狀態顯示"""
        return super().get_status_display(MEMBER_STATUS)
    
    def get_contact_info(self) -> str:
        """獲取聯繫信息"""
        contacts = []
        if self.phone:
            contacts.append(f"手機: {self.phone}")
        if self.email:
            contacts.append(f"郵箱: {self.email}")
        return " | ".join(contacts) if contacts else "無聯繫信息"
    
    def has_external_binding(self) -> bool:
        """檢查是否有外部身份綁定"""
        return bool(self.binding_user_org and self.binding_org_id)
    
    def get_external_binding_info(self) -> str:
        """獲取外部綁定信息"""
        if not self.has_external_binding():
            return "無外部綁定"
        
        platform_names = {
            'wechat': '微信',
            'alipay': '支付寶',
            'line': 'LINE'
        }
        
        platform = platform_names.get(self.binding_user_org, self.binding_user_org)
        return f"{platform}: {self.binding_org_id}"
    
    def to_display_dict(self) -> Dict[str, str]:
        """轉換為顯示字典"""
        return {
            "會員號": self.member_no or "",
            "姓名": self.name or "",
            "手機": self.phone or "",
            "郵箱": self.email or "",
            "狀態": self.get_status_display(),
            "外部綁定": self.get_external_binding_info(),
            "創建時間": self.format_datetime("created_at")
        }

@dataclass
class MemberExternalIdentity(BaseModel, TimestampMixin):
    """會員外部身份模型"""
    
    member_id: Optional[str] = None
    provider: Optional[str] = None
    external_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    
    def get_provider_display(self) -> str:
        """獲取提供商顯示名稱"""
        provider_names = {
            'wechat': '微信',
            'alipay': '支付寶',
            'line': 'LINE',
            'facebook': 'Facebook',
            'google': 'Google'
        }
        return provider_names.get(self.provider, self.provider or "未知")
    
    def get_display_info(self) -> str:
        """獲取顯示信息"""
        return f"{self.get_provider_display()}: {self.external_id}"

@dataclass
class MembershipLevel(BaseModel, TimestampMixin):
    """會員等級模型"""
    
    level: Optional[int] = None
    name: Optional[str] = None
    min_points: Optional[int] = None
    max_points: Optional[int] = None
    discount: Optional[float] = None
    is_active: Optional[bool] = None
    
    def get_points_range(self) -> str:
        """獲取積分範圍"""
        if self.min_points is None:
            return "未設置"
        
        if self.max_points is None:
            return f"{self.min_points:,}+"
        else:
            return f"{self.min_points:,} - {self.max_points:,}"
    
    def get_discount_display(self) -> str:
        """獲取折扣顯示"""
        if self.discount is None or self.discount >= 1.0:
            return "無折扣"
        return f"{self.discount * 100:.1f}折"
    
    def is_points_in_range(self, points: int) -> bool:
        """檢查積分是否在範圍內"""
        if self.min_points is None:
            return False
        
        if points < self.min_points:
            return False
        
        if self.max_points is not None and points > self.max_points:
            return False
        
        return True
    
    def to_display_dict(self) -> Dict[str, str]:
        """轉換為顯示字典"""
        return {
            "等級": str(self.level or 0),
            "名稱": self.name or "",
            "積分範圍": self.get_points_range(),
            "折扣": self.get_discount_display(),
            "狀態": "激活" if self.is_active else "停用"
        }

class MemberHelper:
    """會員助手類"""
    
    @staticmethod
    def validate_member_data(data: Dict[str, Any]) -> List[str]:
        """驗證會員數據"""
        errors = []
        
        # 檢查必填字段
        required_fields = ['name', 'phone']
        for field in required_fields:
            if not data.get(field):
                errors.append(f"{field} 為必填項")
        
        # 驗證手機號格式
        phone = data.get('phone')
        if phone:
            from utils.validators import Validator
            if not Validator.validate_phone(phone):
                errors.append("手機號格式不正確")
        
        # 驗證郵箱格式
        email = data.get('email')
        if email:
            from utils.validators import Validator
            if not Validator.validate_email(email):
                errors.append("郵箱格式不正確")
        
        # 驗證姓名
        name = data.get('name')
        if name:
            from utils.validators import Validator
            if not Validator.validate_name(name):
                errors.append("姓名格式不正確")
        
        return errors
    
    @staticmethod
    def format_member_for_display(member: Member) -> Dict[str, str]:
        """格式化會員信息用於顯示"""
        from utils.formatters import Formatter
        
        return {
            "會員號": member.member_no or "",
            "姓名": member.name or "",
            "手機": Formatter.format_phone(member.phone or ""),
            "郵箱": Formatter.format_email(member.email or ""),
            "狀態": member.get_status_display(),
            "創建時間": member.format_datetime("created_at")
        }
    
    @staticmethod
    def search_members_by_keyword(members: List[Member], keyword: str) -> List[Member]:
        """按關鍵字搜索會員"""
        if not keyword:
            return members
        
        keyword = keyword.lower()
        results = []
        
        for member in members:
            # 搜索姓名、手機號、郵箱、會員號
            searchable_fields = [
                member.name or "",
                member.phone or "",
                member.email or "",
                member.member_no or ""
            ]
            
            if any(keyword in field.lower() for field in searchable_fields):
                results.append(member)
        
        return results