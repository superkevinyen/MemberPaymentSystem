#!/usr/bin/env python3
"""
進階業務流程測試 (Level 1)
基於四種卡片類型的完整測試

卡片類型：
1. Standard (STD) - 標準卡：可充值、有積分、有折扣（可繼承企業折扣）
2. Voucher (VCH) - 代金券：一次性、無積分、無折扣
3. Corporate (COR) - 企業折扣卡：不可充值、不可消費、只提供折扣

測試場景：
1. 卡片類型功能測試 - 驗證每種卡片的特性
2. QR 碼權限測試 - Member/Admin 可生成，Merchant 不可
3. 企業卡綁定測試 - 多人綁定、共享支付
4. 邊界值測試 - 最小/最大金額、餘額不足
5. 異常處理測試 - 無效參數、權限錯誤
"""

import sys
import getpass
from pathlib import Path
from decimal import Decimal

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.supabase_client import supabase_client
from services.auth_service import AuthService
from services.admin_service import AdminService
from services.member_service import MemberService
from test_helpers import (
    setup_admin_auth,
    print_test_header,
    print_test_step,
    print_test_info,
    print_test_result,
    print_test_summary,
    create_test_member,
    create_test_merchant,
    cleanup_all_test_data
)

def test_card_type_features(auth_service):
    """
    測試 1: 卡片類型功能測試
    驗證四種卡片的特性是否正確
    """
    print_test_header("卡片類型功能測試")
    
    try:
        # 創建測試環境
        print_test_step("準備測試環境")
        member_id, member_data = create_test_member(auth_service)
        merchant_id, merchant_data = create_test_merchant(auth_service)
        
        admin_service = AdminService()
        admin_service.set_auth_service(auth_service)
        
        # 測試 1.1: Voucher Card - 驗證不可充值
        print_test_step("測試 1.1: Voucher Card - 驗證不可充值")
        
        # 創建代金券卡（測試用）
        voucher_card_id = supabase_client.rpc("create_voucher_card", {
            "p_owner_member_id": member_id,
            "p_name": "測試代金券",
            "p_initial_balance": "100.00"
        })
        print_test_info("代金券 ID", voucher_card_id)
        
        # 嘗試充值（應該失敗）
        try:
            result = admin_service.rpc_call("user_recharge_card", {
                "p_card_id": voucher_card_id,
                "p_amount": "100.00"
            })
            print_test_info("代金券充值", "❌ 應該失敗但卻成功了")
            raise Exception("代金券不應該允許充值")
        except Exception as e:
            if "UNSUPPORTED_CARD_TYPE" in str(e) or "不支持" in str(e):
                print_test_info("代金券充值", "✅ 正確拒絕（代金券不可充值）")
            else:
                print_test_info("代金券充值", f"❌ 錯誤訊息不正確: {e}")
                raise
        
        # 測試 1.2: Standard Card - 可充值
        print_test_step("測試 1.2: Standard Card - 驗證可充值")
        
        # 獲取會員的 Standard Card
        std_cards = supabase_client.client.table("member_cards")\
            .select("id")\
            .eq("owner_member_id", member_id)\
            .eq("card_type", "standard")\
            .execute()
        
        if std_cards.data:
            std_card_id = std_cards.data[0]['id']
            
            # 充值
            recharge_result = admin_service.rpc_call("user_recharge_card", {
                "p_card_id": std_card_id,
                "p_amount": "500.00"
            })
            # user_recharge_card 返回 TABLE，取第一行
            if isinstance(recharge_result, list) and len(recharge_result) > 0:
                recharge_result = recharge_result[0]
            print_test_info("標準卡充值", f"✅ 成功 - {recharge_result['tx_no']}")
            
            # 驗證餘額
            card_info = supabase_client.client.table("member_cards")\
                .select("balance")\
                .eq("id", std_card_id)\
                .single()\
                .execute()
            print_test_info("充值後餘額", f"¥{card_info.data['balance']}")
        
        # 測試 1.3: Corporate Card - 驗證折扣繼承
        print_test_step("測試 1.3: Corporate Card - 驗證折扣繼承")
        
        # 創建企業折扣卡（8折）
        cor_card_id = supabase_client.rpc("create_corporate_card", {
            "p_owner_member_id": member_id,
            "p_name": "測試企業折扣卡",
            "p_fixed_discount": "0.800"  # 8折
        })
        print_test_info("企業折扣卡 ID", cor_card_id)
        print_test_info("企業折扣", "8折 (0.800)")
        
        # 設置綁定密碼
        supabase_client.rpc("set_card_binding_password", {
            "p_card_id": cor_card_id,
            "p_password": "bind123"
        })
        
        # 創建第二個會員
        member2_id, member2_data = create_test_member(auth_service)
        
        # 獲取 Member2 的標準卡折扣
        member2_cards = supabase_client.client.table("member_cards")\
            .select("id, discount, corporate_discount")\
            .eq("owner_member_id", member2_id)\
            .eq("card_type", "standard")\
            .single()\
            .execute()
        
        original_discount = member2_cards.data['discount']
        print_test_info("Member2 積分折扣", f"{float(original_discount):.3f}")
        
        # 綁定企業折扣卡
        member_service = MemberService()
        member_service.set_auth_service(auth_service)
        
        bind_result = member_service.bind_card(
            card_id=cor_card_id,
            member_id=member2_id,
            role='member',
            binding_password='bind123'
        )
        print_test_info("企業卡綁定", "✅ 成功" if bind_result else "❌ 失敗")
        
        # 驗證企業折扣已設置
        member2_cards_after = supabase_client.client.table("member_cards")\
            .select("discount, corporate_discount")\
            .eq("owner_member_id", member2_id)\
            .eq("card_type", "standard")\
            .single()\
            .execute()
        
        member_discount = float(member2_cards_after.data['discount'])
        corporate_discount = member2_cards_after.data['corporate_discount']
        
        print_test_info("積分折扣", f"{member_discount:.3f}")
        print_test_info("企業折扣", f"{float(corporate_discount):.3f}" if corporate_discount else "None")
        
        if corporate_discount and float(corporate_discount) == 0.800:
            print_test_info("折扣繼承", "✅ 正確（已設置企業折扣）")
        else:
            raise Exception(f"折扣繼承失敗：期望企業折扣 0.800，實際 {corporate_discount}")
        
        print_test_result("卡片類型功能測試", True, "所有卡片類型功能驗證通過")
        return True
        
    except Exception as e:
        print_test_result("卡片類型功能測試", False, str(e))
        import traceback
        traceback.print_exc()
        return False

