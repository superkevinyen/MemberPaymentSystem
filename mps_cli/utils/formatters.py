from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
import wcwidth

class Formatter:
    """數據格式化器"""
    
    @staticmethod
    def format_currency(amount: Any) -> str:
        """格式化貨幣"""
        if amount is None:
            return "¥0.00"
        try:
            return f"¥{float(amount):,.2f}"
        except (ValueError, TypeError):
            return "¥0.00"
    
    @staticmethod
    def format_datetime(dt: Any) -> str:
        """格式化日期時間"""
        if not dt:
            return ""
        
        if isinstance(dt, str):
            try:
                # 處理 ISO 格式的時間字符串
                if dt.endswith('Z'):
                    dt = dt[:-1] + '+00:00'
                dt = datetime.fromisoformat(dt)
            except ValueError:
                return dt
        
        if isinstance(dt, datetime):
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        
        return str(dt)
    
    @staticmethod
    def format_date(dt: Any) -> str:
        """格式化日期"""
        if not dt:
            return ""
        
        if isinstance(dt, str):
            try:
                if dt.endswith('Z'):
                    dt = dt[:-1] + '+00:00'
                dt = datetime.fromisoformat(dt)
            except ValueError:
                return dt
        
        if isinstance(dt, datetime):
            return dt.strftime("%Y-%m-%d")
        
        return str(dt)
    
    @staticmethod
    def format_time(dt: Any) -> str:
        """格式化時間"""
        if not dt:
            return ""
        
        if isinstance(dt, str):
            try:
                if dt.endswith('Z'):
                    dt = dt[:-1] + '+00:00'
                dt = datetime.fromisoformat(dt)
            except ValueError:
                return dt
        
        if isinstance(dt, datetime):
            return dt.strftime("%H:%M:%S")
        
        return str(dt)
    
    @staticmethod
    def format_percentage(value: Any) -> str:
        """格式化百分比"""
        if value is None:
            return "0%"
        try:
            return f"{float(value) * 100:.1f}%"
        except (ValueError, TypeError):
            return "0%"
    
    @staticmethod
    def format_card_no(card_no: str) -> str:
        """格式化卡號（部分遮蔽）"""
        if not card_no or len(card_no) < 8:
            return card_no
        return card_no[:4] + "****" + card_no[-4:]
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 20) -> str:
        """截斷文本，考慮中文字符寬度"""
        if not text:
            return ""
        
        # 計算實際顯示寬度
        current_width = 0
        result = ""
        
        for char in text:
            char_width = wcwidth.wcwidth(char) or 1
            if current_width + char_width > max_length:
                if current_width + 3 <= max_length:
                    result += "..."
                break
            result += char
            current_width += char_width
        
        return result
    
    @staticmethod
    def pad_text(text: str, width: int, align: str = 'left') -> str:
        """填充文本到指定寬度，考慮中文字符"""
        if not text:
            text = ""
        
        # 計算實際顯示寬度
        display_width = 0
        for char in text:
            display_width += wcwidth.wcwidth(char) or 1
        
        # 計算需要填充的空格數
        padding = max(0, width - display_width)
        
        if align == 'left':
            return text + ' ' * padding
        elif align == 'right':
            return ' ' * padding + text
        elif align == 'center':
            left_padding = padding // 2
            right_padding = padding - left_padding
            return ' ' * left_padding + text + ' ' * right_padding
        else:
            return text
    
    @staticmethod
    def format_phone(phone: str) -> str:
        """格式化手機號"""
        if not phone:
            return ""
        
        # 簡單的手機號格式化：138****1234
        if len(phone) == 11:
            return phone[:3] + "****" + phone[-4:]
        return phone
    
    @staticmethod
    def format_email(email: str) -> str:
        """格式化郵箱（部分遮蔽）"""
        if not email or '@' not in email:
            return email
        
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            return email
        
        return local[:2] + "***@" + domain
    
    @staticmethod
    def format_status(status: str, status_map: dict) -> str:
        """格式化狀態"""
        return status_map.get(status, status)
    
    @staticmethod
    def format_points(points: int) -> str:
        """格式化積分"""
        if points is None:
            return "0"
        return f"{points:,}"
    
    @staticmethod
    def format_level(level: int) -> str:
        """格式化等級"""
        if level is None:
            return "0"
        
        level_names = {
            0: "普通",
            1: "銀卡", 
            2: "金卡",
            3: "鑽石"
        }
        
        return level_names.get(level, str(level))
    
    @staticmethod
    def format_discount(discount: float) -> str:
        """格式化折扣"""
        if discount is None:
            return "無折扣"
        
        if discount >= 1.0:
            return "無折扣"
        
        return f"{discount * 100:.1f}折"
    
    @staticmethod
    def format_boolean(value: bool) -> str:
        """格式化布爾值"""
        return "是" if value else "否"
    
    @staticmethod
    def format_list(items: list, separator: str = ", ") -> str:
        """格式化列表"""
        if not items:
            return ""
        return separator.join(str(item) for item in items)
    
    @staticmethod
    def format_json_field(data: dict, field: str, default: str = "") -> str:
        """格式化 JSON 字段"""
        if not data or not isinstance(data, dict):
            return default
        return str(data.get(field, default))