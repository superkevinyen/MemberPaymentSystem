# 結算功能設計文檔

> MPS CLI 商戶結算功能完整設計

## 📋 功能概述

結算功能允許商戶生成和查看交易結算報表，支持多種結算模式（實時結算、T+1結算、月結）。

---

## 🎯 業務需求

### 核心功能
1. **生成結算報表** - 根據指定期間和模式生成結算
2. **查看結算歷史** - 查看歷史結算記錄
3. **結算詳情查看** - 查看單個結算的詳細信息

### 結算模式
- **realtime** - 實時結算（即時到賬）
- **t_plus_1** - T+1結算（次日到賬）
- **monthly** - 月結（每月結算）

---

## 🗄️ 數據模型

### Settlement Model

**文件**: `mps_cli/models/settlement.py`

```python
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
from .base import BaseModel, TimestampMixin

@dataclass
class Settlement(BaseModel, TimestampMixin):
    """結算模型"""
    
    # 基本信息
    settlement_no: Optional[str] = None
    merchant_id: Optional[str] = None
    merchant_code: Optional[str] = None
    merchant_name: Optional[str] = None
    
    # 結算配置
    settlement_mode: Optional[str] = None  # realtime/t_plus_1/monthly
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    
    # 金額統計
    total_transactions: Optional[int] = None
    payment_count: Optional[int] = None
    refund_count: Optional[int] = None
    payment_amount: Optional[Decimal] = None
    refund_amount: Optional[Decimal] = None
    net_amount: Optional[Decimal] = None
    fee_amount: Optional[Decimal] = None
    settlement_amount: Optional[Decimal] = None
    
    # 狀態
    status: Optional[str] = None  # pending/completed/failed
    settled_at: Optional[str] = None
    
    def get_mode_display(self) -> str:
        """獲取結算模式顯示"""
        modes = {
            'realtime': '實時結算',
            't_plus_1': 'T+1結算',
            'monthly': '月結'
        }
        return modes.get(self.settlement_mode, self.settlement_mode or "未知")
    
    def get_status_display(self) -> str:
        """獲取狀態顯示"""
        statuses = {
            'pending': '待結算',
            'completed': '已完成',
            'failed': '失敗'
        }
        return statuses.get(self.status, self.status or "未知")
    
    def display_summary(self) -> str:
        """顯示結算摘要"""
        from utils.formatters import Formatter
        
        return (f"{self.settlement_no} | "
                f"{self.get_mode_display()} | "
                f"淨額: {Formatter.format_currency(self.net_amount)} | "
                f"{self.get_status_display()}")
```

---

## 🔧 Service 層

### Settlement Service

**文件**: `mps_cli/services/settlement_service.py`