def test_qr_code_permissions(auth_service):
    """
    測試 2: QR 碼權限測試
    驗證不同角色的 QR 碼生成權限
    """
    print_test_header("QR 碼權限測試")
    
    try:
        # 創建測試環境
        print_test_step("準備測試環境")
        member_id, member_data = create_test_member(auth_service)
        merchant_id, merchant_data = create_test_merchant(auth_service)
        
        # 獲取會員的卡片
        cards = supabase_client.client.table("member_cards")\
            .select("id")\
            .eq("owner_member_id", member_id)\
            .limit(1)\
            .execute()
        
        if not cards.data:
            raise Exception("找不到會員卡片")
        
        card_id = cards.data[0]['id']
        
        # 測試 2.1: Super Admin 可以生成 QR
        print_test_step("測試 2.1: Super Admin 生成 QR（應該成功）")
        try:
            qr_result = supabase_client.rpc("rotate_card_qr", {
                "p_card_id": card_id,
                "p_ttl_seconds": 900
            })
            print_test_info("Admin 生成 QR", f"✅ 成功 - 長度 {len(qr_result[0]['qr_plain'])}")
        except Exception as e:
            print_test_info("Admin 生成 QR", f"❌ 失敗: {e}")
            raise
        
        # 測試 2.2: Member 可以為自己的卡片生成 QR
        print_test_step("測試 2.2: Member 為自己的卡片生成 QR（應該成功）")
        
        # Member 登入
        member_auth = AuthService()
        member_auth.login_with_identifier(member_data['phone'], member_data['password'])
        
        try:
            member_service = MemberService()
            member_service.set_auth_service(member_auth)
            
            qr_result = member_service.rpc_call("rotate_card_qr", {
                "p_card_id": card_id,
                "p_ttl_seconds": 900
            })
            print_test_info("Member 生成 QR", f"✅ 成功 - 長度 {len(qr_result[0]['qr_plain'])}")
        except Exception as e:
            print_test_info("Member 生成 QR", f"❌ 失敗: {e}")
            raise
        finally:
            member_auth.logout()
        
        # 測試 2.3: Merchant 不能生成 QR
        print_test_step("測試 2.3: Merchant 嘗試生成 QR（應該失敗）")
        
        # Merchant 登入
        merchant_auth = AuthService()
        merchant_auth.login_merchant_with_code(merchant_data['code'], merchant_data['password'])
        
        try:
            merchant_service = AdminService()
            merchant_service.set_auth_service(merchant_auth)
            
            qr_result = merchant_service.rpc_call("rotate_card_qr", {
                "p_card_id": card_id,
                "p_ttl_seconds": 900
            })
            print_test_info("Merchant 生成 QR", "❌ 應該失敗但卻成功了")
            merchant_auth.logout()
            raise Exception("Merchant 不應該能生成 QR 碼")
        except Exception as e:
            error_msg = str(e)
            if "PERMISSION_DENIED" in error_msg or "商戶不能" in error_msg or "權限" in error_msg:
                print_test_info("Merchant 生成 QR", "✅ 正確拒絕")
            else:
                print_test_info("Merchant 生成 QR", f"❌ 應該失敗但卻成功了")
                raise
        finally:
            try:
                merchant_auth.logout()
            except:
                pass
        
        # 測試 2.4: Member 不能為別人的卡片生成 QR
        print_test_step("測試 2.4: Member 為別人的卡片生成 QR（應該失敗）")
        
        # 創建另一個會員
        member2_id, member2_data = create_test_member(auth_service)
        
        # 獲取第二個會員的卡片
        cards2 = supabase_client.client.table("member_cards")\
            .select("id")\
            .eq("owner_member_id", member2_id)\
            .limit(1)\
            .execute()
        
        card2_id = cards2.data[0]['id']
        
        # Member1 登入並嘗試為 Member2 的卡片生成 QR
        member_auth = AuthService()
        member_auth.login_with_identifier(member_data['phone'], member_data['password'])
        
        try:
            member_service = MemberService()
            member_service.set_auth_service(member_auth)
            
            qr_result = member_service.rpc_call("rotate_card_qr", {
                "p_card_id": card2_id,
                "p_ttl_seconds": 900
            })
            print_test_info("跨會員生成 QR", "❌ 應該失敗但卻成功了")
            member_auth.logout()
            raise Exception("Member 不應該能為別人的卡片生成 QR")
        except Exception as e:
            error_msg = str(e)
            if "PERMISSION_DENIED" in error_msg or "沒有權限" in error_msg or "權限" in error_msg:
                print_test_info("跨會員生成 QR", "✅ 正確拒絕")
            else:
                print_test_info("跨會員生成 QR", f"❌ 應該失敗但卻成功了")
                raise
        finally:
            try:
                member_auth.logout()
            except:
                pass
        
        print_test_result("QR 碼權限測試", True, "所有權限驗證通過")
        return True
        
    except Exception as e:
        print_test_result("QR 碼權限測試", False, str(e))
        import traceback
        traceback.print_exc()
        return False

