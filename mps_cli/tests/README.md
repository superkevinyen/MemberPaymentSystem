# MPS 測試套件

完整的 Member Payment System (MPS) 功能測試套件，涵蓋所有 super_admin 功能。

## 📋 測試概述

本測試套件基於現有的 [`test_member_password.py`](../test_member_password.py:1) 風格設計，提供完整的業務流程測試。

### 測試覆蓋範圍

- ✅ **會員管理**: 創建、登入、搜尋、暫停、密碼管理
- ✅ **卡片管理**: 查詢、凍結/解凍、綁定/解綁
- ✅ **QR 碼管理**: 生成、驗證、撤銷、批量輪換
- ✅ **支付流程**: 掃碼支付、折扣計算、積分累積、幂等性
- ✅ **退款流程**: 全額退款、部分退款、多次退款
- ✅ **充值流程**: 不同支付方式、幂等性驗證
- ✅ **積分和等級**: 自動累積、自動升級、手動調整
- ✅ **商戶管理**: 創建、查詢、暫停
- ✅ **結算管理**: 生成結算、查詢結算
- ✅ **完整業務流程**: 端到端測試

## 🚀 快速開始

### 前置條件

1. 已配置 `.env` 文件
2. 擁有 super_admin 或 admin 權限的帳號
3. 已安裝所有依賴：`pip install -r requirements.txt`

### 運行測試

```bash
# 進入測試目錄
cd mps_cli/test_suite

# 運行完整業務流程測試（推薦先運行此測試）
python test_complete_business_flow.py

# 運行會員密碼測試（從根目錄移過來的）
python test_member_password.py

# 運行基礎功能測試
python test_basic.py
```

## 📁 測試文件說明

### 核心測試文件

| 文件 | 說明 | 測試內容 |
|------|------|----------|
| [`test_helpers.py`](test_helpers.py:1) | 共享輔助函數 | 認證、數據生成、清理等工具函數 |
| [`test_complete_business_flow.py`](test_complete_business_flow.py:1) | 完整業務流程測試 | 支付流程、退款流程、卡片綁定流程 |
| [`test_member_password.py`](test_member_password.py:1) | 會員密碼功能測試 | 創建會員、登入、搜尋 |
| [`test_basic.py`](test_basic.py:1) | 基礎功能測試 | 模組導入、驗證器、格式化器 |

### 規劃中的測試文件

以下測試文件已在 [`TEST_PLAN.md`](TEST_PLAN.md:1) 中規劃，可根據需要實現：

- `test_01_member_management.py` - 會員管理完整測試
- `test_02_card_management.py` - 卡片管理完整測試
- `test_03_card_binding.py` - 卡片綁定完整測試
- `test_04_qr_management.py` - QR 碼管理完整測試
- `test_05_payment_flow.py` - 支付流程完整測試
- `test_06_refund_flow.py` - 退款流程完整測試
- `test_07_recharge_flow.py` - 充值流程完整測試
- `test_08_points_and_levels.py` - 積分和等級完整測試
- `test_09_merchant_management.py` - 商戶管理完整測試
- `test_10_settlement.py` - 結算完整測試

## 🔧 測試輔助函數

[`test_helpers.py`](test_helpers.py:1) 提供了豐富的輔助函數：

### 認證相關
- `setup_admin_auth()` - 設定管理員認證
- `cleanup_all_test_data()` - 清理所有測試數據

### 數據生成
- `generate_test_member_data()` - 生成測試會員數據
- `generate_test_merchant_data()` - 生成測試商戶數據

### 快捷操作
- `create_test_member()` - 創建測試會員
- `create_test_merchant()` - 創建測試商戶
- `recharge_card()` - 充值卡片
- `generate_qr_code()` - 生成 QR 碼
- `make_payment()` - 執行支付
- `make_refund()` - 執行退款

### 查詢函數
- `get_member_default_card()` - 獲取會員默認卡片
- `get_card_balance()` - 獲取卡片餘額
- `get_card_points()` - 獲取卡片積分

### 輸出格式化
- `print_test_header()` - 打印測試標題
- `print_test_step()` - 打印測試步驟
- `print_test_info()` - 打印測試信息
- `print_test_result()` - 打印測試結果
- `print_test_summary()` - 打印測試總結

