from typing import Optional, Dict, List
from services.admin_service import AdminService
from services.member_service import MemberService
from services.qr_service import QRService
from services.auth_service import AuthService
from ui.components.menu import Menu, SimpleMenu
from ui.components.table import Table
from ui.components.form import QuickForm, ValidationForm
from ui.base_ui import BaseUI, StatusDisplay
from utils.formatters import Formatter
from utils.validators import Validator
from utils.logger import ui_logger

class AdminUI:
    """管理員用戶界面"""
    
    def __init__(self, auth_service: AuthService):
        self.admin_service = AdminService()
        self.member_service = MemberService()
        self.qr_service = QRService()
        self.auth_service = auth_service
        
        # 設定 auth_service
        self.admin_service.set_auth_service(auth_service)
        self.member_service.set_auth_service(auth_service)
        self.qr_service.set_auth_service(auth_service)
        
        # 從 auth_service 取得資訊
        profile = auth_service.get_current_user()
        self.current_admin_name = profile.get('name', 'Admin') if profile else 'Admin'
    
    def start(self):
        """啟動管理員界面"""
        try:
            # 直接顯示主菜單（已在 main.py 完成登入）
            self._show_main_menu()
            
        except KeyboardInterrupt:
            print("\n▸ Goodbye!")
        except Exception as e:
            BaseUI.show_error(f"System error: {e}")
        finally:
            ui_logger.log_logout("admin")
    
    def _show_main_menu(self):
        """顯示主菜單"""
        options = [
            "Member Management",
            "Merchant Management",
            "Card Management",
            "System Statistics",
            "System Maintenance",
            "Exit System"
        ]
        
        handlers = [
            self._member_management,
            self._merchant_management,
            self._card_management,
            self._system_statistics,
            self._system_maintenance,
            lambda: False  # 退出
        ]
        
        menu = Menu(f"MPS Admin Console - {self.current_admin_name}", options, handlers)
        menu.run()
    
    def _member_management(self):
        """會員管理"""
        while True:
            BaseUI.clear_screen()
            BaseUI.show_header("Member Management")
            
            options = [
                "Create New Member",
                "View Member Info",
                "Search Members",
                "Suspend Member",
                "Return to Main Menu"
            ]
            
            choice = BaseUI.show_menu(options, "Member Management Operations")
            
            if choice == 1:
                self._create_new_member()
            elif choice == 2:
                self._view_member_info()
            elif choice == 3:
                self._search_members()
            elif choice == 4:
                self._suspend_member()
            elif choice == 5:
                break
    
    def _create_new_member(self):
        """創建新會員"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Create New Member")
            
            # 使用驗證表單收集會員信息
            member_data = ValidationForm.create_member_form()
            
            # 確認創建
            print(f"\nMember Information Confirmation:")
            print(f"Name: {member_data['name']}")
            print(f"Phone: {member_data['phone']}")
            print(f"Email: {member_data['email']}")
            
            if member_data.get('bind_external'):
                print(f"External Platform: {member_data['provider']}")
                print(f"External ID: {member_data['external_id']}")
            
            if not QuickForm.get_confirmation("Confirm member creation?"):
                BaseUI.show_info("Member creation cancelled")
                BaseUI.pause()
                return
            
            # 執行創建
            BaseUI.show_loading("Creating member...")
            
            member_id = self.admin_service.create_member_profile(
                member_data['name'],
                member_data['phone'],
                member_data['email'],
                member_data.get('provider'),
                member_data.get('external_id')
            )
            
            BaseUI.clear_screen()
            BaseUI.show_success("Member created successfully!", {
                "Member ID": member_id,
                "Name": member_data['name'],
                "Phone": member_data['phone'],
                "Auto Generated": "Standard card auto-generated and bound"
            })
            
            ui_logger.log_user_action("Create Member", {
                "member_id": member_id,
                "name": member_data['name']
            })
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Member creation failed: {e}")
            BaseUI.pause()
    
    def _view_member_info(self):
        """查看會員信息"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("View Member Information")
            
            member_id = QuickForm.get_text("Please enter Member ID", True,
                                         Validator.validate_member_id,
                                         "Please enter valid UUID format Member ID")
            
            BaseUI.show_loading("Querying member information...")
            
            # 獲取會員詳細信息
            member = self.member_service.get_member_by_id(member_id)
            
            if not member:
                BaseUI.show_error("Member does not exist")
                BaseUI.pause()
                return
            
            # 獲取會員摘要
            summary = self.member_service.get_member_summary(member_id)
            
            BaseUI.clear_screen()
            
            # 顯示會員基本信息
            print("📋 Member Basic Information:")
            print("─" * 40)
            member_info = member.to_display_dict()
            for key, value in member_info.items():
                print(f"  {key}: {value}")
            
            # 顯示卡片統計
            print(f"\n💳 Card Statistics:")
            print("─" * 40)
            print(f"  Total Cards: {summary.get('cards_count', 0)} cards")
            print(f"  Active Cards: {summary.get('active_cards_count', 0)} cards")
            print(f"  Total Balance: {Formatter.format_currency(summary.get('total_balance', 0))}")
            print(f"  Total Points: {Formatter.format_points(summary.get('total_points', 0))}")
            print(f"  Highest Level: {Formatter.format_level(summary.get('highest_level', 0))}")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Query failed: {e}")
            BaseUI.pause()
    
    def _search_members(self):
        """搜索會員"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Search Members")
            
            keyword = QuickForm.get_text("Please enter search keyword", True,
                                       help_text="Search by name, phone, email, member number")
            
            BaseUI.show_loading("Searching...")
            
            members = self.member_service.search_members(keyword, 50)
            
            if not members:
                BaseUI.show_info("No matching members found")
                BaseUI.pause()
                return
            
            BaseUI.clear_screen()
            
            # 顯示搜索結果
            headers = ["Member No", "Name", "Phone", "Status", "Created"]
            data = []
            
            for member in members:
                data.append({
                    "Member No": member.member_no or "",
                    "Name": member.name or "",
                    "Phone": Formatter.format_phone(member.phone or ""),
                    "Status": member.get_status_display(),
                    "Created": member.format_date("created_at")
                })
            
            table = Table(headers, data, f"Search Results (Keyword: {keyword})")
            table.display()
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Search failed: {e}")
            BaseUI.pause()
    
    def _suspend_member(self):
        """暫停會員"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Suspend Member")
            
            member_id = QuickForm.get_text("Please enter Member ID to suspend", True,
                                         Validator.validate_member_id)
            
            # 查詢會員信息
            BaseUI.show_loading("Querying member information...")
            member = self.member_service.get_member_by_id(member_id)
            
            if not member:
                BaseUI.show_error("Member does not exist")
                BaseUI.pause()
                return
            
            # 顯示會員信息
            print(f"\nMember Information:")
            print(f"  Name: {member.name}")
            print(f"  Phone: {member.phone}")
            print(f"  Current Status: {member.get_status_display()}")
            
            if member.status == "suspended":
                BaseUI.show_warning("This member is already suspended")
                BaseUI.pause()
                return
            
            # 確認暫停
            if not QuickForm.get_confirmation(f"Confirm suspend member {member.name}?"):
                BaseUI.show_info("Operation cancelled")
                BaseUI.pause()
                return
            
            # 執行暫停
            BaseUI.show_loading("Suspending member...")
            result = self.admin_service.suspend_member(member_id)
            
            if result:
                BaseUI.show_success("Member suspended successfully")
                ui_logger.log_user_action("Suspend Member", {
                    "member_id": member_id,
                    "member_name": member.name
                })
            else:
                BaseUI.show_error("Member suspension failed")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Suspension failed: {e}")
            BaseUI.pause()
    
    def _merchant_management(self):
        """商戶管理"""
        BaseUI.show_info("Merchant management feature under development...")
        BaseUI.pause()
    
    def _card_management(self):
        """卡片管理"""
        while True:
            BaseUI.clear_screen()
            BaseUI.show_header("Card Management")
            
            options = [
                "Freeze Card",
                "Unfreeze Card",
                "Adjust Points",
                "Search Cards",
                "Return to Main Menu"
            ]
            
            choice = BaseUI.show_menu(options, "Card Management Operations")
            
            if choice == 1:
                self._freeze_card()
            elif choice == 2:
                self._unfreeze_card()
            elif choice == 3:
                self._adjust_points()
            elif choice == 4:
                self._search_cards()
            elif choice == 5:
                break
    
    def _freeze_card(self):
        """凍結卡片"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Freeze Card")
            
            card_id = QuickForm.get_text("Please enter Card ID to freeze", True,
                                       Validator.validate_card_id)
            
            # 查詢卡片信息
            BaseUI.show_loading("Querying card information...")
            card_detail = self.admin_service.get_card_detail(card_id)
            
            if not card_detail:
                BaseUI.show_error("Card does not exist")
                BaseUI.pause()
                return
            
            card = card_detail["card"]
            owner = card_detail["owner"]
            
            # 顯示卡片信息
            print(f"\nCard Information:")
            print(f"  Card No: {card.card_no}")
            print(f"  Type: {card.get_card_type_display()}")
            print(f"  Owner: {owner.name if owner else 'Unknown'}")
            print(f"  Current Status: {card.get_status_display()}")
            print(f"  Balance: {Formatter.format_currency(card.balance)}")
            
            if card.status == "inactive":
                BaseUI.show_warning("This card is already frozen")
                BaseUI.pause()
                return
            
            # 確認凍結
            if not QuickForm.get_confirmation(f"Confirm freeze card {card.card_no}?"):
                BaseUI.show_info("Operation cancelled")
                BaseUI.pause()
                return
            
            # 執行凍結
            BaseUI.show_loading("Freezing card...")
            result = self.admin_service.freeze_card(card_id)
            
            if result:
                BaseUI.show_success("Card frozen successfully")
                ui_logger.log_user_action("Freeze Card", {
                    "card_id": card_id,
                    "card_no": card.card_no
                })
            else:
                BaseUI.show_error("Card freeze failed")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Freeze failed: {e}")
            BaseUI.pause()
    
    def _unfreeze_card(self):
        """解凍卡片"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Unfreeze Card")
            
            card_id = QuickForm.get_text("Please enter Card ID to unfreeze", True,
                                       Validator.validate_card_id)
            
            # 查詢卡片信息
            BaseUI.show_loading("Querying card information...")
            card_detail = self.admin_service.get_card_detail(card_id)
            
            if not card_detail:
                BaseUI.show_error("Card does not exist")
                BaseUI.pause()
                return
            
            card = card_detail["card"]
            
            if card.status != "inactive":
                BaseUI.show_warning("This card is not in frozen status")
                BaseUI.pause()
                return
            
            # 確認解凍
            if not QuickForm.get_confirmation(f"Confirm unfreeze card {card.card_no}?"):
                BaseUI.show_info("Operation cancelled")
                BaseUI.pause()
                return
            
            # 執行解凍
            BaseUI.show_loading("Unfreezing card...")
            result = self.admin_service.unfreeze_card(card_id)
            
            if result:
                BaseUI.show_success("Card unfrozen successfully")
                ui_logger.log_user_action("Unfreeze Card", {
                    "card_id": card_id,
                    "card_no": card.card_no
                })
            else:
                BaseUI.show_error("Card unfreeze failed")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Unfreeze failed: {e}")
            BaseUI.pause()
    
    def _adjust_points(self):
        """調整積分"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Adjust Points")
            
            card_id = QuickForm.get_text("Please enter Card ID", True,
                                       Validator.validate_card_id)
            
            # 查詢卡片信息
            BaseUI.show_loading("Querying card information...")
            card_detail = self.admin_service.get_card_detail(card_id)
            
            if not card_detail:
                BaseUI.show_error("Card does not exist")
                BaseUI.pause()
                return
            
            card = card_detail["card"]
            
            # 顯示當前積分信息
            print(f"\nCurrent Points Information:")
            print(f"  Card No: {card.card_no}")
            print(f"  Current Points: {Formatter.format_points(card.points or 0)}")
            print(f"  Current Level: {card.get_level_display()}")
            
            # 輸入積分變化
            while True:
                try:
                    delta_points = int(input("Enter points change (positive to add, negative to subtract): "))
                    
                    new_points = max(0, (card.points or 0) + delta_points)
                    print(f"Points after adjustment: {Formatter.format_points(new_points)}")
                    
                    break
                except ValueError:
                    print("✗ Please enter a valid integer")
            
            reason = input("Enter adjustment reason: ").strip() or "manual_adjust"
            
            # 確認調整
            if not QuickForm.get_confirmation("Confirm points adjustment?"):
                BaseUI.show_info("Operation cancelled")
                BaseUI.pause()
                return
            
            # 執行調整
            BaseUI.show_loading("Adjusting points...")
            result = self.admin_service.update_points_and_level(card_id, delta_points, reason)
            
            if result:
                BaseUI.show_success("Points adjusted successfully", {
                    "Change": f"{delta_points:+d}",
                    "After Adjustment": f"{new_points:,} points",
                    "Reason": reason
                })
                ui_logger.log_user_action("Adjust Points", {
                    "card_id": card_id,
                    "delta_points": delta_points,
                    "reason": reason
                })
            else:
                BaseUI.show_error("Points adjustment failed")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Adjustment failed: {e}")
            BaseUI.pause()
    
    def _search_cards(self):
        """搜索卡片"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Search Cards")
            
            keyword = QuickForm.get_text("Please enter search keyword", True,
                                       help_text="Search by card number, card name")
            
            BaseUI.show_loading("Searching...")
            
            cards = self.admin_service.search_cards(keyword, 50)
            
            if not cards:
                BaseUI.show_info("No matching cards found")
                BaseUI.pause()
                return
            
            BaseUI.clear_screen()
            
            # 顯示搜索結果
            headers = ["Card No", "Type", "Owner", "Balance", "Points", "Status"]
            data = []
            
            for card in cards:
                # 獲取擁有者信息
                owner = None
                if card.owner_member_id:
                    owner = self.member_service.get_member_by_id(card.owner_member_id)
                
                data.append({
                    "Card No": card.card_no or "",
                    "Type": card.get_card_type_display(),
                    "Owner": owner.name if owner else "Unknown",
                    "Balance": Formatter.format_currency(card.balance),
                    "Points": Formatter.format_points(card.points or 0),
                    "Status": card.get_status_display()
                })
            
            table = Table(headers, data, f"Search Results (Keyword: {keyword})")
            table.display()
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Search failed: {e}")
            BaseUI.pause()
    
    def _system_statistics(self):
        """系統統計"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("System Statistics")
            
            BaseUI.show_loading("Getting system statistics...")
            
            stats = self.admin_service.get_system_statistics()
            
            if not stats:
                BaseUI.show_error("Unable to get system statistics")
                BaseUI.pause()
                return
            
            # 顯示統計信息
            print("📊 System Statistics:")
            print("═" * 50)
            
            # 會員統計
            members = stats.get("members", {})
            print(f"\n👥 Member Statistics:")
            print(f"  Total Members: {members.get('total', 0):,}")
            print(f"  Active Members: {members.get('active', 0):,}")
            print(f"  Inactive Members: {members.get('inactive', 0):,}")
            
            # 卡片統計
            cards = stats.get("cards", {})
            print(f"\n💳 Card Statistics:")
            print(f"  Total Cards: {cards.get('total', 0):,}")
            print(f"  Active Cards: {cards.get('active', 0):,}")
            print(f"  Inactive Cards: {cards.get('inactive', 0):,}")
            
            # 商戶統計
            merchants = stats.get("merchants", {})
            print(f"\n🏪 Merchant Statistics:")
            print(f"  Total Merchants: {merchants.get('total', 0):,}")
            print(f"  Active Merchants: {merchants.get('active', 0):,}")
            print(f"  Inactive Merchants: {merchants.get('inactive', 0):,}")
            
            # 今日交易統計
            today = stats.get("today", {})
            print(f"\n📈 Today's Transactions:")
            print(f"  Transaction Count: {today.get('transaction_count', 0):,}")
            print(f"  Payment Amount: {Formatter.format_currency(today.get('payment_amount', 0))}")
            
            print("═" * 50)
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Failed to get statistics: {e}")
            BaseUI.pause()
    
    def _system_maintenance(self):
        """系統維護"""
        while True:
            BaseUI.clear_screen()
            BaseUI.show_header("System Maintenance")
            
            options = [
                "Batch Rotate QR Codes",
                "Clean Expired Data",
                "System Health Check",
                "Return to Main Menu"
            ]
            
            choice = BaseUI.show_menu(options, "System Maintenance Operations")
            
            if choice == 1:
                self._batch_rotate_qr()
            elif choice == 2:
                BaseUI.show_info("Clean expired data feature under development...")
                BaseUI.pause()
            elif choice == 3:
                BaseUI.show_info("System health check feature under development...")
                BaseUI.pause()
            elif choice == 4:
                break
    
    def _batch_rotate_qr(self):
        """批量輪換 QR 碼"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Batch Rotate QR Codes")
            
            print("!  This operation will rotate QR codes for all active corporate cards")
            print("   After rotation, old QR codes will be immediately invalidated")
            
            # 輸入 TTL 秒數
            while True:
                try:
                    ttl_seconds = int(input("Enter new QR code validity period (seconds, recommended 300-3600): "))
                    if 60 <= ttl_seconds <= 7200:  # 1分鐘到2小時
                        break
                    print("✗ Validity period should be between 60-7200 seconds")
                except ValueError:
                    print("✗ Please enter a valid integer")
            
            # 確認操作
            ttl_minutes = ttl_seconds // 60
            if not QuickForm.get_confirmation(f"Confirm batch QR code rotation? (Validity: {ttl_minutes} minutes)"):
                BaseUI.show_info("Operation cancelled")
                BaseUI.pause()
                return
            
            # 執行批量輪換
            BaseUI.show_loading("Batch rotating QR codes...")
            affected_count = self.admin_service.batch_rotate_qr_tokens(ttl_seconds)
            
            BaseUI.show_success("Batch QR code rotation completed", {
                "Affected Cards": f"{affected_count} cards",
                "New Validity": f"{ttl_minutes} minutes",
                "Execution Time": Formatter.format_datetime(None)  # 當前時間
            })
            
            ui_logger.log_user_action("Batch Rotate QR Codes", {
                "affected_count": affected_count,
                "ttl_seconds": ttl_seconds
            })
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Batch rotation failed: {e}")
            BaseUI.pause()