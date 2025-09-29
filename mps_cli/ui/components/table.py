import sys
import os
from typing import List, Dict, Any, Optional, Callable

# 添加項目根目錄到路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.formatters import Formatter
import wcwidth

class Table:
    """表格組件"""
    
    def __init__(self, headers: List[str], data: List[Dict[str, Any]], 
                 title: Optional[str] = None):
        self.headers = headers
        self.data = data
        self.title = title
        self.col_widths = self._calculate_column_widths()
    
    def _calculate_column_widths(self) -> List[int]:
        """計算列寬，考慮中文字符"""
        widths = []
        
        # 計算標題寬度
        for header in self.headers:
            header_width = 0
            for char in header:
                header_width += wcwidth.wcwidth(char) or 1
            widths.append(header_width)
        
        # 計算數據寬度
        for row in self.data:
            for i, header in enumerate(self.headers):
                value = str(row.get(header, ""))
                value_width = 0
                for char in value:
                    value_width += wcwidth.wcwidth(char) or 1
                
                if i < len(widths):
                    widths[i] = max(widths[i], value_width)
                else:
                    widths.append(value_width)
        
        # 設置最小寬度 8，最大寬度 30
        return [max(8, min(30, width)) for width in widths]
    
    def display(self, page_size: Optional[int] = None, page: int = 0):
        """顯示表格"""
        if self.title:
            self._show_title()
        
        self._show_header()
        
        # 分頁處理
        start_idx = page * page_size if page_size else 0
        end_idx = start_idx + page_size if page_size else len(self.data)
        page_data = self.data[start_idx:end_idx]
        
        if not page_data:
            self._show_empty_message()
        else:
            self._show_data(page_data)
        
        self._show_footer()
        
        # 分頁信息
        if page_size and len(self.data) > page_size:
            total_pages = (len(self.data) + page_size - 1) // page_size
            print(f"Page {page + 1} of {total_pages} (Total {len(self.data)} records)")
    
    def _show_title(self):
        """顯示標題"""
        total_width = sum(self.col_widths) + len(self.headers) * 3 + 1
        print("┌" + "─" * (total_width - 2) + "┐")
        print(f"│{Formatter.pad_text(self.title, total_width - 2, 'center')}│")
        print("├" + "─" * (total_width - 2) + "┤")
    
    def _show_header(self):
        """顯示表頭"""
        header_line = "│"
        separator_line = "├"
        
        for i, (header, width) in enumerate(zip(self.headers, self.col_widths)):
            padded_header = Formatter.pad_text(header, width, 'center')
            header_line += f" {padded_header} │"
            
            if i < len(self.headers) - 1:
                separator_line += "─" * (width + 2) + "┼"
            else:
                separator_line += "─" * (width + 2) + "┤"
        
        if not self.title:
            total_width = sum(self.col_widths) + len(self.headers) * 3 + 1
            print("┌" + "─" * (total_width - 2) + "┐")
        
        print(header_line)
        print(separator_line)
    
    def _show_data(self, data: List[Dict[str, Any]]):
        """顯示數據行"""
        for row in data:
            line = "│"
            for header, width in zip(self.headers, self.col_widths):
                value = str(row.get(header, ""))
                
                # 截斷過長的文本
                truncated_value = Formatter.truncate_text(value, width)
                padded_value = Formatter.pad_text(truncated_value, width, 'left')
                
                line += f" {padded_value} │"
            print(line)
    
    def _show_empty_message(self):
        """顯示空數據消息"""
        total_width = sum(self.col_widths) + len(self.headers) * 3 + 1
        message = "No data available"
        print(f"│{Formatter.pad_text(message, total_width - 2, 'center')}│")
    
    def _show_footer(self):
        """顯示表格底部"""
        total_width = sum(self.col_widths) + len(self.headers) * 3 + 1
        print("└" + "─" * (total_width - 2) + "┘")

