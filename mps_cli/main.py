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
from ui.login_ui import LoginUI
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
        print("正在連接數據庫...")
        if not supabase_client.test_connection():
            print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
            print("║                          連接失敗                                         ║")
            print("╠═══════════════════════════════════════════════════════════════════════════╣")
            print("║  ❌ 無法連接到數據庫                                                      ║")
            print("║                                                                           ║")
            print("║  請檢查：                                                                 ║")
            print("║  1. .env 文件是否存在且配置正確                                           ║")
            print("║  2. SUPABASE_URL 和 SUPABASE_KEY 是否正確                                 ║")
            print("║  3. 網絡連接是否正常                                                      ║")
            print("║                                                                           ║")
            print("║  參考 .env.example 文件進行配置                                           ║")
            print("╚═══════════════════════════════════════════════════════════════════════════╝")
            return
        print("✅ 數據庫連接成功\n")
        
        # 顯示歡迎界面
        show_welcome()
        
        # 統一登入
        login_ui = LoginUI()
        login_result = login_ui.show_login()
        
        if not login_result:
            print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
            print("║                          感謝使用                                         ║")
            print("╠═══════════════════════════════════════════════════════════════════════════╣")
            print("║  👋 再見！期待您的下次使用                                                ║")
            print("╚═══════════════════════════════════════════════════════════════════════════╝")
            return
        
        # 根據角色進入對應界面
        role = login_result["role"]
        auth_service = login_ui.auth_service
        
        try:
            if role in ["admin", "super_admin"]:
                logger.info("Starting admin interface")
                admin_ui = AdminUI(auth_service)
                admin_ui.start()
            elif role == "merchant":
                logger.info("Starting merchant interface")
                merchant_ui = MerchantUI(auth_service)
                merchant_ui.start()
            elif role == "member":
                logger.info("Starting member interface")
                member_ui = MemberUI(auth_service)
                member_ui.start()
            else:
                BaseUI.show_error(f"Unknown role: {role}")
        finally:
            # 登出
            try:
                auth_service.logout()
                print("\n✅ 已安全登出")
            except:
                pass
            
    except KeyboardInterrupt:
        print("\n\n╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║                          程序中斷                                         ║")
        print("╠═══════════════════════════════════════════════════════════════════════════╣")
        print("║  👋 再見！您的操作已保存                                                  ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
        logger.info("User interrupted program")
    except Exception as e:
        print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║                          系統錯誤                                         ║")
        print("╠═══════════════════════════════════════════════════════════════════════════╣")
        print(f"║  ❌ 發生錯誤: {str(e)[:60]:<60} ║")
        print("║                                                                           ║")
        print("║  請聯繫技術支持或查看日誌文件獲取詳細信息                                 ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
        logger.error(f"System error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("MPS CLI Ended")

def show_welcome():
    """顯示歡迎界面 - 商業版"""
    BaseUI.clear_screen()
    print("╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                                                                           ║")
    print("║                     歡迎使用 MPS 會員支付系統                             ║")
    print("║                   Member Payment System v1.0.0                            ║")
    print("║                                                                           ║")
    print("╠═══════════════════════════════════════════════════════════════════════════╣")
    print("║  功能特色：                                                               ║")
    print("║  • 多種卡片類型支持（標準卡/企業卡/代金券）                               ║")
    print("║  • QR 碼支付，安全便捷                                                    ║")
    print("║  • 積分等級系統，自動折扣                                                 ║")
    print("║  • 完整的交易管理和退款支持                                               ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    print()

def member_main():
    """會員用戶入口（已棄用，請使用統一登入）"""
    print("⚠️  Please use unified login: python main.py")
    print("   This direct entry method has been deprecated")

def merchant_main():
    """商戶用戶入口（已棄用，請使用統一登入）"""
    print("⚠️  Please use unified login: python main.py")
    print("   This direct entry method has been deprecated")

def admin_main():
    """管理員入口（已棄用，請使用統一登入）"""
    print("⚠️  Please use unified login: python main.py")
    print("   This direct entry method has been deprecated")

def test_connection():
    """測試數據庫連接 - 商業版"""
    try:
        setup_logging()
        settings.validate()
        
        from config.supabase_client import supabase_client
        
        print("╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║                    數據庫連接測試                                         ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
        print("\n正在測試連接...")
        
        if supabase_client.test_connection():
            print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
            print("║                    連接成功！                                             ║")
            print("╠═══════════════════════════════════════════════════════════════════════════╣")
            
            # 顯示基本統計
            try:
                result = supabase_client.rpc("test_connection", {})
                if result and result.get('stats'):
                    stats = result['stats']
                    print("║  系統概況：                                                               ║")
                    print(f"║  • 會員數量：{stats.get('members', 0):<60} ║")
                    print(f"║  • 卡片數量：{stats.get('cards', 0):<60} ║")
                    print(f"║  • 商戶數量：{stats.get('merchants', 0):<60} ║")
                    print(f"║  • 測試時間：{result.get('timestamp', 'N/A'):<60} ║")
                else:
                    print("║  ⚠️  無法獲取系統統計信息                                                ║")
                
            except Exception as e:
                print(f"║  ⚠️  統計信息獲取失敗: {str(e)[:50]:<50} ║")
            
            print("╚═══════════════════════════════════════════════════════════════════════════╝")
            print("\n✅ 數據庫連接正常，系統可以使用")
        else:
            print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
            print("║                    連接失敗                                               ║")
            print("╠═══════════════════════════════════════════════════════════════════════════╣")
            print("║  ❌ 無法連接到數據庫                                                      ║")
            print("║                                                                           ║")
            print("║  請檢查：                                                                 ║")
            print("║  1. .env 文件是否存在                                                     ║")
            print("║  2. SUPABASE_URL 和 SUPABASE_KEY 是否正確                                 ║")
            print("║  3. 網絡連接是否正常                                                      ║")
            print("╚═══════════════════════════════════════════════════════════════════════════╝")
            
    except Exception as e:
        print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║                    測試失敗                                               ║")
        print("╠═══════════════════════════════════════════════════════════════════════════╣")
        print(f"║  ❌ 錯誤: {str(e)[:64]:<64} ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")

def show_help():
    """顯示幫助信息 - 商業版"""
    print("╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                    MPS CLI 使用說明                                       ║")
    print("║              Member Payment System v1.0.0                                 ║")
    print("╠═══════════════════════════════════════════════════════════════════════════╣")
    print("║  使用方法：                                                               ║")
    print("║                                                                           ║")
    print("║  python main.py              啟動主程序（推薦）                           ║")
    print("║  python main.py test         測試數據庫連接                               ║")
    print("║  python main.py help         顯示此幫助信息                               ║")
    print("║                                                                           ║")
    print("╠═══════════════════════════════════════════════════════════════════════════╣")
    print("║  環境配置：                                                               ║")
    print("║                                                                           ║")
    print("║  1. 複製 .env.example 為 .env                                             ║")
    print("║  2. 配置 Supabase 連接信息：                                              ║")
    print("║     - SUPABASE_URL: 您的 Supabase 項目 URL                                ║")
    print("║     - SUPABASE_KEY: 您的 Supabase API Key                                 ║")
    print("║                                                                           ║")
    print("╠═══════════════════════════════════════════════════════════════════════════╣")
    print("║  系統特色：                                                               ║")
    print("║                                                                           ║")
    print("║  ✓ 三種角色支持（會員/商戶/管理員）                                       ║")
    print("║  ✓ 多種卡片類型（標準卡/企業卡/代金券）                                   ║")
    print("║  ✓ QR 碼支付，安全便捷                                                    ║")
    print("║  ✓ 積分等級系統，自動折扣                                                 ║")
    print("║  ✓ 完整的交易管理和退款支持                                               ║")
    print("║  ✓ 專業的界面設計和錯誤處理                                               ║")
    print("║                                                                           ║")
    print("╠═══════════════════════════════════════════════════════════════════════════╣")
    print("║  技術支持：                                                               ║")
    print("║                                                                           ║")
    print("║  • 文檔：docs/ 目錄                                                       ║")
    print("║  • 測試：python -m pytest tests/                                          ║")
    print("║  • 日誌：logs/ 目錄                                                       ║")
    print("║                                                                           ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")

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