import logging
from typing import Any, Dict, Optional
from config.constants import ERROR_MESSAGES

logger = logging.getLogger(__name__)

class ErrorHandler:
    """錯誤處理器"""
    
    def __init__(self):
        self.logger = logger
    
    def handle_rpc_error(self, error: Exception) -> Exception:
        """處理 RPC 錯誤"""
        error_str = str(error)
        
        # 查找已知錯誤碼
        for code, message in ERROR_MESSAGES.items():
            if code in error_str:
                self.logger.warning(f"業務錯誤: {code}")
                return Exception(message)
        
        # 未知錯誤
        self.logger.error(f"未知錯誤: {error_str}")
        return Exception(f"系統錯誤: {error_str}")
    
    def handle_query_error(self, error: Exception) -> Exception:
        """處理查詢錯誤"""
        error_str = str(error)
        self.logger.error(f"查詢錯誤: {error_str}")
        return Exception("數據查詢失敗，請稍後重試")
    
    def handle_validation_error(self, field: str, value: Any) -> Exception:
        """處理驗證錯誤"""
        self.logger.warning(f"驗證錯誤: {field} = {value}")
        return Exception(f"{field} 格式不正確")
    
    def handle_with_context(self, error: Exception, context: Dict[str, Any]) -> str:
        """帶上下文的錯誤處理"""
        error_str = str(error)
        
        # 根據上下文提供更精確的錯誤信息
        if "INSUFFICIENT_BALANCE" in error_str:
            card_id = context.get("card_id")
            if card_id:
                # 這裡可以查詢當前餘額，但為了簡化先返回通用信息
                return "❌ 餘額不足，請充值後再試"
            return "❌ 餘額不足，請充值後再試"
        
        elif "QR_EXPIRED_OR_INVALID" in error_str:
            return "❌ QR 碼已過期或無效，請重新生成付款碼"
        
        elif "NOT_MERCHANT_USER" in error_str:
            return "❌ 您沒有此商戶的操作權限，請聯繫管理員"
        
        elif "CARD_NOT_FOUND_OR_INACTIVE" in error_str:
            return "❌ 卡片不存在或未激活，請檢查卡片狀態"
        
        elif "EXTERNAL_ID_ALREADY_BOUND" in error_str:
            return "❌ 外部身份已被其他會員綁定"
        
        elif "INVALID_BINDING_PASSWORD" in error_str:
            return "❌ 綁定密碼錯誤"
        
        elif "REFUND_EXCEEDS_REMAINING" in error_str:
            return "❌ 退款金額超過可退金額"
        
        elif "CARD_TYPE_NOT_SHAREABLE" in error_str:
            return "❌ 此類型卡片不支持共享"
        
        elif "CANNOT_REMOVE_LAST_OWNER" in error_str:
            return "❌ 不能移除最後一個擁有者"
        
        elif "UNSUPPORTED_CARD_TYPE_FOR_RECHARGE" in error_str:
            return "❌ 此卡片類型不支持充值"
        
        elif "ONLY_COMPLETED_PAYMENT_REFUNDABLE" in error_str:
            return "❌ 只能退款已完成的支付交易"
        
        # 其他錯誤處理
        return self.handle_rpc_error(error)
    
    def suggest_solution(self, error_code: str) -> Optional[str]:
        """提供解決方案建議"""
        solutions = {
            "INSUFFICIENT_BALANCE": "建議客戶充值或使用其他卡片",
            "QR_EXPIRED_OR_INVALID": "請客戶重新生成付款碼",
            "CARD_NOT_FOUND_OR_INACTIVE": "請檢查卡片狀態或聯繫客服",
            "NOT_MERCHANT_USER": "請聯繫管理員檢查商戶權限",
            "REFUND_EXCEEDS_REMAINING": "請檢查原交易的可退金額",
            "EXTERNAL_ID_ALREADY_BOUND": "請使用其他外部身份或聯繫客服解綁",
            "INVALID_BINDING_PASSWORD": "請確認綁定密碼是否正確",
            "CARD_TYPE_NOT_SHAREABLE": "標準卡和優惠券卡不支持共享",
            "UNSUPPORTED_CARD_TYPE_FOR_RECHARGE": "只有預付卡和企業卡支持充值"
        }
        
        return solutions.get(error_code)
    
    def format_error_message(self, error: Exception, show_suggestion: bool = True) -> str:
        """格式化錯誤信息"""
        error_str = str(error)
        
        # 查找錯誤碼
        error_code = None
        for code in ERROR_MESSAGES.keys():
            if code in error_str:
                error_code = code
                break
        
        # 基本錯誤信息
        if error_code and error_code in ERROR_MESSAGES:
            message = f"❌ {ERROR_MESSAGES[error_code]}"
        else:
            message = f"❌ {error_str}"
        
        # 添加解決方案建議
        if show_suggestion and error_code:
            suggestion = self.suggest_solution(error_code)
            if suggestion:
                message += f"\n💡 建議：{suggestion}"
        
        return message

# 全局錯誤處理器實例
error_handler = ErrorHandler()