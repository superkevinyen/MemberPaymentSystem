#!/usr/bin/env python3
"""
MPS CLI - Member Payment System 命令行界面
主入口程序
"""

import os
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from ui.member_ui import MemberUI
from ui.merchant_ui import MerchantUI
from ui.admin_ui import AdminUI
from ui.base_ui import BaseUI
from utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

def main():
    """主入口函數"""
    try:
        # 設置日誌
        setup_logging()
        logger.info("MPS CLI Started")
        
        # 驗證配置
        settings.validate()
        logger.info("Configuration validation passed")
        
        # 測試數據庫連接
        from config.supabase_client import supabase_client
        if not supabase_client.test_connection():
            BaseUI.show_error("Unable to connect to database, please check configuration")
            return
        
        # 顯示歡迎界面
        show_welcome()
        
        # 選擇角色
        role = select_role()
        
        # 啟動對應界面
        if role == "member":
            logger.info("Starting member interface")
            MemberUI().start()
        elif role == "merchant":
            logger.info("Starting merchant interface")
            MerchantUI().start()
        elif role == "admin":
            logger.info("Starting admin interface")
            AdminUI().start()
        else:
            BaseUI.show_goodbye()
            
    except KeyboardInterrupt:
        print("\n▸ Goodbye!")
        logger.info("User interrupted program")
    except Exception as e:
        BaseUI.show_error(f"System error: {e}")
        logger.error(f"System error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("MPS CLI Ended")

def show_welcome():
    """顯示歡迎界面"""
    BaseUI.show_welcome("MPS System")
    
    print("▸ System Features")
    print("  ├─ MEMBER    Member User: View cards, generate QR codes, recharge")
    print("  ├─ MERCHANT  Merchant User: Scan & charge, process refunds")
    print("  └─ ADMIN     Administrator: Member management, card management")
    print()

def select_role() -> str:
    """選擇用戶角色"""
    roles = {
        "1": ("member", "Member User", "[MEMBER]"),
        "2": ("merchant", "Merchant User", "[MERCHANT]"),
        "3": ("admin", "Administrator", "[ADMIN]"),
        "4": ("exit", "Exit System", "[EXIT]")
    }
    
    print("▸ Please select your role")
    for key, (role, name, prefix) in roles.items():
        print(f"  {key}. {prefix:<12} {name}")
    
    while True:
        try:
            choice = input("Please select (1-4): ").strip()
            if choice in roles:
                selected_role, role_name, icon = roles[choice]
                
                if selected_role == "exit":
                    return "exit"
                
                print(f"\n▸ You selected: {role_name}")
                
                # 確認選擇
                if BaseUI.confirm_action("Confirm to enter?", True):
                    logger.info(f"User selected role: {selected_role}")
                    return selected_role
                else:
                    print()  # 重新選擇
            else:
                print("✗ Please select 1-4")
        except KeyboardInterrupt:
            return "exit"

def member_main():
    """會員用戶入口"""
    try:
        setup_logging()
        settings.validate()
        
        from config.supabase_client import supabase_client
        if not supabase_client.test_connection():
            BaseUI.show_error("Unable to connect to database")
            return
        
        MemberUI().start()
    except Exception as e:
        BaseUI.show_error(f"Member system error: {e}")

def merchant_main():
    """商戶用戶入口"""
    try:
        setup_logging()
        settings.validate()
        
        from config.supabase_client import supabase_client
        if not supabase_client.test_connection():
            BaseUI.show_error("Unable to connect to database")
            return
        
        MerchantUI().start()
    except Exception as e:
        BaseUI.show_error(f"Merchant system error: {e}")

def admin_main():
    """管理員入口"""
    try:
        setup_logging()
        settings.validate()
        
        from config.supabase_client import supabase_client
        if not supabase_client.test_connection():
            BaseUI.show_error("Unable to connect to database")
            return
        
        AdminUI().start()
    except Exception as e:
        BaseUI.show_error(f"Admin system error: {e}")

def test_connection():
    """測試數據庫連接"""
    try:
        setup_logging()
        settings.validate()
        
        from config.supabase_client import supabase_client
        
        print("Testing database connection...")
        
        if supabase_client.test_connection():
            print("▸ Database connection successful")
            
            # 顯示基本統計
            try:
                result = supabase_client.rpc("test_connection", {})
                if result and result.get('stats'):
                    stats = result['stats']
                    print(f"▸ System Overview:")
                    print(f"  Members: {stats.get('members', 0)}")
                    print(f"  Cards: {stats.get('cards', 0)}")
                    print(f"  Merchants: {stats.get('merchants', 0)}")
                    print(f"  Test Time: {result.get('timestamp', 'N/A')}")
                else:
                    print("! Unable to get statistics")
                
            except Exception as e:
                print(f"! Unable to get statistics: {e}")
        else:
            print("✗ Database connection failed")
            
    except Exception as e:
        print(f"✗ Connection test failed: {e}")

def show_help():
    """顯示幫助信息"""
    print("MPS CLI - Member Payment System Command Line Interface")
    print()
    print("Usage:")
    print("  python main.py              # Start main program")
    print("  python main.py member       # Start member interface directly")
    print("  python main.py merchant     # Start merchant interface directly")
    print("  python main.py admin        # Start admin interface directly")
    print("  python main.py test         # Test database connection")
    print("  python main.py help         # Show this help information")
    print()
    print("Environment Configuration:")
    print("  Please ensure .env file is properly configured with Supabase connection info")
    print("  Refer to .env.example file for configuration")
    print()
    print("Features:")
    print("  • Support for Chinese character width alignment")
    print("  • Comprehensive error handling and user prompts")
    print("  • Backend interaction based on Supabase RPC")
    print("  • Modular architecture design")

if __name__ == "__main__":
    # 處理命令行參數
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "member":
            member_main()
        elif command == "merchant":
            merchant_main()
        elif command == "admin":
            admin_main()
        elif command == "test":
            test_connection()
        elif command in ["help", "-h", "--help"]:
            show_help()
        else:
            print(f"✗ Unknown command: {command}")
            print("Use 'python main.py help' to view help information")
    else:
        main()