def test_corporate_card_binding(auth_service):
    """
    測試 3: 企業折扣卡綁定測試
    驗證企業折扣卡的綁定、解綁、折扣繼承功能
    """
    print_test_header("企業折扣卡綁定測試")
    
    try:
        # 創建測試環境
        print_test_step("準備測試環境")
        member1_id, member1_data = create_test_member(auth_service)
        member2_id, member2_data = create_test_member(auth_service)
        member3_id, member3_data = create_test_member(auth_service)
        merchant_id, merchant_data = create_test_merchant(auth_service)
        
        admin_service = AdminService()
        admin_service.set_auth_service(auth_service)
        
        # 創建企業折扣卡（7.5折）
        print_test_step("創建企業折扣卡並設置綁定密碼")
        cor_card_id = supabase_client.rpc("create_corporate_card", {
            "p_owner_member_id": member1_id,
            "p_name": "測試企業折扣卡",
            "p_fixed_discount": "0.750"  # 7.5折
        })
        print_test_info("企業折扣卡 ID", cor_card_id)
        print_test_info("企業折扣", "7.5折 (0.750)")
        
        # 設置綁定密碼
        supabase_client.rpc("set_card_binding_password", {
            "p_card_id": cor_card_id,
            "p_password": "corp123"
        })
        
        # 為三個會員的 Standard Card 充值（用於後續消費測試）
        for i, member_id in enumerate([member1_id, member2_id, member3_id], 1):
            # 獲取 Standard Card
            std_cards = supabase_client.client.table("member_cards")\
                .select("id")\
                .eq("owner_member_id", member_id)\
                .eq("card_type", "standard")\
                .single()\
                .execute()
            
            std_card_id = std_cards.data['id']
            
            # 充值
            admin_service.rpc_call("user_recharge_card", {
                "p_card_id": std_card_id,
                "p_amount": "1000.00"
            })
            print_test_info(f"Member{i} 標準卡充值", "¥1000.00")
        
        # 測試 3.1: 多人綁定
        print_test_step("測試 3.1: Member2 和 Member3 綁定企業卡")
        
        member_service = MemberService()
        member_service.set_auth_service(auth_service)
        
        # Member2 綁定
        bind_result2 = member_service.bind_card(
            card_id=cor_card_id,
            member_id=member2_id,
            role='member',
            binding_password='corp123'
        )
        print_test_info("Member2 綁定", "✅ 成功" if bind_result2 else "❌ 失敗")
        
        # Member3 綁定
        bind_result3 = member_service.bind_card(
            card_id=cor_card_id,
            member_id=member3_id,
            role='member',
            binding_password='corp123'
        )
        print_test_info("Member3 綁定", "✅ 成功" if bind_result3 else "❌ 失敗")
        
        # 測試 3.2: 驗證折扣已應用到會員卡
        print_test_step("測試 3.2: 驗證折扣已應用到綁定會員的卡片")
        
        for i, member_id in enumerate([member2_id, member3_id], 2):
            # 獲取會員的 Standard Card 折扣
            std_cards = supabase_client.client.table("member_cards")\
                .select("discount, corporate_discount")\
                .eq("owner_member_id", member_id)\
                .eq("card_type", "standard")\
                .single()\
                .execute()
            
            member_discount = float(std_cards.data['discount'])
            corporate_discount = std_cards.data['corporate_discount']
            
            print_test_info(f"Member{i} 積分折扣", f"{member_discount:.3f}")
            print_test_info(f"Member{i} 企業折扣", f"{float(corporate_discount):.3f}" if corporate_discount else "None")
            
            if corporate_discount and float(corporate_discount) == 0.750:
                print_test_info(f"Member{i} 折扣繼承", "✅ 正確")
            else:
                raise Exception(f"Member{i} 折扣繼承失敗")
        
        # 測試 3.3: 使用 Standard Card 消費，驗證折扣生效
        print_test_step("測試 3.3: 三個會員使用 Standard Card 消費，驗證折扣")
        
        payments = [Decimal("100.00"), Decimal("200.00"), Decimal("150.00")]
        
        for i, (member_id, member_data_item, amount) in enumerate(zip(
            [member1_id, member2_id, member3_id],
            [member1_data, member2_data, member3_data],
            payments
        ), 1):
            # 獲取會員的 Standard Card
            std_cards = supabase_client.client.table("member_cards")\
                .select("id, discount, corporate_discount")\
                .eq("owner_member_id", member_id)\
                .eq("card_type", "standard")\
                .single()\
                .execute()
            
            std_card_id = std_cards.data['id']
            member_discount = float(std_cards.data['discount'])
            corporate_discount = std_cards.data['corporate_discount']
            # 實際使用的折扣是兩者中的最優值
            discount = min(member_discount, float(corporate_discount) if corporate_discount else 1.0)
            
            # 生成 QR
            qr_result = supabase_client.rpc("rotate_card_qr", {
                "p_card_id": std_card_id,
                "p_ttl_seconds": 900
            })
            
            # 支付
            payment_result = admin_service.rpc_call("merchant_charge_by_qr", {
                "p_merchant_code": merchant_data['code'],
                "p_qr_plain": qr_result[0]['qr_plain'],
                "p_raw_amount": str(amount)
            })
            if isinstance(payment_result, list) and len(payment_result) > 0:
                payment_result = payment_result[0]
            
            final_amount = Decimal(str(payment_result['final_amount']))
            expected_amount = amount * Decimal(str(discount))
            
            print_test_info(f"Member{i} 消費", f"原價¥{amount}, 折扣{discount:.3f}, 實付¥{final_amount}")
            
            if abs(final_amount - expected_amount) < Decimal("0.01"):
                print_test_info(f"Member{i} 折扣計算", "✅ 正確")
            else:
                raise Exception(f"Member{i} 折扣計算錯誤：期望¥{expected_amount}，實際¥{final_amount}")
        
        # 測試 3.4: 解綁企業折扣卡，驗證折扣恢復
        print_test_step("測試 3.4: Member2 解綁企業折扣卡，驗證折扣恢復")
        
        # 解綁 Member2
        unbind_result = member_service.unbind_card(
            card_id=cor_card_id,
            member_id=member2_id
        )
        print_test_info("Member2 解綁", "✅ 成功" if unbind_result else "❌ 失敗")
        
        # 驗證 Member2 的企業折扣已清除
        std_cards_after_unbind = supabase_client.client.table("member_cards")\
            .select("discount, corporate_discount")\
            .eq("owner_member_id", member2_id)\
            .eq("card_type", "standard")\
            .single()\
            .execute()
        
        member_discount = float(std_cards_after_unbind.data['discount'])
        corporate_discount = std_cards_after_unbind.data['corporate_discount']
        
        print_test_info("Member2 積分折扣", f"{member_discount:.3f}")
        print_test_info("Member2 企業折扣", f"{float(corporate_discount):.3f}" if corporate_discount else "已清除")
        
        if corporate_discount is None:
            print_test_info("企業折扣清除", "✅ 正確")
        else:
            raise Exception(f"企業折扣清除失敗：應為 None，實際 {corporate_discount}")
        
        # 測試 3.5: 驗證解綁後消費使用原始折扣
        print_test_step("測試 3.5: Member2 解綁後消費，驗證使用原始折扣")
        
        # 獲取 Member2 的 Standard Card
        std_cards = supabase_client.client.table("member_cards")\
            .select("id, discount, corporate_discount")\
            .eq("owner_member_id", member2_id)\
            .eq("card_type", "standard")\
            .single()\
            .execute()
        
        std_card_id = std_cards.data['id']
        member_discount = float(std_cards.data['discount'])
        corporate_discount = std_cards.data['corporate_discount']
        current_discount = min(member_discount, float(corporate_discount) if corporate_discount else 1.0)
        
        # 生成 QR 並消費
        qr_result = supabase_client.rpc("rotate_card_qr", {
            "p_card_id": std_card_id,
            "p_ttl_seconds": 900
        })
        
        test_amount = Decimal("100.00")
        payment_result = admin_service.rpc_call("merchant_charge_by_qr", {
            "p_merchant_code": merchant_data['code'],
            "p_qr_plain": qr_result[0]['qr_plain'],
            "p_raw_amount": str(test_amount)
        })
        if isinstance(payment_result, list) and len(payment_result) > 0:
            payment_result = payment_result[0]
        
        final_amount = Decimal(str(payment_result['final_amount']))
        expected_amount = test_amount * Decimal(str(current_discount))
        
        print_test_info("解綁後消費", f"原價¥{test_amount}, 折扣{current_discount:.3f}, 實付¥{final_amount}")
        
        if abs(final_amount - expected_amount) < Decimal("0.01"):
            print_test_info("解綁後折扣計算", "✅ 正確（使用原始折扣 1.000）")
        else:
            raise Exception(f"解綁後折扣計算錯誤：期望¥{expected_amount}，實際¥{final_amount}")
        
        # 測試 3.6: 驗證 Member3 仍然享有企業折扣
        print_test_step("測試 3.6: 驗證 Member3 仍然享有企業折扣")
        
        std_cards_m3 = supabase_client.client.table("member_cards")\
            .select("id, corporate_discount")\
            .eq("owner_member_id", member3_id)\
            .eq("card_type", "standard")\
            .single()\
            .execute()
        
        m3_corporate_discount = std_cards_m3.data['corporate_discount']
        print_test_info("Member3 企業折扣", f"{float(m3_corporate_discount):.3f}" if m3_corporate_discount else "None")
        
        if m3_corporate_discount and float(m3_corporate_discount) == 0.750:
            print_test_info("Member3 折扣", "✅ 正確（仍享有企業折扣）")
        else:
            raise Exception(f"Member3 企業折扣錯誤：期望 0.750，實際 {m3_corporate_discount}")
        
        print_test_result("企業折扣卡綁定測試", True, "所有企業折扣卡功能驗證通過")
        return True
        
    except Exception as e:
        print_test_result("企業卡綁定進階測試", False, str(e))
        import traceback
        traceback.print_exc()
        return False

