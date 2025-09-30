from typing import Optional, List, Dict
from services.member_service import MemberService
from services.payment_service import PaymentService
from services.qr_service import QRService
from services.auth_service import AuthService
from ui.components.menu import Menu, SimpleMenu
from ui.components.table import Table, PaginatedTable
from ui.components.form import QuickForm, ValidationForm
from ui.base_ui import BaseUI, StatusDisplay
from models.member import Member
from models.card import Card
from utils.formatters import Formatter
from utils.validators import Validator
from utils.logger import ui_logger
from decimal import Decimal

class MemberUI:
    """會員用戶界面"""
    
    def __init__(self, auth_service: AuthService):
        self.member_service = MemberService()
        self.payment_service = PaymentService()
        self.qr_service = QRService()
        self.auth_service = auth_service
        
        # 設定 auth_service
        self.member_service.set_auth_service(auth_service)
        self.payment_service.set_auth_service(auth_service)
        self.qr_service.set_auth_service(auth_service)
        
        # 從 auth_service 取得資訊
        profile = auth_service.get_current_user()
        self.current_member_id = profile.get('member_id') if profile else None
        self.current_member_name = profile.get('name') if profile else None
        self.current_member: Optional[Member] = None
    
    def start(self):
        """啟動會員界面"""
        try:
            # 直接顯示主菜單（已在 main.py 完成登入）
            self._show_main_menu()
            
        except KeyboardInterrupt:
            print("\n▸ Goodbye!")
        except Exception as e:
            BaseUI.show_error(f"System error: {e}")
        finally:
            if self.current_member_id:
                ui_logger.log_logout("member")
    
    def _show_main_menu(self):
        """顯示主菜單"""
        options = [
            "View My Cards",
            "Generate Payment QR Code",
            "Recharge Card",
            "View Transaction History",
            "Bind New Card",
            "View Points & Level",
            "Exit System"
        ]
        
        handlers = [
            self._show_my_cards,
            self._generate_qr,
            self._recharge_card,
            self._view_transactions,
            self._bind_new_card,
            self._view_points_level,
            lambda: False  # 退出
        ]
        
        menu = Menu(f"MPS Member System - {self.current_member_name}", options, handlers)
        menu.run()
    
    def _show_my_cards(self):
        """顯示我的卡片"""
        try:
            BaseUI.show_loading("Getting card information...")
            cards = self.member_service.get_member_cards(self.current_member_id)
            
            if not cards:
                BaseUI.show_info("You don't have any cards yet")
                BaseUI.pause()
                return
            
            # 準備表格數據
            headers = ["Card No", "Type", "Balance", "Points", "Level", "Status"]
            data = []
            
            for card in cards:
                data.append({
                    "Card No": card.card_no or "",
                    "Type": card.get_card_type_display(),
                    "Balance": Formatter.format_currency(card.balance),
                    "Points": Formatter.format_points(card.points or 0),
                    "Level": card.get_level_display(),
                    "Status": card.get_status_display()
                })
            
            BaseUI.clear_screen()
            table = Table(headers, data, "My Cards")
            table.display()
            
            # 顯示統計信息
            total_balance = sum(card.balance or 0 for card in cards)
            total_points = sum(card.points or 0 for card in cards)
            active_count = len([card for card in cards if card.is_active()])
            
            print(f"\n📊 Statistics:")
            print(f"   Total Cards: {len(cards)} cards")
            print(f"   Active Cards: {active_count} cards")
            print(f"   Total Balance: {Formatter.format_currency(total_balance)}")
            print(f"   Total Points: {Formatter.format_points(total_points)}")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Query failed: {e}")
            BaseUI.pause()
    
    def _generate_qr(self):
        """生成付款 QR 碼"""
        try:
            # 獲取可用卡片
            cards = self.member_service.get_active_cards(self.current_member_id)
            
            if not cards:
                BaseUI.show_error("No active cards available")
                BaseUI.pause()
                return
            
            BaseUI.clear_screen()
            BaseUI.show_header("Generate Payment QR Code")
            
            # 選擇卡片
            print("Please select card to generate QR code:")
            card_options = [card.display_info() for card in cards]
            choice = SimpleMenu.show_options("Available Cards", card_options)
            
            selected_card = cards[choice - 1]
            
            # 生成 QR 碼
            BaseUI.show_loading("Generating QR code...")
            qr_result = self.qr_service.rotate_qr(selected_card.id)
            
            BaseUI.clear_screen()
            
            # 顯示卡片信息
            StatusDisplay.show_card_info({
                "card_no": selected_card.card_no,
                "card_type": selected_card.get_card_type_display(),
                "balance": selected_card.balance,
                "points": selected_card.points,
                "level": selected_card.level,
                "status": selected_card.status
            })
            
            print()
            
            # 顯示 QR 碼信息
            StatusDisplay.show_qr_code(qr_result)
            
            ui_logger.log_user_action("Generate QR Code", {
                "card_id": selected_card.id,
                "card_no": selected_card.card_no
            })
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"QR code generation failed: {e}")
            BaseUI.pause()
    
    def _recharge_card(self):
        """充值卡片"""
        try:
            # 獲取可充值卡片
            cards = self.member_service.get_rechargeable_cards(self.current_member_id)
            
            if not cards:
                BaseUI.show_error("No rechargeable cards available", "Only prepaid and corporate cards support recharge")
                BaseUI.pause()
                return
            
            BaseUI.clear_screen()
            BaseUI.show_header("Card Recharge")
            
            # 選擇卡片
            print("Please select card to recharge:")
            card_options = [card.display_info() for card in cards]
            choice = SimpleMenu.show_options("Rechargeable Cards", card_options)
            
            selected_card = cards[choice - 1]
            
            # 充值表單
            print(f"\nSelected Card: {selected_card.display_info()}")
            
            # 獲取充值金額
            amount = QuickForm.get_amount("Please enter recharge amount", 0.01, 50000)
            
            # 選擇支付方式
            payment_methods = self.payment_service.get_payment_methods()
            method_options = [method["name"] for method in payment_methods]
            method_choice = SimpleMenu.show_options("Payment Method", method_options)
            selected_method = payment_methods[method_choice - 1]["code"]
            
            # 確認充值
            print(f"\nRecharge Information Confirmation:")
            print(f"Card: {selected_card.card_no}")
            print(f"Amount: {Formatter.format_currency(amount)}")
            print(f"Payment Method: {payment_methods[method_choice - 1]['name']}")
            
            if not QuickForm.get_confirmation("Confirm recharge?"):
                BaseUI.show_info("Recharge cancelled")
                BaseUI.pause()
                return
            
            # 執行充值
            BaseUI.show_loading("Processing recharge...")
            result = self.payment_service.recharge_card(
                selected_card.id,
                Decimal(str(amount)),
                selected_method
            )
            
            BaseUI.clear_screen()
            
            # 顯示充值結果
            StatusDisplay.show_transaction_result(True, {
                "Transaction No": result["tx_no"],
                "Recharge Amount": Formatter.format_currency(result["amount"]),
                "Payment Method": payment_methods[method_choice - 1]["name"],
                "Processing Time": Formatter.format_datetime(result.get("created_at"))
            })
            
            ui_logger.log_transaction("Recharge", amount, result["tx_no"])
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Recharge failed: {e}")
            BaseUI.pause()
    
    def _view_transactions(self):
        """查看交易記錄"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Transaction History Query")
            
            # 創建分頁表格
            headers = ["Transaction No", "Type", "Amount", "Status", "Time"]
            
            def fetch_transactions(page: int, page_size: int):
                return self.member_service.get_member_transactions(
                    self.current_member_id, 
                    page_size, 
                    page * page_size
                )
            
            paginated_table = PaginatedTable(headers, fetch_transactions, "My Transaction History")
            
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
            
            # 重新包裝數據獲取函數
            def wrapped_fetch_transactions(page: int, page_size: int):
                raw_data = fetch_transactions(page, page_size)
                return format_transaction_data(raw_data)
            
            paginated_table.data_fetcher = wrapped_fetch_transactions
            paginated_table.display_interactive()
            
        except Exception as e:
            BaseUI.show_error(f"Query failed: {e}")
            BaseUI.pause()
    
    def _bind_new_card(self):
        """綁定新卡片"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Bind New Card")
            
            # 輸入卡片 ID
            card_id = QuickForm.get_text("Please enter Card ID", True, Validator.validate_card_id,
                                       "Please enter valid UUID format Card ID")
            
            # 選擇綁定角色
            roles = ["member", "viewer"]
            role_names = ["Member (Can use card)", "Viewer (View info only)"]
            role_choice = SimpleMenu.show_options("Binding Role", role_names)
            selected_role = roles[role_choice - 1]
            
            # 輸入綁定密碼（如果需要）
            binding_password = input("Enter binding password (optional, if card has password): ").strip()
            if not binding_password:
                binding_password = None
            
            # 確認綁定
            print(f"\nBinding Information Confirmation:")
            print(f"Card ID: {card_id}")
            print(f"Binding Role: {role_names[role_choice - 1]}")
            print(f"Binding Password: {'Set' if binding_password else 'Not Set'}")
            
            if not QuickForm.get_confirmation("Confirm binding?"):
                BaseUI.show_info("Binding cancelled")
                BaseUI.pause()
                return
            
            # 執行綁定
            BaseUI.show_loading("Binding card...")
            result = self.member_service.bind_card(
                card_id,
                self.current_member_id,
                selected_role,
                binding_password
            )
            
            if result:
                BaseUI.show_success("Card bound successfully!")
                ui_logger.log_user_action("Bind Card", {
                    "card_id": card_id,
                    "role": selected_role
                })
            else:
                BaseUI.show_error("Card binding failed")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Binding failed: {e}")
            BaseUI.pause()
    
    def _view_points_level(self):
        """查看積分等級"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Points & Level Information")
            
            cards = self.member_service.get_member_cards(self.current_member_id)
            
            if not cards:
                BaseUI.show_info("You don't have any cards yet")
                BaseUI.pause()
                return
            
            # 顯示每張卡片的積分等級信息
            for i, card in enumerate(cards, 1):
                print(f"\n📱 Card {i}: {card.card_no}")
                print("─" * 40)
                
                level_info = {
                    "Card Type": card.get_card_type_display(),
                    "Current Points": Formatter.format_points(card.points or 0),
                    "Current Level": card.get_level_display(),
                    "Current Discount": card.get_discount_display(),
                    "Card Status": card.get_status_display()
                }
                
                for key, value in level_info.items():
                    print(f"  {key}: {value}")
                
                # 顯示升級信息
                if card.card_type in ['standard', 'prepaid']:
                    self._show_upgrade_info(card.points or 0)
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Query failed: {e}")
            BaseUI.pause()
    
    def _show_upgrade_info(self, current_points: int):
        """顯示升級信息"""
        from config.constants import MEMBERSHIP_LEVELS
        
        current_level = 0
        next_level = None
        
        # 確定當前等級
        for level, info in MEMBERSHIP_LEVELS.items():
            if (current_points >= info["min_points"] and 
                (info["max_points"] is None or current_points <= info["max_points"])):
                current_level = level
                break
        
        # 找到下一等級
        for level in sorted(MEMBERSHIP_LEVELS.keys()):
            if level > current_level:
                next_level = level
                break
        
        if next_level is not None:
            next_info = MEMBERSHIP_LEVELS[next_level]
            points_needed = next_info["min_points"] - current_points
            
            print(f"  Upgrade Information:")
            print(f"    Next Level: {next_info['name']}")
            print(f"    Points Needed: {points_needed:,} points")
            print(f"    Discount After Upgrade: {Formatter.format_discount(next_info['discount'])}")
        else:
            print(f"  🎉 You have reached the highest level!")
    
    def _select_card(self, cards: List[Card], title: str = "Select Card") -> Optional[Card]:
        """選擇卡片的通用方法"""
        if not cards:
            return None
        
        print(f"\n{title}:")
        for i, card in enumerate(cards, 1):
            print(f"  {i}. {card.display_info()}")
        
        while True:
            try:
                choice = int(input(f"Please select (1-{len(cards)}): "))
                if 1 <= choice <= len(cards):
                    return cards[choice - 1]
                print(f"✗ Please select 1-{len(cards)}")
            except ValueError:
                print("✗ Please enter a valid number")
            except KeyboardInterrupt:
                return None