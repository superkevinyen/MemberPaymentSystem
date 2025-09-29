# Member Payment System (MPS)

MPS 是一個基於 **Supabase + PostgreSQL** 的會員支付系統，定位為 **自營支付平台**，結合會員管理、卡片管理、交易、積分、退款與商戶結算，適合商用化場景。

---

## 功能模組

1. **會員管理 (Member Profiles)**
   - 建立 / 更新會員資料
   - 自動生成一張標準會員卡

2. **卡片管理 (Member Cards)**
   - 標準會員卡：自動生成、積分升級
   - 預充卡：可儲值、多用戶共享
   - 優惠券卡：一次性消費
   - 企業 / 聯名卡：固定折扣

3. **卡片綁定 (Card Bindings)**
   - 預充卡 / 企業卡可多人共享
   - 綁定需密碼驗證
   - 每張卡都有 **所有人資訊**

4. **交易管理 (Transactions)**
   - 支付 / 儲值 / 退款
   - 支援冪等性 (idempotency key)
   - 與積分/折扣計算掛鉤

5. **積分管理 (Point Ledger)**
   - 消費累積積分
   - 升級會員等級 → 折扣自動變動

6. **商戶管理 (Merchants)**
   - 商戶資料
   - 商戶用戶帳號（對應 `auth.users`）

7. **結算管理 (Settlements)**
   - **可選結算模式：**
     - 即時（Realtime）
     - T+1
     - 月結
   - 對帳 / 報表 / 財務核算

8. **審計日誌 (Audit Log)**
   - 所有敏感操作全量記錄
   - 交易、退款、綁定、充值可追溯

---

## 初始化

```bash
psql -h <supabase-db-host> -U postgres -d postgres -f schema/mps_clean.sql
```

---

## 下一步
- 定義 RPC API（見 `supabase_rpc.md`）
- 用 Python CLI / TUI 驗證流程
- 接入前端 (Next.js + Supabase client)
