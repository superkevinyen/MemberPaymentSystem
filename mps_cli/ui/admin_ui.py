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
        """會員管理 - 改進版（零 UUID 暴露）"""
        while True:
            BaseUI.clear_screen()
            BaseUI.show_header("Member Management")
            
            options = [
                "🔍 Search & Manage Members (搜尋並管理會員)",
                "📋 Browse All Members (瀏覽所有會員)",
                "➕ Create New Member (創建新會員)",
                "🔙 Return to Main Menu (返回主菜單)"
            ]
            
            choice = BaseUI.show_menu(options, "Member Management Operations")
            
            if choice == 1:
                self._search_and_manage_members()
            elif choice == 2:
                self._browse_all_members_improved()
            elif choice == 3:
                self._create_new_member()
            elif choice == 4:
                break
    
    def _create_new_member(self):
        """創建新會員 - 改進版（支持密碼設置）"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Create New Member")
            
            # 使用驗證表單收集會員信息
            member_data = ValidationForm.create_member_form()
            
            # 密碼設置選項
            print("\n" + "═" * 79)
            print("🔒 密碼設置選項")
            print("═" * 79)
            print("1. 使用手機號碼作為預設密碼 (推薦)")
            print("2. 自定義密碼")
            print("3. 暫不設置密碼 (會員首次登入時需設置)")
            
            password_choice = input("\n請選擇 (1-3): ").strip()
            
            password = None
            password_display = "未設置"
            
            if password_choice == "1":
                password = member_data['phone']
                password_display = "使用手機號作為預設密碼"
                print(f"✓ 將使用手機號作為預設密碼")
            elif password_choice == "2":
                import getpass
                while True:
                    password = getpass.getpass("\n請輸入密碼: ")
                    if not password:
                        BaseUI.show_error("密碼不能為空")
                        continue
                    
                    if len(password) < 6:
                        BaseUI.show_error("密碼長度至少 6 個字符")
                        continue
                    
                    password_confirm = getpass.getpass("請確認密碼: ")
                    
                    if password != password_confirm:
                        BaseUI.show_error("兩次密碼輸入不一致，請重新輸入")
                        continue
                    
                    password_display = "已設置自定義密碼"
                    print("✓ 密碼設置成功")
                    break
            elif password_choice == "3":
                password = None
                password_display = "未設置（首次登入需設置）"
                print("⚠️  會員首次登入時需要設置密碼")
            else:
                BaseUI.show_error("無效的選擇，將不設置密碼")
                password = None
                password_display = "未設置"
            
            # 確認創建
            print("\n" + "═" * 79)
            print("Member Information Confirmation")
            print("═" * 79)
            print(f"Name:     {member_data['name']}")
            print(f"Phone:    {member_data['phone']}")
            print(f"Email:    {member_data['email']}")
            print(f"Password: {password_display}")
            
            if member_data.get('bind_external'):
                print(f"External Platform: {member_data['provider']}")
                print(f"External ID: {member_data['external_id']}")
            print("═" * 79)
            
            if not QuickForm.get_confirmation("\nConfirm member creation?"):
                BaseUI.show_info("Member creation cancelled")
                BaseUI.pause()
                return
            
            # 執行創建（帶密碼）
            BaseUI.show_loading("Creating member...")
            
            member_id = self.member_service.create_member(
                name=member_data['name'],
                phone=member_data['phone'],
                email=member_data['email'],
                password=password
            )
            
            BaseUI.clear_screen()
            BaseUI.show_success("Member created successfully!", {
                "Member ID": member_id,
                "Name": member_data['name'],
                "Phone": member_data['phone'],
                "Password": password_display,
                "Auto Generated": "Standard card auto-generated and bound"
            })
            
            ui_logger.log_user_action("Create Member", {
                "member_id": member_id,
                "name": member_data['name'],
                "password_set": password is not None
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
    
    def _browse_all_members(self):
        """瀏覽所有會員"""
        try:
            page = 1
            page_size = 20
            
            while True:
                BaseUI.clear_screen()
                BaseUI.show_header(f"Browse All Members - Page {page}")
                
                BaseUI.show_loading("Loading members...")
                
                offset = (page - 1) * page_size
                result = self.member_service.get_all_members(page_size, offset)
                
                members = result['data']
                pagination = result['pagination']
                
                if not members:
                    BaseUI.show_info("No members found")
                    BaseUI.pause()
                    return
                
                # 顯示會員列表
                headers = ["Member No", "Name", "Phone", "Email", "Status", "Created"]
                data = []
                
                for member in members:
                    data.append({
                        "Member No": member.member_no or "",
                        "Name": member.name or "",
                        "Phone": Formatter.format_phone(member.phone or ""),
                        "Email": member.email or "",
                        "Status": member.get_status_display(),
                        "Created": member.format_date("created_at")
                    })
                
                table = Table(headers, data, f"Members (Page {page} of {pagination['total_pages']})")
                table.display()
                
                # 顯示分頁信息
                print(f"\n📄 Page {page} of {pagination['total_pages']} | "
                      f"Total: {pagination['total_count']} members")
                
                # 分頁控制選項
                page_options = []
                if pagination['has_prev']:
                    page_options.append("Previous Page")
                if pagination['has_next']:
                    page_options.append("Next Page")
                
                page_options.extend(["Search", "View Details", "Return"])
                
                choice = BaseUI.show_menu(page_options, "Page Navigation")
                
                if choice == 1 and pagination['has_prev']:
                    page -= 1
                elif choice == 1 and not pagination['has_prev'] and pagination['has_next']:
                    page += 1
                elif choice == 2 and pagination['has_next']:
                    page += 1
                elif choice == len(page_options) - 2:  # Search
                    self._search_members_advanced()
                elif choice == len(page_options) - 1:  # View Details
                    member_id = QuickForm.get_text("Enter Member ID to view details", True,
                                                 Validator.validate_member_id)
                    if member_id:
                        self._view_member_details(member_id)
                else:  # Return
                    break
                    
        except Exception as e:
            BaseUI.show_error(f"Browse failed: {e}")
            BaseUI.pause()
    
    def _search_members_advanced(self):
        """高級會員搜尋"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Advanced Member Search")
            
            print("\n🔍 Enter search criteria (leave blank to skip):")
            
            name = input("Name: ").strip() or None
            phone = input("Phone: ").strip() or None
            email = input("Email: ").strip() or None
            member_no = input("Member No: ").strip() or None
            
            # 狀態選擇
            status_options = ["All", "Active", "Inactive", "Suspended"]
            status_choice = BaseUI.show_menu(status_options, "Select Status")
            status_map = {1: None, 2: "active", 3: "inactive", 4: "suspended"}
            status = status_map.get(status_choice)
            
            # 確認搜尋
            if not any([name, phone, email, member_no, status is not None]):
                BaseUI.show_warning("Please enter at least one search criterion")
                BaseUI.pause()
                return
            
            BaseUI.show_loading("Searching...")
            
            members = self.member_service.search_members_advanced(
                name, phone, email, member_no, status, 50
            )
            
            if not members:
                BaseUI.show_info("No matching members found")
                BaseUI.pause()
                return
            
            BaseUI.clear_screen()
            
            # 顯示搜索結果
            headers = ["Member No", "Name", "Phone", "Email", "Status", "Created"]
            data = []
            
            for member in members:
                data.append({
                    "Member No": member.member_no or "",
                    "Name": member.name or "",
                    "Phone": Formatter.format_phone(member.phone or ""),
                    "Email": member.email or "",
                    "Status": member.get_status_display(),
                    "Created": member.format_date("created_at")
                })
            
            table = Table(headers, data, f"Search Results ({len(members)} members)")
            table.display()
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Search failed: {e}")
            BaseUI.pause()
    
    def _update_member_profile(self):
        """更新會員資料"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Update Member Profile")
            
            member_id = QuickForm.get_text("Enter Member ID to update", True,
                                         Validator.validate_member_id)
            
            # 查詢會員信息
            BaseUI.show_loading("Querying member information...")
            member = self.member_service.get_member_by_id(member_id)
            
            if not member:
                BaseUI.show_error("Member does not exist")
                BaseUI.pause()
                return
            
            # 顯示當前信息
            print(f"\nCurrent Member Information:")
            print(f"  Name: {member.name}")
            print(f"  Phone: {member.phone}")
            print(f"  Email: {member.email}")
            print(f"  Status: {member.get_status_display()}")
            
            print(f"\n📝 Enter new information (leave blank to keep current value):")
            
            new_name = input(f"Name [{member.name}]: ").strip() or None
            new_phone = input(f"Phone [{member.phone}]: ").strip() or None
            new_email = input(f"Email [{member.email}]: ").strip() or None
            
            if not any([new_name, new_phone, new_email]):
                BaseUI.show_info("No changes to update")
                BaseUI.pause()
                return
            
            # 確認更新
            print(f"\n📋 Update Summary:")
            if new_name:
                print(f"  Name: {member.name} → {new_name}")
            if new_phone:
                print(f"  Phone: {member.phone} → {new_phone}")
            if new_email:
                print(f"  Email: {member.email} → {new_email}")
            
            if not QuickForm.get_confirmation("Confirm update?"):
                BaseUI.show_info("Update cancelled")
                BaseUI.pause()
                return
            
            # 執行更新
            BaseUI.show_loading("Updating member profile...")
            result = self.member_service.update_member_profile(member_id, new_name, new_phone, new_email)
            
            if result:
                BaseUI.show_success("Member profile updated successfully")
                ui_logger.log_user_action("Update Member Profile", {
                    "member_id": member_id,
                    "updated_fields": {
                        "name": new_name,
                        "phone": new_phone,
                        "email": new_email
                    }
                })
            else:
                BaseUI.show_error("Member profile update failed")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Update failed: {e}")
            BaseUI.pause()
    
    def _reset_member_password(self):
        """重置會員密碼"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Reset Member Password")
            
            # 選擇查找方式
            print("請選擇會員：")
            print("1. 輸入會員 ID")
            print("2. 搜尋會員")
            
            choice = input("\n您的選擇 (1-2): ").strip()
            
            member_id = None
            if choice == "1":
                member_id = QuickForm.get_text(
                    "請輸入會員 ID",
                    required=True,
                    validator=Validator.validate_member_id
                )
            elif choice == "2":
                keyword = input("請輸入姓名或手機號: ").strip()
                if not keyword:
                    BaseUI.show_error("搜尋關鍵字不能為空")
                    BaseUI.pause()
                    return
                
                members = self.member_service.search_members(keyword)
                
                if not members:
                    BaseUI.show_error("未找到會員")
                    BaseUI.pause()
                    return
                
                # 顯示搜尋結果
                print(f"\n找到 {len(members)} 個會員：")
                for i, member in enumerate(members, 1):
                    print(f"{i}. {member.name} - {member.phone} ({member.member_no})")
                
                if len(members) == 1:
                    member_id = members[0].id
                else:
                    idx = QuickForm.get_number("請選擇會員", 1, len(members))
                    member_id = members[idx - 1].id
            else:
                BaseUI.show_error("無效的選擇")
                BaseUI.pause()
                return
            
            # 獲取會員信息
            member = self.member_service.get_member_by_id(member_id)
            if not member:
                BaseUI.show_error("會員不存在")
                BaseUI.pause()
                return
            
            # 顯示會員信息
            print("\n" + "═" * 79)
            print("會員信息")
            print("═" * 79)
            print(f"姓名：  {member.name}")
            print(f"手機：  {member.phone}")
            print(f"郵箱：  {member.email}")
            print(f"狀態：  {member.get_status_display()}")
            print("═" * 79)
            
            # 密碼重置選項
            print("\n🔒 密碼重置選項：")
            print("1. 重置為手機號")
            print("2. 設置自定義密碼")
            print("3. 取消")
            
            reset_choice = input("\n請選擇 (1-3): ").strip()
            
            new_password = None
            password_display = ""
            
            if reset_choice == "1":
                new_password = member.phone
                password_display = f"手機號：{member.phone}"
                print(f"✓ 將重置為手機號：{member.phone}")
            elif reset_choice == "2":
                import getpass
                while True:
                    new_password = getpass.getpass("\n請輸入新密碼: ")
                    if not new_password:
                        BaseUI.show_error("密碼不能為空")
                        continue
                    
                    if len(new_password) < 6:
                        BaseUI.show_error("密碼長度至少 6 個字符")
                        continue
                    
                    confirm_password = getpass.getpass("請確認新密碼: ")
                    
                    if new_password != confirm_password:
                        BaseUI.show_error("兩次密碼輸入不一致，請重新輸入")
                        continue
                    
                    password_display = "自定義密碼"
                    print("✓ 密碼設置成功")
                    break
            elif reset_choice == "3":
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            else:
                BaseUI.show_error("無效的選擇")
                BaseUI.pause()
                return
            
            # 確認重置
            print("\n" + "═" * 79)
            print(f"確認重置 {member.name} 的密碼")
            print(f"新密碼：{password_display}")
            print("═" * 79)
            
            if not BaseUI.confirm_action("\n確認重置密碼？"):
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            
            # 執行重置
            BaseUI.show_loading("正在重置密碼...")
            self.member_service.set_member_password(member_id, new_password)
            
            BaseUI.show_success("密碼重置成功！", {
                "會員": member.name,
                "新密碼": password_display,
                "提示": "請通知會員使用新密碼登入"
            })
            
            ui_logger.log_user_action("Reset Member Password", {
                "member_id": member_id,
                "member_name": member.name
            })
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"密碼重置失敗：{e}")
            BaseUI.pause()
    
    def _view_member_details(self, member_id: str):
        """查看會員詳情"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Member Details")
            
            # 獲取會員詳細信息
            member = self.member_service.get_member_by_id(member_id)
            
            if not member:
                BaseUI.show_error("Member does not exist")
                BaseUI.pause()
                return
            
            # 獲取會員摘要
            summary = self.member_service.get_member_summary(member_id)
            
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
        """卡片管理 - 改進版（零 UUID 暴露）"""
        while True:
            BaseUI.clear_screen()
            BaseUI.show_header("Card Management")
            
            options = [
                "🔍 Search & Manage Cards (搜尋並管理卡片)",
                "📋 Browse All Cards (瀏覽所有卡片)",
                "➕ Create Corporate Card (創建企業卡)",
                "🔙 Return to Main Menu (返回主菜單)"
            ]
            
            choice = BaseUI.show_menu(options, "Card Management Operations")
            
            if choice == 1:
                self._search_and_manage_cards()
            elif choice == 2:
                self._browse_all_cards_improved()
            elif choice == 3:
                self._create_corporate_card()
            elif choice == 4:
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
    
    def _browse_all_cards(self):
        """瀏覽所有卡片"""
        try:
            page = 1
            page_size = 20
            
            while True:
                BaseUI.clear_screen()
                BaseUI.show_header(f"Browse All Cards - Page {page}")
                
                # 篩選選項
                print("\n🔍 Filter options (leave blank to skip):")
                card_type = input("Card Type (standard/corporate/voucher): ").strip() or None
                status = input("Status (active/inactive): ").strip() or None
                owner_name = input("Owner Name: ").strip() or None
                
                BaseUI.show_loading("Loading cards...")
                
                offset = (page - 1) * page_size
                result = self.admin_service.get_all_cards(page_size, offset, card_type, status, owner_name)
                
                cards = result['data']
                pagination = result['pagination']
                
                if not cards:
                    BaseUI.show_info("No cards found")
                    BaseUI.pause()
                    return
                
                # 顯示卡片列表
                headers = ["Card No", "Type", "Name", "Owner", "Balance", "Points", "Status"]
                data = []
                
                for card in cards:
                    data.append({
                        "Card No": card.card_no or "",
                        "Type": card.get_card_type_display(),
                        "Name": card.name or "",
                        "Owner": card.owner_name or "Unknown",
                        "Balance": Formatter.format_currency(card.balance),
                        "Points": Formatter.format_points(card.points or 0),
                        "Status": card.get_status_display()
                    })
                
                table = Table(headers, data, f"Cards (Page {page} of {pagination['total_pages']})")
                table.display()
                
                # 顯示分頁信息
                print(f"\n📄 Page {page} of {pagination['total_pages']} | "
                      f"Total: {pagination['total_count']} cards")
                
                # 分頁控制選項
                page_options = []
                if pagination['has_prev']:
                    page_options.append("Previous Page")
                if pagination['has_next']:
                    page_options.append("Next Page")
                
                page_options.extend(["Change Filter", "View Details", "Return"])
                
                choice = BaseUI.show_menu(page_options, "Page Navigation")
                
                if choice == 1 and pagination['has_prev']:
                    page -= 1
                elif choice == 1 and not pagination['has_prev'] and pagination['has_next']:
                    page += 1
                elif choice == 2 and pagination['has_next']:
                    page += 1
                elif choice == len(page_options) - 2:  # Change Filter
                    continue  # 重新開始循環，應用新篩選
                elif choice == len(page_options) - 1:  # View Details
                    card_id = QuickForm.get_text("Enter Card ID to view details", True,
                                               Validator.validate_card_id)
                    if card_id:
                        self._view_card_details(card_id)
                else:  # Return
                    break
                    
        except Exception as e:
            BaseUI.show_error(f"Browse failed: {e}")
            BaseUI.pause()
    
    def _search_cards_advanced(self):
        """高級卡片搜尋"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Advanced Card Search")
            
            keyword = QuickForm.get_text("Enter search keyword", True,
                                       help_text="Search by card number, card name, owner name, owner phone")
            
            BaseUI.show_loading("Searching...")
            
            cards = self.admin_service.search_cards_advanced(keyword, 50)
            
            if not cards:
                BaseUI.show_info("No matching cards found")
                BaseUI.pause()
                return
            
            BaseUI.clear_screen()
            
            # 顯示搜索結果
            headers = ["Card No", "Type", "Name", "Owner", "Balance", "Points", "Status"]
            data = []
            
            for card in cards:
                data.append({
                    "Card No": card.card_no or "",
                    "Type": card.get_card_type_display(),
                    "Name": card.name or "",
                    "Owner": card.owner_name or "Unknown",
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
    
    def _view_card_details(self, card_id: str):
        """查看卡片詳情"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Card Details")
            
            # 查詢卡片信息
            BaseUI.show_loading("Querying card information...")
            card_detail = self.admin_service.get_card_detail(card_id)
            
            if not card_detail:
                BaseUI.show_error("Card does not exist")
                BaseUI.pause()
                return
            
            card = card_detail["card"]
            owner = card_detail["owner"]
            bindings = card_detail["bindings"]
            
            # 顯示卡片基本信息
            print("💳 Card Basic Information:")
            print("─" * 40)
            print(f"  Card No: {card.card_no}")
            print(f"  Type: {card.get_card_type_display()}")
            print(f"  Name: {card.name or 'N/A'}")
            print(f"  Status: {card.get_status_display()}")
            print(f"  Balance: {Formatter.format_currency(card.balance)}")
            print(f"  Points: {Formatter.format_points(card.points or 0)}")
            print(f"  Level: {card.get_level_display()}")
            print(f"  Discount: {card.get_discount_display()}")
            
            # 顯示擁有者信息
            if owner:
                print(f"\n👤 Owner Information:")
                print("─" * 40)
                print(f"  Name: {owner.name}")
                print(f"  Phone: {Formatter.format_phone(owner.phone or '')}")
                print(f"  Email: {owner.email or 'N/A'}")
                print(f"  Status: {owner.get_status_display()}")
            
            # 顯示綁定信息
            if bindings:
                print(f"\n🔗 Binding Information:")
                print("─" * 40)
                print(f"  Total Bindings: {len(bindings)}")
                for binding in bindings[:5]:  # 只顯示前5個
                    print(f"  - {binding.member_name} ({binding.role})")
                if len(bindings) > 5:
                    print(f"  ... and {len(bindings) - 5} more")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Query failed: {e}")
            BaseUI.pause()
    
    def _system_statistics(self):
        """系統統計"""
        while True:
            BaseUI.clear_screen()
            BaseUI.show_header("System Statistics")
            
            options = [
                "Basic Statistics",
                "Extended Statistics",
                "Today's Transaction Stats",
                "Transaction Trends Analysis",
                "System Health Check",
                "Return to Main Menu"
            ]
            
            choice = BaseUI.show_menu(options, "Statistics Options")
            
            if choice == 1:
                self._show_basic_statistics()
            elif choice == 2:
                self._show_extended_statistics()
            elif choice == 3:
                self._show_today_transaction_stats()
            elif choice == 4:
                self._show_transaction_trends()
            elif choice == 5:
                self._show_system_health_check()
            elif choice == 6:
                break
    
    def _show_basic_statistics(self):
        """基本統計信息"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Basic System Statistics")
            
            BaseUI.show_loading("Getting system statistics...")
            
            stats = self.admin_service.get_system_statistics()
            
            if not stats:
                BaseUI.show_error("Unable to get system statistics")
                BaseUI.pause()
                return
            
            # 顯示統計信息
            print("📊 Basic System Statistics:")
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
    
    def _show_extended_statistics(self):
        """擴展統計信息"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Extended System Statistics")
            
            BaseUI.show_loading("Getting extended system statistics...")
            
            stats = self.admin_service.get_system_statistics_extended()
            
            if not stats:
                BaseUI.show_error("Unable to get extended system statistics")
                BaseUI.pause()
                return
            
            # 顯示擴展統計信息
            print("📊 Extended System Statistics:")
            print("═" * 50)
            
            # 會員統計
            print(f"\n👥 Member Statistics:")
            print(f"  Total Members: {stats.get('members_total', 0):,}")
            print(f"  Active Members: {stats.get('members_active', 0):,}")
            print(f"  Inactive Members: {stats.get('members_inactive', 0):,}")
            print(f"  Suspended Members: {stats.get('members_suspended', 0):,}")
            
            # 卡片統計
            cards_by_type = stats.get('cards_by_type', {})
            print(f"\n💳 Card Statistics:")
            print(f"  Total Cards: {stats.get('cards_total', 0):,}")
            print(f"  Active Cards: {stats.get('cards_active', 0):,}")
            print(f"  Inactive Cards: {stats.get('cards_inactive', 0):,}")
            
            if cards_by_type:
                print(f"  Cards by Type:")
                for card_type, count in cards_by_type.items():
                    print(f"    {card_type}: {count}")
            
            # 商戶統計
            print(f"\n🏪 Merchant Statistics:")
            print(f"  Total Merchants: {stats.get('merchants_total', 0):,}")
            print(f"  Active Merchants: {stats.get('merchants_active', 0):,}")
            print(f"  Inactive Merchants: {stats.get('merchants_inactive', 0):,}")
            
            # 交易統計
            print(f"\n📈 Transaction Statistics:")
            print(f"  Today Transactions: {stats.get('transactions_today', 0):,}")
            print(f"  Today Amount: {Formatter.format_currency(stats.get('transactions_today_amount', 0))}")
            print(f"  This Month Transactions: {stats.get('transactions_this_month', 0):,}")
            print(f"  This Month Amount: {Formatter.format_currency(stats.get('transactions_this_month_amount', 0))}")
            
            print("═" * 50)
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Failed to get extended statistics: {e}")
            BaseUI.pause()
    
    def _show_today_transaction_stats(self):
        """今日交易統計"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Today's Transaction Statistics")
            
            BaseUI.show_loading("Getting today's transaction statistics...")
            
            stats = self.admin_service.get_today_transaction_stats()
            
            if not stats:
                BaseUI.show_error("Unable to get today's transaction statistics")
                BaseUI.pause()
                return
            
            # 顯示統計信息
            print("📊 Today's Transaction Statistics:")
            print("═" * 50)
            
            print(f"\n📈 Transaction Summary:")
            print(f"  Transaction Count: {stats.get('transaction_count', 0):,}")
            print(f"  Payment Amount: {Formatter.format_currency(stats.get('payment_amount', 0))}")
            print(f"  Refund Amount: {Formatter.format_currency(stats.get('refund_amount', 0))}")
            print(f"  Net Amount: {Formatter.format_currency(stats.get('net_amount', 0))}")
            print(f"  Unique Customers: {stats.get('unique_customers', 0):,}")
            print(f"  Average Transaction: {Formatter.format_currency(stats.get('average_transaction', 0))}")
            
            print("═" * 50)
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Failed to get today's transaction statistics: {e}")
            BaseUI.pause()
    
    def _show_transaction_trends(self):
        """交易趨勢分析"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Transaction Trends Analysis")
            
            print("\n📅 Select analysis period:")
            print("1. Last 7 days")
            print("2. Last 30 days")
            print("3. Custom range")
            
            period_choice = input("Your choice (1-3): ").strip()
            
            if period_choice == "1":
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
            elif period_choice == "2":
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
            elif period_choice == "3":
                start_date_str = input("Start date (YYYY-MM-DD): ").strip()
                end_date_str = input("End date (YYYY-MM-DD): ").strip()
                
                try:
                    from datetime import datetime
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                except ValueError:
                    BaseUI.show_error("Invalid date format")
                    BaseUI.pause()
                    return
            else:
                BaseUI.show_error("Invalid choice")
                BaseUI.pause()
                return
            
            print("\n📊 Group by:")
            print("1. Day")
            print("2. Week")
            print("3. Month")
            
            group_choice = input("Your choice (1-3): ").strip()
            group_by_map = {"1": "day", "2": "week", "3": "month"}
            group_by = group_by_map.get(group_choice, "day")
            
            BaseUI.show_loading("Analyzing transaction trends...")
            
            trends = self.admin_service.get_transaction_trends(
                start_date.isoformat(), end_date.isoformat(), None, group_by
            )
            
            if not trends:
                BaseUI.show_info("No transaction data found for the selected period")
                BaseUI.pause()
                return
            
            # 顯示趨勢分析
            print(f"\n📊 Transaction Trends Analysis:")
            print("═" * 80)
            
            headers = ["Period", "Transactions", "Payment", "Refund", "Net", "Customers", "Avg"]
            data = []
            
            for trend in trends:
                data.append({
                    "Period": trend.get('period_start', '')[:10],
                    "Transactions": f"{trend.get('transaction_count', 0):,}",
                    "Payment": Formatter.format_currency(trend.get('payment_amount', 0)),
                    "Refund": Formatter.format_currency(trend.get('refund_amount', 0)),
                    "Net": Formatter.format_currency(trend.get('net_amount', 0)),
                    "Customers": f"{trend.get('unique_customers', 0):,}",
                    "Avg": Formatter.format_currency(trend.get('average_transaction', 0))
                })
            
            table = Table(headers, data, f"Transaction Trends ({group_by.capitalize()})")
            table.display()
            
            print("═" * 80)
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Failed to analyze transaction trends: {e}")
            BaseUI.pause()
    
    def _show_system_health_check(self):
        """系統健康檢查"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("System Health Check")
            
            BaseUI.show_loading("Performing system health check...")
            
            health_checks = self.admin_service.system_health_check()
            
            if not health_checks:
                BaseUI.show_error("Unable to perform system health check")
                BaseUI.pause()
                return
            
            # 顯示健康檢查結果
            print("🔍 System Health Check Results:")
            print("═" * 60)
            
            for check in health_checks:
                check_name = check.get('check_name', 'Unknown')
                status = check.get('status', 'unknown')
                details = check.get('details', {})
                recommendation = check.get('recommendation')
                
                # 狀態圖標
                status_icon = {"ok": "✅", "warning": "⚠️", "error": "❌"}.get(status, "❓")
                
                print(f"\n{status_icon} {check_name.replace('_', ' ').title()}")
                print(f"  Status: {status.upper()}")
                
                # 顯示詳情
                if details:
                    for key, value in details.items():
                        print(f"  {key}: {value}")
                
                # 顯示建議
                if recommendation:
                    print(f"  💡 Recommendation: {recommendation}")
            
            print("\n═" * 60)
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"Failed to perform system health check: {e}")
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
                self._show_system_health_check()
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
    
    # ========== 新增：搜尋並管理功能（零 UUID 暴露）==========
    
    def _search_and_manage_members(self):
        """搜尋並管理會員 - 統一入口（零 UUID 暴露）"""
        while True:
            BaseUI.clear_screen()
            BaseUI.show_header("搜尋並管理會員")
            
            # 顯示搜尋提示
            print("\n💡 您可以輸入：")
            print("  • 會員號（如：M202501001）")
            print("  • 姓名（如：張三）")
            print("  • 手機號（如：138）- 支持部分匹配")
            print("  • 郵箱（如：user@example.com）")
            
            keyword = input("\n請輸入搜尋關鍵字（或按 Enter 返回）: ").strip()
            
            if not keyword:
                return
            
            # 執行搜尋
            BaseUI.show_loading("搜尋中...")
            
            try:
                members = self.member_service.search_members(keyword, 50)
                
                if not members:
                    BaseUI.show_info("未找到匹配的會員")
                    BaseUI.pause()
                    continue
                
                # 顯示搜尋結果並選擇
                selected_member = self._display_and_select_member(members, keyword)
                
                if selected_member:
                    # 進入會員操作菜單
                    self._member_action_menu(selected_member)
                
            except Exception as e:
                BaseUI.show_error(f"搜尋失敗：{e}")
                BaseUI.pause()
    
    def _display_and_select_member(self, members: List, keyword: str) -> Optional:
        """顯示搜尋結果並選擇會員（零 UUID 暴露）"""
        while True:
            BaseUI.clear_screen()
            
            # 顯示搜尋結果
            print(f"🔍 搜尋結果（關鍵字：{keyword}，找到 {len(members)} 個會員）：")
            print("─" * 79)
            print(f"{'序號':<4} {'會員號':<12} {'姓名':<10} {'手機':<13} "
                  f"{'郵箱':<20} {'狀態':<8}")
            print("─" * 79)
            
            for i, member in enumerate(members, 1):
                print(f"{i:<4} {member.member_no:<12} {member.name:<10} "
                      f"{member.phone:<13} {member.email:<20} "
                      f"{member.get_status_display():<8}")
            
            print("─" * 79)
            
            # 操作選項
            print("\n操作選項：")
            print(f"  [1-{len(members)}] 選擇會員進行操作")
            print("  [R] 重新搜尋")
            print("  [Q] 返回")
            
            choice = input("\n請選擇: ").strip().upper()
            
            if choice == 'R':
                return None  # 重新搜尋
            elif choice == 'Q':
                return None  # 返回
            elif choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(members):
                    return members[idx - 1]
                else:
                    BaseUI.show_error(f"請輸入 1-{len(members)}")
                    BaseUI.pause()
            else:
                BaseUI.show_error("無效的選擇")
                BaseUI.pause()
    
    def _member_action_menu(self, member):
        """會員操作菜單（零 UUID 暴露）"""
        while True:
            BaseUI.clear_screen()
            
            # 顯示會員信息（不包含 UUID）
            print("═" * 79)
            print(f"會員操作 - {member.name}")
            print("═" * 79)
            print(f"會員號：  {member.member_no}")
            print(f"姓名：    {member.name}")
            print(f"手機：    {member.phone}")
            print(f"郵箱：    {member.email}")
            print(f"狀態：    {member.get_status_display()}")
            print(f"創建時間：{member.format_datetime('created_at')}")
            print("═" * 79)
            
            # 顯示會員的卡片信息
            try:
                cards = self.member_service.get_member_cards(member.id)
                if cards:
                    print("\n💳 會員卡片：")
                    print("─" * 79)
                    for i, card in enumerate(cards, 1):
                        card_info = f"{i}. {card.card_no} ({card.get_card_type_display()}) - "
                        card_info += f"餘額: {Formatter.format_currency(card.balance)} - "
                        card_info += f"狀態: {card.get_status_display()}"
                        print(card_info)
                    print("─" * 79)
                else:
                    print("\n💳 會員卡片：暫無卡片")
                    print("─" * 79)
            except Exception as e:
                print(f"\n💳 會員卡片：無法載入 ({e})")
                print("─" * 79)
            
            # 操作選項
            options = [
                "📋 查看完整詳情 (View Full Details)",
                "✏️  編輯資料 (Edit Profile)",
                "🔒 重置密碼 (Reset Password)",
                "💳 管理卡片 (Manage Cards)",
                "💰 卡片充值 (Recharge Card)",
                "💸 申請退款 (Request Refund)",
                "📊 查看交易記錄 (View Transactions)",
                "⏸️  暫停/激活 (Suspend/Activate)",
                "🔙 返回搜尋 (Back to Search)"
            ]
            
            choice = BaseUI.show_menu(options, "請選擇操作")
            
            if choice == 1:
                self._view_member_full_details_improved(member)
            elif choice == 2:
                self._edit_member_profile_improved(member)
            elif choice == 3:
                self._reset_member_password_improved(member)
            elif choice == 4:
                self._manage_member_cards_improved(member)
            elif choice == 5:
                self._recharge_card_for_member(member)
            elif choice == 6:
                self._request_refund_for_member(member)
            elif choice == 7:
                self._view_member_transactions_improved(member)
            elif choice == 8:
                self._toggle_member_status_improved(member)
            elif choice == 9:
                break
    
    def _view_member_full_details_improved(self, member):
        """查看會員完整詳情（零 UUID 暴露）"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"會員詳情 - {member.name}")
            
            # 獲取會員摘要
            summary = self.member_service.get_member_summary(member.id)
            
            # 顯示會員基本信息
            print("📋 基本信息：")
            print("─" * 79)
            print(f"  會員號：  {member.member_no}")
            print(f"  姓名：    {member.name}")
            print(f"  手機：    {member.phone}")
            print(f"  郵箱：    {member.email}")
            print(f"  狀態：    {member.get_status_display()}")
            print(f"  創建時間：{member.format_datetime('created_at')}")
            print(f"  更新時間：{member.format_datetime('updated_at')}")
            
            # 顯示卡片統計
            print(f"\n💳 卡片統計：")
            print("─" * 79)
            print(f"  總卡片數：  {summary.get('cards_count', 0)} 張")
            print(f"  活躍卡片：  {summary.get('active_cards_count', 0)} 張")
            print(f"  總餘額：    {Formatter.format_currency(summary.get('total_balance', 0))}")
            print(f"  總積分：    {Formatter.format_points(summary.get('total_points', 0))}")
            print(f"  最高等級：  {Formatter.format_level(summary.get('highest_level', 0))}")
            
            # 顯示卡片詳細列表
            cards = self.member_service.get_member_cards(member.id)
            if cards:
                print(f"\n💳 卡片列表：")
                print("─" * 79)
                for i, card in enumerate(cards, 1):
                    print(f"  {i}. {card.card_no} ({card.get_card_type_display()})")
                    print(f"     餘額: {Formatter.format_currency(card.balance)} | "
                          f"積分: {card.points or 0} | "
                          f"等級: {card.get_level_display()} | "
                          f"狀態: {card.get_status_display()}")
                print("─" * 79)
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"查詢失敗：{e}")
            BaseUI.pause()
    
    def _edit_member_profile_improved(self, member):
        """編輯會員資料（零 UUID 暴露）"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"編輯會員資料 - {member.name}")
            
            # 顯示當前信息
            print("\n當前信息：")
            print(f"  姓名：{member.name}")
            print(f"  手機：{member.phone}")
            print(f"  郵箱：{member.email}")
            
            # 輸入新信息
            print("\n請輸入新信息（留空保持不變）：")
            new_name = input(f"姓名 [{member.name}]: ").strip() or None
            new_phone = input(f"手機 [{member.phone}]: ").strip() or None
            new_email = input(f"郵箱 [{member.email}]: ").strip() or None
            
            if not any([new_name, new_phone, new_email]):
                BaseUI.show_info("沒有需要更新的內容")
                BaseUI.pause()
                return
            
            # 顯示更新摘要
            print("\n更新摘要：")
            if new_name:
                print(f"  姓名：{member.name} → {new_name}")
            if new_phone:
                print(f"  手機：{member.phone} → {new_phone}")
            if new_email:
                print(f"  郵箱：{member.email} → {new_email}")
            
            if not BaseUI.confirm_action("\n確認更新？"):
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            
            # 執行更新（使用會員號）
            BaseUI.show_loading("更新中...")
            result = self.member_service.update_member_by_identifier(
                member.member_no,  # 使用會員號
                new_name,
                new_phone,
                new_email
            )
            
            if result:
                # 更新本地對象
                if new_name:
                    member.name = new_name
                if new_phone:
                    member.phone = new_phone
                if new_email:
                    member.email = new_email
                
                BaseUI.show_success("會員資料更新成功")
            else:
                BaseUI.show_error("會員資料更新失敗")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"更新失敗：{e}")
            BaseUI.pause()
    
    def _reset_member_password_improved(self, member):
        """重置會員密碼（零 UUID 暴露）"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"重置密碼 - {member.name}")
            
            # 顯示會員信息
            print("\n會員信息：")
            print(f"  會員號：{member.member_no}")
            print(f"  姓名：  {member.name}")
            print(f"  手機：  {member.phone}")
            
            # 密碼重置選項
            print("\n🔒 密碼重置選項：")
            print("1. 重置為手機號")
            print("2. 設置自定義密碼")
            print("3. 取消")
            
            choice = input("\n請選擇 (1-3): ").strip()
            
            new_password = None
            password_display = ""
            
            if choice == "1":
                new_password = member.phone
                password_display = f"手機號：{member.phone}"
            elif choice == "2":
                import getpass
                while True:
                    new_password = getpass.getpass("\n請輸入新密碼: ")
                    if not new_password:
                        BaseUI.show_error("密碼不能為空")
                        continue
                    
                    if len(new_password) < 6:
                        BaseUI.show_error("密碼長度至少 6 個字符")
                        continue
                    
                    confirm = getpass.getpass("請確認新密碼: ")
                    if new_password != confirm:
                        BaseUI.show_error("兩次密碼輸入不一致")
                        continue
                    
                    password_display = "自定義密碼"
                    break
            elif choice == "3":
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            else:
                BaseUI.show_error("無效的選擇")
                BaseUI.pause()
                return
            
            # 確認重置
            print("\n" + "═" * 79)
            print(f"確認重置 {member.name} 的密碼")
            print(f"新密碼：{password_display}")
            print("═" * 79)
            
            if not BaseUI.confirm_action("\n確認重置？"):
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            
            # 執行重置（使用會員號）
            BaseUI.show_loading("重置中...")
            self.member_service.set_member_password_by_identifier(member.member_no, new_password)
            
            BaseUI.show_success("密碼重置成功", {
                "會員": member.name,
                "新密碼": password_display
            })
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"重置失敗：{e}")
            BaseUI.pause()
    
    def _manage_member_cards_improved(self, member):
        """管理會員卡片（零 UUID 暴露）"""
        while True:
            try:
                BaseUI.clear_screen()
                BaseUI.show_header(f"管理卡片 - {member.name}")
                
                # 獲取會員卡片
                cards = self.member_service.get_member_cards(member.id)
                
                if not cards:
                    BaseUI.show_info("該會員暫無卡片")
                    BaseUI.pause()
                    return
                
                # 顯示卡片列表（不包含 UUID）
                print("\n💳 會員卡片：")
                print("─" * 79)
                print(f"{'序號':<4} {'卡號':<12} {'類型':<10} {'餘額':<12} "
                      f"{'積分':<8} {'狀態':<8}")
                print("─" * 79)
                
                for i, card in enumerate(cards, 1):
                    print(f"{i:<4} {card.card_no:<12} {card.get_card_type_display():<10} "
                          f"{Formatter.format_currency(card.balance):<12} "
                          f"{card.points or 0:<8} {card.get_status_display():<8}")
                
                print("─" * 79)
                
                # 操作選項
                print("\n操作選項：")
                print(f"  [1-{len(cards)}] 選擇卡片進行操作")
                print("  [Q] 返回")
                
                choice = input("\n請選擇: ").strip().upper()
                
                if choice == 'Q':
                    break
                elif choice.isdigit():
                    idx = int(choice)
                    if 1 <= idx <= len(cards):
                        selected_card = cards[idx - 1]
                        self._card_action_menu(selected_card)
                    else:
                        BaseUI.show_error(f"請輸入 1-{len(cards)}")
                        BaseUI.pause()
                else:
                    BaseUI.show_error("無效的選擇")
                    BaseUI.pause()
                
            except Exception as e:
                BaseUI.show_error(f"操作失敗：{e}")
                BaseUI.pause()
                break
    
    def _view_member_transactions_improved(self, member):
        """查看會員交易記錄（零 UUID 暴露）"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"交易記錄 - {member.name}")
            
            # 獲取交易記錄
            result = self.member_service.get_member_transactions(member.id, 20, 0)
            transactions = result.get('data', [])
            
            if not transactions:
                BaseUI.show_info("該會員暫無交易記錄")
                BaseUI.pause()
                return
            
            # 顯示交易記錄
            print("\n📊 最近交易：")
            print("─" * 79)
            print(f"{'交易號':<20} {'類型':<10} {'金額':<12} {'狀態':<8} {'時間':<20}")
            print("─" * 79)
            
            for tx in transactions[:10]:  # 只顯示前 10 筆
                print(f"{tx.tx_no:<20} {tx.get_tx_type_display():<10} "
                      f"{Formatter.format_currency(tx.final_amount):<12} "
                      f"{tx.get_status_display():<8} {tx.format_datetime('created_at'):<20}")
            
            print("─" * 79)
            print(f"\n共 {result.get('pagination', {}).get('total_count', 0)} 筆交易")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"查詢失敗：{e}")
            BaseUI.pause()
    
    def _toggle_member_status_improved(self, member):
        """切換會員狀態（零 UUID 暴露）"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"切換狀態 - {member.name}")
            
            # 顯示當前狀態
            print(f"\n當前狀態：{member.get_status_display()}")
            
            # 選擇新狀態
            print("\n請選擇新狀態：")
            print("1. 活躍 (active)")
            print("2. 非活躍 (inactive)")
            print("3. 暫停 (suspended)")
            print("4. 取消")
            
            choice = input("\n請選擇 (1-4): ").strip()
            
            status_map = {
                "1": "active",
                "2": "inactive",
                "3": "suspended"
            }
            
            if choice not in status_map:
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            
            new_status = status_map[choice]
            
            if new_status == member.status:
                BaseUI.show_info("狀態未改變")
                BaseUI.pause()
                return
            
            # 確認切換
            if not BaseUI.confirm_action(f"\n確認將狀態切換為 {new_status}？"):
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            
            # 執行切換（使用會員號）
            BaseUI.show_loading("切換中...")
            result = self.member_service.toggle_member_status_by_identifier(
                member.member_no,
                new_status
            )
            
            if result:
                member.status = new_status
                BaseUI.show_success("狀態切換成功", {
                    "會員": member.name,
                    "新狀態": new_status
                })
            else:
                BaseUI.show_error("狀態切換失敗")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"切換失敗：{e}")
            BaseUI.pause()
    
    def _browse_all_members_improved(self):
        """瀏覽所有會員 - 改進版（零 UUID 暴露）"""
        page = 1
        page_size = 20
        
        while True:
            try:
                BaseUI.clear_screen()
                BaseUI.show_header(f"瀏覽所有會員 - 第 {page} 頁")
                
                BaseUI.show_loading("載入中...")
                
                # 獲取會員列表
                offset = (page - 1) * page_size
                result = self.member_service.get_all_members(page_size, offset)
                
                members = result['data']
                pagination = result['pagination']
                
                if not members:
                    BaseUI.show_info("沒有會員記錄")
                    BaseUI.pause()
                    return
                
                # 顯示會員列表（不包含 UUID）
                print("\n─" * 79)
                print(f"{'序號':<4} {'會員號':<12} {'姓名':<10} {'手機':<13} "
                      f"{'郵箱':<20} {'狀態':<8}")
                print("─" * 79)
                
                for i, member in enumerate(members, 1):
                    print(f"{i:<4} {member.member_no:<12} {member.name:<10} "
                          f"{member.phone:<13} {member.email:<20} "
                          f"{member.get_status_display():<8}")
                
                print("─" * 79)
                
                # 分頁信息
                print(f"\n📄 第 {page} / {pagination['total_pages']} 頁 | "
                      f"共 {pagination['total_count']} 個會員")
                
                # 操作選項
                print("\n操作選項：")
                print(f"  [1-{len(members)}] 選擇會員進行操作")
                if pagination['has_next']:
                    print("  [N] 下一頁")
                if pagination['has_prev']:
                    print("  [P] 上一頁")
                print("  [S] 搜尋")
                print("  [Q] 返回")
                
                choice = input("\n請選擇: ").strip().upper()
                
                if choice.isdigit():
                    idx = int(choice)
                    if 1 <= idx <= len(members):
                        selected_member = members[idx - 1]
                        self._member_action_menu(selected_member)
                    else:
                        BaseUI.show_error(f"請輸入 1-{len(members)}")
                        BaseUI.pause()
                elif choice == 'N' and pagination['has_next']:
                    page += 1
                elif choice == 'P' and pagination['has_prev']:
                    page -= 1
                elif choice == 'S':
                    self._search_and_manage_members()
                    return
                elif choice == 'Q':
                    break
                else:
                    BaseUI.show_error("無效的選擇")
                    BaseUI.pause()
                    
            except Exception as e:
                BaseUI.show_error(f"瀏覽失敗：{e}")
                BaseUI.pause()
                break
    
    # ========== 新增：卡片搜尋並管理功能（零 UUID 暴露）==========
    
    def _search_and_manage_cards(self):
        """搜尋並管理卡片 - 統一入口（零 UUID 暴露）"""
        while True:
            BaseUI.clear_screen()
            BaseUI.show_header("搜尋並管理卡片")
            
            # 顯示搜尋提示
            print("\n💡 您可以輸入：")
            print("  • 卡號（如：C202501001）")
            print("  • 持卡人姓名（如：張三）")
            print("  • 持卡人手機（如：138）- 支持部分匹配")
            
            keyword = input("\n請輸入搜尋關鍵字（或按 Enter 返回）: ").strip()
            
            if not keyword:
                return
            
            # 執行搜尋
            BaseUI.show_loading("搜尋中...")
            
            try:
                cards = self.admin_service.search_cards_advanced(keyword, 50)
                
                if not cards:
                    BaseUI.show_info("未找到匹配的卡片")
                    BaseUI.pause()
                    continue
                
                # 顯示搜尋結果並選擇
                selected_card = self._display_and_select_card(cards, keyword)
                
                if selected_card:
                    # 進入卡片操作菜單
                    self._card_action_menu(selected_card)
                
            except Exception as e:
                BaseUI.show_error(f"搜尋失敗：{e}")
                BaseUI.pause()
    
    def _display_and_select_card(self, cards: List, keyword: str) -> Optional:
        """顯示搜尋結果並選擇卡片（零 UUID 暴露）"""
        while True:
            BaseUI.clear_screen()
            
            # 顯示搜尋結果
            print(f"🔍 搜尋結果（關鍵字：{keyword}，找到 {len(cards)} 張卡片）：")
            print("─" * 79)
            print(f"{'序號':<4} {'卡號':<12} {'類型':<10} {'持卡人':<10} "
                  f"{'餘額':<12} {'狀態':<8}")
            print("─" * 79)
            
            for i, card in enumerate(cards, 1):
                owner_name = card.owner_name if hasattr(card, 'owner_name') else 'N/A'
                print(f"{i:<4} {card.card_no:<12} {card.get_card_type_display():<10} "
                      f"{owner_name:<10} "
                      f"{Formatter.format_currency(card.balance):<12} "
                      f"{card.get_status_display():<8}")
            
            print("─" * 79)
            
            # 操作選項
            print("\n操作選項：")
            print(f"  [1-{len(cards)}] 選擇卡片進行操作")
            print("  [R] 重新搜尋")
            print("  [Q] 返回")
            
            choice = input("\n請選擇: ").strip().upper()
            
            if choice == 'R':
                return None  # 重新搜尋
            elif choice == 'Q':
                return None  # 返回
            elif choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(cards):
                    return cards[idx - 1]
                else:
                    BaseUI.show_error(f"請輸入 1-{len(cards)}")
                    BaseUI.pause()
            else:
                BaseUI.show_error("無效的選擇")
                BaseUI.pause()
    
    def _card_action_menu(self, card):
        """卡片操作菜單（零 UUID 暴露）"""
        while True:
            BaseUI.clear_screen()
            
            # 顯示卡片信息（不包含 UUID）
            print("═" * 79)
            print(f"卡片操作 - {card.card_no}")
            print("═" * 79)
            print(f"卡號：    {card.card_no}")
            print(f"類型：    {card.get_card_type_display()}")
            if hasattr(card, 'owner_name') and card.owner_name:
                print(f"持卡人：  {card.owner_name}")
                if hasattr(card, 'owner_phone'):
                    print(f"手機：    {card.owner_phone}")
            print(f"餘額：    {Formatter.format_currency(card.balance)}")
            print(f"積分：    {card.points or 0}")
            print(f"等級：    {card.get_level_display()}")
            print(f"狀態：    {card.get_status_display()}")
            print("═" * 79)
            
            # 操作選項
            options = [
                "📋 查看完整詳情 (View Full Details)",
                "💰 卡片充值 (Recharge Card)",
                "💸 申請退款 (Request Refund)",
                "📊 查看交易記錄 (View Transactions)",
                "👤 查看持卡人信息 (View Owner Info)",
                "🔗 管理綁定 (Manage Bindings)",
                "❄️  凍結/解凍 (Freeze/Unfreeze)",
                "🔙 返回 (Back)"
            ]
            
            choice = BaseUI.show_menu(options, "請選擇操作")
            
            if choice == 1:
                self._view_card_full_details_improved(card)
            elif choice == 2:
                self._recharge_card_directly(card)
            elif choice == 3:
                self._refund_card_directly(card)
            elif choice == 4:
                self._view_card_transactions_improved(card)
            elif choice == 5:
                self._view_card_owner_info_improved(card)
            elif choice == 6:
                self._manage_card_bindings(card)
            elif choice == 7:
                self._toggle_card_status_improved(card)
            elif choice == 8:
                break
    
    def _view_card_full_details_improved(self, card):
        """查看卡片完整詳情（零 UUID 暴露）"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"卡片詳情 - {card.card_no}")
            
            # 顯示卡片詳細信息
            print("📋 卡片信息：")
            print("─" * 79)
            print(f"  卡號：      {card.card_no}")
            print(f"  類型：      {card.get_card_type_display()}")
            print(f"  名稱：      {card.name or 'N/A'}")
            print(f"  餘額：      {Formatter.format_currency(card.balance)}")
            print(f"  積分：      {card.points or 0}")
            print(f"  等級：      {card.get_level_display()}")
            print(f"  折扣：      {card.get_discount_display()}")
            print(f"  狀態：      {card.get_status_display()}")
            print(f"  創建時間：  {card.format_datetime('created_at')}")
            
            if card.expires_at:
                print(f"  過期時間：  {card.format_datetime('expires_at')}")
            
            # 顯示持卡人信息
            if hasattr(card, 'owner_name') and card.owner_name:
                print(f"\n👤 持卡人信息：")
                print("─" * 79)
                print(f"  姓名：      {card.owner_name}")
                if hasattr(card, 'owner_phone'):
                    print(f"  手機：      {card.owner_phone}")
                if hasattr(card, 'owner_email'):
                    print(f"  郵箱：      {card.owner_email}")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"查詢失敗：{e}")
            BaseUI.pause()
    
    def _view_card_owner_info_improved(self, card):
        """查看持卡人信息（零 UUID 暴露）"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"持卡人信息 - {card.card_no}")
            
            if not hasattr(card, 'owner_member_id') or not card.owner_member_id:
                BaseUI.show_info("此卡片暫無持卡人信息")
                BaseUI.pause()
                return
            
            # 獲取持卡人詳細信息
            member = self.member_service.get_member_by_id(card.owner_member_id)
            
            if not member:
                BaseUI.show_error("無法獲取持卡人信息")
                BaseUI.pause()
                return
            
            # 顯示持卡人信息
            print("👤 持卡人信息：")
            print("─" * 79)
            print(f"  會員號：  {member.member_no}")
            print(f"  姓名：    {member.name}")
            print(f"  手機：    {member.phone}")
            print(f"  郵箱：    {member.email}")
            print(f"  狀態：    {member.get_status_display()}")
            
            # 詢問是否進入會員操作菜單
            print("\n")
            if BaseUI.confirm_action("是否進入該會員的操作菜單？"):
                self._member_action_menu(member)
            else:
                BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"查詢失敗：{e}")
            BaseUI.pause()
    
    def _view_card_transactions_improved(self, card):
        """查看卡片交易記錄（零 UUID 暴露）"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"交易記錄 - {card.card_no}")
            
            # 獲取交易記錄（使用卡片 ID）
            # 注意：這裡仍需要使用 ID，因為交易記錄是通過卡片 ID 查詢的
            transactions = self.admin_service.get_card_transactions(card.id, 20)
            
            if not transactions:
                BaseUI.show_info("該卡片暫無交易記錄")
                BaseUI.pause()
                return
            
            # 顯示交易記錄
            print("\n📊 最近交易：")
            print("─" * 79)
            print(f"{'交易號':<20} {'類型':<10} {'金額':<12} {'狀態':<8} {'時間':<20}")
            print("─" * 79)
            
            for tx in transactions[:10]:  # 只顯示前 10 筆
                print(f"{tx.tx_no:<20} {tx.get_tx_type_display():<10} "
                      f"{Formatter.format_currency(tx.final_amount):<12} "
                      f"{tx.get_status_display():<8} {tx.format_datetime('created_at'):<20}")
            
            print("─" * 79)
            print(f"\n共 {len(transactions)} 筆交易")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"查詢失敗：{e}")
            BaseUI.pause()
    
    def _toggle_card_status_improved(self, card):
        """切換卡片狀態（零 UUID 暴露）"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"切換狀態 - {card.card_no}")
            
            # 顯示當前狀態
            print(f"\n當前狀態：{card.get_status_display()}")
            
            # 選擇新狀態
            print("\n請選擇新狀態：")
            print("1. 活躍 (active)")
            print("2. 凍結 (frozen)")
            print("3. 過期 (expired)")
            print("4. 取消")
            
            choice = input("\n請選擇 (1-4): ").strip()
            
            status_map = {
                "1": "active",
                "2": "frozen",
                "3": "expired"
            }
            
            if choice not in status_map:
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            
            new_status = status_map[choice]
            
            if new_status == card.status:
                BaseUI.show_info("狀態未改變")
                BaseUI.pause()
                return
            
            # 確認切換
            if not BaseUI.confirm_action(f"\n確認將狀態切換為 {new_status}？"):
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            
            # 執行切換（使用卡號）
            BaseUI.show_loading("切換中...")
            result = self.admin_service.toggle_card_status_by_card_no(
                card.card_no,
                new_status
            )
            
            if result:
                card.status = new_status
                BaseUI.show_success("狀態切換成功", {
                    "卡號": card.card_no,
                    "新狀態": new_status
                })
            else:
                BaseUI.show_error("狀態切換失敗")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"切換失敗：{e}")
            BaseUI.pause()
    
    def _browse_all_cards_improved(self):
        """瀏覽所有卡片 - 改進版（零 UUID 暴露）"""
        page = 1
        page_size = 20
        
        while True:
            try:
                BaseUI.clear_screen()
                BaseUI.show_header(f"瀏覽所有卡片 - 第 {page} 頁")
                
                BaseUI.show_loading("載入中...")
                
                # 獲取卡片列表
                offset = (page - 1) * page_size
                result = self.admin_service.get_all_cards(page_size, offset)
                
                cards = result['data']
                pagination = result['pagination']
                
                if not cards:
                    BaseUI.show_info("沒有卡片記錄")
                    BaseUI.pause()
                    return
                
                # 顯示卡片列表（不包含 UUID）
                print("\n─" * 79)
                print(f"{'序號':<4} {'卡號':<12} {'類型':<10} {'持卡人':<10} "
                      f"{'餘額':<12} {'狀態':<8}")
                print("─" * 79)
                
                for i, card in enumerate(cards, 1):
                    owner_name = card.owner_name if hasattr(card, 'owner_name') else 'N/A'
                    print(f"{i:<4} {card.card_no:<12} {card.get_card_type_display():<10} "
                          f"{owner_name:<10} "
                          f"{Formatter.format_currency(card.balance):<12} "
                          f"{card.get_status_display():<8}")
                
                print("─" * 79)
                
                # 分頁信息
                print(f"\n📄 第 {page} / {pagination['total_pages']} 頁 | "
                      f"共 {pagination['total_count']} 張卡片")
                
                # 操作選項
                print("\n操作選項：")
                print(f"  [1-{len(cards)}] 選擇卡片進行操作")
                if pagination['has_next']:
                    print("  [N] 下一頁")
                if pagination['has_prev']:
                    print("  [P] 上一頁")
                print("  [S] 搜尋")
                print("  [Q] 返回")
                
                choice = input("\n請選擇: ").strip().upper()
                
                if choice.isdigit():
                    idx = int(choice)
                    if 1 <= idx <= len(cards):
                        selected_card = cards[idx - 1]
                        self._card_action_menu(selected_card)
                    else:
                        BaseUI.show_error(f"請輸入 1-{len(cards)}")
                        BaseUI.pause()
                elif choice == 'N' and pagination['has_next']:
                    page += 1
                elif choice == 'P' and pagination['has_prev']:
                    page -= 1
                elif choice == 'S':
                    self._search_and_manage_cards()
                    return
                elif choice == 'Q':
                    break
                else:
                    BaseUI.show_error("無效的選擇")
                    BaseUI.pause()
                    
            except Exception as e:
                BaseUI.show_error(f"瀏覽失敗：{e}")
                BaseUI.pause()
                break
    
    def _create_corporate_card(self):
        """創建企業卡"""
        BaseUI.show_info("創建企業卡功能開發中...")
        BaseUI.pause()
    
    # ========== 新增：充值和退款功能 ==========
    
    def _recharge_card_for_member(self, member):
        """為會員卡片充值"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"卡片充值 - {member.name}")
            
            # 獲取會員卡片
            cards = self.member_service.get_member_cards(member.id)
            
            if not cards:
                BaseUI.show_error("該會員暫無卡片")
                BaseUI.pause()
                return
            
            # 顯示卡片列表
            print("\n💳 會員卡片：")
            print("─" * 79)
            print(f"{'序號':<4} {'卡號':<12} {'類型':<10} {'餘額':<12} {'狀態':<8}")
            print("─" * 79)
            
            for i, card in enumerate(cards, 1):
                print(f"{i:<4} {card.card_no:<12} {card.get_card_type_display():<10} "
                      f"{Formatter.format_currency(card.balance):<12} "
                      f"{card.get_status_display():<8}")
            
            print("─" * 79)
            
            # 選擇卡片
            choice = input(f"\n請選擇要充值的卡片 (1-{len(cards)}) 或按 Enter 取消: ").strip()
            
            if not choice:
                return
            
            if not choice.isdigit() or int(choice) < 1 or int(choice) > len(cards):
                BaseUI.show_error("無效的選擇")
                BaseUI.pause()
                return
            
            selected_card = cards[int(choice) - 1]
            
            # 檢查卡片狀態
            if selected_card.status != 'active':
                BaseUI.show_error(f"卡片狀態為 {selected_card.get_status_display()}，無法充值")
                BaseUI.pause()
                return
            
            # 輸入充值金額
            print(f"\n當前餘額：{Formatter.format_currency(selected_card.balance)}")
            amount_str = input("請輸入充值金額: ").strip()
            
            try:
                amount = float(amount_str)
                if amount <= 0:
                    BaseUI.show_error("充值金額必須大於 0")
                    BaseUI.pause()
                    return
            except ValueError:
                BaseUI.show_error("無效的金額")
                BaseUI.pause()
                return
            
            # 選擇支付方式
            print("\n請選擇支付方式：")
            print("1. 微信支付 (wechat)")
            print("2. 支付寶 (alipay)")
            print("3. 銀行卡 (bank_card)")
            print("4. 現金 (cash)")
            
            payment_choice = input("\n請選擇 (1-4): ").strip()
            payment_map = {
                "1": "wechat",
                "2": "alipay",
                "3": "bank_card",
                "4": "cash"
            }
            
            payment_method = payment_map.get(payment_choice, "wechat")
            
            # 確認充值
            print("\n" + "═" * 79)
            print("充值確認")
            print("═" * 79)
            print(f"卡號：      {selected_card.card_no}")
            print(f"當前餘額：  {Formatter.format_currency(selected_card.balance)}")
            print(f"充值金額：  {Formatter.format_currency(amount)}")
            print(f"充值後餘額：{Formatter.format_currency(selected_card.balance + amount)}")
            print(f"支付方式：  {payment_method}")
            print("═" * 79)
            
            if not BaseUI.confirm_action("\n確認充值？"):
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            
            # 執行充值
            BaseUI.show_loading("充值中...")
            
            # 調用充值 RPC
            result = self.admin_service.rpc_call("user_recharge_card", {
                "p_card_id": selected_card.id,
                "p_amount": amount,
                "p_payment_method": payment_method,
                "p_tag": {"admin_recharge": True, "admin_name": self.current_admin_name},
                "p_reason": f"Admin recharge for {member.name}",
                "p_session_id": None
            })
            
            if result and len(result) > 0:
                tx_info = result[0]
                BaseUI.show_success("充值成功", {
                    "交易號": tx_info.get('tx_no'),
                    "充值金額": Formatter.format_currency(amount),
                    "新餘額": Formatter.format_currency(selected_card.balance + amount)
                })
                
                # 更新本地卡片餘額
                selected_card.balance += amount
            else:
                BaseUI.show_error("充值失敗")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"充值失敗：{e}")
            BaseUI.pause()
    
    def _request_refund_for_member(self, member):
        """為會員申請退款"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"申請退款 - {member.name}")
            
            # 獲取會員最近的交易記錄
            result = self.member_service.get_member_transactions(member.id, 50, 0)
            transactions = result.get('data', [])
            
            if not transactions:
                BaseUI.show_info("該會員暫無交易記錄")
                BaseUI.pause()
                return
            
            # 過濾出可退款的交易（已完成的支付交易）
            refundable_txs = [tx for tx in transactions 
                            if tx.tx_type == 'payment' and tx.status in ['completed', 'refunded']]
            
            if not refundable_txs:
                BaseUI.show_info("沒有可退款的交易")
                BaseUI.pause()
                return
            
            # 顯示可退款交易
            print("\n📊 可退款交易：")
            print("─" * 79)
            print(f"{'序號':<4} {'交易號':<20} {'金額':<12} {'狀態':<10} {'時間':<20}")
            print("─" * 79)
            
            for i, tx in enumerate(refundable_txs[:20], 1):  # 最多顯示 20 筆
                print(f"{i:<4} {tx.tx_no:<20} "
                      f"{Formatter.format_currency(tx.final_amount):<12} "
                      f"{tx.get_status_display():<10} "
                      f"{tx.format_datetime('created_at'):<20}")
            
            print("─" * 79)
            
            # 選擇交易
            choice = input(f"\n請選擇要退款的交易 (1-{min(len(refundable_txs), 20)}) 或按 Enter 取消: ").strip()
            
            if not choice:
                return
            
            if not choice.isdigit() or int(choice) < 1 or int(choice) > min(len(refundable_txs), 20):
                BaseUI.show_error("無效的選擇")
                BaseUI.pause()
                return
            
            selected_tx = refundable_txs[int(choice) - 1]
            
            # 輸入退款金額
            print(f"\n原交易金額：{Formatter.format_currency(selected_tx.final_amount)}")
            
            # 計算已退款金額
            # TODO: 這裡應該查詢該交易的已退款金額
            print("提示：輸入退款金額（留空則全額退款）")
            amount_str = input("退款金額: ").strip()
            
            if not amount_str:
                refund_amount = selected_tx.final_amount
            else:
                try:
                    refund_amount = float(amount_str)
                    if refund_amount <= 0 or refund_amount > selected_tx.final_amount:
                        BaseUI.show_error(f"退款金額必須在 0 到 {selected_tx.final_amount} 之間")
                        BaseUI.pause()
                        return
                except ValueError:
                    BaseUI.show_error("無效的金額")
                    BaseUI.pause()
                    return
            
            # 輸入退款原因
            reason = input("\n退款原因（可選）: ").strip() or "Admin initiated refund"
            
            # 確認退款
            print("\n" + "═" * 79)
            print("退款確認")
            print("═" * 79)
            print(f"交易號：    {selected_tx.tx_no}")
            print(f"原金額：    {Formatter.format_currency(selected_tx.final_amount)}")
            print(f"退款金額：  {Formatter.format_currency(refund_amount)}")
            print(f"退款原因：  {reason}")
            print("═" * 79)
            
            if not BaseUI.confirm_action("\n確認退款？"):
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            
            # 執行退款
            # 注意：這需要商戶代碼，如果是管理員退款，需要特殊處理
            BaseUI.show_info("管理員退款功能需要商戶授權，請使用商戶賬號進行退款操作")
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"退款失敗：{e}")
            BaseUI.pause()
    
    # ========== 新增：卡片直接操作功能 ==========
    
    def _recharge_card_directly(self, card):
        """直接為卡片充值（從卡片菜單）"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"卡片充值 - {card.card_no}")
            
            # 檢查卡片狀態
            if card.status != 'active':
                BaseUI.show_error(f"卡片狀態為 {card.get_status_display()}，無法充值")
                BaseUI.pause()
                return
            
            # 顯示當前信息
            print(f"\n卡號：{card.card_no}")
            print(f"類型：{card.get_card_type_display()}")
            print(f"當前餘額：{Formatter.format_currency(card.balance)}")
            
            # 輸入充值金額
            amount_str = input("\n請輸入充值金額: ").strip()
            
            try:
                amount = float(amount_str)
                if amount <= 0:
                    BaseUI.show_error("充值金額必須大於 0")
                    BaseUI.pause()
                    return
            except ValueError:
                BaseUI.show_error("無效的金額")
                BaseUI.pause()
                return
            
            # 選擇支付方式
            print("\n請選擇支付方式：")
            print("1. 微信支付 (wechat)")
            print("2. 支付寶 (alipay)")
            print("3. 銀行卡 (bank_card)")
            print("4. 現金 (cash)")
            
            payment_choice = input("\n請選擇 (1-4): ").strip()
            payment_map = {
                "1": "wechat",
                "2": "alipay",
                "3": "bank_card",
                "4": "cash"
            }
            
            payment_method = payment_map.get(payment_choice, "wechat")
            
            # 確認充值
            print("\n" + "═" * 79)
            print("充值確認")
            print("═" * 79)
            print(f"卡號：      {card.card_no}")
            print(f"當前餘額：  {Formatter.format_currency(card.balance)}")
            print(f"充值金額：  {Formatter.format_currency(amount)}")
            print(f"充值後餘額：{Formatter.format_currency(card.balance + amount)}")
            print(f"支付方式：  {payment_method}")
            print("═" * 79)
            
            if not BaseUI.confirm_action("\n確認充值？"):
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            
            # 執行充值
            BaseUI.show_loading("充值中...")
            
            result = self.admin_service.rpc_call("user_recharge_card", {
                "p_card_id": card.id,
                "p_amount": amount,
                "p_payment_method": payment_method,
                "p_tag": {"admin_recharge": True, "admin_name": self.current_admin_name},
                "p_reason": f"Admin recharge for card {card.card_no}",
                "p_session_id": None
            })
            
            if result and len(result) > 0:
                tx_info = result[0]
                BaseUI.show_success("充值成功", {
                    "交易號": tx_info.get('tx_no'),
                    "充值金額": Formatter.format_currency(amount),
                    "新餘額": Formatter.format_currency(card.balance + amount)
                })
                
                # 更新本地卡片餘額
                card.balance += amount
            else:
                BaseUI.show_error("充值失敗")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"充值失敗：{e}")
            BaseUI.pause()
    
    def _refund_card_directly(self, card):
        """直接為卡片申請退款（從卡片菜單）"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"申請退款 - {card.card_no}")
            
            # 獲取卡片交易記錄
            transactions = self.admin_service.get_card_transactions(card.id, 50)
            
            if not transactions:
                BaseUI.show_info("該卡片暫無交易記錄")
                BaseUI.pause()
                return
            
            # 過濾出可退款的交易
            refundable_txs = [tx for tx in transactions 
                            if tx.tx_type == 'payment' and tx.status in ['completed', 'refunded']]
            
            if not refundable_txs:
                BaseUI.show_info("沒有可退款的交易")
                BaseUI.pause()
                return
            
            # 顯示可退款交易
            print("\n📊 可退款交易：")
            print("─" * 79)
            print(f"{'序號':<4} {'交易號':<20} {'金額':<12} {'狀態':<10} {'時間':<20}")
            print("─" * 79)
            
            for i, tx in enumerate(refundable_txs[:20], 1):
                print(f"{i:<4} {tx.tx_no:<20} "
                      f"{Formatter.format_currency(tx.final_amount):<12} "
                      f"{tx.get_status_display():<10} "
                      f"{tx.format_datetime('created_at'):<20}")
            
            print("─" * 79)
            
            # 選擇交易
            choice = input(f"\n請選擇要退款的交易 (1-{min(len(refundable_txs), 20)}) 或按 Enter 取消: ").strip()
            
            if not choice:
                return
            
            if not choice.isdigit() or int(choice) < 1 or int(choice) > min(len(refundable_txs), 20):
                BaseUI.show_error("無效的選擇")
                BaseUI.pause()
                return
            
            selected_tx = refundable_txs[int(choice) - 1]
            
            # 輸入退款金額
            print(f"\n原交易金額：{Formatter.format_currency(selected_tx.final_amount)}")
            print("提示：輸入退款金額（留空則全額退款）")
            amount_str = input("退款金額: ").strip()
            
            if not amount_str:
                refund_amount = selected_tx.final_amount
            else:
                try:
                    refund_amount = float(amount_str)
                    if refund_amount <= 0 or refund_amount > selected_tx.final_amount:
                        BaseUI.show_error(f"退款金額必須在 0 到 {selected_tx.final_amount} 之間")
                        BaseUI.pause()
                        return
                except ValueError:
                    BaseUI.show_error("無效的金額")
                    BaseUI.pause()
                    return
            
            # 輸入退款原因
            reason = input("\n退款原因（可選）: ").strip() or "Admin initiated refund"
            
            # 確認退款
            print("\n" + "═" * 79)
            print("退款確認")
            print("═" * 79)
            print(f"交易號：    {selected_tx.tx_no}")
            print(f"原金額：    {Formatter.format_currency(selected_tx.final_amount)}")
            print(f"退款金額：  {Formatter.format_currency(refund_amount)}")
            print(f"退款原因：  {reason}")
            print("═" * 79)
            
            if not BaseUI.confirm_action("\n確認退款？"):
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            
            # 執行退款
            BaseUI.show_info("管理員退款功能需要商戶授權，請使用商戶賬號進行退款操作")
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"退款失敗：{e}")
            BaseUI.pause()
    
    def _manage_card_bindings(self, card):
        """管理卡片綁定"""
        while True:
            try:
                BaseUI.clear_screen()
                BaseUI.show_header(f"管理綁定 - {card.card_no}")
                
                # 獲取卡片綁定信息
                bindings = self.member_service.get_card_bindings(card.id)
                
                # 顯示卡片信息
                print(f"\n卡號：{card.card_no}")
                print(f"類型：{card.get_card_type_display()}")
                print(f"持卡人：{card.owner_name if hasattr(card, 'owner_name') else 'N/A'}")
                print("─" * 79)
                
                # 顯示綁定列表
                if bindings:
                    print(f"\n🔗 當前綁定（{len(bindings)} 個）：")
                    print("─" * 79)
                    print(f"{'序號':<4} {'會員號':<12} {'姓名':<10} {'手機':<13} {'綁定時間':<20}")
                    print("─" * 79)
                    
                    for i, binding in enumerate(bindings, 1):
                        # 獲取綁定會員信息
                        member = self.member_service.get_member_by_id(binding.member_id)
                        if member:
                            print(f"{i:<4} {member.member_no:<12} {member.name:<10} "
                                  f"{member.phone:<13} {binding.format_datetime('created_at'):<20}")
                    
                    print("─" * 79)
                else:
                    print("\n🔗 當前綁定：無")
                    print("─" * 79)
                
                # 操作選項
                print("\n操作選項：")
                print("  [A] 新增綁定")
                if bindings:
                    print(f"  [1-{len(bindings)}] 選擇綁定進行解除")
                print("  [Q] 返回")
                
                choice = input("\n請選擇: ").strip().upper()
                
                if choice == 'Q':
                    break
                elif choice == 'A':
                    self._add_card_binding(card)
                elif choice.isdigit() and bindings:
                    idx = int(choice)
                    if 1 <= idx <= len(bindings):
                        selected_binding = bindings[idx - 1]
                        self._remove_card_binding(card, selected_binding)
                    else:
                        BaseUI.show_error(f"請輸入 1-{len(bindings)}")
                        BaseUI.pause()
                else:
                    BaseUI.show_error("無效的選擇")
                    BaseUI.pause()
                
            except Exception as e:
                BaseUI.show_error(f"操作失敗：{e}")
                BaseUI.pause()
                break
    
    def _add_card_binding(self, card):
        """新增卡片綁定"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"新增綁定 - {card.card_no}")
            
            print("\n請輸入要綁定的會員信息：")
            print("（可以輸入會員號、手機號或郵箱）")
            
            keyword = input("\n會員識別碼: ").strip()
            
            if not keyword:
                return
            
            # 搜尋會員
            BaseUI.show_loading("搜尋中...")
            members = self.member_service.search_members(keyword, 10)
            
            if not members:
                BaseUI.show_error("未找到匹配的會員")
                BaseUI.pause()
                return
            
            # 顯示搜尋結果
            BaseUI.clear_screen()
            print(f"\n搜尋結果（找到 {len(members)} 個會員）：")
            print("─" * 79)
            print(f"{'序號':<4} {'會員號':<12} {'姓名':<10} {'手機':<13}")
            print("─" * 79)
            
            for i, member in enumerate(members, 1):
                print(f"{i:<4} {member.member_no:<12} {member.name:<10} {member.phone:<13}")
            
            print("─" * 79)
            
            # 選擇會員
            choice = input(f"\n請選擇要綁定的會員 (1-{len(members)}) 或按 Enter 取消: ").strip()
            
            if not choice:
                return
            
            if not choice.isdigit() or int(choice) < 1 or int(choice) > len(members):
                BaseUI.show_error("無效的選擇")
                BaseUI.pause()
                return
            
            selected_member = members[int(choice) - 1]
            
            # 確認綁定
            print("\n" + "═" * 79)
            print("綁定確認")
            print("═" * 79)
            print(f"卡號：    {card.card_no}")
            print(f"綁定給：  {selected_member.name} ({selected_member.member_no})")
            print("═" * 79)
            
            if not BaseUI.confirm_action("\n確認綁定？"):
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            
            # 執行綁定
            BaseUI.show_loading("綁定中...")
            
            result = self.member_service.rpc_call("bind_card_to_member", {
                "p_card_id": card.id,
                "p_member_id": selected_member.id
            })
            
            if result:
                BaseUI.show_success("綁定成功", {
                    "卡號": card.card_no,
                    "綁定給": f"{selected_member.name} ({selected_member.member_no})"
                })
            else:
                BaseUI.show_error("綁定失敗")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"綁定失敗：{e}")
            BaseUI.pause()
    
    def _remove_card_binding(self, card, binding):
        """解除卡片綁定"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"解除綁定 - {card.card_no}")
            
            # 獲取綁定會員信息
            member = self.member_service.get_member_by_id(binding.member_id)
            
            if not member:
                BaseUI.show_error("無法獲取會員信息")
                BaseUI.pause()
                return
            
            # 確認解除
            print("\n" + "═" * 79)
            print("解除綁定確認")
            print("═" * 79)
            print(f"卡號：      {card.card_no}")
            print(f"解除綁定：  {member.name} ({member.member_no})")
            print(f"綁定時間：  {binding.format_datetime('created_at')}")
            print("═" * 79)
            
            if not BaseUI.confirm_action("\n確認解除綁定？"):
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            
            # 執行解除綁定
            BaseUI.show_loading("解除中...")
            
            result = self.member_service.rpc_call("unbind_card_from_member", {
                "p_card_id": card.id,
                "p_member_id": member.id
            })
            
            if result:
                BaseUI.show_success("解除綁定成功", {
                    "卡號": card.card_no,
                    "已解除": f"{member.name} ({member.member_no})"
                })
            else:
                BaseUI.show_error("解除綁定失敗")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"解除綁定失敗：{e}")
            BaseUI.pause()