```python
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from .base_service import BaseService
from models.settlement import Settlement

class SettlementService(BaseService):
    """結算服務"""
    
    def generate_settlement(
        self,
        merchant_id: str,
        mode: str,
        period_start: str,
        period_end: str
    ) -> Dict:
        """
        生成結算報表
        
        Args:
            merchant_id: 商戶 ID
            mode: 結算模式 (realtime/t_plus_1/monthly)
            period_start: 期間開始時間
            period_end: 期間結束時間
            
        Returns:
            結算結果字典
        """
        self.log_operation("生成結算", {
            "merchant_id": merchant_id,
            "mode": mode,
            "period": f"{period_start} ~ {period_end}"
        })
        
        params = {
            "p_merchant_id": merchant_id,
            "p_mode": mode,
            "p_period_start": period_start,
            "p_period_end": period_end
        }
        
        try:
            result = self.rpc_call("generate_settlement", params)
            
            if result and len(result) > 0:
                settlement_data = result[0]
                self.logger.info(f"結算生成成功: {settlement_data.get('settlement_no')}")
                return settlement_data
            else:
                raise Exception("結算生成失敗：無返回數據")
                
        except Exception as e:
            self.logger.error(f"結算生成失敗: {e}")
            raise self.handle_service_error("生成結算", e, params)
    
    def list_settlements(
        self,
        merchant_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict:
        """
        查詢結算列表
        
        Args:
            merchant_id: 商戶 ID
            limit: 每頁數量
            offset: 偏移量
            
        Returns:
            結算列表和分頁信息
        """
        self.log_operation("查詢結算列表", {
            "merchant_id": merchant_id,
            "limit": limit,
            "offset": offset
        })
        
        params = {
            "p_merchant_id": merchant_id,
            "p_limit": limit,
            "p_offset": offset
        }
        
        try:
            result = self.rpc_call("list_settlements", params)
            
            settlements = []
            for item in result:
                settlement = Settlement(
                    id=item.get('id'),
                    settlement_no=item.get('settlement_no'),
                    merchant_id=item.get('merchant_id'),
                    settlement_mode=item.get('settlement_mode'),
                    period_start=item.get('period_start'),
                    period_end=item.get('period_end'),
                    total_transactions=item.get('total_transactions'),
                    payment_count=item.get('payment_count'),
                    refund_count=item.get('refund_count'),
                    payment_amount=Decimal(str(item.get('payment_amount', 0))),
                    refund_amount=Decimal(str(item.get('refund_amount', 0))),
                    net_amount=Decimal(str(item.get('net_amount', 0))),
                    settlement_amount=Decimal(str(item.get('settlement_amount', 0))),
                    status=item.get('status'),
                    settled_at=item.get('settled_at'),
                    created_at=item.get('created_at')
                )
                settlements.append(settlement)
            
            return {
                "data": settlements,
                "pagination": {
                    "total": len(settlements),
                    "limit": limit,
                    "offset": offset
                }
            }
            
        except Exception as e:
            self.logger.error(f"查詢結算列表失敗: {e}")
            raise self.handle_service_error("查詢結算列表", e, params)
    
    def get_settlement_detail(self, settlement_id: str) -> Settlement:
        """
        獲取結算詳情
        
        Args:
            settlement_id: 結算 ID
            
        Returns:
            結算對象
        """
        # 通過查詢實現
        try:
            filters = {"id": settlement_id}
            settlements = self.query_table("settlements", filters, limit=1)
            
            if settlements:
                item = settlements[0]
                return Settlement(
                    id=item.get('id'),
                    settlement_no=item.get('settlement_no'),
                    merchant_id=item.get('merchant_id'),
                    settlement_mode=item.get('settlement_mode'),
                    period_start=item.get('period_start'),
                    period_end=item.get('period_end'),
                    total_transactions=item.get('total_transactions'),
                    payment_count=item.get('payment_count'),
                    refund_count=item.get('refund_count'),
                    payment_amount=Decimal(str(item.get('payment_amount', 0))),
                    refund_amount=Decimal(str(item.get('refund_amount', 0))),
                    net_amount=Decimal(str(item.get('net_amount', 0))),
                    settlement_amount=Decimal(str(item.get('settlement_amount', 0))),
                    status=item.get('status'),
                    settled_at=item.get('settled_at'),
                    created_at=item.get('created_at')
                )
            else:
                raise Exception("結算不存在")
                
        except Exception as e:
            self.logger.error(f"獲取結算詳情失敗: {settlement_id}, 錯誤: {e}")
            raise
```

---

## 🎨 UI 設計

### 商戶端 - 生成結算報表

**文件**: `mps_cli/ui/merchant_ui.py`

**功能位置**: 主菜單新增選項 "5. 生成結算報表"

