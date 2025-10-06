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
            "Change Password",
            "Exit System"
        ]
        
        handlers = [
            self._show_my_cards,
            self._generate_qr,
            self._recharge_card,
            self._view_transactions,
            self._bind_new_card,
            self._view_points_level,
            self._change_password,
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
        """生成付款 QR 碼 - 商業版"""
        try:
            BaseUI.clear_screen()
            print("╔═══════════════════════════════════════════════════════════════════════════╗")
            print("║                          生成付款 QR 碼                                   ║")
            print("╚═══════════════════════════════════════════════════════════════════════════╝")
            
            # Step 1: 獲取可用卡片（排除 Corporate Card）
            BaseUI.show_loading("正在獲取卡片信息...")
            all_cards = self.member_service.get_member_cards(self.current_member_id)
            
            # 過濾：只有 Standard 和 Voucher 可以生成 QR
            available_cards = [
                card for card in all_cards 
                if card.card_type in ['standard', 'voucher'] and card.status == 'active'
            ]
            
            if not available_cards:
                BaseUI.clear_screen()
                print("\n⚠️  沒有可用的卡片")
                print("\n說明：")
                print("  • 標準卡和代金券卡可以生成 QR 碼")
                print("  • 企業折扣卡不能生成 QR 碼（只提供折扣）")
                print("  • 卡片必須處於激活狀態")
                BaseUI.pause()
                return
            
            # Step 2: 顯示卡片列表
            BaseUI.clear_screen()
            print("╔═══════════════════════════════════════════════════════════════════════════╗")
            print("║                          選擇卡片                                         ║")
            print("╚═══════════════════════════════════════════════════════════════════════════╝")
            print("\n可用卡片：")
            print("─" * 79)
            print(f"{'序號':<4} {'卡號':<18} {'類型':<12} {'餘額':<14} {'積分':<8} {'狀態':<8}")
            print("─" * 79)
            
            for i, card in enumerate(available_cards, 1):
                print(f"{i:<4} {card.card_no:<18} {card.get_card_type_display():<12} "
                      f"{Formatter.format_currency(card.balance):<14} "
                      f"{card.points or 0:<8} {card.get_status_display():<8}")
            
            print("─" * 79)
            
            # Step 3: 選擇卡片
            while True:
                try:
                    choice = input(f"\n請選擇卡片 (1-{len(available_cards)}) 或 q 返回: ").strip()
                    if choice.lower() == 'q':
                        return
                    
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(available_cards):
                        selected_card = available_cards[choice_num - 1]
                        break
                    print(f"❌ 請輸入 1-{len(available_cards)}")
                except ValueError:
                    print("❌ 請輸入有效的數字")
            
            # Step 4: 確認生成
            print(f"\n選中卡片：{selected_card.card_no} ({selected_card.get_card_type_display()})")
            print(f"當前餘額：{Formatter.format_currency(selected_card.balance)}")
            
            if not BaseUI.confirm("\n確認生成 QR 碼？"):
                print("❌ 已取消")
                BaseUI.pause()
                return
            
            # Step 5: 生成 QR 碼
            BaseUI.show_loading("正在生成 QR 碼...")
            qr_result = self.qr_service.rotate_qr(selected_card.id, ttl_seconds=900)
            
            # Step 6: 顯示 QR 碼
            BaseUI.clear_screen()
            self._display_qr_code(qr_result, selected_card)
            
            # 記錄日誌
            ui_logger.log_user_action("Generate QR Code", {
                "card_id": selected_card.id,
                "card_no": selected_card.card_no
            })
            
            # Step 7: 操作菜單
            self._qr_action_menu(selected_card, qr_result)
            
        except Exception as e:
            BaseUI.show_error(f"生成 QR 碼失敗: {e}")
            ui_logger.log_error("Generate QR Code", str(e))
            
            # 友好的錯誤提示
            if "PERMISSION_DENIED" in str(e):
                print("\n💡 提示：沒有權限生成 QR 碼")
            elif "CARD_NOT_FOUND" in str(e):
                print("\n💡 提示：卡片不存在或未激活")
            elif "CARD_TYPE_NOT_SUPPORTED" in str(e):
                print("\n💡 提示：此卡片類型不支持生成 QR 碼")
            
            BaseUI.pause()
    
    def _display_qr_code(self, qr_result: Dict, card: Card):
        """顯示 QR 碼信息"""
        qr_plain = qr_result.get('qr_plain')
        expires_at = qr_result.get('expires_at')
        
        print("╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║                          付款 QR 碼                                       ║")
        print("╠═══════════════════════════════════════════════════════════════════════════╣")
        print(f"║  QR 碼:    {qr_plain:<60} ║")
        print(f"║  卡號:     {card.card_no:<60} ║")
        print(f"║  類型:     {card.get_card_type_display():<60} ║")
        print(f"║  餘額:     {Formatter.format_currency(card.balance):<60} ║")
        print("╠═══════════════════════════════════════════════════════════════════════════╣")
        print(f"║  有效期至: {expires_at:<60} ║")
        print(f"║  有效時長: 15 分鐘{'':>56} ║")
        print("╠═══════════════════════════════════════════════════════════════════════════╣")
        print("║  使用說明：                                                               ║")
        print("║  1. 請向商戶出示此 QR 碼                                                  ║")
        print("║  2. 商戶掃碼後輸入金額即可完成支付                                        ║")
        print("║  3. QR 碼過期後需要重新生成                                               ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    def _qr_action_menu(self, card: Card, qr_result: Dict):
        """QR 碼操作菜單"""
        while True:
            print("\n操作選項：")
            print("  1. 刷新 QR 碼")
            print("  2. 撤銷 QR 碼")
            print("  3. 返回主菜單")
            
            choice = input("\n請選擇 (1-3): ").strip()
            
            if choice == '1':
                # 刷新 QR 碼
                if BaseUI.confirm("確認刷新 QR 碼？"):
                    try:
                        BaseUI.show_loading("正在刷新...")
                        new_qr = self.qr_service.rotate_qr(card.id, ttl_seconds=900)
                        BaseUI.clear_screen()
                        self._display_qr_code(new_qr, card)
                        BaseUI.show_success("✅ QR 碼已刷新")
                        qr_result = new_qr  # 更新 QR 結果
                    except Exception as e:
                        BaseUI.show_error(f"刷新失敗: {e}")
            
            elif choice == '2':
                # 撤銷 QR 碼
                if BaseUI.confirm("確認撤銷 QR 碼？撤銷後此 QR 碼將立即失效。"):
                    try:
                        BaseUI.show_loading("正在撤銷...")
                        self.qr_service.revoke_qr(card.id)
                        BaseUI.show_success("✅ QR 碼已撤銷")
                        BaseUI.pause()
                        return
                    except Exception as e:
                        BaseUI.show_error(f"撤銷失敗: {e}")
            
            elif choice == '3':
                return
            
            else:
                print("❌ 請輸入 1-3")
    
    def _recharge_card(self):
        """充值卡片 - 商業版（只支持 Standard Card）"""
        try:
            BaseUI.clear_screen()
            print("╔═══════════════════════════════════════════════════════════════════════════╗")
            print("║                          卡片充值                                         ║")
            print("║                    （只支持標準卡充值）                                   ║")
            print("╚═══════════════════════════════════════════════════════════════════════════╝")
            
            # Step 1: 獲取可充值卡片（只有 Standard Card）
            BaseUI.show_loading("正在獲取卡片信息...")
            all_cards = self.member_service.get_member_cards(self.current_member_id)
            
            rechargeable_cards = [
                card for card in all_cards 
                if card.card_type == 'standard' and card.status == 'active'
            ]
            
            if not rechargeable_cards:
                BaseUI.clear_screen()
                print("\n⚠️  沒有可充值的卡片")
                print("\n說明：")
                print("  • 只有標準卡支持充值")
                print("  • 企業折扣卡和代金券卡不可充值")
                print("  • 卡片必須處於激活狀態")
                BaseUI.pause()
                return
            
            # Step 2: 顯示卡片列表
            BaseUI.clear_screen()
            print("╔═══════════════════════════════════════════════════════════════════════════╗")
            print("║                          選擇卡片                                         ║")
            print("╚═══════════════════════════════════════════════════════════════════════════╝")
            print("\n可充值卡片：")
            print("─" * 79)
            print(f"{'序號':<4} {'卡號':<18} {'當前餘額':<14} {'積分':<8} {'等級':<12}")
            print("─" * 79)
            
            for i, card in enumerate(rechargeable_cards, 1):
                print(f"{i:<4} {card.card_no:<18} "
                      f"{Formatter.format_currency(card.balance):<14} "
                      f"{card.points or 0:<8} {card.get_level_display():<12}")
            
            print("─" * 79)
            
            # Step 3: 選擇卡片
            while True:
                try:
                    choice = input(f"\n請選擇卡片 (1-{len(rechargeable_cards)}) 或 q 返回: ").strip()
                    if choice.lower() == 'q':
                        return
                    
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(rechargeable_cards):
                        selected_card = rechargeable_cards[choice_num - 1]
                        break
                    print(f"❌ 請輸入 1-{len(rechargeable_cards)}")
                except ValueError:
                    print("❌ 請輸入有效的數字")
            
            # Step 4: 輸入充值金額
            print(f"\n選中卡片：{selected_card.card_no}")
            print(f"當前餘額：{Formatter.format_currency(selected_card.balance)}")
            
            while True:
                try:
                    amount_str = input("\n請輸入充值金額 (1-50000): ").strip()
                    if not amount_str:
                        print("❌ 金額不能為空")
                        continue
                    
                    amount = Decimal(amount_str)
                    
                    if amount < Decimal("1"):
                        print("❌ 充值金額不能小於 ¥1")
                        continue
                    if amount > Decimal("50000"):
                        print("❌ 單次充值金額不能超過 ¥50,000")
                        continue
                    
                    break
                except (ValueError, Exception):
                    print("❌ 請輸入有效的金額")
            
            # Step 5: 選擇支付方式
            payment_methods = [
                {"code": "wechat", "name": "微信支付", "icon": "💚"},
                {"code": "alipay", "name": "支付寶", "icon": "💙"},
                {"code": "bank", "name": "銀行卡", "icon": "💳"},
                {"code": "cash", "name": "現金", "icon": "💵"}
            ]
            
            print("\n支付方式：")
            for i, method in enumerate(payment_methods, 1):
                print(f"  {i}. {method['icon']} {method['name']}")
            
            while True:
                try:
                    method_choice = int(input(f"\n請選擇支付方式 (1-{len(payment_methods)}): "))
                    if 1 <= method_choice <= len(payment_methods):
                        selected_method = payment_methods[method_choice - 1]
                        break
                    print(f"❌ 請輸入 1-{len(payment_methods)}")
                except ValueError:
                    print("❌ 請輸入有效的數字")
            
            # Step 6: 確認充值
            print("\n" + "═" * 79)
            print("充值信息確認")
            print("═" * 79)
            print(f"卡號：        {selected_card.card_no}")
            print(f"當前餘額：    {Formatter.format_currency(selected_card.balance)}")
            print(f"充值金額：    {Formatter.format_currency(amount)}")
            print(f"充值後餘額：  {Formatter.format_currency(selected_card.balance + amount)}")
            print(f"支付方式：    {selected_method['icon']} {selected_method['name']}")
            print("═" * 79)
            
            if not BaseUI.confirm("\n確認充值？"):
                print("❌ 已取消充值")
                BaseUI.pause()
                return
            
            # Step 7: 執行充值
            BaseUI.show_loading("正在處理充值...")
            
            import uuid
            idempotency_key = f"recharge-{uuid.uuid4()}"
            
            result = self.payment_service.recharge_card(
                selected_card.id,
                amount,
                selected_method['code'],
                idempotency_key=idempotency_key
            )
            
            # Step 8: 顯示充值結果
            BaseUI.clear_screen()
            print("╔═══════════════════════════════════════════════════════════════════════════╗")
            print("║                          充值成功！                                       ║")
            print("╠═══════════════════════════════════════════════════════════════════════════╣")
            print(f"║  交易號：  {result['tx_no']:<60} ║")
            print(f"║  充值金額：{Formatter.format_currency(amount):<60} ║")
            print(f"║  支付方式：{selected_method['name']:<60} ║")
            print(f"║  處理時間：{Formatter.format_datetime(result.get('created_at')):<60} ║")
            print("╚═══════════════════════════════════════════════════════════════════════════╝")
            
            print("\n✅ 充值已到賬，您可以開始使用了！")
            
            # 記錄日誌
            ui_logger.log_transaction("Recharge", amount, result['tx_no'])
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"充值失敗: {e}")
            ui_logger.log_error("Recharge Card", str(e))
            
            # 友好的錯誤提示
            if "UNSUPPORTED_CARD_TYPE" in str(e):
                print("\n💡 提示：此卡片類型不支持充值")
                print("   只有標準卡可以充值")
            elif "CARD_NOT_FOUND" in str(e):
                print("\n💡 提示：卡片不存在或未激活")
            elif "INVALID_AMOUNT" in str(e):
                print("\n💡 提示：充值金額無效")
                print("   請確保金額在 ¥1 - ¥50,000 之間")
            
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
        """綁定企業卡 - 商業版"""
        try:
            BaseUI.clear_screen()
            print("╔═══════════════════════════════════════════════════════════════════════════╗")
            print("║                        綁定企業折扣卡                                     ║")
            print("╚═══════════════════════════════════════════════════════════════════════════╝")
            
            print("\n企業折扣卡說明：")
            print("  • 企業卡提供固定折扣，可與多人共享")
            print("  • 綁定後，您的標準卡將繼承企業折扣")
            print("  • 支付時自動選擇最優折扣（積分折扣 vs 企業折扣）")
            print("  • 需要企業卡的綁定密碼才能綁定")
            
            # Step 1: 輸入企業卡 ID
            print("\n" + "─" * 79)
            card_id = input("請輸入企業卡 ID: ").strip()
            
            if not card_id:
                print("❌ 企業卡 ID 不能為空")
                BaseUI.pause()
                return
            
            # 驗證 UUID 格式
            try:
                import uuid
                uuid.UUID(card_id)
            except ValueError:
                print("❌ 企業卡 ID 格式不正確（應為 UUID 格式）")
                BaseUI.pause()
                return
            
            # Step 2: 選擇綁定角色
            print("\n綁定角色：")
            roles = [
                {"code": "member", "name": "成員", "desc": "可以查看卡片信息，使用企業折扣"},
                {"code": "viewer", "name": "查看者", "desc": "只能查看卡片信息，不能使用"}
            ]
            
            for i, role in enumerate(roles, 1):
                print(f"  {i}. {role['name']} - {role['desc']}")
            
            while True:
                try:
                    role_choice = int(input(f"\n請選擇角色 (1-{len(roles)}): "))
                    if 1 <= role_choice <= len(roles):
                        selected_role = roles[role_choice - 1]
                        break
                    print(f"❌ 請輸入 1-{len(roles)}")
                except ValueError:
                    print("❌ 請輸入有效的數字")
            
            # Step 3: 輸入綁定密碼
            import getpass
            binding_password = getpass.getpass("\n請輸入企業卡綁定密碼: ")
            
            if not binding_password:
                print("❌ 綁定密碼不能為空")
                BaseUI.pause()
                return
            
            # Step 4: 確認綁定
            print("\n" + "═" * 79)
            print("綁定信息確認")
            print("═" * 79)
            print(f"企業卡 ID：  {card_id}")
            print(f"綁定角色：   {selected_role['name']} ({selected_role['desc']})")
            print(f"綁定密碼：   已設置")
            print("═" * 79)
            
            if not BaseUI.confirm("\n確認綁定？"):
                print("❌ 已取消綁定")
                BaseUI.pause()
                return
            
            # Step 5: 執行綁定
            BaseUI.show_loading("正在綁定企業卡...")
            
            result = self.member_service.bind_card(
                card_id,
                self.current_member_id,
                selected_role['code'],
                binding_password
            )
            
            # Step 6: 顯示綁定結果
            BaseUI.clear_screen()
            print("╔═══════════════════════════════════════════════════════════════════════════╗")
            print("║                        企業卡綁定成功！                                   ║")
            print("╠═══════════════════════════════════════════════════════════════════════════╣")
            print(f"║  企業卡 ID：{card_id[:30]}...{'':>30} ║")
            print(f"║  綁定角色：  {selected_role['name']:<60} ║")
            
            # 如果返回了企業折扣信息
            if result and isinstance(result, dict):
                corporate_discount = result.get('corporate_discount')
                if corporate_discount:
                    discount_percent = (1 - float(corporate_discount)) * 100
                    print(f"║  企業折扣：  {discount_percent:.1f}% OFF{'':>50} ║")
                    print("╠═══════════════════════════════════════════════════════════════════════════╣")
                    print("║  您的標準卡已繼承企業折扣！                                              ║")
                    print("║  支付時將自動選擇最優折扣                                                ║")
            
            print("╚═══════════════════════════════════════════════════════════════════════════╝")
            
            print("\n✅ 綁定成功！您現在可以享受企業折扣了")
            
            # 記錄日誌
            ui_logger.log_user_action("Bind Card", {
                "card_id": card_id,
                "role": selected_role['code']
            })
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"綁定失敗: {e}")
            ui_logger.log_error("Bind Card", str(e))
            
            # 友好的錯誤提示
            if "INVALID_BINDING_PASSWORD" in str(e):
                print("\n💡 提示：綁定密碼錯誤")
                print("   請聯繫企業卡管理員獲取正確的綁定密碼")
            elif "CARD_NOT_FOUND" in str(e):
                print("\n💡 提示：企業卡不存在或未激活")
                print("   請確認企業卡 ID 是否正確")
            elif "CARD_TYPE_NOT_SHAREABLE" in str(e):
                print("\n💡 提示：此卡片類型不支持共享")
                print("   只有企業折扣卡可以綁定")
            elif "ALREADY_BOUND" in str(e):
                print("\n💡 提示：您已經綁定過此企業卡")
            
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
                if card.card_type == 'standard':
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
    
    def _change_password(self):
        """修改密碼"""
        try:
            BaseUI.clear_screen()
            BaseUI.show_header("Change Password")
            
            import getpass
            
            # 輸入舊密碼
            print("請輸入您的密碼信息：")
            old_password = getpass.getpass("\n當前密碼: ")
            if not old_password:
                BaseUI.show_error("密碼不能為空")
                BaseUI.pause()
                return
            
            # 輸入新密碼
            new_password = getpass.getpass("新密碼: ")
            if not new_password:
                BaseUI.show_error("密碼不能為空")
                BaseUI.pause()
                return
            
            # 密碼強度檢查
            if len(new_password) < 6:
                BaseUI.show_error("密碼長度至少 6 個字符")
                BaseUI.pause()
                return
            
            # 確認新密碼
            confirm_password = getpass.getpass("確認新密碼: ")
            if new_password != confirm_password:
                BaseUI.show_error("兩次密碼輸入不一致")
                BaseUI.pause()
                return
            
            # 確認修改
            print("\n" + "═" * 79)
            print("密碼修改確認")
            print("═" * 79)
            print("✓ 新密碼已設置")
            print("⚠️  修改後請使用新密碼登入")
            print("═" * 79)
            
            if not BaseUI.confirm("\n確認修改密碼？"):
                BaseUI.show_info("已取消")
                BaseUI.pause()
                return
            
            # 執行修改
            BaseUI.show_loading("正在修改密碼...")
            
            # 先驗證舊密碼（通過重新登入）
            try:
                member = self.member_service.get_member_by_id(self.current_member_id)
                test_result = self.auth_service.login_with_phone(member.phone, old_password)
                if not test_result or not test_result.get('success'):
                    raise Exception("密碼驗證失敗")
            except Exception:
                BaseUI.show_error("當前密碼錯誤")
                BaseUI.pause()
                return
            
            # 設置新密碼
            self.member_service.set_member_password(
                self.current_member_id,
                new_password
            )
            
            BaseUI.show_success("密碼修改成功！", {
                "提示": "下次登入請使用新密碼"
            })
            
            ui_logger.log_user_action("Change Password", {
                "member_id": self.current_member_id
            })
            
            BaseUI.pause()
            
        except Exception as e:
            BaseUI.show_error(f"密碼修改失敗：{e}")
            BaseUI.pause()
    
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