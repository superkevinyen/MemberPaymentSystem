#!/usr/bin/env python3
"""
測試新添加的 UI 功能
測試新的會員管理、卡片管理、交易統計和系統管理功能
"""

import sys
from pathlib import Path
from decimal import Decimal

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_helpers import (
    setup_admin_auth,
    cleanup_all_test_data,
    print_test_header,
    print_test_step,
    print_test_info,
    print_test_result,
    print_test_summary,
    create_test_member,
    create_test_merchant,
    get_member_default_card,
    recharge_card,
    generate_qr_code,
    make_payment
)
from services.admin_service import AdminService
from services.member_service import MemberService
from services.payment_service import PaymentService
from utils.logger import get_logger

logger = get_logger(__name__)

def test_get_all_members(auth_service):
    """測試分頁獲取所有會員功能"""
    print_test_header("分頁獲取所有會員")
    
    try:
        member_service = MemberService()
        member_service.set_auth_service(auth_service)
        
        # 創建一些測試會員
        print_test_step("創建測試會員")
        test_members = []
        for i in range(5):
            member_id, member_data = create_test_member(auth_service)
            test_members.append((member_id, member_data))
        
        # 測試分頁獲取
        print_test_step("測試分頁獲取所有會員")
        result = member_service.get_all_members(limit=3, offset=0)
        
        members = result['data']
        pagination = result['pagination']
        
        print_test_info("返回會員數量", len(members))
        print_test_info("總會員數", pagination['total_count'])
        print_test_info("當前頁", pagination['current_page'])
        print_test_info("總頁數", pagination['total_pages'])
        
        if len(members) > 3:
            raise Exception(f"返回會員數量超過限制：期望最多3個，實際{len(members)}")
        
        if pagination['total_count'] < 5:
            raise Exception(f"總會員數量不正確：期望至少5個，實際{pagination['total_count']}")
        
        # 測試第二頁
        print_test_step("測試第二頁")
        result2 = member_service.get_all_members(limit=3, offset=3)
        members2 = result2['data']
        pagination2 = result2['pagination']
        
        print_test_info("第二頁會員數量", len(members2))
        print_test_info("第二頁當前頁", pagination2['current_page'])
        
        print_test_result("分頁獲取所有會員", True, "分頁功能正常")
        return True
        
    except Exception as e:
        print_test_result("分頁獲取所有會員", False, str(e))
        logger.error(f"分頁獲取所有會員測試失敗: {e}", exc_info=True)
        return False

def test_search_members_advanced(auth_service):
    """測試高級會員搜尋功能"""
    print_test_header("高級會員搜尋")
    
    try:
        member_service = MemberService()
        member_service.set_auth_service(auth_service)
        
        # 創建測試會員
        print_test_step("創建測試會員")
        member_id, member_data = create_test_member(auth_service, 
                                                name="搜尋測試會員", 
                                                phone="13800138000")
        
        # 測試按名稱搜尋
        print_test_step("測試按名稱搜尋")
        members = member_service.search_members_advanced(name="搜尋測試會員")
        
        if len(members) == 0:
            raise Exception("按名稱搜尋未找到結果")
        
        found_member = members[0]
        if found_member.name != "搜尋測試會員":
            raise Exception(f"搜尋結果名稱不正確：期望'搜尋測試會員'，實際'{found_member.name}'")
        
        print_test_info("按名稱搜尋結果", f"找到{len(members)}個會員")
        
        # 測試按手機搜尋
        print_test_step("測試按手機搜尋")
        members = member_service.search_members_advanced(phone="13800138000")
        
        if len(members) == 0:
            raise Exception("按手機搜尋未找到結果")
        
        print_test_info("按手機搜尋結果", f"找到{len(members)}個會員")
        
        # 測試按狀態搜尋
        print_test_step("測試按狀態搜尋")
        members = member_service.search_members_advanced(status="active")
        
        if len(members) == 0:
            raise Exception("按狀態搜尋未找到結果")
        
        print_test_info("按狀態搜尋結果", f"找到{len(members)}個活躍會員")
        
        print_test_result("高級會員搜尋", True, "高級搜尋功能正常")
        return True
        
    except Exception as e:
        print_test_result("高級會員搜尋", False, str(e))
        logger.error(f"高級會員搜尋測試失敗: {e}", exc_info=True)
        return False