```python
def _generate_settlement(self):
    """生成結算報表 - 商業版"""
    try:
        BaseUI.clear_screen()
        print("╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║                        生成結算報表                                       ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
        
        # Step 1: 選擇結算模式
        print("\n結算模式：")
        modes = [
            {"code": "realtime", "name": "實時結算", "desc": "即時到賬"},
            {"code": "t_plus_1", "name": "T+1結算", "desc": "次日到賬"},
            {"code": "monthly", "name": "月結", "desc": "每月結算"}
        ]
        
        for i, mode in enumerate(modes, 1):
            print(f"  {i}. {mode['name']} - {mode['desc']}")
        
        while True:
            try:
                mode_choice = int(input(f"\n請選擇結算模式 (1-{len(modes)}): "))
                if 1 <= mode_choice <= len(modes):
                    selected_mode = modes[mode_choice - 1]
                    break
                print(f"❌ 請輸入 1-{len(modes)}")
            except ValueError:
                print("❌ 請輸入有效的數字")
        
        # Step 2: 選擇結算期間
        print(f"\n結算期間（{selected_mode['name']}）：")
        
        if selected_mode['code'] == 'realtime':
            # 實時結算 - 選擇日期範圍
            period_start, period_end = self._select_date_range()
        elif selected_mode['code'] == 't_plus_1':
            # T+1結算 - 選擇日期
            period_start, period_end = self._select_single_date()
        else:  # monthly
            # 月結 - 選擇月份
            period_start, period_end = self._select_month()
        
        # Step 3: 確認生成
        print("\n" + "═" * 79)
        print("結算信息確認")
        print("═" * 79)
        print(f"商戶：        {self.current_merchant_name}")
        print(f"結算模式：    {selected_mode['name']}")
        print(f"結算期間：    {period_start} ~ {period_end}")
        print("═" * 79)
        
        if not BaseUI.confirm("\n確認生成結算報表？"):
            print("❌ 已取消")
            BaseUI.pause()
            return
        
        # Step 4: 生成結算
        BaseUI.show_loading("正在生成結算報表...")
        
        from services.settlement_service import SettlementService
        settlement_service = SettlementService()
        settlement_service.set_auth_service(self.auth_service)
        
        result = settlement_service.generate_settlement(
            self.current_merchant_id,
            selected_mode['code'],
            period_start,
            period_end
        )
        
        # Step 5: 顯示結算結果
        BaseUI.clear_screen()
        self._display_settlement_result(result, selected_mode)
        
        BaseUI.pause()
        
    except Exception as e:
        BaseUI.show_error(f"生成結算失敗: {e}")
        self.logger.error(f"生成結算失敗: {e}", exc_info=True)
        
        # 友好的錯誤提示
        if "NO_TRANSACTIONS_IN_PERIOD" in str(e):
            print("\n💡 提示：所選期間內沒有交易記錄")
            print("   請選擇其他時間範圍")
        elif "SETTLEMENT_ALREADY_EXISTS" in str(e):
            print("\n💡 提示：該期間的結算已存在")
            print("   請查看結算歷史")
        
        BaseUI.pause()

def _select_date_range(self):
    """選擇日期範圍"""
    from datetime import datetime, timedelta
    
    print("\n請選擇日期範圍：")
    print("  1. 今日")
    print("  2. 昨日")
    print("  3. 最近7天")
    print("  4. 最近30天")
    print("  5. 自定義範圍")
    
    choice = int(input("\n請選擇 (1-5): "))
    
    today = datetime.now().date()
    
    if choice == 1:  # 今日
        period_start = today.isoformat()
        period_end = today.isoformat()
    elif choice == 2:  # 昨日
        yesterday = today - timedelta(days=1)
        period_start = yesterday.isoformat()
        period_end = yesterday.isoformat()
    elif choice == 3:  # 最近7天
        start = today - timedelta(days=7)
        period_start = start.isoformat()
        period_end = today.isoformat()
    elif choice == 4:  # 最近30天
        start = today - timedelta(days=30)
        period_start = start.isoformat()
        period_end = today.isoformat()
    else:  # 自定義
        period_start = input("開始日期 (YYYY-MM-DD): ").strip()
        period_end = input("結束日期 (YYYY-MM-DD): ").strip()
    
    return period_start, period_end

def _select_single_date(self):
    """選擇單個日期（T+1結算）"""
    from datetime import datetime, timedelta
    
    print("\n請選擇結算日期：")
    print("  1. 昨日")
    print("  2. 前日")
    print("  3. 自定義日期")
    
    choice = int(input("\n請選擇 (1-3): "))
    
    today = datetime.now().date()
    
    if choice == 1:  # 昨日
        date = today - timedelta(days=1)
    elif choice == 2:  # 前日
        date = today - timedelta(days=2)
    else:  # 自定義
        date_str = input("日期 (YYYY-MM-DD): ").strip()
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    return date.isoformat(), date.isoformat()

def _select_month(self):
    """選擇月份（月結）"""
    from datetime import datetime
    from calendar import monthrange
    
    print("\n請選擇結算月份：")
    print("  1. 上個月")
    print("  2. 自定義月份")
    
    choice = int(input("\n請選擇 (1-2): "))
    
    today = datetime.now()
    
    if choice == 1:  # 上個月
        if today.month == 1:
            year = today.year - 1
            month = 12
        else:
            year = today.year
            month = today.month - 1
    else:  # 自定義
        year = int(input("年份 (YYYY): "))
        month = int(input("月份 (1-12): "))
    
    # 計算月份的第一天和最後一天
    first_day = datetime(year, month, 1).date()
    last_day_num = monthrange(year, month)[1]
    last_day = datetime(year, month, last_day_num).date()
    
    return first_day.isoformat(), last_day.isoformat()

def _display_settlement_result(self, result: Dict, mode: Dict):
    """顯示結算結果"""
    from utils.formatters import Formatter
    
    print("╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                        結算報表生成成功！                                 ║")
    print("╠═══════════════════════════════════════════════════════════════════════════╣")
    print(f"║  結算單號：  {result.get('settlement_no'):<60} ║")
    print(f"║  結算模式：  {mode['name']:<60} ║")
    print(f"║  結算期間：  {result.get('period_start')} ~ {result.get('period_end'):<30} ║")
    print("╠═══════════════════════════════════════════════════════════════════════════╣")
    print("║  交易統計：                                                               ║")
    print(f"║  • 總交易數：{result.get('total_transactions', 0):<60} ║")
    print(f"║  • 支付筆數：{result.get('payment_count', 0):<60} ║")
    print(f"║  • 退款筆數：{result.get('refund_count', 0):<60} ║")
    print("╠═══════════════════════════════════════════════════════════════════════════╣")
    print("║  金額統計：                                                               ║")
    print(f"║  • 支付金額：{Formatter.format_currency(result.get('payment_amount', 0)):<60} ║")
    print(f"║  • 退款金額：{Formatter.format_currency(result.get('refund_amount', 0)):<60} ║")
    print(f"║  • 淨收入：  {Formatter.format_currency(result.get('net_amount', 0)):<60} ║")
    print(f"║  • 手續費：  {Formatter.format_currency(result.get('fee_amount', 0)):<60} ║")
    print(f"║  • 結算金額：{Formatter.format_currency(result.get('settlement_amount', 0)):<60} ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    print(f"\n✅ 結算報表已生成，預計 {mode['desc']}")
```

