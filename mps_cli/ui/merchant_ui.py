from typing import Optional, Dict, List
from services.merchant_service import MerchantService
from services.payment_service import PaymentService
from services.qr_service import QRService
from ui.components.menu import Menu, SimpleMenu
from ui.components.table import Table, PaginatedTable
from ui.components.form import QuickForm
from ui.base_ui import BaseUI, StatusDisplay
from models.transaction import Merchant
from utils.formatters import Formatter
from utils.validators import Validator
from utils.logger import ui_logger
from decimal import Decimal
from datetime import datetime

class MerchantUI:
    """商戶用戶界面"""
    
    def __init__(self):
        self.merchant_service = MerchantService()
        self.payment_service = PaymentService()
        self.qr_service = QRService()
        self.current_merchant: Optional[Merchant] = None
        self.current_merchant_code: Optional[str] = None
        self.current_merchant_name: Optional[str] = None
        self.current_operator: Optional[str] = None
    
    def start(self):
        """啟動商戶界面"""
        try:
            # 商戶登入
            if not self._merchant_login():
                return
            
            # 主菜單
            self._show_main_menu()
            
        except KeyboardInterrupt:
            print("\n👋 再見！")
        except Exception as e:
            BaseUI.show_error(f"系統錯誤: {e}")
        finally:
            if self.current_merchant_code:
                ui_logger.log_logout("merchant")
    
    def _merchant_login(self) -> bool:
        """商戶登入流程"""
        BaseUI.clear_screen()
        BaseUI.show_header("商戶 POS 登入")
        
        print("請輸入商戶代碼進行登入")
        merchant_code = input("商戶代碼: ").strip().upper()
        
        if not merchant_code:
            BaseUI.show_error("請輸入商戶代碼")
            BaseUI.pause()
            return False
        
        # 輸入操作員名稱
        operator = input("操作員姓名 (可選): ").strip()
        
        try:
            merchant = self.merchant_service.validate_merchant_login(merchant_code)
            
            if not merchant:
                BaseUI.show_error("商戶代碼不存在或已停用")
                BaseUI.pause()
                return False
            
            self.current_merchant = merchant
            self.current_merchant_code = merchant_code
            self.current_merchant_name = merchant.name
            self.current_operator = operator or "未知操作員"
            
            ui_logger.log_login("merchant", merchant_code)
            
            BaseUI.show_success(f"登入成功！商戶: {merchant.name}")
            if operator:
                print(f"操作員: {operator}")
            BaseUI.pause()
            return True
            
        except Exception as e:
            BaseUI.show_error(f"登入失敗: {e}")
            BaseUI.pause()
            return False
    
    def _show_main_menu(self):
        """顯示主菜單"""
        options = [
            "掃碼收款",
            "退款處理",
            "查看今日交易",
            "查看交易記錄", 
            "查看商戶信息",
            "退出系統"
        ]
        
        handlers = [
            self._scan_and_charge,
            self._process_refund,
            self._view_today_transactions,
            self._view_transaction_history,
            self._view_merchant_info,
            lambda: False  # 退出
        ]
        
        menu = Menu(f"MPS 商戶 POS - {self.current_merchant_name}", options, handlers)
        menu.run()
    
    def _scan_and_charge(self):
        """掃碼收款流程"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("掃碼收款")
            
            print(f"商戶: {self.current_merchant_name}")
            print(f"操作員: {self.current_operator}")
            print("─" * 40)
            
            # Step 1: 獲取 QR 碼
            qr_plain = QuickForm.get_qr_input("請掃描客戶 QR 碼 (或手動輸入)")
            
            # Step 2: 驗證 QR 碼（可選，提前驗證用戶體驗更好）
            try:
                BaseUI.show_loading("正在驗證 QR 碼...")
                card_id = self.qr_service.validate_qr(qr_plain)
                BaseUI.show_success(f"QR 碼有效，卡片 ID: {card_id[:8]}...")
            except Exception as e:
                BaseUI.show_error(f"QR 碼無效: {e}")
                BaseUI.pause()
                return
            
            # Step 3: 輸入收款金額
            amount = QuickForm.get_amount("請輸入收款金額", 0.01, 50000)
            
            # Step 4: 顯示收款確認信息
            print(f"\n┌─────────────────────────────────────┐")
            print(f"│            收款信息確認             │")
            print(f"├─────────────────────────────────────┤")
            print(f"│ 商戶: {Formatter.pad_text(self.current_merchant_name, 25, 'left')} │")
            print(f"│ 操作員: {Formatter.pad_text(self.current_operator, 23, 'left')} │")
            print(f"│ 金額: {Formatter.pad_text(Formatter.format_currency(amount), 25, 'left')} │")
            print(f"│ 時間: {Formatter.pad_text(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 21, 'left')} │")
            print(f"└─────────────────────────────────────┘")
            
            if not QuickForm.get_confirmation("確認收款？"):
                BaseUI.show_info("收款已取消")
                BaseUI.pause()
                return
            
            # Step 5: 執行收款
            BaseUI.show_loading("正在處理收款...")
            
            result = self.payment_service.charge_by_qr(
                self.current_merchant_code,
                qr_plain,
                Decimal(str(amount)),
                tag={"source": "pos_cli", "operator": self.current_operator}
            )
            
            # Step 6: 顯示收款結果
            BaseUI.clear_screen()
            self._show_payment_success(result, amount)
            
            ui_logger.log_transaction("支付", amount, result["tx_no"])
            
        except Exception as e:
            BaseUI.clear_screen()
            self._handle_payment_error(e)
        
        BaseUI.pause()
    
    def _show_payment_success(self, result: Dict, original_amount: float):
        """顯示收款成功界面"""
        print("┌─────────────────────────────────────┐")
        print("│              收款成功               │")
        print("├─────────────────────────────────────┤")
        print(f"│ 交易號: {Formatter.pad_text(result['tx_no'], 23, 'left')} │")
        print(f"│ 原金額: {Formatter.pad_text(Formatter.format_currency(original_amount), 23, 'left')} │")
        print(f"│ 折扣率: {Formatter.pad_text(Formatter.format_percentage(result['discount']), 23, 'left')} │")
        print(f"│ 實收金額: {Formatter.pad_text(Formatter.format_currency(result['final_amount']), 21, 'left')} │")
        print(f"│ 時間: {Formatter.pad_text(datetime.now().strftime('%H:%M:%S'), 27, 'left')} │")
        print("├─────────────────────────────────────┤")
        print("│ 🎉 收款成功，感謝您的使用！         │")
        print("└─────────────────────────────────────┘")
    
    def _handle_payment_error(self, error: Exception):
        """處理支付錯誤"""
        error_str = str(error)
        
        print("┌─────────────────────────────────────┐")
        print("│              收款失敗               │")
        print("├─────────────────────────────────────┤")
        
        if "INSUFFICIENT_BALANCE" in error_str:
            print("│ ❌ 客戶餘額不足                    │")
            print("│ 💡 建議：提醒客戶充值或使用其他卡片 │")
        elif "QR_EXPIRED_OR_INVALID" in error_str:
            print("│ ❌ QR 碼已過期或無效               │")
            print("│ 💡 建議：請客戶重新生成付款碼       │")
        elif "NOT_MERCHANT_USER" in error_str:
            print("│ ❌ 您沒有此商戶的操作權限           │")
            print("│ 💡 建議：聯繫管理員檢查權限設置     │")
        else:
            error_display = Formatter.truncate_text(error_str, 25)
            print(f"│ ❌ 系統錯誤: {Formatter.pad_text(error_display, 25, 'left')} │")
            print("│ 💡 建議：稍後重試或聯繫技術支持     │")
        
        print("└─────────────────────────────────────┘")
    
    def _process_refund(self):
        """退款處理流程"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("退款處理")
            
            # 輸入原交易號
            original_tx_no = QuickForm.get_text("請輸入原交易號", True, 
                                              Validator.validate_tx_no,
                                              "格式：PAY/REF/RCG + 10位數字")
            
            # 查詢原交易詳情
            BaseUI.show_loading("正在查詢原交易...")
            
            try:
                original_tx = self.payment_service.get_transaction_detail(original_tx_no)
                
                if not original_tx:
                    BaseUI.show_error("原交易不存在")
                    BaseUI.pause()
                    return
                
                print(f"\n原交易信息:")
                print(f"交易號: {original_tx.tx_no}")
                print(f"類型: {original_tx.get_tx_type_display()}")
                print(f"金額: {Formatter.format_currency(original_tx.final_amount)}")
                print(f"狀態: {original_tx.get_status_display()}")
                print(f"時間: {original_tx.format_datetime('created_at')}")
                
            except Exception as e:
                BaseUI.show_error(f"查詢原交易失敗: {e}")
                BaseUI.pause()
                return
            
            # 輸入退款金額
            max_refund = original_tx.final_amount or 0
            refund_amount = QuickForm.get_amount("請輸入退款金額", 0.01, max_refund)
            
            # 驗證退款金額
            validation = self.payment_service.validate_refund_amount(
                original_tx_no, Decimal(str(refund_amount))
            )
            
            if not validation["valid"]:
                BaseUI.show_error(validation["error"])
                BaseUI.pause()
                return
            
            # 退款原因
            reason = input("請輸入退款原因 (可選): ").strip()
            
            # 確認退款
            print(f"\n退款信息確認:")
            print(f"原交易號: {original_tx_no}")
            print(f"退款金額: {Formatter.format_currency(refund_amount)}")
            print(f"退款原因: {reason or '無'}")
            print(f"可退餘額: {Formatter.format_currency(validation['remaining_amount'])}")
            
            if not QuickForm.get_confirmation("確認退款？"):
                BaseUI.show_info("退款已取消")
                BaseUI.pause()
                return
            
            # 執行退款
            BaseUI.show_loading("正在處理退款...")
            result = self.payment_service.refund_transaction(
                self.current_merchant_code,
                original_tx_no,
                Decimal(str(refund_amount)),
                reason
            )
            
            BaseUI.clear_screen()
            
            # 顯示退款結果
            StatusDisplay.show_transaction_result(True, {
                "退款單號": result["refund_tx_no"],
                "原交易號": result["original_tx_no"],
                "退款金額": Formatter.format_currency(result["refunded_amount"]),
                "處理時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            ui_logger.log_transaction("退款", refund_amount, result["refund_tx_no"])
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"退款失敗: {e}")
            BaseUI.pause()
    
    def _view_today_transactions(self):
        """查看今日交易"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("今日交易統計")
            
            BaseUI.show_loading("正在獲取今日交易數據...")
            summary = self.merchant_service.get_today_transactions(self.current_merchant.id)
            
            # 顯示統計信息
            print("┌─────────────────────────────────────┐")
            print("│            今日交易統計             │")
            print("├─────────────────────────────────────┤")
            print(f"│ 日期: {Formatter.pad_text(summary['date'], 27, 'left')} │")
            print(f"│ 總交易數: {summary['total_count']:>25} 筆 │")
            print(f"│ 支付交易: {summary['payment_count']:>25} 筆 │")
            print(f"│ 退款交易: {summary['refund_count']:>25} 筆 │")
            print("├─────────────────────────────────────┤")
            print(f"│ 支付金額: {Formatter.pad_text(Formatter.format_currency(summary['payment_amount']), 25, 'right')} │")
            print(f"│ 退款金額: {Formatter.pad_text(Formatter.format_currency(summary['refund_amount']), 25, 'right')} │")
            print(f"│ 淨收入: {Formatter.pad_text(Formatter.format_currency(summary['net_amount']), 27, 'right')} │")
            print("└─────────────────────────────────────┘")
            
            # 詢問是否查看詳細列表
            if summary['total_count'] > 0:
                show_detail = QuickForm.get_confirmation("是否查看詳細交易列表？", False)
                if show_detail:
                    self._show_transaction_list(summary['transactions'])
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"查詢失敗: {e}")
            BaseUI.pause()
    
    def _view_transaction_history(self):
        """查看交易記錄"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("交易記錄查詢")
            
            # 創建分頁表格
            headers = ["交易號", "類型", "金額", "狀態", "時間"]
            
            def fetch_transactions(page: int, page_size: int):
                return self.merchant_service.get_merchant_transactions(
                    self.current_merchant.id, 
                    page_size, 
                    page * page_size
                )
            
            # 轉換數據格式
            def format_transaction_data(tx_data):
                transactions = tx_data.get("data", [])
                formatted_data = []
                
                for tx in transactions:
                    formatted_data.append({
                        "交易號": tx.tx_no or "",
                        "類型": tx.get_tx_type_display(),
                        "金額": Formatter.format_currency(tx.final_amount),
                        "狀態": tx.get_status_display(),
                        "時間": tx.format_datetime("created_at")
                    })
                
                return {
                    "data": formatted_data,
                    "pagination": tx_data.get("pagination", {})
                }
            
            def wrapped_fetch_transactions(page: int, page_size: int):
                raw_data = fetch_transactions(page, page_size)
                return format_transaction_data(raw_data)
            
            paginated_table = PaginatedTable(headers, wrapped_fetch_transactions, "交易記錄")
            paginated_table.display_interactive()
            
        except Exception as e:
            BaseUI.show_error(f"查詢失敗: {e}")
            BaseUI.pause()
    
    def _view_merchant_info(self):
        """查看商戶信息"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("商戶信息")
            
            BaseUI.show_loading("正在獲取商戶信息...")
            summary = self.merchant_service.get_merchant_summary(self.current_merchant.id)
            
            if not summary:
                BaseUI.show_error("無法獲取商戶信息")
                BaseUI.pause()
                return
            
            merchant = summary["merchant"]
            today_stats = summary["today"]
            
            # 顯示基本信息
            print("📋 基本信息:")
            print("─" * 30)
            print(f"  商戶代碼: {merchant.code}")
            print(f"  商戶名稱: {merchant.name}")
            print(f"  聯繫方式: {merchant.contact or '未設置'}")
            print(f"  狀態: {merchant.get_status_display()}")
            print(f"  創建時間: {merchant.format_datetime('created_at')}")
            
            # 顯示今日統計
            print(f"\n📊 今日統計 ({today_stats['date']}):")
            print("─" * 30)
            print(f"  交易筆數: {today_stats['total_count']} 筆")
            print(f"  支付筆數: {today_stats['payment_count']} 筆")
            print(f"  退款筆數: {today_stats['refund_count']} 筆")
            print(f"  淨收入: {Formatter.format_currency(today_stats['net_amount'])}")
            
            # 顯示本月統計
            print(f"\n📈 本月統計:")
            print("─" * 30)
            print(f"  交易筆數: {summary.get('month_transaction_count', 0)} 筆")
            print(f"  收款金額: {Formatter.format_currency(summary.get('month_payment_amount', 0))}")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"查詢失敗: {e}")
            BaseUI.pause()
    
    def _show_transaction_list(self, transactions: List):
        """顯示交易列表"""
        if not transactions:
            BaseUI.show_info("暫無交易記錄")
            return
        
        BaseUI.clear_screen()
        
        headers = ["交易號", "類型", "金額", "狀態", "時間"]
        data = []
        
        for tx in transactions:
            data.append({
                "交易號": tx.tx_no or "",
                "類型": tx.get_tx_type_display(),
                "金額": Formatter.format_currency(tx.final_amount),
                "狀態": tx.get_status_display(),
                "時間": tx.format_time("created_at")
            })
        
        table = Table(headers, data, "詳細交易記錄")
        table.display()