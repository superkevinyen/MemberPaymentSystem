import os
from typing import List, Dict, Any, Optional
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.formatters import Formatter
from utils.logger import ui_logger

class BaseUI:
    """基礎 UI 組件"""
    
    @staticmethod
    def clear_screen():
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    @staticmethod
    def show_header(title: str, width: int = 40):
        """顯示標題"""
        print("┌" + "─" * (width - 2) + "┐")
        print(f"│{Formatter.pad_text(title, width - 2, 'center')}│")
        print("└" + "─" * (width - 2) + "┘")
    
    @staticmethod
    def show_box(title: str, content: List[str], width: int = 40):
        """顯示框架內容"""
        print("┌" + "─" * (width - 2) + "┐")
        print(f"│{Formatter.pad_text(title, width - 2, 'center')}│")
        print("├" + "─" * (width - 2) + "┤")
        
        for line in content:
            print(f"│{Formatter.pad_text(line, width - 2, 'left')}│")
        
        print("└" + "─" * (width - 2) + "┘")
    
    @staticmethod
    def show_info_box(title: str, info: Dict[str, Any], width: int = 40):
        """顯示信息框"""
        content = []
        for key, value in info.items():
            content.append(f"{key}: {value}")
        
        BaseUI.show_box(title, content, width)
    
    @staticmethod
    def show_menu(options: List[str], title: str = "請選擇") -> int:
        """顯示菜單並獲取選擇"""
        print(f"\n{title}:")
        for i, option in enumerate(options, 1):
            print(f"  {i}. {option}")
        
        while True:
            try:
                choice = int(input(f"請選擇 (1-{len(options)}): "))
                if 1 <= choice <= len(options):
                    return choice
                print(f"❌ 請選擇 1-{len(options)}")
            except ValueError:
                print("❌ 請輸入有效數字")
            except KeyboardInterrupt:
                print("\n👋 再見！")
                exit(0)
    
    @staticmethod
    def confirm_action(message: str, default: bool = False) -> bool:
        """確認操作"""
        default_text = "Y/n" if default else "y/N"
        response = input(f"{message} ({default_text}): ").strip().lower()
        
        if not response:
            return default
        
        return response in ['y', 'yes', '是', '確認']
    
    @staticmethod
    def show_success(message: str, details: Optional[Dict[str, Any]] = None):
        """顯示成功信息"""
        print(f"\n✅ {message}")
        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")
    
    @staticmethod
    def show_error(message: str, suggestion: Optional[str] = None):
        """顯示錯誤信息"""
        print(f"\n❌ {message}")
        if suggestion:
            print(f"💡 建議：{suggestion}")
    
    @staticmethod
    def show_warning(message: str):
        """顯示警告信息"""
        print(f"\n⚠️  {message}")
    
    @staticmethod
    def show_info(message: str):
        """顯示信息"""
        print(f"\nℹ️  {message}")
    
    @staticmethod
    def pause(message: str = "按任意鍵繼續..."):
        """暫停等待用戶輸入"""
        try:
            input(message)
        except KeyboardInterrupt:
            print("\n👋 再見！")
            exit(0)
    
    @staticmethod
    def show_loading(message: str = "處理中..."):
        """顯示加載信息"""
        print(f"🔄 {message}")
    
    @staticmethod
    def show_welcome(system_name: str = "MPS 系統"):
        """顯示歡迎界面"""
        BaseUI.clear_screen()
        print("╔═══════════════════════════════════════╗")
        print(f"║{Formatter.pad_text(f'歡迎使用 {system_name}', 39, 'center')}║")
        print("║     Member Payment System             ║")
        print("╚═══════════════════════════════════════╝")
        print()
    
    @staticmethod
    def show_goodbye():
        """顯示再見信息"""
        print("\n╔═══════════════════════════════════════╗")
        print("║              感謝使用                 ║")
        print("║         MPS 系統再見！                ║")
        print("╚═══════════════════════════════════════╝")

