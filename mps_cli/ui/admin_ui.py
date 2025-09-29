from typing import Optional
from services.admin_service import AdminService
from services.member_service import MemberService
from services.qr_service import QRService
from ui.components.menu import Menu, SimpleMenu
from ui.components.table import Table
from ui.components.form import QuickForm, ValidationForm
from ui.base_ui import BaseUI, StatusDisplay
from utils.formatters import Formatter
from utils.validators import Validator
from utils.logger import ui_logger

class AdminUI:
    """管理員用戶界面"""
    
    def __init__(self):
        self.admin_service = AdminService()
        self.member_service = MemberService()
        self.qr_service = QRService()
        self.current_admin_name: Optional[str] = None
    
    def start(self):
        """啟動管理員界面"""
        try:
            # 管理員身份驗證
            if not self._admin_login():
                return
            
            # 主菜單
            self._show_main_menu()
            
        except KeyboardInterrupt:
            print("\n👋 再見！")
        except Exception as e:
            BaseUI.show_error(f"系統錯誤: {e}")
        finally:
            if self.current_admin_name:
                ui_logger.log_logout("admin")
    
    def _admin_login(self) -> bool:
        """管理員身份驗證"""
        BaseUI.clear_screen()
        BaseUI.show_header("管理員控制台登入")
        
        print("請輸入管理員信息進行身份驗證")
        admin_name = input("管理員姓名: ").strip()
        
        if not admin_name:
            BaseUI.show_error("請輸入管理員姓名")
            BaseUI.pause()
            return False
        
        # 簡化的身份驗證（實際應用中應該有更嚴格的驗證）
        admin_code = input("管理員代碼 (可選): ").strip()
        
        try:
            # 驗證管理員權限
            if not self.admin_service.validate_admin_access():
                BaseUI.show_error("管理員權限驗證失敗")
                BaseUI.pause()
                return False
            
            self.current_admin_name = admin_name
            
            ui_logger.log_login("admin", admin_name)
            
            BaseUI.show_success(f"登入成功！管理員: {admin_name}")
            BaseUI.pause()
            return True
            
        except Exception as e:
            BaseUI.show_error(f"登入失敗: {e}")
            BaseUI.pause()
            return False
    
    def _show_main_menu(self):
        """顯示主菜單"""
        options = [
            "會員管理",
            "商戶管理",
            "卡片管理",
            "系統統計",
            "系統維護",
            "退出系統"
        ]
        
        handlers = [
            self._member_management,
            self._merchant_management,
            self._card_management,
            self._system_statistics,
            self._system_maintenance,
            lambda: False  # 退出
        ]
        
        menu = Menu(f"MPS 管理控制台 - {self.current_admin_name}", options, handlers)
        menu.run()
    
    def _member_management(self):
        """會員管理"""
        while True:
            BaseUI.clear_screen()
            BaseUI.show_header("會員管理")
            
            options = [
                "創建新會員",
                "查看會員信息",
                "搜索會員",
                "暫停會員",
                "返回主菜單"
            ]
            
            choice = BaseUI.show_menu(options, "會員管理操作")
            
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
            BaseUI.show_header("創建新會員")
            
            # 使用驗證表單收集會員信息
            member_data = ValidationForm.create_member_form()
            
            # 確認創建
            print(f"\n會員信息確認:")
            print(f"姓名: {member_data['name']}")
            print(f"手機: {member_data['phone']}")
            print(f"郵箱: {member_data['email']}")
            
            if member_data.get('bind_external'):
                print(f"外部平台: {member_data['provider']}")
                print(f"外部 ID: {member_data['external_id']}")
            
            if not QuickForm.get_confirmation("確認創建會員？"):
                BaseUI.show_info("會員創建已取消")
                BaseUI.pause()
                return
            
            # 執行創建
            BaseUI.show_loading("正在創建會員...")
            
            member_id = self.admin_service.create_member_profile(
                member_data['name'],
                member_data['phone'],
                member_data['email'],
                member_data.get('provider'),
                member_data.get('external_id')
            )
            
            BaseUI.clear_screen()
            BaseUI.show_success("會員創建成功！", {
                "會員 ID": member_id,
                "姓名": member_data['name'],
                "手機": member_data['phone'],
                "自動生成": "標準卡已自動生成並綁定"
            })
            
            ui_logger.log_user_action("創建會員", {
                "member_id": member_id,
                "name": member_data['name']
            })
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"會員創建失敗: {e}")
            BaseUI.pause()
    
    def _view_member_info(self):
        """查看會員信息"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("查看會員信息")
            
            member_id = QuickForm.get_text("請輸入會員 ID", True, 
                                         Validator.validate_member_id,
                                         "請輸入有效的 UUID 格式會員 ID")
            
            BaseUI.show_loading("正在查詢會員信息...")
            
            # 獲取會員詳細信息
            member = self.member_service.get_member_by_id(member_id)
            
            if not member:
                BaseUI.show_error("會員不存在")
                BaseUI.pause()
                return
            
            # 獲取會員摘要
            summary = self.member_service.get_member_summary(member_id)
            
            BaseUI.clear_screen()
            
            # 顯示會員基本信息
            print("📋 會員基本信息:")
            print("─" * 40)
            member_info = member.to_display_dict()
            for key, value in member_info.items():
                print(f"  {key}: {value}")
            
            # 顯示卡片統計
            print(f"\n💳 卡片統計:")
            print("─" * 40)
            print(f"  總卡片數: {summary.get('cards_count', 0)} 張")
            print(f"  激活卡片: {summary.get('active_cards_count', 0)} 張")
            print(f"  總餘額: {Formatter.format_currency(summary.get('total_balance', 0))}")
            print(f"  總積分: {Formatter.format_points(summary.get('total_points', 0))}")
            print(f"  最高等級: {Formatter.format_level(summary.get('highest_level', 0))}")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"查詢失敗: {e}")
            BaseUI.pause()
    
    def _search_members(self):
        """搜索會員"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("搜索會員")
            
            keyword = QuickForm.get_text("請輸入搜索關鍵字", True,
                                       help_text="可搜索姓名、手機號、郵箱、會員號")
            
            BaseUI.show_loading("正在搜索...")
            
            members = self.member_service.search_members(keyword, 50)
            
            if not members:
                BaseUI.show_info("未找到匹配的會員")
                BaseUI.pause()
                return
            
            BaseUI.clear_screen()
            
            # 顯示搜索結果
            headers = ["會員號", "姓名", "手機", "狀態", "創建時間"]
            data = []
            
            for member in members:
                data.append({
                    "會員號": member.member_no or "",
                    "姓名": member.name or "",
                    "手機": Formatter.format_phone(member.phone or ""),
                    "狀態": member.get_status_display(),
                    "創建時間": member.format_date("created_at")
                })
            
            table = Table(headers, data, f"搜索結果 (關鍵字: {keyword})")
            table.display()
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"搜索失敗: {e}")
            BaseUI.pause()
    
    def _suspend_member(self):
        """暫停會員"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("暫停會員")
            
            member_id = QuickForm.get_text("請輸入要暫停的會員 ID", True,
                                         Validator.validate_member_id)
            
            # 查詢會員信息
            BaseUI.show_loading("正在查詢會員信息...")
            member = self.member_service.get_member_by_id(member_id)
            
            if not member:
                BaseUI.show_error("會員不存在")
                BaseUI.pause()
                return
            
            # 顯示會員信息
            print(f"\n會員信息:")
            print(f"  姓名: {member.name}")
            print(f"  手機: {member.phone}")
            print(f"  當前狀態: {member.get_status_display()}")
            
            if member.status == "suspended":
                BaseUI.show_warning("該會員已經處於暫停狀態")
                BaseUI.pause()
                return
            
            # 確認暫停
            if not QuickForm.get_confirmation(f"確認暫停會員 {member.name}？"):
                BaseUI.show_info("操作已取消")
                BaseUI.pause()
                return
            
            # 執行暫停
            BaseUI.show_loading("正在暫停會員...")
            result = self.admin_service.suspend_member(member_id)
            
            if result:
                BaseUI.show_success("會員暫停成功")
                ui_logger.log_user_action("暫停會員", {
                    "member_id": member_id,
                    "member_name": member.name
                })
            else:
                BaseUI.show_error("會員暫停失敗")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"暫停失敗: {e}")
            BaseUI.pause()
    
    def _merchant_management(self):
        """商戶管理"""
        BaseUI.show_info("商戶管理功能開發中...")
        BaseUI.pause()
    
    def _card_management(self):
        """卡片管理"""
        while True:
            BaseUI.clear_screen()
            BaseUI.show_header("卡片管理")
            
            options = [
                "凍結卡片",
                "解凍卡片",
                "調整積分",
                "搜索卡片",
                "返回主菜單"
            ]
            
            choice = BaseUI.show_menu(options, "卡片管理操作")
            
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
            BaseUI.show_header("凍結卡片")
            
            card_id = QuickForm.get_text("請輸入要凍結的卡片 ID", True,
                                       Validator.validate_card_id)
            
            # 查詢卡片信息
            BaseUI.show_loading("正在查詢卡片信息...")
            card_detail = self.admin_service.get_card_detail(card_id)
            
            if not card_detail:
                BaseUI.show_error("卡片不存在")
                BaseUI.pause()
                return
            
            card = card_detail["card"]
            owner = card_detail["owner"]
            
            # 顯示卡片信息
            print(f"\n卡片信息:")
            print(f"  卡號: {card.card_no}")
            print(f"  類型: {card.get_card_type_display()}")
            print(f"  擁有者: {owner.name if owner else '未知'}")
            print(f"  當前狀態: {card.get_status_display()}")
            print(f"  餘額: {Formatter.format_currency(card.balance)}")
            
            if card.status == "inactive":
                BaseUI.show_warning("該卡片已經處於凍結狀態")
                BaseUI.pause()
                return
            
            # 確認凍結
            if not QuickForm.get_confirmation(f"確認凍結卡片 {card.card_no}？"):
                BaseUI.show_info("操作已取消")
                BaseUI.pause()
                return
            
            # 執行凍結
            BaseUI.show_loading("正在凍結卡片...")
            result = self.admin_service.freeze_card(card_id)
            
            if result:
                BaseUI.show_success("卡片凍結成功")
                ui_logger.log_user_action("凍結卡片", {
                    "card_id": card_id,
                    "card_no": card.card_no
                })
            else:
                BaseUI.show_error("卡片凍結失敗")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"凍結失敗: {e}")
            BaseUI.pause()
    
    def _unfreeze_card(self):
        """解凍卡片"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("解凍卡片")
            
            card_id = QuickForm.get_text("請輸入要解凍的卡片 ID", True,
                                       Validator.validate_card_id)
            
            # 查詢卡片信息
            BaseUI.show_loading("正在查詢卡片信息...")
            card_detail = self.admin_service.get_card_detail(card_id)
            
            if not card_detail:
                BaseUI.show_error("卡片不存在")
                BaseUI.pause()
                return
            
            card = card_detail["card"]
            
            if card.status != "inactive":
                BaseUI.show_warning("該卡片不是凍結狀態")
                BaseUI.pause()
                return
            
            # 確認解凍
            if not QuickForm.get_confirmation(f"確認解凍卡片 {card.card_no}？"):
                BaseUI.show_info("操作已取消")
                BaseUI.pause()
                return
            
            # 執行解凍
            BaseUI.show_loading("正在解凍卡片...")
            result = self.admin_service.unfreeze_card(card_id)
            
            if result:
                BaseUI.show_success("卡片解凍成功")
                ui_logger.log_user_action("解凍卡片", {
                    "card_id": card_id,
                    "card_no": card.card_no
                })
            else:
                BaseUI.show_error("卡片解凍失敗")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"解凍失敗: {e}")
            BaseUI.pause()
    
    def _adjust_points(self):
        """調整積分"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("調整積分")
            
            card_id = QuickForm.get_text("請輸入卡片 ID", True,
                                       Validator.validate_card_id)
            
            # 查詢卡片信息
            BaseUI.show_loading("正在查詢卡片信息...")
            card_detail = self.admin_service.get_card_detail(card_id)
            
            if not card_detail:
                BaseUI.show_error("卡片不存在")
                BaseUI.pause()
                return
            
            card = card_detail["card"]
            
            # 顯示當前積分信息
            print(f"\n當前積分信息:")
            print(f"  卡號: {card.card_no}")
            print(f"  當前積分: {Formatter.format_points(card.points or 0)}")
            print(f"  當前等級: {card.get_level_display()}")
            
            # 輸入積分變化
            while True:
                try:
                    delta_points = int(input("請輸入積分變化量 (正數增加，負數減少): "))
                    
                    new_points = max(0, (card.points or 0) + delta_points)
                    print(f"調整後積分: {Formatter.format_points(new_points)}")
                    
                    break
                except ValueError:
                    print("❌ 請輸入有效的整數")
            
            reason = input("請輸入調整原因: ").strip() or "manual_adjust"
            
            # 確認調整
            if not QuickForm.get_confirmation("確認調整積分？"):
                BaseUI.show_info("操作已取消")
                BaseUI.pause()
                return
            
            # 執行調整
            BaseUI.show_loading("正在調整積分...")
            result = self.admin_service.update_points_and_level(card_id, delta_points, reason)
            
            if result:
                BaseUI.show_success("積分調整成功", {
                    "變化量": f"{delta_points:+d}",
                    "調整後": f"{new_points:,} 分",
                    "原因": reason
                })
                ui_logger.log_user_action("調整積分", {
                    "card_id": card_id,
                    "delta_points": delta_points,
                    "reason": reason
                })
            else:
                BaseUI.show_error("積分調整失敗")
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"調整失敗: {e}")
            BaseUI.pause()
    
    def _search_cards(self):
        """搜索卡片"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("搜索卡片")
            
            keyword = QuickForm.get_text("請輸入搜索關鍵字", True,
                                       help_text="可搜索卡號、卡片名稱")
            
            BaseUI.show_loading("正在搜索...")
            
            cards = self.admin_service.search_cards(keyword, 50)
            
            if not cards:
                BaseUI.show_info("未找到匹配的卡片")
                BaseUI.pause()
                return
            
            BaseUI.clear_screen()
            
            # 顯示搜索結果
            headers = ["卡號", "類型", "擁有者", "餘額", "積分", "狀態"]
            data = []
            
            for card in cards:
                # 獲取擁有者信息
                owner = None
                if card.owner_member_id:
                    owner = self.member_service.get_member_by_id(card.owner_member_id)
                
                data.append({
                    "卡號": card.card_no or "",
                    "類型": card.get_card_type_display(),
                    "擁有者": owner.name if owner else "未知",
                    "餘額": Formatter.format_currency(card.balance),
                    "積分": Formatter.format_points(card.points or 0),
                    "狀態": card.get_status_display()
                })
            
            table = Table(headers, data, f"搜索結果 (關鍵字: {keyword})")
            table.display()
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"搜索失敗: {e}")
            BaseUI.pause()
    
    def _system_statistics(self):
        """系統統計"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("系統統計")
            
            BaseUI.show_loading("正在獲取系統統計...")
            
            stats = self.admin_service.get_system_statistics()
            
            if not stats:
                BaseUI.show_error("無法獲取系統統計")
                BaseUI.pause()
                return
            
            # 顯示統計信息
            print("📊 系統統計信息:")
            print("═" * 50)
            
            # 會員統計
            members = stats.get("members", {})
            print(f"\n👥 會員統計:")
            print(f"  總會員數: {members.get('total', 0):,}")
            print(f"  激活會員: {members.get('active', 0):,}")
            print(f"  非激活會員: {members.get('inactive', 0):,}")
            
            # 卡片統計
            cards = stats.get("cards", {})
            print(f"\n💳 卡片統計:")
            print(f"  總卡片數: {cards.get('total', 0):,}")
            print(f"  激活卡片: {cards.get('active', 0):,}")
            print(f"  非激活卡片: {cards.get('inactive', 0):,}")
            
            # 商戶統計
            merchants = stats.get("merchants", {})
            print(f"\n🏪 商戶統計:")
            print(f"  總商戶數: {merchants.get('total', 0):,}")
            print(f"  激活商戶: {merchants.get('active', 0):,}")
            print(f"  停用商戶: {merchants.get('inactive', 0):,}")
            
            # 今日交易統計
            today = stats.get("today", {})
            print(f"\n📈 今日交易:")
            print(f"  交易筆數: {today.get('transaction_count', 0):,}")
            print(f"  支付金額: {Formatter.format_currency(today.get('payment_amount', 0))}")
            
            print("═" * 50)
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"獲取統計失敗: {e}")
            BaseUI.pause()
    
    def _system_maintenance(self):
        """系統維護"""
        while True:
            BaseUI.clear_screen()
            BaseUI.show_header("系統維護")
            
            options = [
                "批量輪換 QR 碼",
                "清理過期數據",
                "系統健康檢查",
                "返回主菜單"
            ]
            
            choice = BaseUI.show_menu(options, "系統維護操作")
            
            if choice == 1:
                self._batch_rotate_qr()
            elif choice == 2:
                BaseUI.show_info("清理過期數據功能開發中...")
                BaseUI.pause()
            elif choice == 3:
                BaseUI.show_info("系統健康檢查功能開發中...")
                BaseUI.pause()
            elif choice == 4:
                break
    
    def _batch_rotate_qr(self):
        """批量輪換 QR 碼"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("批量輪換 QR 碼")
            
            print("⚠️  此操作將輪換所有激活的預付卡和企業卡的 QR 碼")
            print("   輪換後，舊的 QR 碼將立即失效")
            
            # 輸入 TTL 秒數
            while True:
                try:
                    ttl_seconds = int(input("請輸入新 QR 碼有效期 (秒，建議 300-3600): "))
                    if 60 <= ttl_seconds <= 7200:  # 1分鐘到2小時
                        break
                    print("❌ 有效期應在 60-7200 秒之間")
                except ValueError:
                    print("❌ 請輸入有效的整數")
            
            # 確認操作
            ttl_minutes = ttl_seconds // 60
            if not QuickForm.get_confirmation(f"確認批量輪換 QR 碼？(有效期: {ttl_minutes} 分鐘)"):
                BaseUI.show_info("操作已取消")
                BaseUI.pause()
                return
            
            # 執行批量輪換
            BaseUI.show_loading("正在批量輪換 QR 碼...")
            affected_count = self.admin_service.batch_rotate_qr_tokens(ttl_seconds)
            
            BaseUI.show_success("批量 QR 碼輪換完成", {
                "影響卡片數": f"{affected_count} 張",
                "新有效期": f"{ttl_minutes} 分鐘",
                "執行時間": Formatter.format_datetime(None)  # 當前時間
            })
            
            ui_logger.log_user_action("批量輪換 QR 碼", {
                "affected_count": affected_count,
                "ttl_seconds": ttl_seconds
            })
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"批量輪換失敗: {e}")
            BaseUI.pause()