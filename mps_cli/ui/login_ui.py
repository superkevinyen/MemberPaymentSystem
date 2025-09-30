from typing import Optional, Dict
from services.auth_service import AuthService
from ui.base_ui import BaseUI
from utils.logger import get_logger
import getpass

logger = get_logger(__name__)

class LoginUI:
    """統一登入界面"""
    
    def __init__(self):
        self.auth_service = AuthService()
    
    def show_login(self) -> Optional[Dict]:
        """顯示登入界面"""
        BaseUI.clear_screen()
        BaseUI.show_header("MPS System Login")
        
        print("\n請選擇登入方式：")
        print("1. Admin/Merchant Login (Email + Password)")
        print("2. Member Login (Phone/Member No + Password)")
        print("3. Exit")
        
        choice = input("\n您的選擇 (1-3): ").strip()
        
        if choice == "1":
            return self._login_with_email()
        elif choice == "2":
            return self._login_with_identifier()
        elif choice == "3":
            return None
        else:
            BaseUI.show_error("無效的選擇")
            BaseUI.pause()
            return self.show_login()
    
    def _login_with_email(self) -> Optional[Dict]:
        """Email 登入"""
        BaseUI.clear_screen()
        BaseUI.show_header("Admin/Merchant Login")
        
        print("\n請輸入您的登入資訊：")
        email = input("Email: ").strip()
        password = getpass.getpass("Password: ")
        
        if not email or not password:
            BaseUI.show_error("請輸入 email 和密碼")
            BaseUI.pause()
            return None
        
        try:
            result = self.auth_service.login_with_email(email, password)
            
            role_display = {
                "admin": "管理員",
                "super_admin": "超級管理員",
                "merchant": "商戶"
            }.get(result['role'], result['role'])
            
            BaseUI.show_success(f"登入成功！角色：{role_display}")
            logger.info(f"Login successful - Role: {result['role']}, Email: {email}")
            BaseUI.pause()
            
            return result
            
        except Exception as e:
            BaseUI.show_error(f"登入失敗：{e}")
            BaseUI.pause()
            return None
    
    def _login_with_identifier(self) -> Optional[Dict]:
        """會員登入"""
        BaseUI.clear_screen()
        BaseUI.show_header("Member Login")
        
        print("\n請輸入您的登入資訊：")
        print("（可使用手機號碼或會員編號）")
        identifier = input("Phone/Member No: ").strip()
        password = getpass.getpass("Password: ")
        
        if not identifier or not password:
            BaseUI.show_error("請輸入識別碼和密碼")
            BaseUI.pause()
            return None
        
        try:
            result = self.auth_service.login_with_identifier(identifier, password)
            
            profile = result['profile']
            BaseUI.show_success(f"登入成功！歡迎 {profile.get('name', '')}")
            logger.info(f"Member login successful - Identifier: {identifier}")
            BaseUI.pause()
            
            return result
            
        except Exception as e:
            BaseUI.show_error(f"登入失敗：{e}")
            BaseUI.pause()
            return None