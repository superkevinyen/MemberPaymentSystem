from typing import Optional, Dict, Any
from .base_service import BaseService
from utils.logger import get_logger

logger = get_logger(__name__)

class AuthService(BaseService):
    """統一身份驗證服務"""
    
    def __init__(self):
        super().__init__()
        self.current_user = None
        self.current_role = None
        self.auth_type = None  # 'supabase_auth' or 'custom'
    
    def login_with_email(self, email: str, password: str) -> Dict[str, Any]:
        """Email 登入（管理員/商戶）"""
        self.log_operation("Email login", {"email": email})
        
        try:
            # 1. Supabase Auth 登入
            auth_response = self.client.sign_in_with_password(email, password)
            
            # 2. 取得用戶角色和資料
            profile = self.rpc_call("get_user_profile", {})
            
            if not profile:
                self.client.sign_out()
                raise Exception("USER_NOT_AUTHORIZED")
            
            # 3. 只允許 admin 和 merchant
            role = profile.get("role")
            if role not in ["admin", "super_admin", "merchant"]:
                self.client.sign_out()
                raise Exception("INVALID_LOGIN_METHOD")
            
            self.current_user = profile
            self.current_role = role
            self.auth_type = "supabase_auth"
            
            self.logger.info(f"Email login successful: {email}, role: {role}")
            
            return {
                "success": True,
                "role": role,
                "profile": profile,
                "auth_type": "supabase_auth"
            }
            
        except Exception as e:
            self.logger.error(f"Email login failed: {email}, error: {e}")
            raise self.handle_service_error("Email login", e)
    
    def login_with_identifier(self, identifier: str, password: str) -> Dict[str, Any]:
        """識別碼登入（會員）"""
        self.log_operation("Member login", {"identifier": identifier})
        
        try:
            result = self.rpc_call("member_login", {
                "p_identifier": identifier,
                "p_password": password
            })
            
            if not result:
                raise Exception("LOGIN_FAILED")
            
            self.current_user = result
            self.current_role = "member"
            self.auth_type = "custom"
            
            self.logger.info(f"Member login successful: {identifier}")
            
            return {
                "success": True,
                "role": "member",
                "profile": result,
                "auth_type": "custom"
            }
            
        except Exception as e:
            self.logger.error(f"Member login failed: {identifier}, error: {e}")
            raise self.handle_service_error("Member login", e)
    
    def login_merchant_with_code(self, merchant_code: str, password: str) -> Dict[str, Any]:
        """商戶代碼登入"""
        self.log_operation("Merchant code login", {"merchant_code": merchant_code})
        
        try:
            result = self.rpc_call("merchant_login", {
                "p_merchant_code": merchant_code,
                "p_password": password
            })
            
            if not result:
                raise Exception("LOGIN_FAILED")
            
            self.current_user = result
            self.current_role = "merchant"
            self.auth_type = "custom"
            
            self.logger.info(f"Merchant login successful: {merchant_code}")
            
            return {
                "success": True,
                "role": "merchant",
                "profile": result,
                "auth_type": "custom"
            }
            
        except Exception as e:
            self.logger.error(f"Merchant login failed: {merchant_code}, error: {e}")
            raise self.handle_service_error("Merchant login", e)
    
    def logout(self):
        """登出"""
        try:
            if self.auth_type == "supabase_auth":
                self.client.sign_out()
            
            self.logger.info(f"Logout successful: role {self.current_role}")
            
            self.current_user = None
            self.current_role = None
            self.auth_type = None
            
        except Exception as e:
            self.logger.error(f"Logout failed: {e}")
    
    def get_current_user(self) -> Optional[Dict]:
        """取得當前用戶"""
        return self.current_user
    
    def get_current_role(self) -> Optional[str]:
        """取得當前角色"""
        return self.current_role
    
    def check_permission(self, required_role: str) -> bool:
        """檢查權限"""
        if not self.current_role:
            return False
        
        role_hierarchy = {
            "super_admin": 4,
            "admin": 3,
            "merchant": 2,
            "member": 1
        }
        
        current_level = role_hierarchy.get(self.current_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return current_level >= required_level
    
    def is_authenticated(self) -> bool:
        """檢查是否已登入"""
        if self.auth_type == "supabase_auth":
            return self.client.is_authenticated()
        elif self.auth_type == "custom":
            return self.current_user is not None
        return False