---

### 商戶端 - 查看結算歷史

**功能位置**: 主菜單新增選項 "6. 查看結算歷史"

```python
def _view_settlement_history(self):
    """查看結算歷史 - 商業版"""
    try:
        BaseUI.clear_screen()
        print("╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║                        結算歷史                                           ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
        
        # 獲取結算列表
        BaseUI.show_loading("正在獲取結算記錄...")
        
        from services.settlement_service import SettlementService
        settlement_service = SettlementService()
        settlement_service.set_auth_service(self.auth_service)
        
        result = settlement_service.list_settlements(
            self.current_merchant_id,
            limit=50,
            offset=0
        )
        
        settlements = result.get('data', [])
        
        if not settlements:
            BaseUI.clear_screen()
            print("\n⚠️  暫無結算記錄")
            BaseUI.pause()
            return
        
        # 顯示結算列表
        BaseUI.clear_screen()
        print("╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║                        結算歷史記錄                                       ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
        print("\n結算記錄：")
        print("─" * 79)
        print(f"{'序號':<4} {'結算單號':<20} {'模式':<12} {'期間':<20} {'淨額':<15} {'狀態':<8}")
        print("─" * 79)
        
        for i, settlement in enumerate(settlements, 1):
            from utils.formatters import Formatter
            period = f"{settlement.period_start[:10]}~{settlement.period_end[:10]}"
            print(f"{i:<4} {settlement.settlement_no:<20} "
                  f"{settlement.get_mode_display():<12} "
                  f"{period:<20} "
                  f"{Formatter.format_currency(settlement.net_amount):<15} "
                  f"{settlement.get_status_display():<8}")
        
        print("─" * 79)
        
        # 操作選項
        print("\n操作選項：")
        print("  輸入序號查看詳情")
        print("  輸入 q 返回")
        
        choice = input("\n請選擇: ").strip()
        
        if choice.lower() == 'q':
            return
        
        try:
            index = int(choice)
            if 1 <= index <= len(settlements):
                selected = settlements[index - 1]
                self._show_settlement_detail(selected)
        except ValueError:
            print("❌ 無效的輸入")
            BaseUI.pause()
        
    except Exception as e:
        BaseUI.show_error(f"查詢結算歷史失敗: {e}")
        self.logger.error(f"查詢結算歷史失敗: {e}", exc_info=True)
        BaseUI.pause()

def _show_settlement_detail(self, settlement):
    """顯示結算詳情"""
    from utils.formatters import Formatter
    
    BaseUI.clear_screen()
    print("╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                        結算詳情                                           ║")
    print("╠═══════════════════════════════════════════════════════════════════════════╣")
    print(f"║  結算單號：  {settlement.settlement_no:<60} ║")
    print(f"║  結算模式：  {settlement.get_mode_display():<60} ║")
    print(f"║  結算期間：  {settlement.period_start} ~ {settlement.period_end:<30} ║")
    print(f"║  結算狀態：  {settlement.get_status_display():<60} ║")
    print("╠═══════════════════════════════════════════════════════════════════════════╣")
    print("║  交易統計：                                                               ║")
    print(f"║  • 總交易數：{settlement.total_transactions or 0:<60} ║")
    print(f"║  • 支付筆數：{settlement.payment_count or 0:<60} ║")
    print(f"║  • 退款筆數：{settlement.refund_count or 0:<60} ║")
    print("╠═══════════════════════════════════════════════════════════════════════════╣")
    print("║  金額統計：                                                               ║")
    print(f"║  • 支付金額：{Formatter.format_currency(settlement.payment_amount or 0):<60} ║")
    print(f"║  • 退款金額：{Formatter.format_currency(settlement.refund_amount or 0):<60} ║")
    print(f"║  • 淨收入：  {Formatter.format_currency(settlement.net_amount or 0):<60} ║")
    print(f"║  • 手續費：  {Formatter.format_currency(settlement.fee_amount or 0):<60} ║")
    print(f"║  • 結算金額：{Formatter.format_currency(settlement.settlement_amount or 0):<60} ║")
    print("╠═══════════════════════════════════════════════════════════════════════════╣")
    print(f"║  創建時間：  {settlement.created_at:<60} ║")
    if settlement.settled_at:
        print(f"║  結算時間：  {settlement.settled_at:<60} ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    BaseUI.pause()
```

