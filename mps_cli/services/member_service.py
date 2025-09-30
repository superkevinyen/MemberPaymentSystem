from typing import List, Optional, Dict, Any
from .base_service import BaseService
from models.member import Member
from models.card import Card, CardBinding
from models.transaction import Transaction

class MemberService(BaseService):
    """會員服務"""
    
    def create_member(self, name: str, phone: str, email: str,
                     password: Optional[str] = None,
                     binding_user_org: Optional[str] = None,
                     binding_org_id: Optional[str] = None) -> str:
        """創建新會員"""
        self.log_operation("創建會員", {
            "name": name,
            "phone": phone,
            "email": email,
            "has_password": bool(password),
            "has_external_binding": bool(binding_user_org and binding_org_id)
        })
        
        params = {
            "p_name": name,
            "p_phone": phone,
            "p_email": email,
            "p_password": password,
            "p_binding_user_org": binding_user_org,
            "p_binding_org_id": binding_org_id,
            "p_default_card_type": "standard"
        }
        
        try:
            member_id = self.rpc_call("create_member_profile", params)
            
            if member_id:
                self.logger.info(f"會員創建成功: {member_id}")
                return member_id
            else:
                raise Exception("會員創建失敗：無返回 ID")
                
        except Exception as e:
            self.logger.error(f"會員創建失敗: {e}")
            raise self.handle_service_error("創建會員", e, {
                "name": name, 
                "phone": phone, 
                "email": email
            })
    
    def get_member_by_id(self, member_id: str) -> Optional[Member]:
        """根據 ID 獲取會員"""
        try:
            members = self.query_table("member_profiles", {"id": member_id})
            
            if members:
                member_data = members[0]
                self.logger.debug(f"獲取會員成功: {member_id}")
                return Member.from_dict(member_data)
            else:
                self.logger.debug(f"會員不存在: {member_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"獲取會員失敗: {member_id}, 錯誤: {e}")
            return None
    
    def get_member_by_phone(self, phone: str) -> Optional[Member]:
        """根據手機號獲取會員"""
        try:
            members = self.query_table("member_profiles", {"phone": phone})
            
            if members:
                member_data = members[0]
                self.logger.debug(f"根據手機號獲取會員成功: {phone}")
                return Member.from_dict(member_data)
            else:
                self.logger.debug(f"手機號對應的會員不存在: {phone}")
                return None
                
        except Exception as e:
            self.logger.error(f"根據手機號獲取會員失敗: {phone}, 錯誤: {e}")
            return None
    
    def get_member_cards(self, member_id: str) -> List[Card]:
        """獲取會員的所有卡片"""
        try:
            # 查詢會員擁有的卡片
            owned_cards = self.query_table("member_cards", {"owner_member_id": member_id})
            
            # 查詢會員綁定的共享卡片
            bindings = self.query_table("card_bindings", {"member_id": member_id})
            shared_card_ids = [b["card_id"] for b in bindings]
            
            shared_cards = []
            for card_id in shared_card_ids:
                cards = self.query_table("member_cards", {"id": card_id})
                if cards:
                    shared_cards.extend(cards)
            
            # 合併並去重
            all_cards_data = owned_cards + shared_cards
            unique_cards = {card["id"]: card for card in all_cards_data}.values()
            
            cards = [Card.from_dict(card_data) for card_data in unique_cards]
            
            self.logger.debug(f"獲取會員卡片成功: {member_id}, 共 {len(cards)} 張")
            return cards
            
        except Exception as e:
            self.logger.error(f"獲取會員卡片失敗: {member_id}, 錯誤: {e}")
            return []
    
    def get_member_transactions(self, member_id: str, limit: int = 20, 
                              offset: int = 0) -> Dict[str, Any]:
        """獲取會員交易記錄"""
        self.log_operation("查詢會員交易", {
            "member_id": member_id, 
            "limit": limit, 
            "offset": offset
        })
        
        params = {
            "p_member_id": member_id,
            "p_limit": limit,
            "p_offset": offset
        }
        
        try:
            result = self.rpc_call("get_member_transactions", params)
            
            if result:
                # 計算分頁信息
                total_count = result[0].get('total_count', 0) if result else 0
                total_pages = (total_count + limit - 1) // limit
                current_page = offset // limit
                
                transactions = [Transaction.from_dict(tx) for tx in result]
                
                self.logger.info(f"獲取會員交易成功: {member_id}, 返回 {len(transactions)} 筆")
                
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
            self.logger.error(f"獲取會員交易失敗: {member_id}, 錯誤: {e}")
            raise self.handle_service_error("查詢會員交易", e, {"member_id": member_id})
    
    def bind_card(self, card_id: str, member_id: str, role: str = "member",
                 binding_password: Optional[str] = None) -> bool:
        """綁定卡片到會員"""
        self.log_operation("綁定卡片", {
            "card_id": card_id, 
            "member_id": member_id, 
            "role": role
        })
        
        params = {
            "p_card_id": card_id,
            "p_member_id": member_id,
            "p_role": role,
            "p_binding_password": binding_password
        }
        
        try:
            result = self.rpc_call("bind_member_to_card", params)
            
            if result:
                self.logger.info(f"卡片綁定成功: {card_id} -> {member_id}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"卡片綁定失敗: {card_id} -> {member_id}, 錯誤: {e}")
            raise self.handle_service_error("綁定卡片", e, {
                "card_id": card_id, 
                "member_id": member_id
            })
    
    def unbind_card(self, card_id: str, member_id: str) -> bool:
        """解綁會員卡片"""
        self.log_operation("解綁卡片", {"card_id": card_id, "member_id": member_id})
        
        params = {
            "p_card_id": card_id,
            "p_member_id": member_id
        }
        
        try:
            result = self.rpc_call("unbind_member_from_card", params)
            
            if result:
                self.logger.info(f"卡片解綁成功: {card_id} -> {member_id}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"卡片解綁失敗: {card_id} -> {member_id}, 錯誤: {e}")
            raise self.handle_service_error("解綁卡片", e, {
                "card_id": card_id, 
                "member_id": member_id
            })
    
    def get_card_bindings(self, card_id: str) -> List[CardBinding]:
        """獲取卡片綁定信息"""
        try:
            bindings_data = self.query_table("card_bindings", {"card_id": card_id})
            bindings = [CardBinding.from_dict(binding) for binding in bindings_data]
            
            self.logger.debug(f"獲取卡片綁定成功: {card_id}, 共 {len(bindings)} 個綁定")
            return bindings
            
        except Exception as e:
            self.logger.error(f"獲取卡片綁定失敗: {card_id}, 錯誤: {e}")
            return []
    
    def validate_member_access(self, member_id: str) -> bool:
        """驗證會員訪問權限"""
        member = self.get_member_by_id(member_id)
        
        if not member:
            return False
        
        return member.is_active()
    
    def search_members(self, keyword: str, limit: int = 50) -> List[Member]:
        """搜索會員"""
        try:
            # 使用基類的搜索方法
            search_fields = ["name", "phone", "email", "member_no"]
            members_data = self.search_records("member_profiles", search_fields, keyword, limit)
            
            members = [Member.from_dict(member_data) for member_data in members_data]
            
            self.logger.debug(f"搜索會員成功: 關鍵字 '{keyword}', 返回 {len(members)} 個結果")
            return members
            
        except Exception as e:
            self.logger.error(f"搜索會員失敗: 關鍵字 '{keyword}', 錯誤: {e}")
            return []
    
    def get_member_summary(self, member_id: str) -> Dict[str, Any]:
        """獲取會員摘要信息"""
        try:
            member = self.get_member_by_id(member_id)
            if not member:
                return {}
            
            cards = self.get_member_cards(member_id)
            
            # 計算統計信息
            total_balance = sum(card.balance or 0 for card in cards)
            total_points = sum(card.points or 0 for card in cards)
            active_cards = len([card for card in cards if card.is_active()])
            
            summary = {
                "member": member,
                "cards_count": len(cards),
                "active_cards_count": active_cards,
                "total_balance": total_balance,
                "total_points": total_points,
                "highest_level": max((card.level or 0 for card in cards), default=0)
            }
            
            self.logger.debug(f"獲取會員摘要成功: {member_id}")
            return summary
            
        except Exception as e:
            self.logger.error(f"獲取會員摘要失敗: {member_id}, 錯誤: {e}")
            return {}
    
    def update_member_info(self, member_id: str, updates: Dict[str, Any]) -> bool:
        """更新會員信息"""
        self.log_operation("更新會員信息", {"member_id": member_id, "updates": updates})
        
        try:
            # 過濾允許更新的字段
            allowed_fields = ["name", "phone", "email", "status"]
            filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
            
            if not filtered_updates:
                self.logger.warning(f"沒有有效的更新字段: {member_id}")
                return False
            
            result = self.update_record("member_profiles", filtered_updates, {"id": member_id})
            
            if result:
                self.logger.info(f"會員信息更新成功: {member_id}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"會員信息更新失敗: {member_id}, 錯誤: {e}")
            raise self.handle_service_error("更新會員信息", e, {"member_id": member_id})
    
    def suspend_member(self, member_id: str) -> bool:
        """暫停會員"""
        return self.update_member_info(member_id, {"status": "suspended"})
    
    def activate_member(self, member_id: str) -> bool:
        """激活會員"""
        return self.update_member_info(member_id, {"status": "active"})
    
    def get_member_external_identities(self, member_id: str) -> List[Dict]:
        """獲取會員外部身份"""
        try:
            identities = self.query_table("member_external_identities", {"member_id": member_id})
            
            self.logger.debug(f"獲取會員外部身份成功: {member_id}, 共 {len(identities)} 個")
            return identities
            
        except Exception as e:
            self.logger.error(f"獲取會員外部身份失敗: {member_id}, 錯誤: {e}")
            return []
    
    def validate_member_login(self, identifier: str) -> Optional[Member]:
        """驗證會員登入"""
        self.log_operation("會員登入驗證", {"identifier": identifier[:8] + "..."})
        
        try:
            # 嘗試按 ID 查詢
            if self.validate_uuid(identifier):
                member = self.get_member_by_id(identifier)
            else:
                # 按手機號查詢
                member = self.get_member_by_phone(identifier)
            
            if not member:
                self.logger.warning(f"會員不存在: {identifier}")
                return None
            
            if not member.is_active():
                self.logger.warning(f"會員狀態異常: {identifier}, 狀態: {member.status}")
                return None
            
            self.logger.info(f"會員登入驗證成功: {member.id}")
            return member
            
        except Exception as e:
            self.logger.error(f"會員登入驗證失敗: {identifier}, 錯誤: {e}")
            return None
    
    def get_member_card_by_no(self, member_id: str, card_no: str) -> Optional[Card]:
        """根據卡號獲取會員卡片"""
        try:
            cards = self.get_member_cards(member_id)
            
            for card in cards:
                if card.card_no == card_no:
                    return card
            
            self.logger.debug(f"會員卡片不存在: {member_id}, 卡號: {card_no}")
            return None
            
        except Exception as e:
            self.logger.error(f"獲取會員卡片失敗: {member_id}, 卡號: {card_no}, 錯誤: {e}")
            return None
    
    def get_active_cards(self, member_id: str) -> List[Card]:
        """獲取會員的激活卡片"""
        cards = self.get_member_cards(member_id)
        return [card for card in cards if card.is_active()]
    
    def get_rechargeable_cards(self, member_id: str) -> List[Card]:
        """獲取會員的可充值卡片"""
        cards = self.get_member_cards(member_id)
        return [card for card in cards if card.can_recharge()]
    
    def check_member_permissions(self, member_id: str, card_id: str) -> Optional[str]:
        """檢查會員對卡片的權限"""
        try:
            # 檢查是否是卡片擁有者
            card = self.get_single_record("member_cards", {"id": card_id})
            if card and card.get("owner_member_id") == member_id:
                return "owner"
            
            # 檢查綁定權限
            binding = self.get_single_record("card_bindings", {
                "card_id": card_id, 
                "member_id": member_id
            })
            
            if binding:
                return binding.get("role")
            
            return None
            
        except Exception as e:
            self.logger.error(f"檢查會員權限失敗: {member_id}, 卡片: {card_id}, 錯誤: {e}")
            return None