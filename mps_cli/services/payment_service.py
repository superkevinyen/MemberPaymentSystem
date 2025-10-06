from typing import Dict, Any, Optional, List
from decimal import Decimal
from .base_service import BaseService
from models.transaction import Transaction
import uuid

class PaymentService(BaseService):
    """支付服務"""
    
    def charge_by_qr(self, merchant_code: str, qr_plain: str, amount: Decimal,
                    tag: Optional[Dict] = None, external_order_id: Optional[str] = None) -> Dict:
        """掃碼支付"""
        self.log_operation("掃碼支付", {
            "merchant_code": merchant_code,
            "amount": float(amount),
            "has_external_order": bool(external_order_id)
        })
        
        idempotency_key = f"payment-{uuid.uuid4()}"
        
        params = {
            "p_merchant_code": merchant_code,
            "p_qr_plain": qr_plain,
            "p_raw_amount": float(amount),
            "p_idempotency_key": idempotency_key,
            "p_tag": tag or {"source": "cli"},
            "p_external_order_id": external_order_id
        }
        
        try:
            result = self.rpc_call("merchant_charge_by_qr", params)
            
            if result and len(result) > 0:
                payment_data = result[0]
                
                self.logger.info(f"掃碼支付成功: {payment_data.get('tx_no')}")
                
                return {
                    "tx_id": payment_data.get("tx_id"),
                    "tx_no": payment_data.get("tx_no"),
                    "card_id": payment_data.get("card_id"),
                    "final_amount": payment_data.get("final_amount"),
                    "discount": payment_data.get("discount"),
                    "raw_amount": float(amount)
                }
            else:
                raise Exception("支付失敗：無返回數據")
                
        except Exception as e:
            self.logger.error(f"掃碼支付失敗: {e}")
            raise self.handle_service_error("掃碼支付", e, {
                "merchant_code": merchant_code,
                "amount": float(amount)
            })
    
    def refund_transaction(self, merchant_code: str, original_tx_no: str, 
                          refund_amount: Decimal, reason: Optional[str] = None) -> Dict:
        """退款交易"""
        self.log_operation("退款交易", {
            "merchant_code": merchant_code,
            "original_tx_no": original_tx_no,
            "refund_amount": float(refund_amount),
            "reason": reason
        })
        
        params = {
            "p_merchant_code": merchant_code,
            "p_original_tx_no": original_tx_no,
            "p_refund_amount": float(refund_amount),
            "p_tag": {"reason": reason or "", "source": "cli"}
        }
        
        try:
            result = self.rpc_call("merchant_refund_tx", params)
            
            if result and len(result) > 0:
                refund_data = result[0]
                
                self.logger.info(f"退款成功: {refund_data.get('refund_tx_no')}")
                
                return {
                    "refund_tx_id": refund_data.get("refund_tx_id"),
                    "refund_tx_no": refund_data.get("refund_tx_no"),
                    "refunded_amount": refund_data.get("refunded_amount"),
                    "original_tx_no": original_tx_no
                }
            else:
                raise Exception("退款失敗：無返回數據")
                
        except Exception as e:
            self.logger.error(f"退款失敗: {e}")
            raise self.handle_service_error("退款交易", e, {
                "merchant_code": merchant_code,
                "original_tx_no": original_tx_no,
                "refund_amount": float(refund_amount)
            })
    
    def recharge_card(self, card_id: str, amount: Decimal, payment_method: str = "wechat",
                     tag: Optional[Dict] = None, external_order_id: Optional[str] = None) -> Dict:
        """充值卡片"""
        self.log_operation("充值卡片", {
            "card_id": card_id,
            "amount": float(amount),
            "payment_method": payment_method
        })
        
        idempotency_key = f"recharge-{uuid.uuid4()}"
        
        params = {
            "p_card_id": card_id,
            "p_amount": float(amount),
            "p_payment_method": payment_method,
            "p_tag": tag or {"source": "cli"},
            "p_idempotency_key": idempotency_key,
            "p_external_order_id": external_order_id
        }
        
        try:
            result = self.rpc_call("user_recharge_card", params)
            
            if result and len(result) > 0:
                recharge_data = result[0]
                
                self.logger.info(f"充值成功: {recharge_data.get('tx_no')}")
                
                return {
                    "tx_id": recharge_data.get("tx_id"),
                    "tx_no": recharge_data.get("tx_no"),
                    "card_id": recharge_data.get("card_id"),
                    "amount": recharge_data.get("amount"),
                    "payment_method": payment_method
                }
            else:
                raise Exception("充值失敗：無返回數據")
                
        except Exception as e:
            self.logger.error(f"充值失敗: {e}")
            raise self.handle_service_error("充值卡片", e, {
                "card_id": card_id,
                "amount": float(amount)
            })
    
    def get_transaction_detail(self, tx_no: str) -> Optional[Transaction]:
        """獲取交易詳情"""
        self.log_operation("查詢交易詳情", {"tx_no": tx_no})
        
        params = {"p_tx_no": tx_no}
        
        try:
            result = self.rpc_call("get_transaction_detail", params)
            
            if result:
                transaction_data = result if isinstance(result, dict) else result[0]
                transaction = Transaction.from_dict(transaction_data)
                
                self.logger.info(f"獲取交易詳情成功: {tx_no}")
                return transaction
            else:
                self.logger.warning(f"交易不存在: {tx_no}")
                return None
                
        except Exception as e:
            self.logger.error(f"獲取交易詳情失敗: {tx_no}, 錯誤: {e}")
            raise self.handle_service_error("查詢交易詳情", e, {"tx_no": tx_no})
    
    def validate_refund_amount(self, original_tx_no: str, refund_amount: Decimal) -> Dict[str, Any]:
        """驗證退款金額"""
        try:
            # 獲取原交易詳情
            original_tx = self.get_transaction_detail(original_tx_no)
            
            if not original_tx:
                return {"valid": False, "error": "原交易不存在"}
            
            if not original_tx.can_refund():
                return {"valid": False, "error": "此交易不支持退款"}
            
            # 計算已退款金額
            refunded_txs = self.query_table("transactions", {
                "reason": original_tx_no,
                "tx_type": "refund"
            })
            
            total_refunded = sum(
                tx.get("final_amount", 0) 
                for tx in refunded_txs 
                if tx.get("status") in ["completed", "processing"]
            )
            
            remaining_amount = (original_tx.final_amount or 0) - total_refunded
            
            if float(refund_amount) > remaining_amount:
                return {
                    "valid": False, 
                    "error": f"退款金額超過可退金額 ¥{remaining_amount:.2f}"
                }
            
            return {
                "valid": True,
                "original_amount": original_tx.final_amount,
                "refunded_amount": total_refunded,
                "remaining_amount": remaining_amount,
                "original_tx": original_tx
            }
            
        except Exception as e:
            self.logger.error(f"驗證退款金額失敗: {original_tx_no}, 錯誤: {e}")
            return {"valid": False, "error": str(e)}
    
    def get_payment_methods(self) -> List[Dict[str, str]]:
        """獲取支付方式列表"""
        from config.constants import PAYMENT_METHODS
        
        return [
            {"code": code, "name": name}
            for code, name in PAYMENT_METHODS.items()
            if code != "balance"  # 餘額支付不在充值選項中
        ]
    
    def calculate_discount_preview(self, card_id: str, amount: Decimal) -> Dict[str, Any]:
        """計算折扣預覽"""
        try:
            card = self.get_single_record("member_cards", {"id": card_id})
            
            if not card:
                return {"error": "卡片不存在"}
            
            # 根據卡片類型計算折扣
            discount_rate = 1.0
            
            if card.get("card_type") == "standard":
                # 標準卡根據積分計算折扣
                points = card.get("points", 0)
                if points >= 10000:
                    discount_rate = 0.85
                elif points >= 5000:
                    discount_rate = 0.90
                elif points >= 1000:
                    discount_rate = 0.95
            # Standard Card 已移除 prepaid，不需要此邏輯
            elif card.get("card_type") == "corporate":
                # 企業卡使用固定折扣
                discount_rate = card.get("fixed_discount", 1.0)
            
            final_amount = float(amount) * discount_rate
            savings = float(amount) - final_amount
            
            return {
                "original_amount": float(amount),
                "discount_rate": discount_rate,
                "final_amount": final_amount,
                "savings": savings,
                "card_type": card.get("card_type"),
                "points": card.get("points", 0)
            }
            
        except Exception as e:
            self.logger.error(f"計算折扣預覽失敗: {card_id}, 錯誤: {e}")
            return {"error": str(e)}
    
    # 新增的交易統計擴展功能
    def get_today_transaction_stats(self, merchant_id: Optional[str] = None) -> Dict[str, Any]:
        """今日交易統計"""
        self.log_operation("獲取今日交易統計", {"merchant_id": merchant_id})
        
        params = {"p_merchant_id": merchant_id}
        
        try:
            result = self.rpc_call("get_today_transaction_stats", params)
            
            if result and len(result) > 0:
                stats = result[0]
                self.logger.info("獲取今日交易統計成功")
                return stats
            else:
                return {}
                
        except Exception as e:
            self.logger.error(f"獲取今日交易統計失敗: {e}")
            raise self.handle_service_error("獲取今日交易統計", e, {"merchant_id": merchant_id})
    
    def get_transaction_trends(self, start_date: str, end_date: str,
                             merchant_id: Optional[str] = None, group_by: str = "day") -> List[Dict[str, Any]]:
        """交易趨勢分析"""
        self.log_operation("獲取交易趨勢分析", {
            "start_date": start_date,
            "end_date": end_date,
            "merchant_id": merchant_id,
            "group_by": group_by
        })
        
        params = {
            "p_start_date": start_date,
            "p_end_date": end_date,
            "p_merchant_id": merchant_id,
            "p_group_by": group_by
        }
        
        try:
            result = self.rpc_call("get_transaction_trends", params)
            
            if result:
                trends = [trend for trend in result]
                self.logger.info(f"獲取交易趨勢分析成功，返回 {len(trends)} 條記錄")
                return trends
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"獲取交易趨勢分析失敗: {e}")
            raise self.handle_service_error("獲取交易趨勢分析", e, {
                "start_date": start_date,
                "end_date": end_date,
                "merchant_id": merchant_id,
                "group_by": group_by
            })
    
    def get_merchant_transactions_advanced(self, merchant_id: str, limit: int = 50,
                                         offset: int = 0, start_date: Optional[str] = None,
                                         end_date: Optional[str] = None) -> Dict[str, Any]:
        """獲取商戶交易記錄（高級）"""
        self.log_operation("獲取商戶交易記錄", {
            "merchant_id": merchant_id,
            "limit": limit,
            "offset": offset,
            "start_date": start_date,
            "end_date": end_date
        })
        
        params = {
            "p_merchant_id": merchant_id,
            "p_limit": limit,
            "p_offset": offset,
            "p_start_date": start_date,
            "p_end_date": end_date
        }
        
        try:
            result = self.rpc_call("get_merchant_transactions", params)
            
            if result:
                # 計算分頁信息
                total_count = result[0].get('total_count', 0) if result else 0
                total_pages = (total_count + limit - 1) // limit
                current_page = offset // limit
                
                transactions = [Transaction.from_dict(tx) for tx in result]
                
                self.logger.info(f"獲取商戶交易記錄成功: {merchant_id}, 返回 {len(transactions)} 筆")
                
                return {
                    "data": transactions,
                    "pagination": {
                        "current_page": current_page,
                        "page_size": limit,
                        "total_count": total_count,
                        "total_pages": total_pages,
                        "has_next": current_page < total_pages - 1,
                        "has_prev": current_page > 0
                    }
                }
            else:
                return {
                    "data": [],
                    "pagination": {
                        "current_page": 0,
                        "page_size": limit,
                        "total_count": 0,
                        "total_pages": 0,
                        "has_next": False,
                        "has_prev": False
                    }
                }
                
        except Exception as e:
            self.logger.error(f"獲取商戶交易記錄失敗: {merchant_id}, 錯誤: {e}")
            raise self.handle_service_error("獲取商戶交易記錄", e, {
                "merchant_id": merchant_id,
                "limit": limit,
                "offset": offset
            })