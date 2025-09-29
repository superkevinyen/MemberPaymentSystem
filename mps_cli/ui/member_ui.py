from typing import Optional, List, Dict
from services.member_service import MemberService
from services.payment_service import PaymentService
from services.qr_service import QRService
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
    
    def __init__(self):
        self.member_service = MemberService()
        self.payment_service = PaymentService()
        self.qr_service = QRService()
        self.current_member: Optional[Member] = None
        self.current_member_id: Optional[str] = None
        self.current_member_name: Optional[str] = None
    
    def start(self):
        """啟動會員界面"""
        try:
            # 會員登入
            if not self._member_login():
                return
            
            # 主菜單
            self._show_main_menu()
            
        except KeyboardInterrupt:
            print("\n▸ 再見！")
        except Exception as e:
            BaseUI.show_error(f"系統錯誤: {e}")
        finally:
            if self.current_member_id:
                ui_logger.log_logout("member")
    
    def _member_login(self) -> bool:
        """會員登入流程"""
        BaseUI.clear_screen()
        BaseUI.show_header("會員系統登入")
        
        print("請輸入會員 ID 或手機號進行登入")
        identifier = input("會員 ID/手機號: ").strip()
        
        if not identifier:
            BaseUI.show_error("請輸入會員 ID 或手機號")
            BaseUI.pause()
            return False
        
        try:
            member = self.member_service.validate_member_login(identifier)
            
            if not member:
                BaseUI.show_error("會員不存在或狀態異常")
                BaseUI.pause()
                return False
            
            self.current_member = member
            self.current_member_id = member.id
            self.current_member_name = member.name
            
            ui_logger.log_login("member", identifier)
            
            BaseUI.show_success(f"登入成功！歡迎 {member.name}")
            BaseUI.pause()
            return True
            
        except Exception as e:
            BaseUI.show_error(f"登入失敗: {e}")
            BaseUI.pause()
            return False
    
    def _show_main_menu(self):
        """顯示主菜單"""
        options = [
            "查看我的卡片",
            "生成付款 QR 碼", 
            "充值卡片",
            "查看交易記錄",
            "綁定新卡片",
            "查看積分等級",
            "退出系統"
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
        
        menu = Menu(f"MPS 會員系統 - {self.current_member_name}", options, handlers)
        menu.run()
    
    def _show_my_cards(self):
        """顯示我的卡片"""
        try:
            BaseUI.show_loading("正在獲取卡片信息...")
            cards = self.member_service.get_member_cards(self.current_member_id)
            
            if not cards:
                BaseUI.show_info("您還沒有任何卡片")
                BaseUI.pause()
                return
            
            # 準備表格數據
            headers = ["卡號", "類型", "餘額", "積分", "等級", "狀態"]
            data = []
            
            for card in cards:
                data.append({
                    "卡號": card.card_no or "",
                    "類型": card.get_card_type_display(),
                    "餘額": Formatter.format_currency(card.balance),
                    "積分": Formatter.format_points(card.points or 0),
                    "等級": card.get_level_display(),
                    "狀態": card.get_status_display()
                })
            
            BaseUI.clear_screen()
            table = Table(headers, data, "我的卡片")
            table.display()
            
            # 顯示統計信息
            total_balance = sum(card.balance or 0 for card in cards)
            total_points = sum(card.points or 0 for card in cards)
            active_count = len([card for card in cards if card.is_active()])
            
            print(f"\n📊 統計信息:")
            print(f"   總卡片數: {len(cards)} 張")
            print(f"   激活卡片: {active_count} 張")
            print(f"   總餘額: {Formatter.format_currency(total_balance)}")
            print(f"   總積分: {Formatter.format_points(total_points)}")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"查詢失敗: {e}")
            BaseUI.pause()
    
    def _generate_qr(self):
        """生成付款 QR 碼"""
        try:
            # 獲取可用卡片
            cards = self.member_service.get_active_cards(self.current_member_id)
            
            if not cards:
                BaseUI.show_error("沒有可用的激活卡片")
                BaseUI.pause()
                return
            
            BaseUI.clear_screen()
            BaseUI.show_header("生成付款 QR 碼")
            
            # 選擇卡片
            print("請選擇要生成 QR 碼的卡片:")
            card_options = [card.display_info() for card in cards]
            choice = SimpleMenu.show_options("可用卡片", card_options)
            
            selected_card = cards[choice - 1]
            
            # 生成 QR 碼
            BaseUI.show_loading("正在生成 QR 碼...")
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
            
            ui_logger.log_user_action("生成 QR 碼", {
                "card_id": selected_card.id,
                "card_no": selected_card.card_no
            })
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"QR 碼生成失敗: {e}")
            BaseUI.pause()
    
    def _recharge_card(self):
        """充值卡片"""
        try:
            # 獲取可充值卡片
            cards = self.member_service.get_rechargeable_cards(self.current_member_id)
            
            if not cards:
                BaseUI.show_error("沒有可充值的卡片", "只有預付卡和企業卡支持充值")
                BaseUI.pause()
                return
            
            BaseUI.clear_screen()
            BaseUI.show_header("卡片充值")
            
            # 選擇卡片
            print("請選擇要充值的卡片:")
            card_options = [card.display_info() for card in cards]
            choice = SimpleMenu.show_options("可充值卡片", card_options)
            
            selected_card = cards[choice - 1]
            
            # 充值表單
            print(f"\n選中卡片: {selected_card.display_info()}")
            
            # 獲取充值金額
            amount = QuickForm.get_amount("請輸入充值金額", 0.01, 50000)
            
            # 選擇支付方式
            payment_methods = self.payment_service.get_payment_methods()
            method_options = [method["name"] for method in payment_methods]
            method_choice = SimpleMenu.show_options("支付方式", method_options)
            selected_method = payment_methods[method_choice - 1]["code"]
            
            # 確認充值
            print(f"\n充值信息確認:")
            print(f"卡片: {selected_card.card_no}")
            print(f"金額: {Formatter.format_currency(amount)}")
            print(f"支付方式: {payment_methods[method_choice - 1]['name']}")
            
            if not QuickForm.get_confirmation("確認充值？"):
                BaseUI.show_info("充值已取消")
                BaseUI.pause()
                return
            
            # 執行充值
            BaseUI.show_loading("正在處理充值...")
            result = self.payment_service.recharge_card(
                selected_card.id,
                Decimal(str(amount)),
                selected_method
            )
            
            BaseUI.clear_screen()
            
            # 顯示充值結果
            StatusDisplay.show_transaction_result(True, {
                "交易號": result["tx_no"],
                "充值金額": Formatter.format_currency(result["amount"]),
                "支付方式": payment_methods[method_choice - 1]["name"],
                "處理時間": Formatter.format_datetime(result.get("created_at"))
            })
            
            ui_logger.log_transaction("充值", amount, result["tx_no"])
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"充值失敗: {e}")
            BaseUI.pause()
    
    def _view_transactions(self):
        """查看交易記錄"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("交易記錄查詢")
            
            # 創建分頁表格
            headers = ["交易號", "類型", "金額", "狀態", "時間"]
            
            def fetch_transactions(page: int, page_size: int):
                return self.member_service.get_member_transactions(
                    self.current_member_id, 
                    page_size, 
                    page * page_size
                )
            
            paginated_table = PaginatedTable(headers, fetch_transactions, "我的交易記錄")
            
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
            
            # 重新包裝數據獲取函數
            def wrapped_fetch_transactions(page: int, page_size: int):
                raw_data = fetch_transactions(page, page_size)
                return format_transaction_data(raw_data)
            
            paginated_table.data_fetcher = wrapped_fetch_transactions
            paginated_table.display_interactive()
            
        except Exception as e:
            BaseUI.show_error(f"查詢失敗: {e}")
            BaseUI.pause()
    
    def _bind_new_card(self):
        """綁定新卡片"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("綁定新卡片")
            
            # 輸入卡片 ID
            card_id = QuickForm.get_text("請輸入卡片 ID", True, Validator.validate_card_id,
                                       "請輸入有效的 UUID 格式卡片 ID")
            
            # 選擇綁定角色
            roles = ["member", "viewer"]
            role_names = ["成員 (可使用卡片)", "查看者 (僅查看信息)"]
            role_choice = SimpleMenu.show_options("綁定角色", role_names)
            selected_role = roles[role_choice - 1]
            
            # 輸入綁定密碼（如果需要）
            binding_password = input("請輸入綁定密碼 (如果卡片設置了密碼，可選): ").strip()
            if not binding_password:
                binding_password = None
            
            # 確認綁定
            print(f"\n綁定信息確認:")
            print(f"卡片 ID: {card_id}")
            print(f"綁定角色: {role_names[role_choice - 1]}")
            print(f"綁定密碼: {'已設置' if binding_password else '未設置'}")
            
            if not QuickForm.get_confirmation("確認綁定？"):
                BaseUI.show_info("綁定已取消")
                BaseUI.pause()
                return
            
            # 執行綁定
            BaseUI.show_loading("正在綁定卡片...")
            result = self.member_service.bind_card(
                card_id,
                self.current_member_id,
                selected_role,
                binding_password
            )
            
            if result:
                BaseUI.show_success("卡片綁定成功！")
                ui_logger.log_user_action("綁定卡片", {
                    "card_id": card_id,
                    "role": selected_role
                })
            else:
                BaseUI.show_error("卡片綁定失敗")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"綁定失敗: {e}")
            BaseUI.pause()
    
    def _view_points_level(self):
        """查看積分等級"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("積分等級信息")
            
            cards = self.member_service.get_member_cards(self.current_member_id)
            
            if not cards:
                BaseUI.show_info("您還沒有任何卡片")
                BaseUI.pause()
                return
            
            # 顯示每張卡片的積分等級信息
            for i, card in enumerate(cards, 1):
                print(f"\n📱 卡片 {i}: {card.card_no}")
                print("─" * 40)
                
                level_info = {
                    "卡片類型": card.get_card_type_display(),
                    "當前積分": Formatter.format_points(card.points or 0),
                    "當前等級": card.get_level_display(),
                    "當前折扣": card.get_discount_display(),
                    "卡片狀態": card.get_status_display()
                }
                
                for key, value in level_info.items():
                    print(f"  {key}: {value}")
                
                # 顯示升級信息
                if card.card_type in ['standard', 'prepaid']:
                    self._show_upgrade_info(card.points or 0)
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"查詢失敗: {e}")
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
            
            print(f"  升級信息:")
            print(f"    下一等級: {next_info['name']}")
            print(f"    所需積分: {points_needed:,} 分")
            print(f"    升級後折扣: {Formatter.format_discount(next_info['discount'])}")
        else:
            print(f"  🎉 您已達到最高等級！")
    
    def _select_card(self, cards: List[Card], title: str = "選擇卡片") -> Optional[Card]:
        """選擇卡片的通用方法"""
        if not cards:
            return None
        
        print(f"\n{title}:")
        for i, card in enumerate(cards, 1):
            print(f"  {i}. {card.display_info()}")
        
        while True:
            try:
                choice = int(input(f"請選擇 (1-{len(cards)}): "))
                if 1 <= choice <= len(cards):
                    return cards[choice - 1]
                print(f"✗ 請選擇 1-{len(cards)}")
            except ValueError:
                print("✗ 請輸入有效數字")
            except KeyboardInterrupt:
                return None