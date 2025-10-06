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
        self._show_welcome_screen()
        
        choice = input("\n您的選擇 (1-4): ").strip()
        
        if choice == "1":
            return self._super_admin_login()
        elif choice == "2":
            return self._merchant_login()
        elif choice == "3":
            return self._member_login()
        elif choice == "4":
            return None
        else:
            BaseUI.show_error("無效的選擇")
            BaseUI.pause()
            return self.show_login()
    
    def _show_welcome_screen(self):
        """顯示歡迎界面"""
        print("╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║                   歡迎使用 MPS 會員支付系統                             ║")
        print("║                 Member Payment System v2.0                                ║")
        print("╠═══════════════════════════════════════════════════════════════════════════╣")
        print("║  請選擇您的角色類型：                                                     ║")
        print("║                                                                           ║")
        print("║  🔑 1. 系統管理員 (Super Admin)                                          ║")
        print("║  🏪 2. 商戶用戶 (Merchant)                                                ║")
        print("║  👤 3. 會員用戶 (Member)                                                  ║")
        print("║  ❌ 4. 退出系統                                                          ║")
        print("║                                                                           ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    def _super_admin_login(self) -> Optional[Dict]:
        """超級管理員登入"""
        BaseUI.clear_screen()
        BaseUI.show_header("Super Admin Login")
        
        print("\n請輸入您的登入資訊：")
        email = input("Email: ").strip()
        password = getpass.getpass("Password: ")
        
        if not email or not password:
            BaseUI.show_error("請輸入 email 和密碼")
            BaseUI.pause()
            return None
        
        try:
            result = self.auth_service.login_with_email(email, password)
            
            if result.get('role') not in ['admin', 'super_admin']:
                BaseUI.show_error("您沒有管理員權限")
                BaseUI.pause()
                return None
            
            role_display = {
                "admin": "管理員",
                "super_admin": "超級管理員"
            }.get(result['role'], result['role'])
            
            BaseUI.show_success(f"登入成功！角色：{role_display}")
            logger.info(f"Super Admin login successful - Role: {result['role']}, Email: {email}")
            BaseUI.pause()
            
            return result
            
        except Exception as e:
            BaseUI.show_error(f"登入失敗：{e}")
            BaseUI.pause()
            return None
    
    def _merchant_login(self) -> Optional[Dict]:
        """商戶登入"""
        BaseUI.clear_screen()
        BaseUI.show_header("Merchant Login")
        
        print("\n請輸入您的登入資訊：")
        merchant_code = input("Merchant Code: ").strip()
        password = getpass.getpass("Password: ")
        
        if not merchant_code or not password:
            BaseUI.show_error("請輸入商戶代碼和密碼")
            BaseUI.pause()
            return None
        
        try:
            result = self.auth_service.login_with_merchant_code(merchant_code, password)
            
            BaseUI.show_success(f"登入成功！歡迎 {result['profile'].get('merchant_name', '')}")
            logger.info(f"Merchant login successful - Code: {merchant_code}")
            BaseUI.pause()
            
            return result
            
        except Exception as e:
            BaseUI.show_error(f"登入失敗：{e}")
            BaseUI.pause()
            return None
    
    def _member_login(self) -> Optional[Dict]:
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
    
    # 保留舊方法以保持兼容性
    def _login_with_email(self) -> Optional[Dict]:
        """Email 登入（兼容性方法）"""
        return self._super_admin_login()
    
    def _login_with_identifier(self) -> Optional[Dict]:
        """會員登入（兼容性方法）"""
        return self._member_login()