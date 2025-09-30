#!/usr/bin/env python3
"""
測試會員密碼功能 v2
- 使用隨機測試數據避免重複
- 包含完整的清理功能
- 測試創建、登入、搜尋功能
"""

import sys
from pathlib import Path
import getpass
import random
import time

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.member_service import MemberService
from services.auth_service import AuthService
from utils.logger import get_logger

logger = get_logger(__name__)

# 全局變量儲存創建的測試會員
test_members = []

def setup_admin_auth():
    """設定管理員認證"""
    print("\n🔐 需要管理員權限來創建和管理會員")
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

def generate_test_data():
    """生成隨機測試數據"""
    timestamp = str(int(time.time()))[-6:]
    random_num = str(random.randint(100, 999))
    
    return {
        "name": f"測試用戶_{timestamp}",
        "phone": f"138{timestamp}{random_num}"[:11],  # 確保11位手機號
        "email": f"test_{timestamp}_{random_num}@example.com",
        "password": f"test{timestamp}"
    }

def test_create_member_with_password(auth_service):
    """測試創建帶密碼的會員"""
    print("\n" + "="*60)
    print("測試：創建帶密碼的會員")
    print("="*60)
    
    member_service = MemberService()
    member_service.set_auth_service(auth_service)
    
    # 生成隨機測試數據
    test_data = generate_test_data()
    
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
        
        # 記錄創建的會員
        test_members.append({
            "member_id": member_id,
            "data": test_data
        })
        
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
                return False, None
        
        return True, test_data
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        logger.error(f"創建會員失敗: {e}", exc_info=True)
        return False, None

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

def test_search_members(auth_service):
    """測試搜尋會員功能"""
    print("\n" + "="*60)
    print("測試：搜尋會員功能")
    print("="*60)
    
    member_service = MemberService()
    member_service.set_auth_service(auth_service)
    
    try:
        # 測試 1: 按姓名搜尋
        print(f"\n🔍 測試 1: 按姓名搜尋...")
        search_keyword = "測試"
        print(f"   搜尋關鍵字: {search_keyword}")
        
        results = member_service.search_members(search_keyword)
        print(f"   搜尋結果: {len(results)} 個會員")
        
        for i, member in enumerate(results[:3], 1):  # 只顯示前3個
            print(f"   {i}. {member.name} ({member.phone}) - {member.member_no}")
        
        # 測試 2: 按手機號搜尋
        if test_members:
            test_phone = test_members[0]["data"]["phone"][:5]  # 取前5位
            print(f"\n🔍 測試 2: 按手機號搜尋...")
            print(f"   搜尋關鍵字: {test_phone}")
            
            results = member_service.search_members(test_phone)
            print(f"   搜尋結果: {len(results)} 個會員")
            
            for i, member in enumerate(results[:3], 1):
                print(f"   {i}. {member.name} ({member.phone}) - {member.member_no}")
        
        # 測試 3: 無效搜尋
        print(f"\n🔍 測試 3: 無效搜尋...")
        search_invalid = "不存在的關鍵字xyz123"
        print(f"   搜尋關鍵字: {search_invalid}")
        
        results = member_service.search_members(search_invalid)
        print(f"   搜尋結果: {len(results)} 個會員")
        
        print(f"\n✅ 搜尋功能測試完成")
        return True
        
    except Exception as e:
        print(f"\n❌ 搜尋測試失敗: {e}")
        logger.error(f"搜尋會員失敗: {e}", exc_info=True)
        return False

def cleanup_test_members(auth_service):
    """清理測試會員"""
    if not test_members:
        return
        
    print("\n" + "="*60)
    print("清理測試數據")
    print("="*60)
    
    member_service = MemberService()
    member_service.set_auth_service(auth_service)
    
    for test_member in test_members:
        member_id = test_member["member_id"]
        member_name = test_member["data"]["name"]
        try:
            # 暫停會員（軟刪除）
            result = member_service.rpc_call("admin_suspend_member", {"p_member_id": member_id})
            print(f"✅ 已暫停測試會員: {member_name} ({member_id})")
        except Exception as e:
            print(f"⚠️  清理會員失敗: {member_name}, 錯誤: {e}")
    
    test_members.clear()

def main():
    """主測試函數"""
    print("\n" + "="*60)
    print("會員密碼功能測試 v2")
    print("="*60)
    
    # 先進行管理員認證
    try:
        auth_service = setup_admin_auth()
    except Exception as e:
        print(f"❌ 管理員認證失敗: {e}")
        print("\n⚠️  無法進行測試，需要管理員權限")
        return 1
    
    try:
        # 測試 1: 創建帶密碼的會員
        print(f"\n📝 開始測試...")
        test1_result = test_create_member_with_password(auth_service)
        test1_passed = test1_result[0] if isinstance(test1_result, tuple) else test1_result
        test_data = test1_result[1] if isinstance(test1_result, tuple) else None
        
        # 測試 2: 會員登入
        test2_passed = False
        if test1_passed and test_data:
            test2_passed = test_member_login(test_data["phone"], test_data["password"])
        else:
            print("\n⏭️  跳過登入測試（因為會員創建失敗）")
        
        # 測試 3: 搜尋會員功能
        test3_passed = False
        if test1_passed:
            test3_passed = test_search_members(auth_service)
        else:
            print("\n⏭️  跳過搜尋測試（因為會員創建失敗）")
        
        # 總結
        print("\n" + "="*60)
        print("測試總結")
        print("="*60)
        print(f"創建會員測試: {'✅ 通過' if test1_passed else '❌ 失敗'}")
        print(f"會員登入測試: {'✅ 通過' if test2_passed else '❌ 失敗'}")
        print(f"搜尋會員測試: {'✅ 通過' if test3_passed else '❌ 失敗'}")
        
        success = test1_passed and test2_passed and test3_passed
        
        if success:
            print("\n🎉 所有測試通過！")
        else:
            print("\n⚠️  部分測試失敗，請檢查錯誤訊息")
        
        return 0 if success else 1
        
    finally:
        # 確保清理測試數據
        cleanup_test_members(auth_service)

if __name__ == "__main__":
    sys.exit(main())