def run_test_with_clean_session(test_name, test_func, admin_email, admin_password):
    """使用乾淨的 session 運行單個測試"""
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

def main():
    """主測試函數"""
    print("\n" + "="*60)
    print("進階業務流程測試 (Level 1)")
    print("="*60)
    
    # 獲取管理員憑證
    print("\n🔐 需要管理員權限來執行測試")
    print("請輸入管理員登入資訊（將用於所有測試）：")
    
    admin_email = input("Admin Email: ").strip()
    admin_password = getpass.getpass("Admin Password: ")
    
    if not admin_email or not admin_password:
        print("❌ 請輸入完整的管理員登入資訊")
        return False
    
    results = {}
    
    try:
        # 運行所有測試
        print("\n🚀 開始運行進階測試...")
        
        results["卡片類型功能測試"] = run_test_with_clean_session(
            "卡片類型功能測試", 
            test_card_type_features, 
            admin_email, 
            admin_password
        )
        
        results["QR 碼權限測試"] = run_test_with_clean_session(
            "QR 碼權限測試", 
            test_qr_code_permissions, 
            admin_email, 
            admin_password
        )
        
        results["企業卡綁定進階測試"] = run_test_with_clean_session(
            "企業卡綁定進階測試", 
            test_corporate_card_binding, 
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
            auth_service = setup_admin_auth(admin_email, admin_password)
            cleanup_all_test_data(auth_service, hard_delete=True)
            auth_service.logout()
        except Exception as e:
            print(f"⚠️  最終清理失敗: {e}")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