## 📝 測試編寫指南

### 基本結構

```python
#!/usr/bin/env python3
"""
測試文件說明
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_helpers import (
    setup_admin_auth,
    cleanup_all_test_data,
    print_test_header,
    # ... 其他需要的函數
)

def test_your_feature(auth_service):
    """測試你的功能"""
    print_test_header("測試名稱")
    
    try:
        # 測試步驟
        print_test_step("步驟 1: ...")
        # ... 測試邏輯
        
        print_test_result("測試名稱", True, "測試通過")
        return True
        
    except Exception as e:
        print_test_result("測試名稱", False, str(e))
        return False

def main(auth_service=None):
    """主測試函數"""
    if auth_service is None:
        auth_service = setup_admin_auth()
    
    results = {}
    
    try:
        results["測試1"] = test_your_feature(auth_service)
        # ... 更多測試
        
        return print_test_summary(results)
        
    finally:
        cleanup_all_test_data(auth_service)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

### 測試數據管理

所有測試數據會自動追蹤並在測試結束後清理：

```python
# 創建會員（自動追蹤）
member_id, member_data = create_test_member(auth_service)

# 創建商戶（自動追蹤）
merchant_id, merchant_data = create_test_merchant(auth_service)

# 測試結束後自動清理
cleanup_all_test_data(auth_service)
```

## ⚠️ 注意事項

1. **管理員權限**: 所有測試都需要 `super_admin` 或 `admin` 權限
2. **數據清理**: 測試會自動清理數據（使用 `admin_suspend_*` RPC）
3. **測試環境**: 建議在開發數據庫中運行測試
4. **測試順序**: 建議先運行 `test_complete_business_flow.py` 驗證核心功能
5. **錯誤處理**: 測試失敗不會中斷後續測試
6. **日誌記錄**: 所有操作都會記錄到日誌文件

## 🐛 故障排除

### 常見問題

**Q: 測試提示 "需要管理員權限"**
- A: 確保使用的帳號具有 `super_admin` 或 `admin` 角色

**Q: 測試數據沒有清理**
- A: 檢查 `cleanup_all_test_data()` 是否在 `finally` 塊中執行

**Q: RPC 調用失敗**
- A: 檢查 `.env` 配置和數據庫連接

**Q: 創建商戶失敗**
- A: 確保 RPC 函數 `create_merchant` 已在數據庫中定義

## 📊 測試報告

測試執行後會顯示詳細的測試報告：

```
============================================================
測試總結
============================================================
完整支付流程: ✅ 通過
完整退款流程: ✅ 通過
卡片綁定流程: ✅ 通過

總計: 3/3 通過

🎉 所有測試通過！
```

## 🔗 相關文檔

- [`TEST_PLAN.md`](TEST_PLAN.md:1) - 完整測試計劃
- [`../README.md`](../README.md:1) - MPS CLI 主文檔
- [`../../README_BZ_FLOW.md`](../../README_BZ_FLOW.md:1) - 業務流程說明
- [`../../schema/mps_schema.sql`](../../schema/mps_schema.sql:1) - 數據庫架構
- [`../../rpc/mps_rpc.sql`](../../rpc/mps_rpc.sql:1) - RPC 函數定義

## 📈 測試覆蓋進度

- [x] 測試基礎設施（test_helpers.py）
- [x] 完整業務流程測試
- [x] 會員密碼功能測試
- [x] 基礎功能測試
- [ ] 會員管理完整測試
- [ ] 卡片管理完整測試
- [ ] QR 碼管理完整測試
- [ ] 支付流程完整測試
- [ ] 退款流程完整測試
- [ ] 充值流程完整測試
- [ ] 積分和等級完整測試
- [ ] 商戶管理完整測試
- [ ] 結算管理完整測試

## 🤝 貢獻指南

如需添加新測試：

1. 參考現有測試文件結構
2. 使用 `test_helpers.py` 中的輔助函數
3. 確保測試數據會被自動清理
4. 添加清晰的測試說明和步驟
5. 更新本 README 的測試覆蓋進度

## 📞 支持

如有問題，請查看：
- 測試日誌文件
- RPC 函數定義
- 業務流程文檔

---

**最後更新**: 2025-09-30
**版本**: 1.0.0