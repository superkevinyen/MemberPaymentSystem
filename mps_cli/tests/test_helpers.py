#!/usr/bin/env python3
"""
測試輔助函數
提供所有測試共用的工具函數
"""

import sys
from pathlib import Path
import getpass
import random
import time
from typing import Dict, Any, List, Optional
from decimal import Decimal

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.auth_service import AuthService
from services.member_service import MemberService
from services.admin_service import AdminService
from services.merchant_service import MerchantService
from services.payment_service import PaymentService
from services.qr_service import QRService
from utils.logger import get_logger

logger = get_logger(__name__)

# 全局測試數據追蹤
test_data_tracker = {
    "members": [],
    "merchants": [],
    "cards": [],
    "transactions": []
}

def setup_admin_auth(email: str = None, password: str = None) -> AuthService:
    """設定管理員認證（統一入口）"""
    # 如果沒有提供憑證，則詢問用戶
    if not email or not password:
        print("\n🔐 需要管理員權限來執行測試")
        print("請輸入管理員登入資訊：")
        
        email = input("Admin Email: ").strip()
        password = getpass.getpass("Admin Password: ")
    
    if not email or not password:
        raise Exception("請輸入完整的管理員登入資訊")
    
    auth_service = AuthService()
    
    try:
        result = auth_service.login_with_email(email, password)
        if result and result.get('success'):
            role = result.get('role')
            print(f"✅ 管理員登入成功：{role}")
            
            if role not in ['admin', 'super_admin']:
                raise Exception("需要 admin 或 super_admin 權限")
            
            # 保存憑證到 auth_service 以便後續重新登入
            auth_service._admin_email = email
            auth_service._admin_password = password
            
            return auth_service
        else:
            raise Exception("管理員登入失敗")
    except Exception as e:
        raise Exception(f"管理員認證失敗: {e}")

def generate_test_member_data() -> Dict[str, str]:
    """生成測試會員數據（使用固定密碼）"""
    # 使用更高精度的時間戳和隨機數確保唯一性
    timestamp = str(int(time.time() * 1000))[-8:]  # 毫秒級時間戳
    random_num = str(random.randint(100, 999))
    
    return {
        "name": f"測試會員_{timestamp}",
        "phone": f"138{timestamp[:8]}"[:11],  # 確保手機號唯一
        "email": f"test_{timestamp}_{random_num}@example.com",
        "password": "test123456"  # 固定密碼，方便後續角色測試
    }

def generate_test_merchant_data() -> Dict[str, str]:
    """生成測試商戶數據（使用固定密碼）"""
    timestamp = str(int(time.time()))[-6:]
    random_num = str(random.randint(100, 999))
    
    return {
        "code": f"M{timestamp}{random_num}"[:10],
        "name": f"測試商戶_{timestamp}",
        "contact": f"138{timestamp}{random_num}"[:11],
        "password": "merchant123456"  # 固定密碼，方便後續角色測試
    }

def track_test_member(member_id: str, data: Dict[str, Any]):
    """追蹤測試會員"""
    test_data_tracker["members"].append({
        "id": member_id,
        "data": data
    })
    logger.debug(f"追蹤測試會員: {member_id}")

def track_test_merchant(merchant_id: str, data: Dict[str, Any]):
    """追蹤測試商戶"""
    test_data_tracker["merchants"].append({
        "id": merchant_id,
        "data": data
    })
    logger.debug(f"追蹤測試商戶: {merchant_id}")

def track_test_card(card_id: str, data: Dict[str, Any]):
    """追蹤測試卡片"""
    test_data_tracker["cards"].append({
        "id": card_id,
        "data": data
    })
    logger.debug(f"追蹤測試卡片: {card_id}")

def track_test_transaction(tx_id: str, data: Dict[str, Any]):
    """追蹤測試交易"""
    test_data_tracker["transactions"].append({
        "id": tx_id,
        "data": data
    })
    logger.debug(f"追蹤測試交易: {tx_id}")

