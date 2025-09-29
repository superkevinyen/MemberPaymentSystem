#!/usr/bin/env python3
"""
MPS CLI 基本功能測試腳本
用於驗證各個模組是否能正常導入和基本功能
"""

import os
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """測試模組導入"""
    print("🔍 測試模組導入...")
    
    try:
        # 測試配置模組
        from config.settings import settings
        from config.constants import CARD_TYPES, ERROR_MESSAGES
        from config.supabase_client import SupabaseClient
        print("✅ 配置模組導入成功")
        
        # 測試工具模組
        from utils.validators import Validator
        from utils.formatters import Formatter
        from utils.error_handler import ErrorHandler
        from utils.logger import setup_logging
        print("✅ 工具模組導入成功")
        
        # 測試數據模型
        from models.base import BaseModel
        from models.member import Member
        from models.card import Card
        from models.transaction import Transaction
        print("✅ 數據模型導入成功")
        
        # 測試服務層
        from services.base_service import BaseService
        from services.member_service import MemberService
        from services.payment_service import PaymentService
        from services.qr_service import QRService
        from services.admin_service import AdminService
        from services.merchant_service import MerchantService
        print("✅ 服務層導入成功")
        
        # 測試 UI 組件
        from ui.components.menu import Menu
        from ui.components.table import Table
        from ui.components.form import Form
        from ui.base_ui import BaseUI
        print("✅ UI 組件導入成功")
        
        # 測試 UI 界面
        from ui.member_ui import MemberUI
        from ui.merchant_ui import MerchantUI
        from ui.admin_ui import AdminUI
        print("✅ UI 界面導入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 模組導入失敗: {e}")
        return False

def test_validators():
    """測試驗證器"""
    print("\n🔍 測試驗證器...")
    
    try:
        from utils.validators import Validator
        
        # 測試手機號驗證
        assert Validator.validate_phone("13800138000") == True
        assert Validator.validate_phone("12345678901") == False
        
        # 測試郵箱驗證
        assert Validator.validate_email("test@example.com") == True
        assert Validator.validate_email("invalid-email") == False
        
        # 測試金額驗證
        assert Validator.validate_amount(100.50) == True
        assert Validator.validate_amount(-10) == False
        
        print("✅ 驗證器測試通過")
        return True
        
    except Exception as e:
        print(f"❌ 驗證器測試失敗: {e}")
        return False

def test_formatters():
    """測試格式化器"""
    print("\n🔍 測試格式化器...")
    
    try:
        from utils.formatters import Formatter
        
        # 測試貨幣格式化
        assert Formatter.format_currency(1234.56) == "¥1,234.56"
        assert Formatter.format_currency(None) == "¥0.00"
        
        # 測試文本截斷
        long_text = "這是一個很長的中文文本測試"
        truncated = Formatter.truncate_text(long_text, 10)
        assert len(truncated) <= 13  # 包含 "..." 的長度
        
        # 測試文本填充
        padded = Formatter.pad_text("測試", 10, 'left')
        assert len(padded) == 10
        
        print("✅ 格式化器測試通過")
        return True
        
    except Exception as e:
        print(f"❌ 格式化器測試失敗: {e}")
        return False

def test_models():
    """測試數據模型"""
    print("\n🔍 測試數據模型...")
    
    try:
        from models.member import Member
        from models.card import Card
        from models.transaction import Transaction
        
        # 測試會員模型
        member_data = {
            "id": "test-member-id",
            "name": "測試會員",
            "phone": "13800138000",
            "email": "test@example.com",
            "status": "active"
        }
        member = Member.from_dict(member_data)
        assert member.name == "測試會員"
        assert member.is_active() == True
        
        # 測試卡片模型
        card_data = {
            "id": "test-card-id",
            "card_no": "STD00000001",
            "card_type": "standard",
            "balance": 1000.0,
            "points": 500,
            "status": "active"
        }
        card = Card.from_dict(card_data)
        assert card.can_recharge() == False  # 標準卡不能充值
        assert card.is_active() == True
        
        print("✅ 數據模型測試通過")
        return True
        
    except Exception as e:
        print(f"❌ 數據模型測試失敗: {e}")
        return False

def test_ui_components():
    """測試 UI 組件"""
    print("\n🔍 測試 UI 組件...")
    
    try:
        from ui.components.table import Table
        from ui.base_ui import BaseUI
        
        # 測試表格組件
        headers = ["姓名", "年齡", "城市"]
        data = [
            {"姓名": "張三", "年齡": "25", "城市": "北京"},
            {"姓名": "李四", "年齡": "30", "城市": "上海"}
        ]
        
        table = Table(headers, data, "測試表格")
        # 不實際顯示，只測試創建
        assert table.headers == headers
        assert len(table.data) == 2
        
        print("✅ UI 組件測試通過")
        return True
        
    except Exception as e:
        print(f"❌ UI 組件測試失敗: {e}")
        return False

def test_configuration():
    """測試配置"""
    print("\n🔍 測試配置...")
    
    try:
        from config.settings import settings
        
        # 檢查配置結構
        assert hasattr(settings, 'database')
        assert hasattr(settings, 'ui')
        assert hasattr(settings, 'logging')
        
        # 檢查默認值
        assert settings.ui.page_size > 0
        assert settings.ui.qr_ttl_seconds > 0
        
        print("✅ 配置測試通過")
        return True
        
    except Exception as e:
        print(f"❌ 配置測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("🚀 MPS CLI 基本功能測試")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_configuration,
        test_validators,
        test_formatters,
        test_models,
        test_ui_components
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 測試結果: {passed}/{total} 通過")
    
    if passed == total:
        print("🎉 所有基本功能測試通過！")
        print("\n📋 下一步:")
        print("  1. 配置 .env 文件")
        print("  2. 運行 python main.py test 測試數據庫連接")
        print("  3. 運行 python main.py 啟動程序")
        return True
    else:
        print("❌ 部分測試失敗，請檢查錯誤信息")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)