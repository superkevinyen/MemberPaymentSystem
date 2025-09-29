from typing import Dict, Optional, List
from .base_service import BaseService
from models.card import QRCode

class QRService(BaseService):
    """QR 碼服務"""
    
    def rotate_qr(self, card_id: str, ttl_seconds: int = 900) -> Dict:
        """生成/刷新 QR 碼"""
        self.log_operation("生成 QR 碼", {"card_id": card_id, "ttl": ttl_seconds})
        
        params = {
            "p_card_id": card_id,
            "p_ttl_seconds": ttl_seconds
        }
        
        try:
            result = self.rpc_call("rotate_card_qr", params)
            
            if result and len(result) > 0:
                qr_data = result[0]
                self.logger.info(f"QR 碼生成成功: {card_id}")
                return {
                    "qr_plain": qr_data.get("qr_plain"),
                    "expires_at": qr_data.get("qr_expires_at"),
                    "card_id": card_id
                }
            else:
                raise Exception("QR 碼生成失敗：無返回數據")
                
        except Exception as e:
            self.logger.error(f"QR 碼生成失敗: {card_id}, 錯誤: {e}")
            raise self.handle_service_error("生成 QR 碼", e, {"card_id": card_id})
    
    def validate_qr(self, qr_plain: str) -> str:
        """驗證 QR 碼並返回卡片 ID"""
        self.log_operation("驗證 QR 碼", {"qr_length": len(qr_plain) if qr_plain else 0})
        
        if not qr_plain or len(qr_plain) < 16:
            raise Exception("QR 碼格式不正確")
        
        params = {"p_qr_plain": qr_plain}
        
        try:
            card_id = self.rpc_call("validate_qr_plain", params)
            
            if card_id:
                self.logger.info(f"QR 碼驗證成功，對應卡片: {card_id}")
                return card_id
            else:
                raise Exception("QR 碼驗證失敗")
                
        except Exception as e:
            self.logger.error(f"QR 碼驗證失敗: {e}")
            raise self.handle_service_error("驗證 QR 碼", e, {"qr_plain": qr_plain[:10] + "..."})
    
    def revoke_qr(self, card_id: str) -> bool:
        """撤銷 QR 碼"""
        self.log_operation("撤銷 QR 碼", {"card_id": card_id})
        
        params = {"p_card_id": card_id}
        
        try:
            result = self.rpc_call("revoke_card_qr", params)
            
            if result:
                self.logger.info(f"QR 碼撤銷成功: {card_id}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"QR 碼撤銷失敗: {card_id}, 錯誤: {e}")
            raise self.handle_service_error("撤銷 QR 碼", e, {"card_id": card_id})
    
    def batch_rotate_qr(self, ttl_seconds: int = 300) -> int:
        """批量輪換 QR 碼"""
        self.log_operation("批量輪換 QR 碼", {"ttl": ttl_seconds})
        
        params = {"p_ttl_seconds": ttl_seconds}
        
        try:
            affected_count = self.rpc_call("cron_rotate_qr_tokens", params)
            
            self.logger.info(f"批量 QR 碼輪換完成，影響 {affected_count} 張卡片")
            return affected_count or 0
            
        except Exception as e:
            self.logger.error(f"批量 QR 碼輪換失敗: {e}")
            raise self.handle_service_error("批量輪換 QR 碼", e, {"ttl": ttl_seconds})
    
    def get_qr_history(self, card_id: str, limit: int = 10) -> List[Dict]:
        """獲取 QR 碼歷史"""
        try:
            filters = {"card_id": card_id}
            history = self.query_table("card_qr_history", filters, limit, 
                                     order_by="issued_at", ascending=False)
            
            self.logger.debug(f"獲取 QR 碼歷史: {card_id}, 返回 {len(history)} 條記錄")
            return history
            
        except Exception as e:
            self.logger.error(f"獲取 QR 碼歷史失敗: {card_id}, 錯誤: {e}")
            return []
    
    def get_current_qr_state(self, card_id: str) -> Optional[Dict]:
        """獲取當前 QR 碼狀態"""
        try:
            filters = {"card_id": card_id}
            qr_states = self.query_table("card_qr_state", filters, limit=1)
            
            if qr_states:
                qr_state = qr_states[0]
                self.logger.debug(f"獲取 QR 碼狀態: {card_id}")
                return qr_state
            else:
                self.logger.debug(f"未找到 QR 碼狀態: {card_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"獲取 QR 碼狀態失敗: {card_id}, 錯誤: {e}")
            return None
    
    def is_qr_active(self, card_id: str) -> bool:
        """檢查 QR 碼是否有效"""
        qr_state = self.get_current_qr_state(card_id)
        
        if not qr_state:
            return False
        
        # 檢查是否過期
        expires_at = qr_state.get("expires_at")
        if not expires_at:
            return False
        
        from datetime import datetime
        try:
            if expires_at.endswith('Z'):
                expire_time_str = expires_at[:-1] + '+00:00'
            else:
                expire_time_str = expires_at
            
            expire_time = datetime.fromisoformat(expire_time_str)
            return datetime.now(expire_time.tzinfo) < expire_time
            
        except ValueError:
            return False
    
    def get_qr_info(self, card_id: str) -> Optional[QRCode]:
        """獲取 QR 碼信息"""
        qr_state = self.get_current_qr_state(card_id)
        
        if not qr_state:
            return None
        
        # 注意：實際的 qr_plain 不會存儲在狀態表中，這裡只是示例
        # 實際使用時需要從 rotate_qr 的返回結果中獲取
        qr_code = QRCode(
            card_id=card_id,
            qr_plain="",  # 實際不會存儲明文
            expires_at=qr_state.get("expires_at"),
            created_at=qr_state.get("updated_at")
        )
        
        return qr_code