def test_update_member_profile(auth_service):
    """測試更新會員資料功能"""
    print_test_header("更新會員資料")
    
    try:
        member_service = MemberService()
        member_service.set_auth_service(auth_service)
        
        # 創建測試會員
        print_test_step("創建測試會員")
        member_id, member_data = create_test_member(auth_service)
        
        # 更新會員資料
        print_test_step("更新會員資料")
        result = member_service.update_member_profile(
            member_id,
            name="更新後的會員名稱",
            phone="13900139000",
            email="updated@example.com"
        )
        
        if not result:
            raise Exception("更新會員資料失敗")
        
        # 驗證更新結果
        print_test_step("驗證更新結果")
        updated_member = member_service.get_member_by_id(member_id)
        
        if updated_member.name != "更新後的會員名稱":
            raise Exception(f"名稱更新失敗：期望'更新後的會員名稱'，實際'{updated_member.name}'")
        
        if updated_member.phone != "13900139000":
            raise Exception(f"手機更新失敗：期望'13900139000'，實際'{updated_member.phone}'")
        
        if updated_member.email != "updated@example.com":
            raise Exception(f"郵箱更新失敗：期望'updated@example.com'，實際'{updated_member.email}'")
        
        print_test_info("更新後名稱", updated_member.name)
        print_test_info("更新後手機", updated_member.phone)
        print_test_info("更新後郵箱", updated_member.email)
        
        print_test_result("更新會員資料", True, "更新功能正常")
        return True
        
    except Exception as e:
        print_test_result("更新會員資料", False, str(e))
        logger.error(f"更新會員資料測試失敗: {e}", exc_info=True)
        return False

def test_get_all_cards(auth_service):
    """測試分頁獲取所有卡片功能"""
    print_test_header("分頁獲取所有卡片")
    
    try:
        admin_service = AdminService()
        admin_service.set_auth_service(auth_service)
        
        # 創建測試會員和卡片
        print_test_step("創建測試會員和卡片")
        member_id, member_data = create_test_member(auth_service)
        
        # 測試分頁獲取
        print_test_step("測試分頁獲取所有卡片")
        result = admin_service.get_all_cards(limit=5, offset=0)
        
        cards = result['data']
        pagination = result['pagination']
        
        print_test_info("返回卡片數量", len(cards))
        print_test_info("總卡片數", pagination['total_count'])
        
        if len(cards) > 5:
            raise Exception(f"返回卡片數量超過限制：期望最多5個，實際{len(cards)}")
        
        # 驗證卡片信息結構
        if cards and len(cards) > 0:
            card = cards[0]
            if not hasattr(card, 'card_no') or not hasattr(card, 'owner_name'):
                raise Exception("卡片信息結構不完整，缺少必要字段")
        
        print_test_result("分頁獲取所有卡片", True, "分頁功能正常")
        return True
        
    except Exception as e:
        print_test_result("分頁獲取所有卡片", False, str(e))
        logger.error(f"分頁獲取所有卡片測試失敗: {e}", exc_info=True)
        return False

def test_search_cards_advanced(auth_service):
    """測試高級卡片搜尋功能"""
    print_test_header("高級卡片搜尋")
    
    try:
        admin_service = AdminService()
        admin_service.set_auth_service(auth_service)
        
        # 創建測試會員
        print_test_step("創建測試會員")
        member_id, member_data = create_test_member(auth_service, name="卡片搜尋測試")
        
        # 測試按擁有者名稱搜尋
        print_test_step("測試按擁有者名稱搜尋")
        cards = admin_service.search_cards_advanced("卡片搜尋測試")
        
        if len(cards) == 0:
            raise Exception("按擁有者名稱搜尋未找到結果")
        
        print_test_info("按擁有者名稱搜尋結果", f"找到{len(cards)}張卡片")
        
        # 驗證卡片信息結構
        if cards and len(cards) > 0:
            card = cards[0]
            if not hasattr(card, 'card_no') or not hasattr(card, 'owner_name'):
                raise Exception("卡片信息結構不完整")
            
            if card.owner_name != "卡片搜尋測試":
                raise Exception(f"搜尋結果擁有者名稱不正確：期望'卡片搜尋測試'，實際'{card.owner_name}'")
        
        print_test_result("高級卡片搜尋", True, "高級搜尋功能正常")
        return True
        
    except Exception as e:
        print_test_result("高級卡片搜尋", False, str(e))
        logger.error(f"高級卡片搜尋測試失敗: {e}", exc_info=True)
        return False

