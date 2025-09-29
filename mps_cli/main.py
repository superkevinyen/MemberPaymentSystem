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
        logger.info("MPS CLI 啟動")
        
        # 驗證配置
        settings.validate()
        logger.info("配置驗證通過")
        
        # 測試數據庫連接
        from config.supabase_client import supabase_client
        if not supabase_client.test_connection():
            BaseUI.show_error("無法連接到數據庫，請檢查配置")
            return
        
        # 顯示歡迎界面
        show_welcome()
        
        # 選擇角色
        role = select_role()
        
        # 啟動對應界面
        if role == "member":
            logger.info("啟動會員界面")
            MemberUI().start()
        elif role == "merchant":
            logger.info("啟動商戶界面")
            MerchantUI().start()
        elif role == "admin":
            logger.info("啟動管理員界面")
            AdminUI().start()
        else:
            BaseUI.show_goodbye()
            
    except KeyboardInterrupt:
        print("\n▸ 再見！")
        logger.info("用戶中斷程序")
    except Exception as e:
        BaseUI.show_error(f"系統錯誤: {e}")
        logger.error(f"系統錯誤: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("MPS CLI 結束")

def show_welcome():
    """顯示歡迎界面"""
    BaseUI.show_welcome("MPS 系統")
    
    print("▸ 系統功能")
    print("  ├─ MEMBER    會員用戶：查看卡片、生成 QR 碼、充值")
    print("  ├─ MERCHANT  商戶用戶：掃碼收款、退款處理")
    print("  └─ ADMIN     管理員：會員管理、卡片管理")
    print()

def select_role() -> str:
    """選擇用戶角色"""
    roles = {
        "1": ("member", "會員用戶", "[MEMBER]"),
        "2": ("merchant", "商戶用戶", "[MERCHANT]"), 
        "3": ("admin", "管理員", "[ADMIN]"),
        "4": ("exit", "退出系統", "[EXIT]")
    }
    
    print("▸ 請選擇您的角色")
    for key, (role, name, prefix) in roles.items():
        print(f"  {key}. {prefix:<12} {name}")
    
    while True:
        try:
            choice = input("請選擇 (1-4): ").strip()
            if choice in roles:
                selected_role, role_name, icon = roles[choice]
                
                if selected_role == "exit":
                    return "exit"
                
                print(f"\n▸ 您選擇了：{role_name}")
                
                # 確認選擇
                if BaseUI.confirm_action("確認進入？", True):
                    logger.info(f"用戶選擇角色: {selected_role}")
                    return selected_role
                else:
                    print()  # 重新選擇
            else:
                print("✗ 請選擇 1-4")
        except KeyboardInterrupt:
            return "exit"

def member_main():
    """會員用戶入口"""
    try:
        setup_logging()
        settings.validate()
        
        from config.supabase_client import supabase_client
        if not supabase_client.test_connection():
            BaseUI.show_error("無法連接到數據庫")
            return
        
        MemberUI().start()
    except Exception as e:
        BaseUI.show_error(f"會員系統錯誤: {e}")

def merchant_main():
    """商戶用戶入口"""
    try:
        setup_logging()
        settings.validate()
        
        from config.supabase_client import supabase_client
        if not supabase_client.test_connection():
            BaseUI.show_error("無法連接到數據庫")
            return
        
        MerchantUI().start()
    except Exception as e:
        BaseUI.show_error(f"商戶系統錯誤: {e}")

def admin_main():
    """管理員入口"""
    try:
        setup_logging()
        settings.validate()
        
        from config.supabase_client import supabase_client
        if not supabase_client.test_connection():
            BaseUI.show_error("無法連接到數據庫")
            return
        
        AdminUI().start()
    except Exception as e:
        BaseUI.show_error(f"管理系統錯誤: {e}")

def test_connection():
    """測試數據庫連接"""
    try:
        setup_logging()
        settings.validate()
        
        from config.supabase_client import supabase_client
        
        print("正在測試數據庫連接...")
        
        if supabase_client.test_connection():
            print("▸ 數據庫連接成功")
            
            # 顯示基本統計
            try:
                result = supabase_client.rpc("test_connection", {})
                if result and result.get('stats'):
                    stats = result['stats']
                    print(f"▸ 系統概況:")
                    print(f"  會員數量: {stats.get('members', 0)}")
                    print(f"  卡片數量: {stats.get('cards', 0)}")
                    print(f"  商戶數量: {stats.get('merchants', 0)}")
                    print(f"  測試時間: {result.get('timestamp', 'N/A')}")
                else:
                    print("! 無法獲取統計信息")
                
            except Exception as e:
                print(f"! 無法獲取統計信息: {e}")
        else:
            print("✗ 數據庫連接失敗")
            
    except Exception as e:
        print(f"✗ 連接測試失敗: {e}")

def show_help():
    """顯示幫助信息"""
    print("MPS CLI - Member Payment System 命令行界面")
    print()
    print("使用方法:")
    print("  python main.py              # 啟動主程序")
    print("  python main.py member       # 直接啟動會員界面")
    print("  python main.py merchant     # 直接啟動商戶界面")
    print("  python main.py admin        # 直接啟動管理員界面")
    print("  python main.py test         # 測試數據庫連接")
    print("  python main.py help         # 顯示此幫助信息")
    print()
    print("環境配置:")
    print("  請確保 .env 文件已正確配置 Supabase 連接信息")
    print("  參考 .env.example 文件進行配置")
    print()
    print("功能特色:")
    print("  • 支持中文字符寬度對齊")
    print("  • 完善的錯誤處理和用戶提示")
    print("  • 基於 Supabase RPC 的後端交互")
    print("  • 模組化的架構設計")

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
            print(f"✗ 未知命令: {command}")
            print("使用 'python main.py help' 查看幫助信息")
    else:
        main()