def cleanup_all_test_data(auth_service: AuthService, hard_delete: bool = True):
    """
    清理所有測試數據
    
    Args:
        auth_service: 認證服務
        hard_delete: True=硬刪除（使用 delete_test_* RPC），False=軟刪除（暫停）
    """
    if not any(test_data_tracker.values()):
        return
        
    print("\n" + "="*60)
    print("清理測試數據")
    print("="*60)
    
    admin_service = AdminService()
    admin_service.set_auth_service(auth_service)
    
    # 清理會員
    for member in test_data_tracker["members"]:
        try:
            if hard_delete:
                # 使用測試專用的硬刪除 RPC
                admin_service.rpc_call("delete_test_member", {"p_member_id": member["id"]})
                print(f"✅ 已刪除測試會員: {member['data'].get('name', 'Unknown')}")
            else:
                # 使用商業 RPC 暫停
                admin_service.rpc_call("admin_suspend_member", {"p_member_id": member["id"]})
                print(f"✅ 已暫停測試會員: {member['data'].get('name', 'Unknown')}")
        except Exception as e:
            print(f"⚠️  清理會員失敗: {e}")
    
    # 清理商戶
    for merchant in test_data_tracker["merchants"]:
        try:
            if hard_delete:
                # 使用測試專用的硬刪除 RPC
                admin_service.rpc_call("delete_test_merchant", {"p_merchant_id": merchant["id"]})
                print(f"✅ 已刪除測試商戶: {merchant['data'].get('name', 'Unknown')}")
            else:
                # 使用商業 RPC 暫停
                admin_service.rpc_call("admin_suspend_merchant", {"p_merchant_id": merchant["id"]})
                print(f"✅ 已暫停測試商戶: {merchant['data'].get('name', 'Unknown')}")
        except Exception as e:
            print(f"⚠️  清理商戶失敗: {e}")
    
    # 清空追蹤器
    test_data_tracker["members"].clear()
    test_data_tracker["merchants"].clear()
    test_data_tracker["cards"].clear()
    test_data_tracker["transactions"].clear()
    
    delete_type = "硬刪除" if hard_delete else "軟刪除（暫停）"
    print(f"✅ 測試數據清理完成（{delete_type}）")

def print_test_header(test_name: str):
    """打印測試標題"""
    print("\n" + "="*60)
    print(f"測試：{test_name}")
    print("="*60)

def print_test_step(step: str):
    """打印測試步驟"""
    print(f"\n📝 {step}")

def print_test_info(label: str, value: Any):
    """打印測試信息"""
    print(f"   {label}: {value}")

def print_test_result(test_name: str, passed: bool, details: str = ""):
    """打印測試結果"""
    status = "✅ 通過" if passed else "❌ 失敗"
    print(f"\n{test_name}: {status}")
    if details:
        print(f"   {details}")

def print_test_summary(results: Dict[str, bool]) -> bool:
    """打印測試總結"""
    print("\n" + "="*60)
    print("測試總結")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
    
    print(f"\n總計: {passed}/{total} 通過")
    
    if passed == total:
        print("\n🎉 所有測試通過！")
        return True
    else:
        print("\n⚠️  部分測試失敗，請檢查錯誤訊息")
        return False

def create_test_member(auth_service: AuthService, with_password: bool = True, 
                      name: str = None, phone: str = None, email: str = None) -> tuple:
    """創建測試會員並返回 (member_id, member_data)
    
    Args:
        auth_service: 認證服務
        with_password: 是否設置密碼
        name: 自定義會員名稱（可選）
        phone: 自定義手機號碼（可選）
        email: 自定義郵箱（可選）
    """
    member_service = MemberService()
    member_service.set_auth_service(auth_service)
    
    member_data = generate_test_member_data()
    
    # 使用自定義參數覆蓋生成的數據
    if name:
        member_data['name'] = name
    if phone:
        member_data['phone'] = phone
    if email:
        member_data['email'] = email
    
    try:
        member_id = member_service.create_member(
            name=member_data['name'],
            phone=member_data['phone'],
            email=member_data['email'],
            password=member_data['password'] if with_password else None
        )
        
        track_test_member(member_id, member_data)
        return member_id, member_data
        
    except Exception as e:
        logger.error(f"創建測試會員失敗: {e}")
        raise

def create_test_merchant(auth_service: AuthService) -> tuple:
    """創建測試商戶並返回 (merchant_id, merchant_data)"""
    admin_service = AdminService()
    admin_service.set_auth_service(auth_service)
    
    merchant_data = generate_test_merchant_data()
    
    try:
        # 使用 RPC 創建商戶（帶密碼）
        merchant_id = admin_service.rpc_call("create_merchant", {
            "p_code": merchant_data['code'],
            "p_name": merchant_data['name'],
            "p_contact": merchant_data['contact'],
            "p_password": merchant_data['password']
        })
        
        if merchant_id:
            track_test_merchant(merchant_id, merchant_data)
            return merchant_id, merchant_data
        else:
            raise Exception("創建商戶失敗：無返回數據")
            
    except Exception as e:
        logger.error(f"創建測試商戶失敗: {e}")
        raise

def get_member_default_card(auth_service: AuthService, member_id: str) -> Optional[str]:
    """獲取會員的默認卡片 ID"""
    admin_service = AdminService()
    admin_service.set_auth_service(auth_service)
    
    try:
        # 使用 RPC 獲取會員卡片
        result = admin_service.rpc_call("get_member_cards", {"p_member_id": member_id})
        if result and len(result) > 0:
            # 返回第一張卡片（通常是標準卡）
            return result[0]['id']
        return None
    except Exception as e:
        logger.error(f"獲取會員默認卡片失敗: {e}")
        return None

def recharge_card(auth_service: AuthService, card_id: str, amount: Decimal) -> Dict:
    """充值卡片"""
    payment_service = PaymentService()
    payment_service.set_auth_service(auth_service)
    
    try:
        result = payment_service.recharge_card(
            card_id=card_id,
            amount=amount,
            payment_method="wechat"
        )
        
        if result:
            track_test_transaction(result['tx_id'], result)
        
        return result
    except Exception as e:
        logger.error(f"充值卡片失敗: {e}")
        raise

