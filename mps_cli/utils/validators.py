import re
import uuid
from typing import Any, Union
from decimal import Decimal

class Validator:
    """輸入驗證器"""
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """驗證手機號"""
        if not phone:
            return False
        
        # 中國大陸手機號格式：1開頭，第二位是3-9，總共11位
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """驗證郵箱"""
        if not email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_amount(amount: Any) -> bool:
        """驗證金額"""
        try:
            value = float(amount)
            return value > 0 and value <= 999999.99  # 設置合理上限
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_positive_amount(amount: Any) -> bool:
        """驗證正數金額"""
        try:
            value = float(amount)
            return value > 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_card_id(card_id: str) -> bool:
        """驗證卡片 ID 格式（UUID）"""
        if not card_id:
            return False
        
        try:
            uuid.UUID(card_id)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_member_id(member_id: str) -> bool:
        """驗證會員 ID 格式（UUID）"""
        return Validator.validate_card_id(member_id)  # 同樣是 UUID 格式
    
    @staticmethod
    def validate_tx_no(tx_no: str) -> bool:
        """驗證交易號格式"""
        if not tx_no:
            return False
        
        # PAY/REF/RCG + 10位數字
        pattern = r'^(PAY|REF|RCG)\d{10}$'
        return bool(re.match(pattern, tx_no))
    
    @staticmethod
    def validate_merchant_code(code: str) -> bool:
        """驗證商戶代碼"""
        if not code:
            return False
        
        # 商戶代碼：3-20位字母數字
        pattern = r'^[A-Za-z0-9]{3,20}$'
        return bool(re.match(pattern, code))
    
    @staticmethod
    def validate_qr_code(qr_code: str) -> bool:
        """驗證 QR 碼格式"""
        if not qr_code:
            return False
        
        # QR 碼至少16位字符
        return len(qr_code.strip()) >= 16
    
    @staticmethod
    def validate_password(password: str) -> bool:
        """驗證密碼強度"""
        if not password:
            return False
        
        # 密碼至少6位
        return len(password) >= 6
    
    @staticmethod
    def validate_name(name: str) -> bool:
        """驗證姓名"""
        if not name:
            return False
        
        # 姓名：2-50位字符，支持中文、英文、空格
        name = name.strip()
        if len(name) < 2 or len(name) > 50:
            return False
        
        # 只允許中文、英文字母、空格
        pattern = r'^[\u4e00-\u9fa5a-zA-Z\s]+$'
        return bool(re.match(pattern, name))
    
    @staticmethod
    def validate_points(points: Any) -> bool:
        """驗證積分"""
        try:
            value = int(points)
            return value >= 0 and value <= 999999  # 設置合理上限
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_level(level: Any) -> bool:
        """驗證等級"""
        try:
            value = int(level)
            return 0 <= value <= 10  # 等級範圍 0-10
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_discount(discount: Any) -> bool:
        """驗證折扣率"""
        try:
            value = float(discount)
            return 0.1 <= value <= 1.0  # 折扣範圍 10%-100%
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_choice(choice: str, max_choice: int) -> bool:
        """驗證選擇項"""
        try:
            value = int(choice)
            return 1 <= value <= max_choice
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_page_number(page: Any) -> bool:
        """驗證頁碼"""
        try:
            value = int(page)
            return value >= 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_limit(limit: Any) -> bool:
        """驗證限制數量"""
        try:
            value = int(limit)
            return 1 <= value <= 1000  # 合理的查詢限制
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_date_string(date_str: str) -> bool:
        """驗證日期字符串格式 YYYY-MM-DD"""
        if not date_str:
            return False
        
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date_str):
            return False
        
        # 進一步驗證日期有效性
        try:
            from datetime import datetime
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_external_id(external_id: str) -> bool:
        """驗證外部身份 ID"""
        if not external_id:
            return False
        
        # 外部 ID：3-100位字符
        return 3 <= len(external_id.strip()) <= 100
    
    @staticmethod
    def validate_provider(provider: str) -> bool:
        """驗證外部身份提供商"""
        if not provider:
            return False
        
        valid_providers = ['wechat', 'alipay', 'line', 'facebook', 'google']
        return provider.lower() in valid_providers
    
    @staticmethod
    def validate_card_type(card_type: str) -> bool:
        """驗證卡片類型"""
        if not card_type:
            return False
        
        valid_types = ['standard', 'prepaid', 'corporate', 'voucher']
        return card_type.lower() in valid_types
    
    @staticmethod
    def validate_payment_method(method: str) -> bool:
        """驗證支付方式"""
        if not method:
            return False
        
        valid_methods = ['balance', 'cash', 'wechat', 'alipay']
        return method.lower() in valid_methods
    
    @staticmethod
    def validate_bind_role(role: str) -> bool:
        """驗證綁定角色"""
        if not role:
            return False
        
        valid_roles = ['owner', 'admin', 'member', 'viewer']
        return role.lower() in valid_roles
    
    @staticmethod
    def validate_settlement_mode(mode: str) -> bool:
        """驗證結算模式"""
        if not mode:
            return False
        
        valid_modes = ['realtime', 't_plus_1', 'monthly']
        return mode.lower() in valid_modes
    
    @staticmethod
    def validate_non_empty(value: str) -> bool:
        """驗證非空字符串"""
        return bool(value and value.strip())
    
    @staticmethod
    def validate_length(value: str, min_length: int = 0, max_length: int = 255) -> bool:
        """驗證字符串長度"""
        if not value:
            return min_length == 0
        
        return min_length <= len(value) <= max_length