---

## 📝 常量定義

**文件**: `mps_cli/config/constants.py`

```python
# 結算模式
SETTLEMENT_MODES = {
    'realtime': '實時結算',
    't_plus_1': 'T+1結算',
    'monthly': '月結'
}

# 結算狀態
SETTLEMENT_STATUS = {
    'pending': '待結算',
    'completed': '已完成',
    'failed': '失敗'
}
```

---

## 🔗 RPC 函數對接

### generate_settlement

**RPC 定義**: `rpc/mps_rpc.sql` Line 1505-1538

```sql
CREATE OR REPLACE FUNCTION generate_settlement(
  p_merchant_id uuid,
  p_mode settlement_mode,
  p_period_start timestamptz,
  p_period_end timestamptz
) RETURNS settlements
```

**參數說明**:
- `p_merchant_id`: 商戶 ID
- `p_mode`: 結算模式 (realtime/t_plus_1/monthly)
- `p_period_start`: 期間開始時間
- `p_period_end`: 期間結束時間

**返回**: settlements 表記錄

---

### list_settlements

**RPC 定義**: `rpc/mps_rpc.sql` Line 1540-1564

```sql
CREATE OR REPLACE FUNCTION list_settlements(
  p_merchant_id uuid,
  p_limit integer DEFAULT 50,
  p_offset integer DEFAULT 0,
  p_session_id text DEFAULT NULL
) RETURNS SETOF settlements
```

**參數說明**:
- `p_merchant_id`: 商戶 ID
- `p_limit`: 每頁數量
- `p_offset`: 偏移量
- `p_session_id`: Session ID（可選）

**返回**: settlements 表記錄集合

---

## 🧪 測試用例

### 測試文件

**文件**: `mps_cli/tests/test_settlement.py`