def generate_qr_code(auth_service: AuthService, card_id: str) -> Dict:
    """生成 QR 碼"""
    qr_service = QRService()
    qr_service.set_auth_service(auth_service)
    
    try:
        result = qr_service.rotate_qr(card_id, ttl_seconds=900)
        return result
    except Exception as e:
        logger.error(f"生成 QR 碼失敗: {e}")
        raise

def make_payment(auth_service: AuthService, merchant_code: str, qr_plain: str, amount: Decimal) -> Dict:
    """執行支付"""
    payment_service = PaymentService()
    payment_service.set_auth_service(auth_service)
    
    try:
        result = payment_service.charge_by_qr(
            merchant_code=merchant_code,
            qr_plain=qr_plain,
            amount=amount
        )
        
        if result:
            track_test_transaction(result['tx_id'], result)
        
        return result
    except Exception as e:
        logger.error(f"支付失敗: {e}")
        raise

def make_refund(auth_service: AuthService, merchant_code: str, tx_no: str, amount: Decimal,
                merchant_password: str = None) -> Dict:
    """
    執行退款
    
    Args:
        auth_service: 認證服務（可以是管理員或商戶）
        merchant_code: 商戶代碼
        tx_no: 原交易號
        amount: 退款金額
        merchant_password: 商戶密碼（如果需要切換到商戶身份）
    """
    # 如果提供了商戶密碼，則使用商戶身份登入
    if merchant_password:
        merchant_auth = AuthService()
        try:
            logger.debug(f"[DEBUG] 使用商戶身份登入: {merchant_code}")
            result = merchant_auth.login_merchant_with_code(merchant_code, merchant_password)
            if not result or not result.get('success'):
                raise Exception(f"商戶登入失敗: {merchant_code}")
            
            payment_service = PaymentService()
            payment_service.set_auth_service(merchant_auth)
        except Exception as e:
            logger.error(f"商戶登入失敗: {e}")
            raise
    else:
        payment_service = PaymentService()
        payment_service.set_auth_service(auth_service)
    
    try:
        # 添加調試日誌
        logger.debug(f"[DEBUG] make_refund - merchant_code: {merchant_code}, tx_no: {tx_no}, amount: {amount}")
        logger.debug(f"[DEBUG] make_refund - auth_service user: {payment_service.auth_service.current_user}")
        logger.debug(f"[DEBUG] make_refund - auth_service role: {payment_service.auth_service.current_role}")
        
        result = payment_service.refund_transaction(
            merchant_code=merchant_code,
            original_tx_no=tx_no,
            refund_amount=amount
        )
        
        if result:
            track_test_transaction(result['refund_tx_id'], result)
        
        return result
    except Exception as e:
        logger.error(f"退款失敗: {e}")
        logger.error(f"[DEBUG] 退款失敗時的上下文 - merchant_code: {merchant_code}, tx_no: {tx_no}")
        raise

def get_card_balance(auth_service: AuthService, card_id: str) -> Optional[Decimal]:
    """獲取卡片餘額"""
    admin_service = AdminService()
    admin_service.set_auth_service(auth_service)
    
    try:
        card_data = admin_service.get_single_record("member_cards", {"id": card_id})
        logger.debug(f"[DEBUG] get_card_balance - card_id: {card_id}, card_data: {card_data}")
        if card_data:
            balance_value = card_data.get('balance', 0)
            logger.debug(f"[DEBUG] get_card_balance - balance_value: {balance_value}, type: {type(balance_value)}")
            # 處理 None 值
            if balance_value is None:
                logger.warning(f"卡片餘額為 None，返回 0: {card_id}")
                return Decimal('0')
            return Decimal(str(balance_value))
        logger.warning(f"卡片不存在: {card_id}")
        return None
    except Exception as e:
        logger.error(f"獲取卡片餘額失敗: {e}")
        return None

def get_card_points(auth_service: AuthService, card_id: str) -> Optional[int]:
    """獲取卡片積分"""
    admin_service = AdminService()
    admin_service.set_auth_service(auth_service)
    
    try:
        card_data = admin_service.get_single_record("member_cards", {"id": card_id})
        logger.debug(f"[DEBUG] get_card_points - card_id: {card_id}, card_data: {card_data}")
        if card_data:
            points_value = card_data.get('points', 0)
            logger.debug(f"[DEBUG] get_card_points - points_value: {points_value}, type: {type(points_value)}")
            # 處理 None 值
            if points_value is None:
                logger.warning(f"卡片積分為 None，返回 0: {card_id}")
                return 0
            return int(points_value)
        logger.warning(f"卡片不存在: {card_id}")
        return None
    except Exception as e:
        logger.error(f"獲取卡片積分失敗: {e}")
        return None

def wait_for_user_confirmation(message: str = "按 Enter 繼續..."):
    """等待用戶確認"""
    input(f"\n{message}")