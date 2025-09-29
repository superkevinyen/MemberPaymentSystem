import os
import sys
from typing import List, Callable, Optional

# 添加項目根目錄到路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.formatters import Formatter

class Menu:
    """菜單組件"""
    
    def __init__(self, title: str, options: List[str], handlers: List[Callable]):
        self.title = title
        self.options = options
        self.handlers = handlers
        
        if len(options) != len(handlers):
            raise ValueError("選項和處理函數數量必須相同")
    
    def display(self):
        """顯示菜單"""
        self.clear_screen()
        self.show_header()
        self.show_options()
    
    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_header(self):
        """顯示標題"""
        # 計算標題寬度，考慮中文字符
        title_width = 0
        for char in self.title:
            import wcwidth
            title_width += wcwidth.wcwidth(char) or 1
        
        # 設置最小寬度
        width = max(title_width + 4, 40)
        
        print("┌" + "─" * (width - 2) + "┐")
        print(f"│{Formatter.pad_text(self.title, width - 2, 'center')}│")
        print("├" + "─" * (width - 2) + "┤")
    
    def show_options(self):
        """顯示選項"""
        for i, option in enumerate(self.options, 1):
            # 計算選項寬度
            option_text = f" {i}. {option}"
            padded_text = Formatter.pad_text(option_text, 38, 'left')
            print(f"│{padded_text}│")
        print("└" + "─" * 38 + "┘")
    
    def get_choice(self) -> int:
        """獲取用戶選擇"""
        while True:
            try:
                choice = input(f"請選擇 (1-{len(self.options)}): ").strip()
                if not choice:
                    continue
                    
                choice_num = int(choice)
                if 1 <= choice_num <= len(self.options):
                    return choice_num
                print(f"❌ 請選擇 1-{len(self.options)}")
            except ValueError:
                print("❌ 請輸入有效數字")
            except KeyboardInterrupt:
                print("\n👋 再見！")
                exit(0)
    
    def run(self):
        """運行菜單"""
        while True:
            self.display()
            choice = self.get_choice()
            
            try:
                # 執行對應的處理函數
                result = self.handlers[choice - 1]()
                
                # 如果返回 False，退出菜單
                if result is False:
                    break
                    
            except Exception as e:
                print(f"❌ 操作失敗: {e}")
                input("按任意鍵繼續...")

class SimpleMenu:
    """簡化菜單組件"""
    
    @staticmethod
    def show_options(title: str, options: List[str]) -> int:
        """顯示選項並獲取選擇"""
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
    def confirm(message: str, default: bool = False) -> bool:
        """確認對話框"""
        default_text = "Y/n" if default else "y/N"
        response = input(f"{message} ({default_text}): ").strip().lower()
        
        if not response:
            return default
        
        return response in ['y', 'yes', '是', '確認']
    
    @staticmethod
    def show_message(title: str, message: str, message_type: str = "info"):
        """顯示消息"""
        icons = {
            "info": "ℹ️",
            "success": "✅", 
            "warning": "⚠️",
            "error": "❌"
        }
        
        icon = icons.get(message_type, "ℹ️")
        
        print(f"\n{icon} {title}")
        if message:
            print(f"   {message}")
    
    @staticmethod
    def pause(message: str = "按任意鍵繼續..."):
        """暫停等待用戶輸入"""
        try:
            input(message)
        except KeyboardInterrupt:
            print("\n👋 再見！")
            exit(0)

class ProgressMenu:
    """帶進度的菜單"""
    
    def __init__(self, title: str, steps: List[str]):
        self.title = title
        self.steps = steps
        self.current_step = 0
    
    def show_progress(self):
        """顯示進度"""
        print(f"\n{self.title}")
        print("─" * 40)
        
        for i, step in enumerate(self.steps):
            if i < self.current_step:
                print(f"✅ {step}")
            elif i == self.current_step:
                print(f"🔄 {step}")
            else:
                print(f"⏳ {step}")
        
        print("─" * 40)
        print(f"進度: {self.current_step}/{len(self.steps)}")
    
    def next_step(self):
        """下一步"""
        if self.current_step < len(self.steps):
            self.current_step += 1
    
    def reset(self):
        """重置進度"""
        self.current_step = 0