class PaginatedTable(Table):
    """分頁表格組件"""
    
    def __init__(self, headers: List[str], data_fetcher: Callable, 
                 title: Optional[str] = None, page_size: int = 20):
        self.headers = headers
        self.data_fetcher = data_fetcher
        self.title = title
        self.page_size = page_size
        self.current_page = 0
        self.data = []  # 初始化為空
        self.col_widths = self._calculate_initial_widths()
    
    def _calculate_initial_widths(self) -> List[int]:
        """計算初始列寬"""
        widths = []
        for header in self.headers:
            header_width = 0
            for char in header:
                header_width += wcwidth.wcwidth(char) or 1
            widths.append(max(8, header_width))
        return widths
    
    def display_interactive(self):
        """交互式分頁顯示"""
        while True:
            # 獲取當前頁數據
            result = self.data_fetcher(self.current_page, self.page_size)
            
            if isinstance(result, dict):
                data = result.get("data", [])
                pagination = result.get("pagination", {})
            else:
                data = result
                pagination = {}
            
            # 更新數據和列寬
            self.data = data
            if data:
                self.col_widths = self._calculate_column_widths()
            
            # 顯示表格
            self.display()
            
            # 顯示分頁信息
            if pagination:
                current = pagination.get('current_page', self.current_page) + 1
                total = pagination.get('total_pages', 1)
                count = pagination.get('total_count', len(data))
                print(f"Page {current} of {total} (Total {count} records)")
            
            # 分頁控制
            if not data:
                print("📝 No data available")
                input("Press any key to return...")
                break
            
            actions = []
            if pagination.get("has_prev", False) or self.current_page > 0:
                actions.append("P-Previous")
            if pagination.get("has_next", False):
                actions.append("N-Next")
            actions.append("Q-Quit")
            
            if len(actions) > 1:
                action = input(f"{' | '.join(actions)}: ").upper()
                if action == "N" and pagination.get("has_next", False):
                    self.current_page += 1
                elif action == "P" and (pagination.get("has_prev", False) or self.current_page > 0):
                    self.current_page = max(0, self.current_page - 1)
                elif action == "Q":
                    break
            else:
                input("Press any key to return...")
                break

class SimpleTable:
    """簡化表格組件"""
    
    @staticmethod
    def show_key_value_pairs(title: str, data: Dict[str, Any], 
                           formatters: Optional[Dict[str, Callable]] = None):
        """顯示鍵值對表格"""
        if not data:
            print(f"\n{title}: No data available")
            return
        
        print(f"\n{title}:")
        print("─" * 40)
        
        for key, value in data.items():
            # 應用格式化器
            if formatters and key in formatters:
                formatted_value = formatters[key](value)
            else:
                formatted_value = str(value)
            
            # 計算鍵的顯示寬度
            key_width = 0
            for char in key:
                key_width += wcwidth.wcwidth(char) or 1
            
            # 對齊顯示
            padding = max(0, 15 - key_width)
            print(f"{key}{' ' * padding}: {formatted_value}")
        
        print("─" * 40)
    
    @staticmethod
    def show_list(title: str, items: List[str], numbered: bool = True):
        """顯示列表"""
        if not items:
            print(f"\n{title}: No items")
            return
        
        print(f"\n{title}:")
        for i, item in enumerate(items, 1):
            if numbered:
                print(f"  {i}. {item}")
            else:
                print(f"  • {item}")

class StatusTable:
    """狀態表格組件"""
    
    @staticmethod
    def show_status_grid(title: str, status_data: Dict[str, Dict[str, Any]]):
        """顯示狀態網格"""
        print(f"\n{title}")
        print("═" * 50)
        
        for category, data in status_data.items():
            print(f"\n📊 {category}")
            print("─" * 30)
            
            for key, value in data.items():
                # 根據值類型選擇顯示方式
                if isinstance(value, bool):
                    status = "✓" if value else "✗"
                    print(f"  {key}: {status}")
                elif isinstance(value, (int, float)):
                    print(f"  {key}: {value:,}")
                else:
                    print(f"  {key}: {value}")
        
        print("═" * 50)

class ComparisonTable:
    """對比表格組件"""
    
    @staticmethod
    def show_before_after(title: str, before: Dict[str, Any], 
                         after: Dict[str, Any], 
                         formatters: Optional[Dict[str, Callable]] = None):
        """顯示前後對比"""
        print(f"\n{title}")
        print("┌" + "─" * 48 + "┐")
        print("│" + Formatter.pad_text("Item", 15) + "│" +
              Formatter.pad_text("Before", 15) + "│" +
              Formatter.pad_text("After", 15) + "│")
        print("├" + "─" * 15 + "┼" + "─" * 15 + "┼" + "─" * 15 + "┤")
        
        all_keys = set(before.keys()) | set(after.keys())
        
        for key in sorted(all_keys):
            before_val = before.get(key, "")
            after_val = after.get(key, "")
            
            # 應用格式化器
            if formatters and key in formatters:
                before_str = formatters[key](before_val) if before_val else ""
                after_str = formatters[key](after_val) if after_val else ""
            else:
                before_str = str(before_val)
                after_str = str(after_val)
            
            # 截斷過長文本
            before_str = Formatter.truncate_text(before_str, 13)
            after_str = Formatter.truncate_text(after_str, 13)
            
            print("│" + Formatter.pad_text(key, 15) + "│" + 
                  Formatter.pad_text(before_str, 15) + "│" + 
                  Formatter.pad_text(after_str, 15) + "│")
        
        print("└" + "─" * 48 + "┘")