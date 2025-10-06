"""
識別碼解析器
用於識別和驗證各種業務識別碼類型
"""

import re
from typing import Optional, Tuple


class IdentifierResolver:
    """識別碼解析器"""
    
    # UUID 正則表達式
    UUID_PATTERN = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    
    @staticmethod
    def is_uuid(identifier: str) -> bool:
        """判斷是否為 UUID
        
        Args:
            identifier: 識別碼字符串
            
        Returns:
            bool: 是否為 UUID
        """
        if not identifier:
            return False
        return bool(re.match(IdentifierResolver.UUID_PATTERN, identifier.lower()))
    
    @staticmethod
    def is_member_no(identifier: str) -> bool:
        """判斷是否為會員號
        
        會員號格式：M + 9位數字 (如：M202501001)
        
        Args:
            identifier: 識別碼字符串
            
        Returns:
            bool: 是否為會員號
        """
        if not identifier:
            return False
        return identifier.startswith('M') and len(identifier) == 10 and identifier[1:].isdigit()
    
    @staticmethod
    def is_card_no(identifier: str) -> bool:
        """判斷是否為卡號
        
        卡號格式：C + 9位數字 (如：C202501001)
        
        Args:
            identifier: 識別碼字符串
            
        Returns:
            bool: 是否為卡號
        """
        if not identifier:
            return False
        return identifier.startswith('C') and len(identifier) == 10 and identifier[1:].isdigit()
    
    @staticmethod
    def is_phone(identifier: str) -> bool:
        """判斷是否為手機號
        
        手機號格式：11位數字
        
        Args:
            identifier: 識別碼字符串
            
        Returns:
            bool: 是否為手機號
        """
        if not identifier:
            return False
        return identifier.isdigit() and len(identifier) == 11
    
    @staticmethod
    def is_email(identifier: str) -> bool:
        """判斷是否為郵箱
        
        Args:
            identifier: 識別碼字符串
            
        Returns:
            bool: 是否為郵箱
        """
        if not identifier:
            return False
        return '@' in identifier and '.' in identifier
    
    @staticmethod
    def is_merchant_code(identifier: str) -> bool:
        """判斷是否為商戶代碼
        
        商戶代碼格式：M + 字母數字組合
        
        Args:
            identifier: 識別碼字符串
            
        Returns:
            bool: 是否為商戶代碼
        """
        if not identifier:
            return False
        # 商戶代碼通常是 M 開頭的字母數字組合
        return identifier.startswith('M') and len(identifier) >= 4
    
    @staticmethod
    def get_identifier_type(identifier: str) -> str:
        """獲取識別碼類型
        
        Args:
            identifier: 識別碼字符串
            
        Returns:
            str: 識別碼類型 (uuid, member_no, card_no, phone, email, merchant_code, unknown)
        """
        if not identifier:
            return 'unknown'
        
        identifier = identifier.strip()
        
        if IdentifierResolver.is_uuid(identifier):
            return 'uuid'
        elif IdentifierResolver.is_member_no(identifier):
            return 'member_no'
        elif IdentifierResolver.is_card_no(identifier):
            return 'card_no'
        elif IdentifierResolver.is_phone(identifier):
            return 'phone'
        elif IdentifierResolver.is_email(identifier):
            return 'email'
        elif IdentifierResolver.is_merchant_code(identifier):
            return 'merchant_code'
        else:
            return 'unknown'
    
    @staticmethod
    def validate_and_get_type(identifier: str) -> Tuple[bool, str]:
        """驗證識別碼並獲取類型
        
        Args:
            identifier: 識別碼字符串
            
        Returns:
            Tuple[bool, str]: (是否有效, 識別碼類型)
        """
        id_type = IdentifierResolver.get_identifier_type(identifier)
        is_valid = id_type != 'unknown'
        return is_valid, id_type
    
    @staticmethod
    def get_display_name(id_type: str) -> str:
        """獲取識別碼類型的顯示名稱
        
        Args:
            id_type: 識別碼類型
            
        Returns:
            str: 顯示名稱
        """
        display_names = {
            'uuid': 'UUID',
            'member_no': '會員號',
            'card_no': '卡號',
            'phone': '手機號',
            'email': '郵箱',
            'merchant_code': '商戶代碼',
            'unknown': '未知類型'
        }
        return display_names.get(id_type, '未知類型')
    
    @staticmethod
    def format_identifier(identifier: str, id_type: str = None) -> str:
        """格式化識別碼顯示
        
        Args:
            identifier: 識別碼字符串
            id_type: 識別碼類型（可選，自動檢測）
            
        Returns:
            str: 格式化後的識別碼
        """
        if not identifier:
            return ''
        
        if id_type is None:
            id_type = IdentifierResolver.get_identifier_type(identifier)
        
        # UUID 不應該顯示，但如果必須顯示則縮短
        if id_type == 'uuid':
            return f"{identifier[:8]}..."
        
        # 手機號格式化：138****8000
        if id_type == 'phone' and len(identifier) == 11:
            return f"{identifier[:3]}****{identifier[-4:]}"
        
        # 其他識別碼直接返回
        return identifier
