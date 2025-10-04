from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
from .base import BaseModel, TimestampMixin

@dataclass
class Settlement(BaseModel, TimestampMixin):
    """結算模型"""
    
    # 基本信息
    settlement_no: Optional[str] = None
    merchant_id: Optional[str] = None
    merchant_code: Optional[str] = None
    merchant_name: Optional[str] = None
    
    # 結算配置
    settlement_mode: Optional[str] = None  # realtime/t_plus_1/monthly
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    
    # 金額統計
    total_transactions: Optional[int] = None
    payment_count: Optional[int] = None
    refund_count: Optional[int] = None
    payment_amount: Optional[Decimal] = None
    refund_amount: Optional[Decimal] = None
    net_amount: Optional[Decimal] = None
    fee_amount: Optional[Decimal] = None
    settlement_amount: Optional[Decimal] = None
    
    # 狀態
    status: Optional[str] = None  # pending/completed/failed
    settled_at: Optional[str] = None
    
    def get_mode_display(self) -> str:
        """獲取結算模式顯示"""
        from config.constants import SETTLEMENT_MODES
        return SETTLEMENT_MODES.get(self.settlement_mode, self.settlement_mode or "未知")
    
    def get_status_display(self) -> str:
        """獲取狀態顯示"""
        from config.constants import SETTLEMENT_STATUS
        return SETTLEMENT_STATUS.get(self.status, self.status or "未知")
    
    def display_summary(self) -> str:
        """顯示結算摘要"""
        from utils.formatters import Formatter
        
        return (f"{self.settlement_no} | "
                f"{self.get_mode_display()} | "
                f"淨額: {Formatter.format_currency(self.net_amount)} | "
                f"{self.get_status_display()}")