class StatusDisplay:
    """狀態顯示組件"""
    
    @staticmethod
    def show_transaction_result(success: bool, tx_info: Dict[str, Any]):
        """顯示交易結果"""
        if success:
            print("┌─────────────────────────────────────┐")
            print("│              交易成功               │")
            print("├─────────────────────────────────────┤")
            
            for key, value in tx_info.items():
                formatted_key = Formatter.pad_text(f"{key}:", 10, 'left')
                formatted_value = Formatter.pad_text(str(value), 25, 'left')
                print(f"│ {formatted_key} {formatted_value} │")
            
            print("└─────────────────────────────────────┘")
        else:
            print("┌─────────────────────────────────────┐")
            print("│              交易失敗               │")
            print("├─────────────────────────────────────┤")
            
            error_msg = tx_info.get("error", "未知錯誤")
            print(f"│ {Formatter.pad_text(error_msg, 35, 'left')} │")
            
            suggestion = tx_info.get("suggestion")
            if suggestion:
                print("├─────────────────────────────────────┤")
                print(f"│ 💡 {Formatter.pad_text(suggestion, 32, 'left')} │")
            
            print("└─────────────────────────────────────┘")
    
    @staticmethod
    def show_card_info(card_info: Dict[str, Any]):
        """顯示卡片信息"""
        print("┌─────────────────────────────────────┐")
        print("│              卡片信息               │")
        print("├─────────────────────────────────────┤")
        
        # 格式化顯示卡片信息
        fields = [
            ("卡號", card_info.get("card_no", "")),
            ("類型", card_info.get("card_type", "")),
            ("餘額", Formatter.format_currency(card_info.get("balance", 0))),
            ("積分", Formatter.format_points(card_info.get("points", 0))),
            ("等級", Formatter.format_level(card_info.get("level", 0))),
            ("狀態", card_info.get("status", ""))
        ]
        
        for label, value in fields:
            formatted_label = Formatter.pad_text(f"{label}:", 8, 'left')
            formatted_value = Formatter.pad_text(str(value), 25, 'left')
            print(f"│ {formatted_label} {formatted_value} │")
        
        print("└─────────────────────────────────────┘")
    
    @staticmethod
    def show_qr_code(qr_info: Dict[str, Any]):
        """顯示 QR 碼信息"""
        print("┌─────────────────────────────────────┐")
        print("│            付款 QR 碼               │")
        print("├─────────────────────────────────────┤")
        
        qr_plain = qr_info.get("qr_plain", "")
        expires_at = qr_info.get("expires_at", "")
        
        # 顯示 QR 碼（截斷顯示）
        qr_display = Formatter.truncate_text(qr_plain, 25)
        print(f"│ QR 碼: {Formatter.pad_text(qr_display, 25, 'left')} │")
        
        # 顯示過期時間
        expires_display = Formatter.format_datetime(expires_at)
        print(f"│ 過期時間: {Formatter.pad_text(expires_display, 21, 'left')} │")
        
        print("├─────────────────────────────────────┤")
        print("│ 🔔 請向商戶出示此 QR 碼進行支付     │")
        print("│ ⏰ QR 碼將在 15 分鐘後自動過期      │")
        print("└─────────────────────────────────────┘")

class InputHelper:
    """輸入助手"""
    
    @staticmethod
    def get_safe_input(prompt: str, input_type: str = "text", 
                      validator: Optional[Callable] = None,
                      required: bool = True) -> Any:
        """安全的輸入獲取"""
        while True:
            try:
                if input_type == "password":
                    import getpass
                    value = getpass.getpass(f"{prompt}: ")
                else:
                    value = input(f"{prompt}: ").strip()
                
                # 檢查必填
                if required and not value:
                    print("❌ 此項為必填")
                    continue
                
                # 類型轉換
                if input_type == "int":
                    value = int(value) if value else None
                elif input_type == "float":
                    value = float(value) if value else None
                elif input_type == "bool":
                    value = value.lower() in ['y', 'yes', '是', '1', 'true'] if value else False
                
                # 驗證
                if value and validator and not validator(value):
                    print("❌ 輸入格式不正確")
                    continue
                
                return value
                
            except ValueError:
                print(f"❌ 請輸入有效的{input_type}")
            except KeyboardInterrupt:
                print("\n👋 再見！")
                exit(0)
    
    @staticmethod
    def get_multi_line_input(prompt: str, end_marker: str = "END") -> str:
        """獲取多行輸入"""
        print(f"{prompt} (輸入 '{end_marker}' 結束):")
        lines = []
        
        while True:
            try:
                line = input()
                if line.strip() == end_marker:
                    break
                lines.append(line)
            except KeyboardInterrupt:
                print("\n👋 再見！")
                exit(0)
        
        return '\n'.join(lines)