```python
#!/usr/bin/env python3
"""
結算功能測試
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_helpers import (
    setup_admin_auth,
    print_test_header,
    print_test_step,
    print_test_info,
    print_test_result,
    create_test_merchant
)
from services.settlement_service import SettlementService

def test_generate_settlement(auth_service):
    """測試生成結算"""
    print_test_header("生成結算測試")
    
    try:
        # 創建測試商戶
        print_test_step("步驟 1: 創建測試商戶")
        merchant_id, merchant_data = create_test_merchant(auth_service)
        print_test_info("商戶 ID", merchant_id)
        
        # 生成結算
        print_test_step("步驟 2: 生成結算報表")
        
        settlement_service = SettlementService()
        settlement_service.set_auth_service(auth_service)
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        result = settlement_service.generate_settlement(
            merchant_id,
            'realtime',
            yesterday.isoformat(),
            yesterday.isoformat()
        )
        
        print_test_info("結算單號", result.get('settlement_no'))
        print_test_info("淨收入", result.get('net_amount'))
        
        print_test_result("生成結算", True, "結算生成成功")
        return True
        
    except Exception as e:
        print_test_result("生成結算", False, str(e))
        return False

def test_list_settlements(auth_service):
    """測試查詢結算列表"""
    print_test_header("查詢結算列表測試")
    
    try:
        # 創建測試商戶
        merchant_id, merchant_data = create_test_merchant(auth_service)
        
        # 查詢結算列表
        settlement_service = SettlementService()
        settlement_service.set_auth_service(auth_service)
        
        result = settlement_service.list_settlements(merchant_id)
        
        settlements = result.get('data', [])
        print_test_info("結算記錄數", len(settlements))
        
        print_test_result("查詢結算列表", True, "查詢成功")
        return True
        
    except Exception as e:
        print_test_result("查詢結算列表", False, str(e))
        return False

if __name__ == "__main__":
    auth_service = setup_admin_auth()
    
    print("\n開始結算功能測試...\n")
    
    results = {
        "生成結算": test_generate_settlement(auth_service),
        "查詢結算列表": test_list_settlements(auth_service)
    }
    
    print("\n" + "="*60)
    print("測試總結")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
```

---

## 📋 實施清單

### Phase 1: 基礎設施 (1小時)

- [ ] 創建 Settlement Model (`models/settlement.py`)
- [ ] 創建 Settlement Service (`services/settlement_service.py`)
- [ ] 添加常量定義 (`config/constants.py`)

### Phase 2: UI 實現 (1.5小時)

- [ ] 實現生成結算報表 UI (`ui/merchant_ui.py::_generate_settlement`)
- [ ] 實現查看結算歷史 UI (`ui/merchant_ui.py::_view_settlement_history`)
- [ ] 實現結算詳情顯示 (`ui/merchant_ui.py::_show_settlement_detail`)
- [ ] 添加日期選擇輔助方法

### Phase 3: 菜單集成 (0.5小時)

- [ ] 更新商戶主菜單，添加結算選項
- [ ] 更新菜單處理器

### Phase 4: 測試 (1小時)

- [ ] 創建測試文件 (`tests/test_settlement.py`)
- [ ] 編寫單元測試
- [ ] 執行集成測試
- [ ] 修復發現的問題

---

## 🎯 預期效果

### 用戶體驗

1. **生成結算**
   - 選擇結算模式（實時/T+1/月結）
   - 選擇結算期間（靈活的日期選擇）
   - 確認並生成
   - 查看詳細的結算報表

2. **查看歷史**
   - 列表顯示所有結算記錄
   - 支持查看詳情
   - 清晰的狀態顯示

### 商業價值

- ✅ 商戶可以清楚了解收入情況
- ✅ 支持多種結算模式，靈活配置
- ✅ 完整的結算記錄，便於對賬
- ✅ 專業的報表展示

---

## 📊 預計工時

| 任務 | 預計時間 |
|------|---------|
| Model + Service | 1 小時 |
| UI 實現 | 1.5 小時 |
| 菜單集成 | 0.5 小時 |
| 測試 | 1 小時 |
| **總計** | **4 小時** |

---

## 🚀 下一步

1. **立即實施** - 如果需要完整的商業產品
2. **延後實施** - 如果當前功能已足夠
3. **分階段實施** - 先實現基礎功能，再優化

---

**文檔版本**: v1.0.0  
**創建時間**: 2025-10-01  
**預計實施**: 待定
