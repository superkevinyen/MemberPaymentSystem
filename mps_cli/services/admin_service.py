from typing import List, Optional, Dict, Any
from .base_service import BaseService
from .member_service import MemberService
from models.member import Member
from models.card import Card
from models.transaction import Transaction

class AdminService(BaseService):
    """管理員服務"""
    
    def __init__(self):
        super().__init__()
        self.member_service = MemberService()
    
    def create_member_profile(self, name: str, phone: str, email: str,
                            binding_user_org: Optional[str] = None,
                            binding_org_id: Optional[str] = None) -> str:
        """創建會員檔案（管理員操作）"""
        self.log_operation("管理員創建會員", {
            "name": name,
            "phone": phone,
            "email": email,
            "has_external_binding": bool(binding_user_org and binding_org_id)
        })
        
        try:
            member_id = self.member_service.create_member(
                name, phone, email, binding_user_org, binding_org_id
            )
            
            self.logger.info(f"管理員創建會員成功: {member_id}")
            return member_id
            
        except Exception as e:
            self.logger.error(f"管理員創建會員失敗: {e}")
            raise self.handle_service_error("創建會員", e, {
                "name": name,
                "phone": phone,
                "email": email
            })
    
    def freeze_card(self, card_id: str) -> bool:
        """凍結卡片"""
        self.log_operation("凍結卡片", {"card_id": card_id})
        
        params = {"p_card_id": card_id}
        
        try:
            result = self.rpc_call("freeze_card", params)
            
            if result:
                self.logger.info(f"卡片凍結成功: {card_id}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"卡片凍結失敗: {card_id}, 錯誤: {e}")
            raise self.handle_service_error("凍結卡片", e, {"card_id": card_id})
    
    def unfreeze_card(self, card_id: str) -> bool:
        """解凍卡片"""
        self.log_operation("解凍卡片", {"card_id": card_id})
        
        params = {"p_card_id": card_id}
        
        try:
            result = self.rpc_call("unfreeze_card", params)
            
            if result:
                self.logger.info(f"卡片解凍成功: {card_id}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"卡片解凍失敗: {card_id}, 錯誤: {e}")
            raise self.handle_service_error("解凍卡片", e, {"card_id": card_id})
    
    def suspend_member(self, member_id: str) -> bool:
        """暫停會員"""
        self.log_operation("暫停會員", {"member_id": member_id})
        
        params = {"p_member_id": member_id}
        
        try:
            result = self.rpc_call("admin_suspend_member", params)
            
            if result:
                self.logger.info(f"會員暫停成功: {member_id}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"會員暫停失敗: {member_id}, 錯誤: {e}")
            raise self.handle_service_error("暫停會員", e, {"member_id": member_id})
    
    def suspend_merchant(self, merchant_id: str) -> bool:
        """暫停商戶"""
        self.log_operation("暫停商戶", {"merchant_id": merchant_id})
        
        params = {"p_merchant_id": merchant_id}
        
        try:
            result = self.rpc_call("admin_suspend_merchant", params)
            
            if result:
                self.logger.info(f"商戶暫停成功: {merchant_id}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"商戶暫停失敗: {merchant_id}, 錯誤: {e}")
            raise self.handle_service_error("暫停商戶", e, {"merchant_id": merchant_id})
    
    def update_points_and_level(self, card_id: str, delta_points: int, 
                               reason: str = "manual_adjust") -> bool:
        """調整積分和等級"""
        self.log_operation("調整積分", {
            "card_id": card_id,
            "delta_points": delta_points,
            "reason": reason
        })
        
        params = {
            "p_card_id": card_id,
            "p_delta_points": delta_points,
            "p_reason": reason
        }
        
        try:
            result = self.rpc_call("update_points_and_level", params)
            
            if result:
                self.logger.info(f"積分調整成功: {card_id}, 變化: {delta_points}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"積分調整失敗: {card_id}, 錯誤: {e}")
            raise self.handle_service_error("調整積分", e, {
                "card_id": card_id,
                "delta_points": delta_points
            })
    
    def batch_rotate_qr_tokens(self, ttl_seconds: int = 300) -> int:
        """批量輪換 QR 碼"""
        self.log_operation("批量輪換 QR 碼", {"ttl_seconds": ttl_seconds})
        
        from services.qr_service import QRService
        qr_service = QRService()
        
        try:
            affected_count = qr_service.batch_rotate_qr(ttl_seconds)
            
            self.logger.info(f"批量 QR 碼輪換成功，影響 {affected_count} 張卡片")
            return affected_count
            
        except Exception as e:
            self.logger.error(f"批量 QR 碼輪換失敗: {e}")
            raise self.handle_service_error("批量輪換 QR 碼", e, {"ttl_seconds": ttl_seconds})
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """獲取系統統計信息"""
        try:
            stats = {}
            
            # 會員統計
            total_members = self.count_records("member_profiles")
            active_members = self.count_records("member_profiles", {"status": "active"})
            
            # 卡片統計
            total_cards = self.count_records("member_cards")
            active_cards = self.count_records("member_cards", {"status": "active"})
            
            # 商戶統計
            total_merchants = self.count_records("merchants")
            active_merchants = self.count_records("merchants", {"active": True})
            
            # 今日交易統計
            from datetime import datetime, time
            today = datetime.now().date()
            start_time = datetime.combine(today, time.min)
            end_time = datetime.combine(today, time.max)
            
            # 簡化的今日交易統計（直接查詢表）
            today_transactions = self.query_table("transactions", 
                                                 limit=10000,  # 假設單日不超過10000筆
                                                 order_by="created_at")
            
            today_tx_count = 0
            today_payment_amount = 0.0
            
            for tx in today_transactions:
                tx_time = tx.get("created_at", "")
                if tx_time and start_time.isoformat() <= tx_time <= end_time.isoformat():
                    today_tx_count += 1
                    if tx.get("tx_type") == "payment":
                        today_payment_amount += tx.get("final_amount", 0)
            
            stats = {
                "members": {
                    "total": total_members,
                    "active": active_members,
                    "inactive": total_members - active_members
                },
                "cards": {
                    "total": total_cards,
                    "active": active_cards,
                    "inactive": total_cards - active_cards
                },
                "merchants": {
                    "total": total_merchants,
                    "active": active_merchants,
                    "inactive": total_merchants - active_merchants
                },
                "today": {
                    "transaction_count": today_tx_count,
                    "payment_amount": today_payment_amount
                }
            }
            
            self.logger.debug("獲取系統統計成功")
            return stats
            
        except Exception as e:
            self.logger.error(f"獲取系統統計失敗: {e}")
            return {}
    
    def search_cards(self, keyword: str, limit: int = 50) -> List[Card]:
        """搜索卡片"""
        try:
            search_fields = ["card_no", "name"]
            cards_data = self.search_records("member_cards", search_fields, keyword, limit)
            
            cards = [Card.from_dict(card_data) for card_data in cards_data]
            
            self.logger.debug(f"搜索卡片成功: 關鍵字 '{keyword}', 返回 {len(cards)} 個結果")
            return cards
            
        except Exception as e:
            self.logger.error(f"搜索卡片失敗: 關鍵字 '{keyword}', 錯誤: {e}")
            return []
    
    def get_card_detail(self, card_id: str) -> Optional[Dict[str, Any]]:
        """獲取卡片詳細信息"""
        try:
            card_data = self.get_single_record("member_cards", {"id": card_id})
            
            if not card_data:
                return None
            
            card = Card.from_dict(card_data)
            
            # 獲取綁定信息
            bindings = self.member_service.get_card_bindings(card_id)
            
            # 獲取擁有者信息
            owner = None
            if card.owner_member_id:
                owner = self.member_service.get_member_by_id(card.owner_member_id)
            
            detail = {
                "card": card,
                "owner": owner,
                "bindings": bindings,
                "binding_count": len(bindings)
            }
            
            self.logger.debug(f"獲取卡片詳情成功: {card_id}")
            return detail
            
        except Exception as e:
            self.logger.error(f"獲取卡片詳情失敗: {card_id}, 錯誤: {e}")
            return None
    
    def validate_admin_access(self) -> bool:
        """驗證管理員訪問權限"""
        # 這裡可以添加更複雜的權限驗證邏輯
        # 目前簡化為總是返回 True
        return True