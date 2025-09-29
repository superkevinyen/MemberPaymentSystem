from typing import List, Optional, Dict, Any
from .base_service import BaseService
from models.transaction import Merchant, Transaction

class MerchantService(BaseService):
    """商戶服務"""
    
    def get_merchant_by_code(self, merchant_code: str) -> Optional[Merchant]:
        """根據商戶代碼獲取商戶"""
        try:
            merchants = self.query_table("merchants", {"code": merchant_code})
            
            if merchants:
                merchant_data = merchants[0]
                self.logger.debug(f"獲取商戶成功: {merchant_code}")
                return Merchant.from_dict(merchant_data)
            else:
                self.logger.debug(f"商戶不存在: {merchant_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"獲取商戶失敗: {merchant_code}, 錯誤: {e}")
            return None
    
    def validate_merchant_login(self, merchant_code: str) -> Optional[Merchant]:
        """驗證商戶登入"""
        self.log_operation("商戶登入驗證", {"merchant_code": merchant_code})
        
        try:
            merchant = self.get_merchant_by_code(merchant_code)
            
            if not merchant:
                self.logger.warning(f"商戶不存在: {merchant_code}")
                return None
            
            if not merchant.is_active():
                self.logger.warning(f"商戶已停用: {merchant_code}")
                return None
            
            self.logger.info(f"商戶登入驗證成功: {merchant_code}")
            return merchant
            
        except Exception as e:
            self.logger.error(f"商戶登入驗證失敗: {merchant_code}, 錯誤: {e}")
            return None
    
    def get_merchant_transactions(self, merchant_id: str, limit: int = 20, 
                                offset: int = 0, start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> Dict[str, Any]:
        """獲取商戶交易記錄"""
        self.log_operation("查詢商戶交易", {
            "merchant_id": merchant_id,
            "limit": limit,
            "offset": offset,
            "date_range": f"{start_date} ~ {end_date}" if start_date and end_date else None
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
                
                self.logger.info(f"獲取商戶交易成功: {merchant_id}, 返回 {len(transactions)} 筆")
                
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
            self.logger.error(f"獲取商戶交易失敗: {merchant_id}, 錯誤: {e}")
            raise self.handle_service_error("查詢商戶交易", e, {"merchant_id": merchant_id})
    
    def get_today_transactions(self, merchant_id: str) -> Dict[str, Any]:
        """獲取今日交易統計"""
        from datetime import datetime, time
        
        # 設置今日時間範圍
        today = datetime.now().date()
        start_time = datetime.combine(today, time.min)
        end_time = datetime.combine(today, time.max)
        
        try:
            result = self.get_merchant_transactions(
                merchant_id,
                limit=1000,  # 假設單日不超過1000筆
                offset=0,
                start_date=start_time.isoformat(),
                end_date=end_time.isoformat()
            )
            
            transactions = result.get("data", [])
            
            # 統計計算
            summary = {
                "date": today.strftime("%Y-%m-%d"),
                "total_count": 0,
                "payment_count": 0,
                "refund_count": 0,
                "payment_amount": 0.0,
                "refund_amount": 0.0,
                "net_amount": 0.0,
                "transactions": transactions
            }
            
            for tx in transactions:
                summary["total_count"] += 1
                if tx.tx_type == "payment":
                    summary["payment_count"] += 1
                    summary["payment_amount"] += tx.final_amount or 0
                elif tx.tx_type == "refund":
                    summary["refund_count"] += 1
                    summary["refund_amount"] += tx.final_amount or 0
            
            summary["net_amount"] = summary["payment_amount"] - summary["refund_amount"]
            
            self.logger.info(f"獲取今日交易統計成功: {merchant_id}")
            return summary
            
        except Exception as e:
            self.logger.error(f"獲取今日交易統計失敗: {merchant_id}, 錯誤: {e}")
            return {
                "date": today.strftime("%Y-%m-%d"),
                "total_count": 0,
                "payment_count": 0,
                "refund_count": 0,
                "payment_amount": 0.0,
                "refund_amount": 0.0,
                "net_amount": 0.0,
                "transactions": []
            }
    
    def check_merchant_permissions(self, merchant_id: str, user_id: str) -> bool:
        """檢查商戶權限"""
        try:
            # 檢查用戶是否是商戶的授權用戶
            merchant_users = self.query_table("merchant_users", {
                "merchant_id": merchant_id,
                "auth_user_id": user_id
            })
            
            return len(merchant_users) > 0
            
        except Exception as e:
            self.logger.error(f"檢查商戶權限失敗: {merchant_id}, 用戶: {user_id}, 錯誤: {e}")
            return False
    
    def get_merchant_summary(self, merchant_id: str) -> Dict[str, Any]:
        """獲取商戶摘要信息"""
        try:
            merchant = self.get_single_record("merchants", {"id": merchant_id})
            if not merchant:
                return {}
            
            # 獲取今日統計
            today_stats = self.get_today_transactions(merchant_id)
            
            # 獲取本月統計（簡化實現）
            from datetime import datetime
            month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            month_result = self.get_merchant_transactions(
                merchant_id,
                limit=10000,
                start_date=month_start.isoformat()
            )
            
            month_transactions = month_result.get("data", [])
            month_payment_amount = sum(
                tx.final_amount or 0 
                for tx in month_transactions 
                if tx.tx_type == "payment"
            )
            
            summary = {
                "merchant": Merchant.from_dict(merchant),
                "today": today_stats,
                "month_payment_amount": month_payment_amount,
                "month_transaction_count": len(month_transactions)
            }
            
            self.logger.debug(f"獲取商戶摘要成功: {merchant_id}")
            return summary
            
        except Exception as e:
            self.logger.error(f"獲取商戶摘要失敗: {merchant_id}, 錯誤: {e}")
            return {}