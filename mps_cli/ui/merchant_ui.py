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
        """退款處理 - 商業版（支持多次部分退款）"""
        try:
            BaseUI.clear_screen()
            print("╔═══════════════════════════════════════════════════════════════════════════╗")
            print("║                          退款處理                                         ║")
            print("║                  （支持多次部分退款）                                     ║")
            print("╚═══════════════════════════════════════════════════════════════════════════╝")
            
            # Step 1: 輸入原交易號
            tx_no = input("\n請輸入原交易號: ").strip()
            
            if not tx_no:
                print("❌ 交易號不能為空")
                BaseUI.pause()
                return
            
            # Step 2: 查詢原交易
            BaseUI.show_loading("正在查詢交易...")
            
            try:
                original_tx = self.payment_service.get_transaction_detail(tx_no)
            except Exception as e:
                print(f"\n❌ 查詢交易失敗: {e}")
                print("\n💡 提示：")
                print("   • 請確認交易號是否正確")
                print("   • 只能查詢本商戶的交易")
                BaseUI.pause()
                return
            
            # Step 3: 顯示原交易信息
            BaseUI.clear_screen()
            print("╔═══════════════════════════════════════════════════════════════════════════╗")
            print("║                        原交易信息                                         ║")
            print("╠═══════════════════════════════════════════════════════════════════════════╣")
            print(f"║  交易號：    {original_tx.tx_no:<60} ║")
            print(f"║  交易類型：  {original_tx.get_tx_type_display():<60} ║")
            print(f"║  交易金額：  {Formatter.format_currency(original_tx.final_amount):<60} ║")
            print(f"║  交易狀態：  {original_tx.get_status_display():<60} ║")
            print(f"║  交易時間：  {original_tx.format_datetime('created_at'):<60} ║")
            
            # 計算剩餘可退金額
            refunded_amount = self._calculate_total_refunded(tx_no)
            remaining_amount = Decimal(str(original_tx.final_amount)) - refunded_amount
            
            print("╠═══════════════════════════════════════════════════════════════════════════╣")
            print(f"║  已退金額：  {Formatter.format_currency(refunded_amount):<60} ║")
            print(f"║  剩餘可退：  {Formatter.format_currency(remaining_amount):<60} ║")
            print("╚═══════════════════════════════════════════════════════════════════════════╝")
            
            # 檢查是否可以退款
            if original_tx.status not in ['completed', 'refunded']:
                print("\n❌ 此交易不可退款")
                print(f"   當前狀態：{original_tx.get_status_display()}")
                print("   只有已完成的交易才能退款")
                BaseUI.pause()
                return
            
            if remaining_amount <= 0:
                print("\n❌ 此交易已全額退款，無剩餘可退金額")
                BaseUI.pause()
                return
            
            # Step 4: 輸入退款金額
            print(f"\n可退款金額：{Formatter.format_currency(remaining_amount)}")
            
            while True:
                try:
                    refund_amount_str = input(f"請輸入退款金額 (0.01-{remaining_amount}): ").strip()
                    if not refund_amount_str:
                        print("❌ 金額不能為空")
                        continue
                    
                    refund_amount = Decimal(refund_amount_str)
                    
                    if refund_amount <= 0:
                        print("❌ 退款金額必須大於 0")
                        continue
                    if refund_amount > remaining_amount:
                        print(f"❌ 退款金額不能超過剩餘可退金額 {Formatter.format_currency(remaining_amount)}")
                        continue
                    
                    break
                except (ValueError, Exception):
                    print("❌ 請輸入有效的金額")
            
            # Step 5: 輸入退款原因
            print("\n退款原因（可選）：")
            reason = input("請輸入退款原因: ").strip()
            if not reason:
                reason = "客戶要求退款"
            
            # Step 6: 確認退款
            print("\n" + "═" * 79)
            print("退款信息確認")
            print("═" * 79)
            print(f"原交易號：    {tx_no}")
            print(f"原交易金額：  {Formatter.format_currency(original_tx.final_amount)}")
            print(f"已退金額：    {Formatter.format_currency(refunded_amount)}")
            print(f"本次退款：    {Formatter.format_currency(refund_amount)}")
            print(f"退款後剩餘：  {Formatter.format_currency(remaining_amount - refund_amount)}")
            print(f"退款原因：    {reason}")
            print("═" * 79)
            
            if not BaseUI.confirm("\n確認退款？"):
                print("❌ 已取消退款")
                BaseUI.pause()
                return
            
            # Step 7: 執行退款
            BaseUI.show_loading("正在處理退款...")
            
            refund_result = self.payment_service.refund_transaction(
                self.current_merchant_code,
                tx_no,
                refund_amount,
                reason
            )
            
            # Step 8: 顯示退款結果
            BaseUI.clear_screen()
            print("╔═══════════════════════════════════════════════════════════════════════════╗")
            print("║                          退款成功！                                       ║")
            print("╠═══════════════════════════════════════════════════════════════════════════╣")
            print(f"║  退款交易號：{refund_result['refund_tx_no']:<60} ║")
            print(f"║  原交易號：  {tx_no:<60} ║")
            print(f"║  退款金額：  {Formatter.format_currency(refund_amount):<60} ║")
            print(f"║  退款原因：  {reason[:50]:<60} ║")
            print(f"║  處理時間：  {Formatter.format_datetime(refund_result.get('created_at')):<60} ║")
            print("╚═══════════════════════════════════════════════════════════════════════════╝")
            
            print("\n✅ 退款已處理，金額將退回客戶卡片")
            
            # 記錄日誌
            ui_logger.log_transaction("Refund", refund_amount, refund_result['refund_tx_no'])
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"退款失敗: {e}")
            ui_logger.log_error("Process Refund", str(e))
            
            # 友好的錯誤提示
            if "REFUND_EXCEEDS_REMAINING" in str(e):
                print("\n💡 提示：退款金額超過剩餘可退金額")
                print("   此交易可能已經部分退款")
            elif "ONLY_COMPLETED_PAYMENT_REFUNDABLE" in str(e):
                print("\n💡 提示：只能退款已完成的支付交易")
            elif "NOT_AUTHORIZED" in str(e):
                print("\n💡 提示：沒有權限操作此交易")
                print("   只能退款本商戶的交易")
            
            BaseUI.pause()
    
    def _calculate_total_refunded(self, original_tx_no: str) -> Decimal:
        """計算已退款總金額"""
        try:
            # 查詢所有退款記錄
            refunds = self.payment_service.get_refund_history(original_tx_no)
            total = Decimal("0")
            for refund in refunds:
                if refund.get('status') == 'completed':
                    total += Decimal(str(refund.get('amount', 0)))
            return total
        except:
            return Decimal("0")
    
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