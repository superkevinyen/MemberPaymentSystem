from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from decimal import Decimal
from .base import BaseModel, StatusMixin, TimestampMixin
from config.constants import TRANSACTION_TYPES, TRANSACTION_STATUS, PAYMENT_METHODS

@dataclass
class Transaction(BaseModel, StatusMixin, TimestampMixin):
    """交易模型"""
    
    tx_no: Optional[str] = None
    tx_type: Optional[str] = None
    card_id: Optional[str] = None
    merchant_id: Optional[str] = None
    raw_amount: Optional[float] = None
    discount_applied: Optional[float] = None
    final_amount: Optional[float] = None
    points_earned: Optional[int] = None
    reason: Optional[str] = None
    payment_method: Optional[str] = None
    external_order_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    original_tx_id: Optional[str] = None
    processed_by_user_id: Optional[str] = None
    tag: Optional[Dict[str, Any]] = None
    
    def get_tx_type_display(self) -> str:
        """獲取交易類型顯示"""
        return TRANSACTION_TYPES.get(self.tx_type, self.tx_type or "未知")
    
    def get_status_display(self) -> str:
        """獲取狀態顯示"""
        return super().get_status_display(TRANSACTION_STATUS)
    
    def get_payment_method_display(self) -> str:
        """獲取支付方式顯示"""
        return PAYMENT_METHODS.get(self.payment_method, self.payment_method or "未知")
    
    def display_summary(self) -> str:
        """顯示交易摘要"""
        from utils.formatters import Formatter
        
        tx_type_name = self.get_tx_type_display()
        status_name = self.get_status_display()
        amount_str = Formatter.format_currency(self.final_amount or 0)
        
        return f"{self.tx_no} | {tx_type_name} | {amount_str} | {status_name}"
    
    def is_payment(self) -> bool:
        """檢查是否是支付交易"""
        return self.tx_type == "payment"
    
    def is_refund(self) -> bool:
        """檢查是否是退款交易"""
        return self.tx_type == "refund"
    
    def is_recharge(self) -> bool:
        """檢查是否是充值交易"""
        return self.tx_type == "recharge"
    
    def is_completed(self) -> bool:
        """檢查是否已完成"""
        return self.status == "completed"
    
    def is_refunded(self) -> bool:
        """檢查是否已退款"""
        return self.status == "refunded"
    
    def can_refund(self) -> bool:
        """檢查是否可以退款"""
        return (self.is_payment() and 
                self.status in ["completed", "refunded"])
    
    def get_discount_info(self) -> str:
        """獲取折扣信息"""
        if not self.discount_applied or self.discount_applied >= 1.0:
            return "無折扣"
        
        from utils.formatters import Formatter
        return Formatter.format_percentage(self.discount_applied)
    
    def get_savings_amount(self) -> float:
        """獲取節省金額"""
        if not self.raw_amount or not self.final_amount:
            return 0.0
        
        return max(0, self.raw_amount - self.final_amount)
    
    def to_display_dict(self) -> Dict[str, str]:
        """轉換為顯示字典"""
        from utils.formatters import Formatter
        
        return {
            "交易號": self.tx_no or "",
            "類型": self.get_tx_type_display(),
            "原金額": Formatter.format_currency(self.raw_amount or 0),
            "折扣": self.get_discount_info(),
            "實際金額": Formatter.format_currency(self.final_amount or 0),
            "積分": Formatter.format_points(self.points_earned or 0),
            "支付方式": self.get_payment_method_display(),
            "狀態": self.get_status_display(),
            "時間": self.format_datetime("created_at")
        }
    
    def to_summary_dict(self) -> Dict[str, str]:
        """轉換為摘要字典"""
        from utils.formatters import Formatter
        
        return {
            "交易號": self.tx_no or "",
            "類型": self.get_tx_type_display(),
            "金額": Formatter.format_currency(self.final_amount or 0),
            "狀態": self.get_status_display(),
            "時間": self.format_datetime("created_at")
        }

