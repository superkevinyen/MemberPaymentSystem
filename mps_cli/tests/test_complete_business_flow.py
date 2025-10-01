#!/usr/bin/env python3
"""
完整業務流程測試
測試從會員創建到支付、退款、綁定等完整業務流程
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
    make_payment,
    make_refund,
    get_card_balance,
    get_card_points
)
from services.admin_service import AdminService
from services.member_service import MemberService
from utils.logger import get_logger

logger = get_logger(__name__)

def test_complete_payment_flow(auth_service):
    """
    測試完整支付流程
    1. 創建會員 → 2. 獲取默認卡片 → 3. 充值 → 4. 創建商戶 → 
    5. 生成 QR 碼 → 6. 支付 → 7. 驗證餘額和積分
    """
    print_test_header("完整支付流程")
    
    # 確保使用管理員身份開始測試
    from config.supabase_client import supabase_client
    current_role = supabase_client.rpc("get_user_role", {})
    print(f"[測試開始] 當前角色: {current_role}")
    
    try:
        # 步驟 1: 創建會員
        print_test_step("步驟 1: 創建測試會員")
        member_id, member_data = create_test_member(auth_service)
        print_test_info("會員 ID", member_id)
        print_test_info("會員姓名", member_data['name'])
        print_test_info("會員手機", member_data['phone'])
        
        # 步驟 2: 獲取默認卡片
        print_test_step("步驟 2: 獲取會員默認卡片")
        card_id = get_member_default_card(auth_service, member_id)
        if not card_id:
            raise Exception("無法獲取會員默認卡片")
        print_test_info("卡片 ID", card_id)
        
        # 記錄初始餘額和積分
        initial_balance = get_card_balance(auth_service, card_id)
        initial_points = get_card_points(auth_service, card_id)
        print_test_info("初始餘額", f"¥{initial_balance}")
        print_test_info("初始積分", initial_points)
        
        # 步驟 3: 充值
        print_test_step("步驟 3: 充值卡片")
        recharge_amount = Decimal("1000.00")
        recharge_result = recharge_card(auth_service, card_id, recharge_amount)
        print_test_info("充值金額", f"¥{recharge_amount}")
        print_test_info("充值交易號", recharge_result['tx_no'])
        
        # 驗證充值後餘額
        balance_after_recharge = get_card_balance(auth_service, card_id)
        expected_balance = initial_balance + recharge_amount
        print_test_info("充值後餘額", f"¥{balance_after_recharge}")
        
        if balance_after_recharge != expected_balance:
            raise Exception(f"充值後餘額不正確：期望 ¥{expected_balance}，實際 ¥{balance_after_recharge}")
        
        # 步驟 4: 創建商戶
        print_test_step("步驟 4: 創建測試商戶")
        merchant_id, merchant_data = create_test_merchant(auth_service)
        print_test_info("商戶 ID", merchant_id)
        print_test_info("商戶代碼", merchant_data['code'])
        print_test_info("商戶名稱", merchant_data['name'])
        
        # 步驟 5: 生成 QR 碼
        print_test_step("步驟 5: 生成支付 QR 碼")
        qr_result = generate_qr_code(auth_service, card_id)
        qr_plain = qr_result['qr_plain']
        print_test_info("QR 碼長度", len(qr_plain))
        print_test_info("QR 碼過期時間", qr_result['expires_at'])
        
        # 步驟 6: 執行支付
        print_test_step("步驟 6: 執行掃碼支付")
        payment_amount = Decimal("100.00")
        payment_result = make_payment(
            auth_service,
            merchant_data['code'],
            qr_plain,
            payment_amount
        )
        print_test_info("支付金額", f"¥{payment_amount}")
        print_test_info("實付金額", f"¥{payment_result['final_amount']}")
        print_test_info("折扣率", payment_result['discount'])
        print_test_info("交易號", payment_result['tx_no'])
        
        # 步驟 7: 驗證餘額和積分
        print_test_step("步驟 7: 驗證支付後餘額和積分")
        balance_after_payment = get_card_balance(auth_service, card_id)
        points_after_payment = get_card_points(auth_service, card_id)
        
        expected_balance_after_payment = balance_after_recharge - Decimal(str(payment_result['final_amount']))
        expected_points = initial_points + int(payment_amount)  # 標準卡：消費金額 = 積分
        
        print_test_info("支付後餘額", f"¥{balance_after_payment}")
        print_test_info("支付後積分", points_after_payment)
        print_test_info("期望餘額", f"¥{expected_balance_after_payment}")
        print_test_info("期望積分", expected_points)
        
        # 驗證餘額
        if abs(balance_after_payment - expected_balance_after_payment) > Decimal("0.01"):
            raise Exception(f"支付後餘額不正確：期望 ¥{expected_balance_after_payment}，實際 ¥{balance_after_payment}")
        
        # 驗證積分
        if points_after_payment != expected_points:
            raise Exception(f"支付後積分不正確：期望 {expected_points}，實際 {points_after_payment}")
        
        print_test_result("完整支付流程", True, "所有步驟驗證通過")
        return True
        
    except Exception as e:
        print_test_result("完整支付流程", False, str(e))
        logger.error(f"完整支付流程測試失敗: {e}", exc_info=True)
        return False

def test_complete_refund_flow(auth_service):
    """
    測試完整退款流程
    1. 創建會員和商戶 → 2. 充值 → 3. 支付 → 4. 部分退款 → 
    5. 再次部分退款 → 6. 驗證不能超額退款
    """
    print_test_header("完整退款流程")
    
    try:
        # 步驟 1: 創建會員和商戶
        print_test_step("步驟 1: 創建測試會員和商戶")
        member_id, member_data = create_test_member(auth_service)
        merchant_id, merchant_data = create_test_merchant(auth_service)
        print_test_info("會員 ID", member_id)
        print_test_info("商戶代碼", merchant_data['code'])
        
        # 步驟 2: 獲取卡片並充值
        print_test_step("步驟 2: 獲取卡片並充值")
        card_id = get_member_default_card(auth_service, member_id)
        recharge_amount = Decimal("1000.00")
        recharge_card(auth_service, card_id, recharge_amount)
        print_test_info("充值金額", f"¥{recharge_amount}")
        
        balance_before_payment = get_card_balance(auth_service, card_id)
        
        # 步驟 3: 執行支付
        print_test_step("步驟 3: 執行支付")
        qr_result = generate_qr_code(auth_service, card_id)
        payment_amount = Decimal("300.00")
        payment_result = make_payment(
            auth_service,
            merchant_data['code'],
            qr_result['qr_plain'],
            payment_amount
        )
        tx_no = payment_result['tx_no']
        final_amount = Decimal(str(payment_result['final_amount']))
        print_test_info("支付金額", f"¥{payment_amount}")
        print_test_info("實付金額", f"¥{final_amount}")
        print_test_info("交易號", tx_no)
        
        balance_after_payment = get_card_balance(auth_service, card_id)
        
        # 步驟 4: 第一次部分退款（使用商戶身份）
        print_test_step("步驟 4: 第一次部分退款（使用商戶身份）")
        refund_amount_1 = Decimal("100.00")
        refund_result_1 = make_refund(
            auth_service,
            merchant_data['code'],
            tx_no,
            refund_amount_1,
            merchant_password=merchant_data['password']
        )
        print_test_info("退款金額", f"¥{refund_amount_1}")
        print_test_info("退款交易號", refund_result_1['refund_tx_no'])
        
        balance_after_refund_1 = get_card_balance(auth_service, card_id)
        expected_balance_1 = balance_after_payment + refund_amount_1
        print_test_info("第一次退款後餘額", f"¥{balance_after_refund_1}")
        print_test_info("期望餘額", f"¥{expected_balance_1}")
        
        if abs(balance_after_refund_1 - expected_balance_1) > Decimal("0.01"):
            raise Exception(f"第一次退款後餘額不正確")
        
        # 步驟 5: 第二次部分退款（使用商戶身份）
        print_test_step("步驟 5: 第二次部分退款（使用商戶身份）")
        refund_amount_2 = Decimal("50.00")
        refund_result_2 = make_refund(
            auth_service,
            merchant_data['code'],
            tx_no,
            refund_amount_2,
            merchant_password=merchant_data['password']
        )
        print_test_info("退款金額", f"¥{refund_amount_2}")
        print_test_info("退款交易號", refund_result_2['refund_tx_no'])
        
        balance_after_refund_2 = get_card_balance(auth_service, card_id)
        expected_balance_2 = balance_after_refund_1 + refund_amount_2
        print_test_info("第二次退款後餘額", f"¥{balance_after_refund_2}")
        print_test_info("期望餘額", f"¥{expected_balance_2}")
        
        if abs(balance_after_refund_2 - expected_balance_2) > Decimal("0.01"):
            raise Exception(f"第二次退款後餘額不正確")
        
        # 步驟 6: 嘗試超額退款（應該失敗）
        print_test_step("步驟 6: 測試超額退款（應該失敗）")
        remaining_amount = final_amount - refund_amount_1 - refund_amount_2
        over_refund_amount = remaining_amount + Decimal("100.00")
        print_test_info("剩餘可退金額", f"¥{remaining_amount}")
        print_test_info("嘗試退款金額", f"¥{over_refund_amount}")
        
        try:
            make_refund(
                auth_service,
                merchant_data['code'],
                tx_no,
                over_refund_amount,
                merchant_password=merchant_data['password']
            )
            raise Exception("超額退款應該失敗但卻成功了")
        except Exception as e:
            if "REFUND_EXCEEDS_REMAINING" in str(e) or "超過" in str(e):
                print_test_info("驗證結果", "✅ 正確拒絕超額退款")
            else:
                raise Exception(f"超額退款失敗原因不正確: {e}")
        
        print_test_result("完整退款流程", True, "所有步驟驗證通過")
        return True
        
    except Exception as e:
        print_test_result("完整退款流程", False, str(e))
        logger.error(f"完整退款流程測試失敗: {e}", exc_info=True)
        return False

def test_card_binding_flow(auth_service):
    """
    測試卡片綁定流程
    1. 創建兩個會員 → 2. 創建企業卡 → 3. 設定綁定密碼 → 
    4. 第二個會員綁定 → 5. 驗證共享支付
    """
    print_test_header("卡片綁定流程")
    
    try:
        from config.supabase_client import supabase_client
        
        # 驗證當前角色（應該已經是乾淨的 session）
        current_role = supabase_client.rpc("get_user_role", {})
        print(f"[測試開始] 當前角色: {current_role}")
        
        if current_role != 'super_admin':
            raise Exception(f"角色錯誤: 期望 super_admin，實際 {current_role}")
        
        # 步驟 1: 創建兩個會員
        print_test_step("步驟 1: 創建兩個測試會員")
        member1_id, member1_data = create_test_member(auth_service)
        member2_id, member2_data = create_test_member(auth_service)
        print_test_info("會員1 ID", member1_id)
        print_test_info("會員2 ID", member2_id)
        
        # 步驟 2: 創建企業折扣卡（需要通過 RPC）
        print_test_step("步驟 2: 為會員1創建企業折扣卡")
        
        # 創建企業折扣卡（8折）
        card_result = supabase_client.rpc("create_corporate_card", {
            "p_owner_member_id": member1_id,
            "p_name": "測試企業折扣卡",
            "p_fixed_discount": "0.800"  # 8折
        })
        
        if not card_result:
            raise Exception("創建企業卡失敗")
        
        corporate_card_id = card_result if isinstance(card_result, str) else card_result[0]
        print_test_info("企業卡 ID", corporate_card_id)
        
        # 步驟 3: 設定綁定密碼
        print_test_step("步驟 3: 設定企業卡綁定密碼")
        binding_password = "bind123456"
        supabase_client.rpc("set_card_binding_password", {
            "p_card_id": corporate_card_id,
            "p_password": binding_password
        })
        print_test_info("綁定密碼", "已設定")
        
        # 步驟 4: 第二個會員綁定企業卡
        print_test_step("步驟 4: 會員2綁定企業卡")
        member_service = MemberService()
        member_service.set_auth_service(auth_service)
        
        bind_result = member_service.bind_card(
            card_id=corporate_card_id,
            member_id=member2_id,
            role='member',
            binding_password=binding_password
        )
        print_test_info("綁定結果", "成功" if bind_result else "失敗")
        
        # 步驟 5: 驗證企業折扣已設置
        print_test_step("步驟 5: 驗證企業折扣已設置到會員卡")
        
        # 獲取會員2的 Standard Card
        member2_cards = supabase_client.client.table("member_cards")\
            .select("discount, corporate_discount")\
            .eq("owner_member_id", member2_id)\
            .eq("card_type", "standard")\
            .single()\
            .execute()
        
        corporate_discount = member2_cards.data.get('corporate_discount')
        print_test_info("會員2企業折扣", f"{float(corporate_discount):.3f}" if corporate_discount else "None")
        
        if not corporate_discount or float(corporate_discount) != 0.800:
            raise Exception(f"企業折扣設置失敗：期望 0.800，實際 {corporate_discount}")
        
        # 步驟 6: 為兩個會員的 Standard Card 充值
        print_test_step("步驟 6: 為會員充值 Standard Card")
        merchant_id, merchant_data = create_test_merchant(auth_service)
        
        # 獲取會員1和會員2的 Standard Card
        member1_std_card = supabase_client.client.table("member_cards")\
            .select("id")\
            .eq("owner_member_id", member1_id)\
            .eq("card_type", "standard")\
            .single()\
            .execute()
        
        member2_std_card = supabase_client.client.table("member_cards")\
            .select("id")\
            .eq("owner_member_id", member2_id)\
            .eq("card_type", "standard")\
            .single()\
            .execute()
        
        member1_card_id = member1_std_card.data['id']
        member2_card_id = member2_std_card.data['id']
        
        # 充值
        recharge_card(auth_service, member1_card_id, Decimal("1000.00"))
        recharge_card(auth_service, member2_card_id, Decimal("1000.00"))
        print_test_info("會員1充值", "¥1000.00")
        print_test_info("會員2充值", "¥1000.00")
        
        # 步驟 7: 驗證折扣生效
        print_test_step("步驟 7: 驗證企業折扣在支付時生效")
        
        # 會員1支付（無企業折扣，折扣 1.0）
        qr_result_1 = generate_qr_code(auth_service, member1_card_id)
        payment_result_1 = make_payment(
            auth_service,
            merchant_data['code'],
            qr_result_1['qr_plain'],
            Decimal("100.00")
        )
        print_test_info("會員1支付（無企業折扣）", f"原價¥100, 實付¥{payment_result_1['final_amount']}")
        
        # 會員2支付（有企業折扣 0.8）
        qr_result_2 = generate_qr_code(auth_service, member2_card_id)
        payment_result_2 = make_payment(
            auth_service,
            merchant_data['code'],
            qr_result_2['qr_plain'],
            Decimal("100.00")
        )
        print_test_info("會員2支付（有企業折扣）", f"原價¥100, 實付¥{payment_result_2['final_amount']}")
        
        # 驗證折扣
        if abs(Decimal(str(payment_result_1['final_amount'])) - Decimal("100.00")) > Decimal("0.01"):
            raise Exception(f"會員1折扣錯誤：期望¥100.00，實際¥{payment_result_1['final_amount']}")
        
        if abs(Decimal(str(payment_result_2['final_amount'])) - Decimal("80.00")) > Decimal("0.01"):
            raise Exception(f"會員2折扣錯誤：期望¥80.00（8折），實際¥{payment_result_2['final_amount']}")
        
        print_test_result("卡片綁定流程", True, "所有步驟驗證通過")
        return True
        
    except Exception as e:
        print_test_result("卡片綁定流程", False, str(e))
        logger.error(f"卡片綁定流程測試失敗: {e}", exc_info=True)
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
    print("完整業務流程測試")
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
        
        results["完整支付流程"] = run_test_with_clean_session(
            "完整支付流程", 
            test_complete_payment_flow, 
            admin_email, 
            admin_password
        )
        
        results["完整退款流程"] = run_test_with_clean_session(
            "完整退款流程", 
            test_complete_refund_flow, 
            admin_email, 
            admin_password
        )
        
        results["卡片綁定流程"] = run_test_with_clean_session(
            "卡片綁定流程", 
            test_card_binding_flow, 
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