def test_today_transaction_stats(auth_service):
    """測試今日交易統計功能"""
    print_test_header("今日交易統計")
    
    try:
        payment_service = PaymentService()
        payment_service.set_auth_service(auth_service)
        
        # 創建測試數據
        print_test_step("創建測試數據")
        member_id, member_data = create_test_member(auth_service)
        merchant_id, merchant_data = create_test_merchant(auth_service)
        
        card_id = get_member_default_card(auth_service, member_id)
        recharge_card(auth_service, card_id, Decimal("1000.00"))
        
        # 執行一些交易
        print_test_step("執行測試交易")
        for i in range(3):
            qr_result = generate_qr_code(auth_service, card_id)
            make_payment(
                auth_service,
                merchant_data['code'],
                qr_result['qr_plain'],
                Decimal("100.00")
            )
        
        # 獲取今日交易統計
        print_test_step("獲取今日交易統計")
        stats = payment_service.get_today_transaction_stats()
        
        if not stats:
            raise Exception("獲取今日交易統計失敗")
        
        print_test_info("交易筆數", stats.get('transaction_count', 0))
        print_test_info("支付金額", f"¥{stats.get('payment_amount', 0)}")
        print_test_info("退款金額", f"¥{stats.get('refund_amount', 0)}")
        print_test_info("淨額", f"¥{stats.get('net_amount', 0)}")
        print_test_info("獨立客戶數", stats.get('unique_customers', 0))
        print_test_info("平均交易額", f"¥{stats.get('average_transaction', 0)}")
        
        # 驗證統計數據合理性
        if stats.get('transaction_count', 0) < 3:
            raise Exception("交易筆數統計不正確")
        
        if stats.get('payment_amount', 0) <= 0:
            raise Exception("支付金額統計不正確")
        
        print_test_result("今日交易統計", True, "統計功能正常")
        return True
        
    except Exception as e:
        print_test_result("今日交易統計", False, str(e))
        logger.error(f"今日交易統計測試失敗: {e}", exc_info=True)
        return False

def test_system_statistics_extended(auth_service):
    """測試擴展系統統計功能"""
    print_test_header("擴展系統統計")
    
    try:
        admin_service = AdminService()
        admin_service.set_auth_service(auth_service)
        
        # 創建一些測試數據
        print_test_step("創建測試數據")
        for i in range(3):
            create_test_member(auth_service)
        
        # 獲取擴展系統統計
        print_test_step("獲取擴展系統統計")
        stats = admin_service.get_system_statistics_extended()
        
        if not stats:
            raise Exception("獲取擴展系統統計失敗")
        
        print_test_info("會員總數", stats.get('members_total', 0))
        print_test_info("活躍會員數", stats.get('members_active', 0))
        print_test_info("非活躍會員數", stats.get('members_inactive', 0))
        print_test_info("暫停會員數", stats.get('members_suspended', 0))
        
        print_test_info("卡片總數", stats.get('cards_total', 0))
        print_test_info("活躍卡片數", stats.get('cards_active', 0))
        
        print_test_info("商戶總數", stats.get('merchants_total', 0))
        print_test_info("活躍商戶數", stats.get('merchants_active', 0))
        
        print_test_info("今日交易筆數", stats.get('transactions_today', 0))
        print_test_info("今日交易金額", f"¥{stats.get('transactions_today_amount', 0)}")
        
        # 驗證統計數據合理性
        if stats.get('members_total', 0) < 3:
            raise Exception("會員總數統計不正確")
        
        if stats.get('cards_total', 0) < 3:  # 每個會員至少有一張預設卡
            raise Exception("卡片總數統計不正確")
        
        # 檢查卡片類型統計
        cards_by_type = stats.get('cards_by_type', {})
        if cards_by_type:
            print_test_info("卡片類型統計", str(cards_by_type))
        
        print_test_result("擴展系統統計", True, "統計功能正常")
        return True
        
    except Exception as e:
        print_test_result("擴展系統統計", False, str(e))
        logger.error(f"擴展系統統計測試失敗: {e}", exc_info=True)
        return False

