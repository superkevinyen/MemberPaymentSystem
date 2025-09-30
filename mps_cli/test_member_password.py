#!/usr/bin/env python3
"""
測試會員密碼功能
驗證創建會員時是否正確設定密碼
"""

import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.member_service import MemberService
from services.auth_service import AuthService
from utils.logger import get_logger
import getpass

logger = get_logger(__name__)

def setup_admin_auth():
    """設定管理員認證"""
    print("\n🔐 需要管理員權限來創建會員")
    print("請輸入管理員登入資訊：")
    
    email = input("Admin Email: ").strip()
    password = getpass.getpass("Admin Password: ")
    
    if not email or not password:
        raise Exception("請輸入完整的管理員登入資訊")
    
    auth_service = AuthService()
    
    try:
        result = auth_service.login_with_email(email, password)
        if result and result.get('success'):
            print(f"✅ 管理員登入成功：{result.get('role')}")
            return auth_service
        else:
            raise Exception("管理員登入失敗")
    except Exception as e:
        raise Exception(f"管理員認證失敗: {e}")

def test_create_member_with_password():
    """測試創建帶密碼的會員"""
    print("\n" + "="*60)
    print("測試：創建帶密碼的會員")
    print("="*60)
    
    # 先進行管理員認證
    try:
        auth_service = setup_admin_auth()
    except Exception as e:
        print(f"❌ 認證失敗: {e}")
        return False
    
    member_service = MemberService()
    member_service.set_auth_service(auth_service)
    
    # 測試數據
    test_data = {
        "name": "測試用戶",
        "phone": "13800138000",
        "email": "test@example.com",
        "password": "test123456"
    }
    
    try:
        print(f"\n📝 創建會員...")
        print(f"   姓名: {test_data['name']}")
        print(f"   手機: {test_data['phone']}")
        print(f"   郵箱: {test_data['email']}")
        print(f"   密碼: {'*' * len(test_data['password'])}")
        
        member_id = member_service.create_member(
            name=test_data['name'],
            phone=test_data['phone'],
            email=test_data['email'],
            password=test_data['password']
        )
        
        print(f"\n✅ 會員創建成功！")
        print(f"   會員 ID: {member_id}")
        
        # 驗證會員資料
        member = member_service.get_member_by_id(member_id)
        if member:
            print(f"\n📋 會員資料:")
            print(f"   會員號: {member.member_no}")
            print(f"   姓名: {member.name}")
            print(f"   手機: {member.phone}")
            print(f"   郵箱: {member.email}")
            print(f"   密碼雜湊: {'已設定' if member.password_hash else '未設定'}")
            
            if not member.password_hash:
                print("\n❌ 警告：密碼雜湊未設定！")
                return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        logger.error(f"創建會員失敗: {e}", exc_info=True)
        return False

def test_member_login(test_phone, test_password):
    """測試會員登入"""
    print("\n" + "="*60)
    print("測試：會員登入")
    print("="*60)
    
    # 創建新的 AuthService（不需要管理員權限）
    auth_service = AuthService()
    
    try:
        print(f"\n🔐 嘗試登入...")
        print(f"   手機: {test_phone}")
        print(f"   密碼: {'*' * len(test_password)}")
        
        result = auth_service.login_with_identifier(test_phone, test_password)
        
        if result and result.get('success'):
            print(f"\n✅ 登入成功！")
            profile = result.get('profile', {})
            print(f"   會員 ID: {profile.get('member_id')}")
            print(f"   會員號: {profile.get('member_no')}")
            print(f"   姓名: {profile.get('name')}")
            print(f"   角色: {result.get('role')}")
            return True
        else:
            print(f"\n❌ 登入失敗")
            return False
            
    except Exception as e:
        print(f"\n❌ 登入測試失敗: {e}")
        logger.error(f"會員登入失敗: {e}", exc_info=True)
        return False

def main():
    """主測試函數"""
    print("\n" + "="*60)
    print("會員密碼功能測試")
    print("="*60)
    
    # 測試 1: 創建帶密碼的會員
    test1_passed = test_create_member_with_password()
    
    # 測試 2: 會員登入（只有在創建成功時才測試）
    test2_passed = False
    if test1_passed:
        test2_passed = test_member_login("13800138000", "test123456")
    else:
        print("\n⏭️  跳過登入測試（因為會員創建失敗）")
    
    # 總結
    print("\n" + "="*60)
    print("測試總結")
    print("="*60)
    print(f"創建會員測試: {'✅ 通過' if test1_passed else '❌ 失敗'}")
    print(f"會員登入測試: {'✅ 通過' if test2_passed else '❌ 失敗'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 所有測試通過！")
        return 0
    else:
        print("\n⚠️  部分測試失敗，請檢查錯誤訊息")
        return 1

if __name__ == "__main__":
    sys.exit(main())