@dataclass
class Merchant(BaseModel, TimestampMixin):
    """商戶模型"""
    
    code: Optional[str] = None
    name: Optional[str] = None
    contact: Optional[str] = None
    active: Optional[bool] = None
    
    def get_display_name(self) -> str:
        """獲取顯示名稱"""
        if self.name:
            return self.name
        elif self.code:
            return self.code
        else:
            return super().get_display_name()
    
    def is_active(self) -> bool:
        """檢查是否激活"""
        return self.active is True
    
    def get_status_display(self) -> str:
        """獲取狀態顯示"""
        return "激活" if self.is_active() else "停用"
    
    def to_display_dict(self) -> Dict[str, str]:
        """轉換為顯示字典"""
        return {
            "商戶代碼": self.code or "",
            "商戶名稱": self.name or "",
            "聯繫方式": self.contact or "",
            "狀態": self.get_status_display(),
            "創建時間": self.format_datetime("created_at")
        }

@dataclass
class Settlement(BaseModel, StatusMixin, TimestampMixin):
    """結算模型"""
    
    merchant_id: Optional[str] = None
    mode: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    total_amount: Optional[float] = None
    total_tx_count: Optional[int] = None
    payload: Optional[Dict[str, Any]] = None
    
    def get_mode_display(self) -> str:
        """獲取結算模式顯示"""
        from config.constants import SETTLEMENT_MODES
        return SETTLEMENT_MODES.get(self.mode, self.mode or "未知")
    
    def get_period_display(self) -> str:
        """獲取結算期間顯示"""
        start = self.format_date("period_start")
        end = self.format_date("period_end")
        
        if start and end:
            return f"{start} ~ {end}"
        elif start:
            return f"從 {start}"
        elif end:
            return f"至 {end}"
        else:
            return "未設置"
    
    def to_display_dict(self) -> Dict[str, str]:
        """轉換為顯示字典"""
        from utils.formatters import Formatter
        
        return {
            "結算 ID": self.id[:8] + "..." if self.id else "",
            "結算模式": self.get_mode_display(),
            "結算期間": self.get_period_display(),
            "交易筆數": str(self.total_tx_count or 0),
            "結算金額": Formatter.format_currency(self.total_amount or 0),
            "狀態": self.get_status_display({"pending": "待結算", "settled": "已結算", "failed": "失敗", "paid": "已支付"}),
            "創建時間": self.format_datetime("created_at")
        }

class TransactionHelper:
    """交易助手類"""
    
    @staticmethod
    def filter_by_type(transactions: List[Transaction], tx_type: str) -> List[Transaction]:
        """按類型過濾交易"""
        return [tx for tx in transactions if tx.tx_type == tx_type]
    
    @staticmethod
    def filter_by_status(transactions: List[Transaction], status: str) -> List[Transaction]:
        """按狀態過濾交易"""
        return [tx for tx in transactions if tx.status == status]
    
    @staticmethod
    def filter_by_date_range(transactions: List[Transaction], 
                           start_date: str, end_date: str) -> List[Transaction]:
        """按日期範圍過濾交易"""
        from datetime import datetime
        
        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            return transactions
        
        filtered = []
        for tx in transactions:
            tx_dt = tx.get_created_datetime()
            if tx_dt and start_dt <= tx_dt <= end_dt:
                filtered.append(tx)
        
        return filtered
    
    @staticmethod
    def calculate_summary(transactions: List[Transaction]) -> Dict[str, Any]:
        """計算交易摘要"""
        summary = {
            "total_count": len(transactions),
            "payment_count": 0,
            "refund_count": 0,
            "recharge_count": 0,
            "payment_amount": 0.0,
            "refund_amount": 0.0,
            "recharge_amount": 0.0,
            "total_points": 0
        }
        
        for tx in transactions:
            if tx.tx_type == "payment":
                summary["payment_count"] += 1
                summary["payment_amount"] += tx.final_amount or 0
            elif tx.tx_type == "refund":
                summary["refund_count"] += 1
                summary["refund_amount"] += tx.final_amount or 0
            elif tx.tx_type == "recharge":
                summary["recharge_count"] += 1
                summary["recharge_amount"] += tx.final_amount or 0
            
            summary["total_points"] += tx.points_earned or 0
        
        summary["net_amount"] = (summary["payment_amount"] + 
                               summary["recharge_amount"] - 
                               summary["refund_amount"])
        
        return summary
    
    @staticmethod
    def sort_by_time(transactions: List[Transaction], descending: bool = True) -> List[Transaction]:
        """按時間排序交易"""
        return sorted(transactions, 
                     key=lambda x: x.created_at or "", 
                     reverse=descending)
    
    @staticmethod
    def find_by_tx_no(transactions: List[Transaction], tx_no: str) -> Optional[Transaction]:
        """按交易號查找交易"""
        for tx in transactions:
            if tx.tx_no == tx_no:
                return tx
        return None