def test_system_health_check(auth_service):
    """測試系統健康檢查功能"""
    print_test_header("系統健康檢查")
    
    try:
        admin_service = AdminService()
        admin_service.set_auth_service(auth_service)
        
        # 執行系統健康檢查
        print_test_step("執行系統健康檢查")
        health_checks = admin_service.system_health_check()
        
        if not health_checks:
            raise Exception("系統健康檢查返回空結果")
        
        print_test_info("健康檢查項數", len(health_checks))
        
        # 檢查每個健康檢查項
        for check in health_checks:
            check_name = check.get('check_name', 'Unknown')
            status = check.get('status', 'unknown')
            details = check.get('details', {})
            recommendation = check.get('recommendation')
            
            print_test_info(f"檢查項: {check_name}", f"狀態: {status}")
            
            if details:
                for key, value in details.items():
                    print_test_info(f"  {key}", str(value))
            
            if recommendation:
                print_test_info(f"  建議", recommendation)
            
            # 驗證必要字段
            if not check_name:
                raise Exception("健康檢查項缺少名稱")
            
            if status not in ['ok', 'warning', 'error']:
                raise Exception(f"健康檢查狀態無效: {status}")
        
        print_test_result("系統健康檢查", True, "健康檢查功能正常")
        return True
        
    except Exception as e:
        print_test_result("系統健康檢查", False, str(e))
        logger.error(f"系統健康檢查測試失敗: {e}", exc_info=True)
        return False

def run_test_with_clean_session(test_name, test_func, admin_email, admin_password):
    """使用乾淨的 session 運行單個測試"""
    from config.supabase_client import supabase_client
    
    print(f"\n{'='*60}")
    print(f"準備測試: {test_name}")
    print(f"{'='*60}")
    
    # 1. 確保 session 乾淨
    print("🔄 確保 session 狀態乾淨...")
    try:
        supabase_client.ensure_clean_session()
        print("   ✅ Session 已清除")
    except Exception as e:
        print(f"   ⚠️  清除 session 失敗: {e}")
    
    # 2. 重新登入
    print(f"🔐 使用管理員身份登入...")
    try:
        auth_service = setup_admin_auth(admin_email, admin_password)
        print(f"   ✅ 登入成功")
    except Exception as e:
        print(f"   ❌ 登入失敗: {e}")
        return False
    
    # 3. 運行測試
    try:
        result = test_func(auth_service)
        return result
    finally:
        # 4. 測試結束後登出
        print(f"\n🔓 測試結束，登出...")
        try:
            auth_service.logout()
            print(f"   ✅ 已登出")
        except Exception as e:
            print(f"   ⚠️  登出失敗: {e}")

def main(auth_service=None):
    """主測試函數"""
    print("\n" + "="*60)
    print("新 UI 功能測試")
    print("="*60)
    
    # 獲取管理員憑證（只詢問一次）
    print("\n🔐 需要管理員權限來執行測試")
    print("請輸入管理員登入資訊（將用於所有測試）：")
    
    import getpass
    admin_email = input("Admin Email: ").strip()
    admin_password = getpass.getpass("Admin Password: ")
    
    if not admin_email or not admin_password:
        print("❌ 請輸入完整的管理員登入資訊")
        return False
    
    results = {}
    
    try:
        # 運行所有測試（每個測試都有獨立的 login/logout）
        print("\n🚀 開始運行測試...")
        
        results["分頁獲取所有會員"] = run_test_with_clean_session(
            "分頁獲取所有會員", 
            test_get_all_members, 
            admin_email, 
            admin_password
        )
        
        results["高級會員搜尋"] = run_test_with_clean_session(
            "高級會員搜尋", 
            test_search_members_advanced, 
            admin_email, 
            admin_password
        )
        
        results["更新會員資料"] = run_test_with_clean_session(
            "更新會員資料", 
            test_update_member_profile, 
            admin_email, 
            admin_password
        )
        
        results["分頁獲取所有卡片"] = run_test_with_clean_session(
            "分頁獲取所有卡片", 
            test_get_all_cards, 
            admin_email, 
            admin_password
        )
        
        results["高級卡片搜尋"] = run_test_with_clean_session(
            "高級卡片搜尋", 
            test_search_cards_advanced, 
            admin_email, 
            admin_password
        )
        
        results["今日交易統計"] = run_test_with_clean_session(
            "今日交易統計", 
            test_today_transaction_stats, 
            admin_email, 
            admin_password
        )
        
        results["擴展系統統計"] = run_test_with_clean_session(
            "擴展系統統計", 
            test_system_statistics_extended, 
            admin_email, 
            admin_password
        )
        
        results["系統健康檢查"] = run_test_with_clean_session(
            "系統健康檢查", 
            test_system_health_check, 
            admin_email, 
            admin_password
        )
        
        # 打印總結
        success = print_test_summary(results)
        return success
        
    finally:
        # 最終清理
        print("\n" + "="*60)
        print("最終清理")
        print("="*60)
        try:
            # 重新登入以執行清理
            auth_service = setup_admin_auth(admin_email, admin_password)
            cleanup_all_test_data(auth_service, hard_delete=True)
            auth_service.logout()
        except Exception as e:
            print(f"⚠️  最終清理失敗: {e}")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)