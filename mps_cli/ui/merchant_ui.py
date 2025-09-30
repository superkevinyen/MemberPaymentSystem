from typing import Optional, Dict, List
from services.merchant_service import MerchantService
from services.payment_service import PaymentService
from services.qr_service import QRService
from services.auth_service import AuthService
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
    
    def __init__(self, auth_service: AuthService):
        self.merchant_service = MerchantService()
        self.payment_service = PaymentService()
        self.qr_service = QRService()
        self.auth_service = auth_service
        
        # 設定 auth_service
        self.merchant_service.set_auth_service(auth_service)
        self.payment_service.set_auth_service(auth_service)
        self.qr_service.set_auth_service(auth_service)
        
        # 從 auth_service 取得資訊
        profile = auth_service.get_current_user()
        self.current_merchant_id = profile.get('merchant_id') if profile else None
        self.current_merchant_code = profile.get('merchant_code') if profile else None
        self.current_merchant_name = profile.get('merchant_name') if profile else None
        self.current_operator = profile.get('merchant_name') if profile else None
        self.current_merchant: Optional[Merchant] = None
    
    def start(self):
        """啟動商戶界面"""
        try:
            # 直接顯示主菜單（已在 main.py 完成登入）
            self._show_main_menu()
            
        except KeyboardInterrupt:
            print("\n▸ Goodbye!")
        except Exception as e:
            BaseUI.show_error(f"System error: {e}")
        finally:
            if self.current_merchant_id:
                ui_logger.log_logout("merchant")
    
    def _show_main_menu(self):
        """顯示主菜單"""
        options = [
            "Scan & Charge",
            "Process Refund",
            "View Today's Transactions",
            "View Transaction History",
            "View Merchant Info",
            "Exit System"
        ]
        
        handlers = [
            self._scan_and_charge,
            self._process_refund,
            self._view_today_transactions,
            self._view_transaction_history,
            self._view_merchant_info,
            lambda: False  # 退出
        ]
        
        menu = Menu(f"MPS Merchant POS - {self.current_merchant_name}", options, handlers)
        menu.run()
    
    def _scan_and_charge(self):
        """掃碼收款流程"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Scan & Charge")
            
            print(f"Merchant: {self.current_merchant_name}")
            print(f"Operator: {self.current_operator}")
            print("─" * 40)
            
            # Step 1: 獲取 QR 碼
            qr_plain = QuickForm.get_qr_input("Please scan customer QR code (or enter manually)")
            
            # Step 2: 驗證 QR 碼（可選，提前驗證用戶體驗更好）
            try:
                BaseUI.show_loading("Validating QR code...")
                card_id = self.qr_service.validate_qr(qr_plain)
                BaseUI.show_success(f"QR code valid, Card ID: {card_id[:8]}...")
            except Exception as e:
                BaseUI.show_error(f"Invalid QR code: {e}")
                BaseUI.pause()
                return
            
            # Step 3: 輸入收款金額
            amount = QuickForm.get_amount("Please enter charge amount", 0.01, 50000)
            
            # Step 4: 顯示收款確認信息
            print(f"\n┌─────────────────────────────────────┐")
            print(f"│         Charge Info Confirmation    │")
            print(f"├─────────────────────────────────────┤")
            print(f"│ Merchant: {Formatter.pad_text(self.current_merchant_name, 23, 'left')} │")
            print(f"│ Operator: {Formatter.pad_text(self.current_operator, 23, 'left')} │")
            print(f"│ Amount: {Formatter.pad_text(Formatter.format_currency(amount), 25, 'left')} │")
            print(f"│ Time: {Formatter.pad_text(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 27, 'left')} │")
            print(f"└─────────────────────────────────────┘")
            
            if not QuickForm.get_confirmation("Confirm charge?"):
                BaseUI.show_info("Charge cancelled")
                BaseUI.pause()
                return
            
            # Step 5: 執行收款
            BaseUI.show_loading("Processing charge...")
            
            result = self.payment_service.charge_by_qr(
                self.current_merchant_code,
                qr_plain,
                Decimal(str(amount)),
                tag={"source": "pos_cli", "operator": self.current_operator}
            )
            
            # Step 6: 顯示收款結果
            BaseUI.clear_screen()
            self._show_payment_success(result, amount)
            
            ui_logger.log_transaction("Payment", amount, result["tx_no"])
            
        except Exception as e:
            BaseUI.clear_screen()
            self._handle_payment_error(e)
        
        BaseUI.pause()
    
    def _show_payment_success(self, result: Dict, original_amount: float):
        """顯示收款成功界面"""
        print("┌─────────────────────────────────────┐")
        print("│            Charge Successful        │")
        print("├─────────────────────────────────────┤")
        print(f"│ Transaction: {Formatter.pad_text(result['tx_no'], 21, 'left')} │")
        print(f"│ Original: {Formatter.pad_text(Formatter.format_currency(original_amount), 25, 'left')} │")
        print(f"│ Discount: {Formatter.pad_text(Formatter.format_percentage(result['discount']), 25, 'left')} │")
        print(f"│ Final Amount: {Formatter.pad_text(Formatter.format_currency(result['final_amount']), 19, 'left')} │")
        print(f"│ Time: {Formatter.pad_text(datetime.now().strftime('%H:%M:%S'), 27, 'left')} │")
        print("├─────────────────────────────────────┤")
        print("│ 🎉 Charge successful, thank you!    │")
        print("└─────────────────────────────────────┘")
    
    def _handle_payment_error(self, error: Exception):
        """處理支付錯誤"""
        error_str = str(error)
        
        print("┌─────────────────────────────────────┐")
        print("│             Charge Failed           │")
        print("├─────────────────────────────────────┤")
        
        if "INSUFFICIENT_BALANCE" in error_str:
            print("│ ✗ Customer balance insufficient     │")
            print("│ ▸ Suggest: Ask customer to recharge │")
        elif "QR_EXPIRED_OR_INVALID" in error_str:
            print("│ ✗ QR code expired or invalid       │")
            print("│ ▸ Suggest: Ask customer to regenerate │")
        elif "NOT_MERCHANT_USER" in error_str:
            print("│ ✗ No permission for this merchant  │")
            print("│ ▸ Suggest: Contact admin for access │")
        else:
            error_display = Formatter.truncate_text(error_str, 25)
            print(f"│ ✗ System error: {Formatter.pad_text(error_display, 23, 'left')} │")
            print("│ ▸ Suggest: Retry or contact support │")
        
        print("└─────────────────────────────────────┘")
    
    def _process_refund(self):
        """退款處理流程"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Process Refund")
            
            # 輸入原交易號
            original_tx_no = QuickForm.get_text("Please enter original transaction number", True,
                                              Validator.validate_tx_no,
                                              "Format: PAY/REF/RCG + 10 digits")
            
            # 查詢原交易詳情
            BaseUI.show_loading("Querying original transaction...")
            
            try:
                original_tx = self.payment_service.get_transaction_detail(original_tx_no)
                
                if not original_tx:
                    BaseUI.show_error("Original transaction does not exist")
                    BaseUI.pause()
                    return
                
                print(f"\nOriginal Transaction Information:")
                print(f"Transaction No: {original_tx.tx_no}")
                print(f"Type: {original_tx.get_tx_type_display()}")
                print(f"Amount: {Formatter.format_currency(original_tx.final_amount)}")
                print(f"Status: {original_tx.get_status_display()}")
                print(f"Time: {original_tx.format_datetime('created_at')}")
                
            except Exception as e:
                BaseUI.show_error(f"Failed to query original transaction: {e}")
                BaseUI.pause()
                return
            
            # 輸入退款金額
            max_refund = original_tx.final_amount or 0
            refund_amount = QuickForm.get_amount("Please enter refund amount", 0.01, max_refund)
            
            # 驗證退款金額
            validation = self.payment_service.validate_refund_amount(
                original_tx_no, Decimal(str(refund_amount))
            )
            
            if not validation["valid"]:
                BaseUI.show_error(validation["error"])
                BaseUI.pause()
                return
            
            # 退款原因
            reason = input("Enter refund reason (optional): ").strip()
            
            # 確認退款
            print(f"\nRefund Information Confirmation:")
            print(f"Original Transaction: {original_tx_no}")
            print(f"Refund Amount: {Formatter.format_currency(refund_amount)}")
            print(f"Refund Reason: {reason or 'None'}")
            print(f"Remaining Refundable: {Formatter.format_currency(validation['remaining_amount'])}")
            
            if not QuickForm.get_confirmation("Confirm refund?"):
                BaseUI.show_info("Refund cancelled")
                BaseUI.pause()
                return
            
            # 執行退款
            BaseUI.show_loading("Processing refund...")
            result = self.payment_service.refund_transaction(
                self.current_merchant_code,
                original_tx_no,
                Decimal(str(refund_amount)),
                reason
            )
            
            BaseUI.clear_screen()
            
            # 顯示退款結果
            StatusDisplay.show_transaction_result(True, {
                "Refund No": result["refund_tx_no"],
                "Original Transaction": result["original_tx_no"],
                "Refund Amount": Formatter.format_currency(result["refunded_amount"]),
                "Processing Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            ui_logger.log_transaction("Refund", refund_amount, result["refund_tx_no"])
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Refund failed: {e}")
            BaseUI.pause()
    
    def _view_today_transactions(self):
        """查看今日交易"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Today's Transaction Statistics")
            
            BaseUI.show_loading("Getting today's transaction data...")
            summary = self.merchant_service.get_today_transactions(self.current_merchant.id)
            
            # 顯示統計信息
            print("┌─────────────────────────────────────┐")
            print("│        Today's Transaction Stats    │")
            print("├─────────────────────────────────────┤")
            print(f"│ Date: {Formatter.pad_text(summary['date'], 29, 'left')} │")
            print(f"│ Total Transactions: {summary['total_count']:>17} │")
            print(f"│ Payment Transactions: {summary['payment_count']:>15} │")
            print(f"│ Refund Transactions: {summary['refund_count']:>16} │")
            print("├─────────────────────────────────────┤")
            print(f"│ Payment Amount: {Formatter.pad_text(Formatter.format_currency(summary['payment_amount']), 19, 'right')} │")
            print(f"│ Refund Amount: {Formatter.pad_text(Formatter.format_currency(summary['refund_amount']), 20, 'right')} │")
            print(f"│ Net Income: {Formatter.pad_text(Formatter.format_currency(summary['net_amount']), 23, 'right')} │")
            print("└─────────────────────────────────────┘")
            
            # 詢問是否查看詳細列表
            if summary['total_count'] > 0:
                show_detail = QuickForm.get_confirmation("View detailed transaction list?", False)
                if show_detail:
                    self._show_transaction_list(summary['transactions'])
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Query failed: {e}")
            BaseUI.pause()
    
    def _view_transaction_history(self):
        """查看交易記錄"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Transaction History Query")
            
            # 創建分頁表格
            headers = ["Transaction No", "Type", "Amount", "Status", "Time"]
            
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
                        "Transaction No": tx.tx_no or "",
                        "Type": tx.get_tx_type_display(),
                        "Amount": Formatter.format_currency(tx.final_amount),
                        "Status": tx.get_status_display(),
                        "Time": tx.format_datetime("created_at")
                    })
                
                return {
                    "data": formatted_data,
                    "pagination": tx_data.get("pagination", {})
                }
            
            def wrapped_fetch_transactions(page: int, page_size: int):
                raw_data = fetch_transactions(page, page_size)
                return format_transaction_data(raw_data)
            
            paginated_table = PaginatedTable(headers, wrapped_fetch_transactions, "Transaction History")
            paginated_table.display_interactive()
            
        except Exception as e:
            BaseUI.show_error(f"Query failed: {e}")
            BaseUI.pause()
    
    def _view_merchant_info(self):
        """查看商戶信息"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Merchant Information")
            
            BaseUI.show_loading("Getting merchant information...")
            summary = self.merchant_service.get_merchant_summary(self.current_merchant.id)
            
            if not summary:
                BaseUI.show_error("Unable to get merchant information")
                BaseUI.pause()
                return
            
            merchant = summary["merchant"]
            today_stats = summary["today"]
            
            # 顯示基本信息
            print("📋 Basic Information:")
            print("─" * 30)
            print(f"  Merchant Code: {merchant.code}")
            print(f"  Merchant Name: {merchant.name}")
            print(f"  Contact: {merchant.contact or 'Not Set'}")
            print(f"  Status: {merchant.get_status_display()}")
            print(f"  Created: {merchant.format_datetime('created_at')}")
            
            # 顯示今日統計
            print(f"\n📊 Today's Statistics ({today_stats['date']}):")
            print("─" * 30)
            print(f"  Total Transactions: {today_stats['total_count']}")
            print(f"  Payment Transactions: {today_stats['payment_count']}")
            print(f"  Refund Transactions: {today_stats['refund_count']}")
            print(f"  Net Income: {Formatter.format_currency(today_stats['net_amount'])}")
            
            # 顯示本月統計
            print(f"\n📈 Monthly Statistics:")
            print("─" * 30)
            print(f"  Total Transactions: {summary.get('month_transaction_count', 0)}")
            print(f"  Payment Amount: {Formatter.format_currency(summary.get('month_payment_amount', 0))}")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Query failed: {e}")
            BaseUI.pause()
    
    def _show_transaction_list(self, transactions: List):
        """顯示交易列表"""
        if not transactions:
            BaseUI.show_info("No transaction records")
            return
        
        BaseUI.clear_screen()
        
        headers = ["Transaction No", "Type", "Amount", "Status", "Time"]
        data = []
        
        for tx in transactions:
            data.append({
                "Transaction No": tx.tx_no or "",
                "Type": tx.get_tx_type_display(),
                "Amount": Formatter.format_currency(tx.final_amount),
                "Status": tx.get_status_display(),
                "Time": tx.format_time("created_at")
            })
        
        table = Table(headers, data, "Detailed Transaction Records")
        table.display()