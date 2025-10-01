# MPS Python UI 流程圖

## 📋 三個角色的詳細 UI 流程設計

### 👤 會員用戶 UI 流程

#### 登入與主菜單流程
```mermaid
flowchart TD
    A[啟動會員 App] --> B[輸入手機/會員號 + 密碼]
    B --> C[調用 member_login RPC]
    C --> D{登入驗證}
    D -->|失敗| E[顯示錯誤信息]
    D -->|成功| F[獲得 session_id]
    F --> G[保存 session 資訊]
    G --> H[顯示主菜單]
    
    H --> I{選擇功能}
    I -->|1| J[查看我的卡片]
    I -->|2| K[生成付款 QR 碼]
    I -->|3| L[充值卡片]
    I -->|4| M[查看交易記錄]
    I -->|5| N[綁定企業卡]
    I -->|6| O[查看積分等級]
    I -->|7| P[修改密碼]
    I -->|8| Q[登出系統]
    
    J --> R[顯示卡片列表]
    K --> S[選擇卡片生成 QR]
    L --> T[選擇卡片充值]
    M --> U[顯示交易記錄]
    N --> V[輸入卡片信息]
    O --> W[顯示積分等級]
    P --> X[輸入新密碼]
    Q --> Y[調用 logout_session]
    
    R --> H
    S --> Z[顯示 QR 碼]
    T --> AA[充值流程]
    U --> H
    V --> AB[綁定流程]
    W --> H
    X --> H
    Y --> AC[刪除 session]
    Z --> H
    AA --> H
    AB --> H
    AC --> AD[結束程序]
    
    E --> B
    
    style A fill:#e1f5fe
    style C fill:#fff3e0
    style H fill:#f3e5f5
    style AD fill:#c8e6c9
```

#### 生成 QR 碼詳細流程
```mermaid
flowchart TD
    A[選擇生成 QR 碼] --> B[顯示可用卡片]
    B --> C[用戶選擇卡片]
    C --> D{卡片類型檢查}
    D -->|Corporate Card| E[企業卡不能生成 QR]
    D -->|Standard/Voucher| F{卡片狀態檢查}
    F -->|inactive| G[顯示卡片未激活]
    F -->|active| H[調用 rotate_card_qr RPC + session_id]
    
    H --> I{RPC 調用結果}
    I -->|成功| J[顯示 QR 碼信息]
    I -->|失敗| K[顯示錯誤信息]
    
    J --> L[顯示過期時間]
    L --> M[提示向商戶出示]
    M --> N[等待用戶確認]
    N --> O[返回主菜單]
    
    E --> P[返回卡片選擇]
    G --> P
    K --> P
    P --> B
    
    style A fill:#e1f5fe
    style H fill:#fff3e0
    style J fill:#c8e6c9
    style K fill:#ffebee
```

#### 充值流程（只支持 Standard Card）
```mermaid
flowchart TD
    A[選擇充值功能] --> B[顯示可充值卡片]
    B --> C[用戶選擇卡片]
    C --> D{卡片類型檢查}
    D -->|Corporate/Voucher| E[顯示不支持充值]
    D -->|Standard| F[輸入充值金額]
    
    F --> G{金額驗證}
    G -->|≤ 0| H[顯示金額錯誤]
    G -->|> 0| I[選擇支付方式]
    
    I --> J[顯示支付方式列表]
    J --> K[用戶選擇支付方式]
    K --> L[顯示充值確認信息]
    L --> M{用戶確認}
    M -->|否| N[取消充值]
    M -->|是| O[調用 user_recharge_card RPC + session_id]
    
    O --> P{RPC 調用結果}
    P -->|成功| Q[顯示充值成功]
    P -->|失敗| R[顯示錯誤信息]
    
    Q --> S[顯示交易號]
    S --> T[返回主菜單]
    
    E --> U[返回卡片選擇]
    H --> F
    N --> T
    R --> T
    U --> B
    
    style A fill:#e1f5fe
    style O fill:#fff3e0
    style Q fill:#c8e6c9
    style R fill:#ffebee
    style E fill:#ffecb3
```

---

### 🏪 商戶用戶 UI 流程

#### 登入與主菜單流程
```mermaid
flowchart TD
    A[啟動商戶 POS] --> B[輸入商戶代碼 + 密碼]
    B --> C[調用 merchant_login RPC]
    C --> D{登入驗證}
    D -->|失敗| E[顯示錯誤信息]
    D -->|成功| F[獲得 session_id]
    F --> G[保存 session 資訊]
    G --> H[顯示主菜單]
    
    H --> I{選擇功能}
    I -->|1| J[掃碼收款]
    I -->|2| K[退款處理]
    I -->|3| L[查看今日交易]
    I -->|4| M[查看交易記錄]
    I -->|5| N[生成結算報表]
    I -->|6| O[查看結算歷史]
    I -->|7| P[修改密碼]
    I -->|8| Q[登出系統]
    
    J --> R[掃碼收款流程]
    K --> S[退款處理流程]
    L --> T[顯示今日交易]
    M --> U[顯示交易記錄]
    N --> V[結算生成流程]
    O --> W[顯示結算歷史]
    P --> X[輸入新密碼]
    Q --> Y[調用 logout_session]
    
    R --> H
    S --> H
    T --> H
    U --> H
    V --> H
    W --> H
    X --> H
    Y --> Z[刪除 session]
    Z --> AA[結束程序]
    
    E --> B
    
    style A fill:#e1f5fe
    style C fill:#fff3e0
    style H fill:#f3e5f5
    style AA fill:#c8e6c9
```

#### 掃碼收款詳細流程
```mermaid
flowchart TD
    A[選擇掃碼收款] --> B[提示掃描 QR 碼]
    B --> C[輸入 QR 碼內容]
    C --> D[輸入收款金額]
    D --> E{金額驗證}
    E -->|≤ 0| F[顯示金額錯誤]
    E -->|> 0| G[顯示收款確認信息]
    
    G --> H{用戶確認}
    H -->|否| I[取消收款]
    H -->|是| J[調用 merchant_charge_by_qr RPC + session_id]
    
    J --> K{RPC 調用結果}
    K -->|成功| L[顯示收款成功]
    K -->|失敗| M[分析錯誤類型]
    
    M --> N{錯誤類型}
    N -->|餘額不足| O[提示客戶充值]
    N -->|QR 過期| P[提示重新掃碼]
    N -->|權限錯誤| Q[檢查商戶權限]
    N -->|企業卡錯誤| R[提示使用標準卡]
    N -->|其他錯誤| S[顯示通用錯誤]
    
    L --> T[顯示交易詳情]
    T --> U[打印收據選項]
    U --> V[返回主菜單]
    
    F --> D
    I --> V
    O --> V
    P --> B
    Q --> V
    R --> V
    S --> V
    
    style A fill:#e1f5fe
    style J fill:#fff3e0
    style L fill:#c8e6c9
    style M fill:#ffecb3
    style O fill:#ffebee
    style R fill:#ffecb3
```

#### 退款處理詳細流程（支持多次部分退款）
```mermaid
flowchart TD
    A[選擇退款處理] --> B[輸入原交易號]
    B --> C[調用 get_transaction_detail RPC]
    C --> D{查詢結果}
    D -->|失敗| E[顯示交易不存在]
    D -->|成功| F[顯示原交易信息 + 剩餘可退金額]
    
    F --> G[輸入退款金額]
    G --> H{金額驗證}
    H -->|≤ 0| I[顯示金額錯誤]
    H -->|> 原金額| J[顯示金額超限]
    H -->|有效| K[輸入退款原因]
    
    K --> L[顯示退款確認信息]
    L --> M{用戶確認}
    M -->|否| N[取消退款]
    M -->|是| O[調用 merchant_refund_tx RPC + session_id]
    
    O --> P{RPC 調用結果}
    P -->|成功| Q[顯示退款成功]
    P -->|失敗| R[分析錯誤類型]
    
    R --> S{錯誤類型}
    S -->|超過可退金額| T[顯示剩餘可退金額不足]
    S -->|交易狀態錯誤| U[顯示交易不可退款]
    S -->|權限錯誤| V[檢查商戶權限]
    S -->|其他錯誤| W[顯示通用錯誤]
    
    Q --> X[顯示退款單號]
    X --> Y[返回主菜單]
    
    E --> B
    I --> G
    J --> G
    N --> Y
    T --> Y
    U --> Y
    V --> Y
    W --> Y
    
    style A fill:#e1f5fe
    style O fill:#fff3e0
    style Q fill:#c8e6c9
    style R fill:#ffecb3
    style T fill:#ffebee
    style V fill:#ffecb3
```

---

### 👨‍💼 管理員 UI 流程

#### 主菜單流程
```mermaid
flowchart TD
    A[啟動管理控制台] --> B[管理員身份驗證]
    B --> C{身份驗證}
    C -->|失敗| D[顯示權限錯誤]
    C -->|成功| E[顯示主菜單]
    
    E --> F{選擇功能}
    F -->|1| G[會員管理]
    F -->|2| H[商戶管理]
    F -->|3| I[卡片管理]
    F -->|4| J[交易監控]
    F -->|5| K[系統維護]
    F -->|6| L[數據報表]
    F -->|7| M[退出系統]
    
    G --> N[會員管理子菜單]
    H --> O[商戶管理子菜單]
    I --> P[卡片管理子菜單]
    J --> Q[交易監控界面]
    K --> R[系統維護界面]
    L --> S[數據報表界面]
    
    N --> E
    O --> E
    P --> E
    Q --> E
    R --> E
    S --> E
    
    D --> B
    M --> T[結束程序]
    
    style A fill:#e1f5fe
    style E fill:#f3e5f5
    style T fill:#c8e6c9
```

#### 會員管理詳細流程
```mermaid
flowchart TD
    A[進入會員管理] --> B[顯示會員管理菜單]
    B --> C{選擇操作}
    C -->|1| D[創建新會員]
    C -->|2| E[查看會員信息]
    C -->|3| F[暫停會員]
    C -->|4| G[恢復會員]
    C -->|5| H[返回主菜單]
    
    D --> I[輸入會員基本信息]
    I --> J[選擇是否綁定外部身份]
    J --> K{綁定外部身份?}
    K -->|是| L[輸入外部身份信息]
    K -->|否| M[調用 create_member_profile RPC]
    L --> M
    
    M --> N{創建結果}
    N -->|成功| O[顯示創建成功]
    N -->|失敗| P[顯示錯誤信息]
    
    E --> Q[輸入會員 ID]
    Q --> R[查詢會員信息]
    R --> S[顯示會員詳情]
    
    F --> T[輸入要暫停的會員 ID]
    T --> U[確認暫停操作]
    U --> V[調用 admin_suspend_member RPC]
    V --> W{暫停結果}
    W -->|成功| X[顯示暫停成功]
    W -->|失敗| Y[顯示暫停失敗]
    
    O --> B
    P --> B
    S --> B
    X --> B
    Y --> B
    H --> Z[返回主菜單]
    
    style A fill:#e1f5fe
    style M fill:#fff3e0
    style V fill:#fff3e0
    style O fill:#c8e6c9
    style P fill:#ffebee
```

#### 卡片管理詳細流程
```mermaid
flowchart TD
    A[進入卡片管理] --> B[顯示卡片管理菜單]
    B --> C{選擇操作}
    C -->|1| D[凍結卡片]
    C -->|2| E[解凍卡片]
    C -->|3| F[調整積分]
    C -->|4| G[批量輪換 QR 碼]
    C -->|5| H[返回主菜單]
    
    D --> I[輸入卡片 ID]
    I --> J[確認凍結操作]
    J --> K[調用 freeze_card RPC]
    K --> L{凍結結果}
    L -->|成功| M[顯示凍結成功]
    L -->|失敗| N[顯示凍結失敗]
    
    E --> O[輸入卡片 ID]
    O --> P[確認解凍操作]
    P --> Q[調用 unfreeze_card RPC]
    Q --> R{解凍結果}
    R -->|成功| S[顯示解凍成功]
    R -->|失敗| T[顯示解凍失敗]
    
    F --> U[輸入卡片 ID]
    U --> V[輸入積分變化量]
    V --> W[輸入調整原因]
    W --> X[調用 update_points_and_level RPC]
    X --> Y{調整結果}
    Y -->|成功| Z[顯示調整成功]
    Y -->|失敗| AA[顯示調整失敗]
    
    G --> BB[輸入 TTL 秒數]
    BB --> CC[確認批量輪換]
    CC --> DD[調用 cron_rotate_qr_tokens RPC]
    DD --> EE{輪換結果}
    EE -->|成功| FF[顯示輪換統計]
    EE -->|失敗| GG[顯示輪換失敗]
    
    M --> B
    N --> B
    S --> B
    T --> B
    Z --> B
    AA --> B
    FF --> B
    GG --> B
    H --> HH[返回主菜單]
    
    style A fill:#e1f5fe
    style K fill:#fff3e0
    style Q fill:#fff3e0
    style X fill:#fff3e0
    style DD fill:#fff3e0
    style M fill:#c8e6c9
    style S fill:#c8e6c9
    style Z fill:#c8e6c9
    style FF fill:#c8e6c9
```

---

## 🎨 UI 界面設計模板

### 📱 會員界面模板

#### 主菜單界面
```
╔═══════════════════════════════════════╗
║            MPS 會員系統               ║
╠═══════════════════════════════════════╣
║ 會員: 張小明 (M00000001)              ║
║ 登入時間: 2025-01-15 14:30:25         ║
╠═══════════════════════════════════════╣
║ 1. 查看我的卡片                       ║
║ 2. 生成付款 QR 碼                     ║
║ 3. 充值卡片                           ║
║ 4. 查看交易記錄                       ║
║ 5. 綁定新卡片                         ║
║ 6. 查看積分等級                       ║
║ 7. 退出系統                           ║
╚═══════════════════════════════════════╝
請選擇功能 (1-7): _
```

#### 卡片列表界面
```
╔═══════════════════════════════════════════════════════════════╗
║                          我的卡片                             ║
╠═══════════════════════════════════════════════════════════════╣
║ 序號 │ 卡號        │ 類型   │ 餘額      │ 積分   │ 等級   │ 狀態 ║
╠═══════════════════════════════════════════════════════════════╣
║  1   │ STD00000001 │ 標準卡 │  ¥1,250.50│  1,250 │   1    │ 激活 ║
║  2   │ PPD00000123 │ 預付卡 │    ¥500.00│    500 │   0    │ 激活 ║
║  3   │ COR00000456 │ 企業卡 │  ¥2,000.00│      0 │   -    │ 激活 ║
╚═══════════════════════════════════════════════════════════════╝
請選擇卡片 (1-3) 或按 0 返回: _
```

#### QR 碼顯示界面
```
╔═══════════════════════════════════════╗
║              付款 QR 碼               ║
╠═══════════════════════════════════════╣
║ 卡片: STD00000001 (標準卡)            ║
║ 餘額: ¥1,250.50                       ║
╠═══════════════════════════════════════╣
║ QR 碼: ABC123XYZ789...                ║
║ 生成時間: 2025-01-15 14:35:12         ║
║ 過期時間: 2025-01-15 14:50:12         ║
╠═══════════════════════════════════════╣
║ 🔔 請向商戶出示此 QR 碼進行支付       ║
║ ⏰ QR 碼將在 15 分鐘後自動過期        ║
╚═══════════════════════════════════════╝
按任意鍵返回主菜單...
```

### 🏪 商戶界面模板

#### 收款界面
```
╔═══════════════════════════════════════╗
║              掃碼收款                 ║
╠═══════════════════════════════════════╣
║ 商戶: 星巴克咖啡 (SHOP001)            ║
║ 操作員: 李小華                        ║
╠═══════════════════════════════════════╣
║ 1. 請掃描客戶的付款 QR 碼             ║
║                                       ║
║ QR 碼內容: __________________________ ║
║                                       ║
║ 2. 請輸入收款金額                     ║
║                                       ║
║ 金額: ¥ _______________               ║
║                                       ║
╚═══════════════════════════════════════╝
```

#### 收款成功界面
```
╔═══════════════════════════════════════╗
║              收款成功                 ║
╠═══════════════════════════════════════╣
║ 交易號: PAY0000000123                 ║
║ 時間: 2025-01-15 14:35:45             ║
╠═══════════════════════════════════════╣
║ 原金額:                    ¥299.00   ║
║ 會員折扣:                     95%     ║
║ 實收金額:                  ¥284.05   ║
╠═══════════════════════════════════════╣
║ 客戶獲得積分: 299 分                  ║
║ 客戶當前等級: 銀卡會員                ║
╚═══════════════════════════════════════╝
按任意鍵繼續...
```

### 👨‍💼 管理員界面模板

#### 會員創建界面
```
╔═══════════════════════════════════════╗
║              創建新會員               ║
╠═══════════════════════════════════════╣
║ 會員姓名: __________________________ ║
║                                       ║
║ 手機號碼: __________________________ ║
║                                       ║
║ 電子郵件: __________________________ ║
║                                       ║
║ 是否綁定外部身份? (y/n): ____________ ║
║                                       ║
║ 外部平台 (wechat/alipay/line):        ║
║ _____________________________________ ║
║                                       ║
║ 外部用戶 ID:                          ║
║ _____________________________________ ║
╚═══════════════════════════════════════╝
```

#### 系統狀態監控界面
```
╔═══════════════════════════════════════════════════════════════╗
║                        系統狀態監控                           ║
╠═══════════════════════════════════════════════════════════════╣
║ 系統時間: 2025-01-15 14:35:45                                 ║
║ 運行時間: 15 天 8 小時 23 分鐘                                ║
╠═══════════════════════════════════════════════════════════════╣
║ 📊 今日統計                                                   ║
║ ├─ 總交易數: 1,234 筆                                         ║
║ ├─ 成功支付: 1,198 筆 (97.1%)                                ║
║ ├─ 失敗支付: 36 筆 (2.9%)                                    ║
║ ├─ 退款交易: 15 筆                                            ║
║ └─ 充值交易: 89 筆                                            ║
╠═══════════════════════════════════════════════════════════════╣
║ 🎯 活躍統計                                                   ║
║ ├─ 活躍會員: 8,567 人                                         ║
║ ├─ 活躍商戶: 234 家                                           ║
║ ├─ 活躍卡片: 12,345 張                                        ║
║ └─ QR 碼生成: 2,456 次                                        ║
╠═══════════════════════════════════════════════════════════════╣
║ ⚠️  系統告警                                                  ║
║ ├─ 無異常                                                     ║
╚═══════════════════════════════════════════════════════════════╝
按 R 刷新 | 按 Q 退出
```

---

## 🔧 具體功能實現流程

### 📋 會員端功能流程

#### 1. 查看交易記錄流程
```python
def view_member_transactions(member_id: str):
    """查看會員交易記錄"""
    print("┌─────────────────────────────────────┐")
    print("│            交易記錄查詢             │")
    print("└─────────────────────────────────────┘")
    
    # 設置查詢參數
    limit = 20
    offset = 0
    
    while True:
        try:
            # 調用 get_member_transactions RPC
            result = rpc("get_member_transactions", {
                "p_member_id": member_id,
                "p_limit": limit,
                "p_offset": offset
            })
            
            if not result:
                print("📝 暫無交易記錄")
                break
            
            # 顯示交易記錄
            print("┌─────────────────────────────────────────────────────────────────────┐")
            print("│                              交易記錄                               │")
            print("├─────────────────────────────────────────────────────────────────────┤")
            print("│ 交易號        │ 類型   │ 金額      │ 狀態     │ 時間              │")
            print("├─────────────────────────────────────────────────────────────────────┤")
            
            for tx in result:
                print(f"│ {tx['tx_no']:<12} │ {tx['tx_type']:<6} │ ¥{tx['final_amount']:>8.2f} │ {tx['status']:<8} │ {tx['created_at']:<17} │")
            
            print("└─────────────────────────────────────────────────────────────────────┘")
            
            # 分頁控制
            total_count = result[0].get('total_count', 0) if result else 0
            current_page = offset // limit + 1
            total_pages = (total_count + limit - 1) // limit
            
            print(f"第 {current_page} 頁，共 {total_pages} 頁 (總計 {total_count} 筆)")
            
            if total_pages > 1:
                action = input("N-下一頁 | P-上一頁 | Q-退出: ").upper()
                if action == 'N' and current_page < total_pages:
                    offset += limit
                elif action == 'P' and current_page > 1:
                    offset -= limit
                elif action == 'Q':
                    break
            else:
                input("按任意鍵返回...")
                break
                
        except Exception as e:
            print(f"❌ 查詢失敗: {e}")
            break
```

#### 2. 綁定新卡片流程
```python
def bind_new_card(member_id: str):
    """綁定新卡片流程"""
    print("┌─────────────────────────────────────┐")
    print("│            綁定新卡片               │")
    print("└─────────────────────────────────────┘")
    
    # 輸入卡片 ID
    card_id = input("請輸入卡片 ID: ")
    
    # 選擇綁定角色
    roles = ["member", "viewer"]
    print("\n可選角色:")
    for i, role in enumerate(roles, 1):
        role_desc = "成員" if role == "member" else "查看者"
        print(f"{i}. {role} ({role_desc})")
    
    while True:
        try:
            choice = int(input("請選擇角色 (1-2): "))
            if 1 <= choice <= 2:
                selected_role = roles[choice - 1]
                break
            print("❌ 請選擇 1-2")
        except ValueError:
            print("❌ 請輸入有效數字")
    
    # 輸入綁定密碼（如果需要）
    binding_password = input("請輸入綁定密碼 (如果卡片設置了密碼): ")
    
    # 確認綁定
    print(f"\n綁定信息確認:")
    print(f"卡片 ID: {card_id}")
    print(f"綁定角色: {selected_role}")
    confirm = input("確認綁定？(y/n): ")
    
    if confirm.lower() != 'y':
        print("❌ 綁定已取消")
        return
    
    try:
        # 調用 bind_member_to_card RPC
        result = rpc("bind_member_to_card", {
            "p_card_id": card_id,
            "p_member_id": member_id,
            "p_role": selected_role,
            "p_binding_password": binding_password if binding_password else None
        })
        
        if result:
            print("✅ 卡片綁定成功！")
        else:
            print("❌ 卡片綁定失敗")
            
    except Exception as e:
        error_msg = str(e)
        if "CARD_TYPE_NOT_SHAREABLE" in error_msg:
            print("❌ 此類型卡片不支持共享")
        elif "INVALID_BINDING_PASSWORD" in error_msg:
            print("❌ 綁定密碼錯誤")
        elif "CARD_NOT_FOUND_OR_INACTIVE" in error_msg:
            print("❌ 卡片不存在或未激活")
        else:
            print(f"❌ 綁定失敗: {error_msg}")
```

### 🏪 商戶端功能流程

#### 1. 查看今日交易
```python
def view_today_transactions(merchant_id: str):
    """查看今日交易"""
    from datetime import datetime, time
    
    print("┌─────────────────────────────────────┐")
    print("│            今日交易統計             │")
    print("└─────────────────────────────────────┘")
    
    # 設置今日時間範圍
    today = datetime.now().date()
    start_time = datetime.combine(today, time.min)
    end_time = datetime.combine(today, time.max)
    
    try:
        # 調用 get_merchant_transactions RPC
        result = rpc("get_merchant_transactions", {
            "p_merchant_id": merchant_id,
            "p_limit": 100,
            "p_offset": 0,
            "p_start_date": start_time.isoformat(),
            "p_end_date": end_time.isoformat()
        })
        
        if not result:
            print("📝 今日暫無交易記錄")
            return
        
        # 統計數據
        total_count = 0
        payment_count = 0
        refund_count = 0
        total_amount = 0
        payment_amount = 0
        refund_amount = 0
        
        for tx in result:
            total_count += 1
            if tx['tx_type'] == 'payment':
                payment_count += 1
                payment_amount += tx['final_amount']
            elif tx['tx_type'] == 'refund':
                refund_count += 1
                refund_amount += tx['final_amount']
            total_amount += tx['final_amount']
        
        # 顯示統計信息
        print("┌─────────────────────────────────────┐")
        print("│            今日交易統計             │")
        print("├─────────────────────────────────────┤")
        print(f"│ 總交易數: {total_count:>25} 筆 │")
        print(f"│ 支付交易: {payment_count:>25} 筆 │")
        print(f"│ 退款交易: {refund_count:>25} 筆 │")
        print("├─────────────────────────────────────┤")
        print(f"│ 支付金額: ¥{payment_amount:>24.2f} │")
        print(f"│ 退款金額: ¥{refund_amount:>24.2f} │")
        print(f"│ 淨收入: ¥{payment_amount - refund_amount:>26.2f} │")
        print("└─────────────────────────────────────┘")
        
        # 顯示詳細交易列表
        show_detail = input("是否查看詳細交易列表？(y/n): ")
        if show_detail.lower() == 'y':
            print("\n詳細交易記錄:")
            print("┌─────────────────────────────────────────────────────────────────────┐")
            print("│ 交易號        │ 類型   │ 金額      │ 狀態     │ 時間              │")
            print("├─────────────────────────────────────────────────────────────────────┤")
            
            for tx in result:
                print(f"│ {tx['tx_no']:<12} │ {tx['tx_type']:<6} │ ¥{tx['final_amount']:>8.2f} │ {tx['status']:<8} │ {tx['created_at']:<17} │")
            
            print("└─────────────────────────────────────────────────────────────────────┘")
        
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")
```

#### 2. 生成結算報表
```python
def generate_settlement_report(merchant_id: str):
    """生成結算報表"""
    print("┌─────────────────────────────────────┐")
    print("│            生成結算報表             │")
    print("└─────────────────────────────────────┘")
    
    # 選擇結算模式
    modes = ["realtime", "t_plus_1", "monthly"]
    mode_names = ["實時結算", "T+1結算", "月結算"]
    
    print("\n結算模式:")
    for i, (mode, name) in enumerate(zip(modes, mode_names), 1):
        print(f"{i}. {name} ({mode})")
    
    while True:
        try:
            choice = int(input("請選擇結算模式 (1-3): "))
            if 1 <= choice <= 3:
                selected_mode = modes[choice - 1]
                break
            print("❌ 請選擇 1-3")
        except ValueError:
            print("❌ 請輸入有效數字")
    
    # 輸入結算期間
    print("\n請輸入結算期間:")
    start_date = input("開始日期 (YYYY-MM-DD): ")
    end_date = input("結束日期 (YYYY-MM-DD): ")
    
    try:
        # 調用 generate_settlement RPC
        settlement_id = rpc("generate_settlement", {
            "p_merchant_id": merchant_id,
            "p_mode": selected_mode,
            "p_period_start": f"{start_date}T00:00:00Z",
            "p_period_end": f"{end_date}T23:59:59Z"
        })
        
        print(f"✅ 結算報表生成成功！")
        print(f"📋 結算 ID: {settlement_id}")
        
        # 查詢結算詳情
        settlements = rpc("list_settlements", {
            "p_merchant_id": merchant_id,
            "p_limit": 1,
            "p_offset": 0
        })
        
        if settlements:
            settlement = settlements[0]
            print("┌─────────────────────────────────────┐")
            print("│            結算報表詳情             │")
            print("├─────────────────────────────────────┤")
            print(f"│ 結算期間: {start_date} ~ {end_date} │")
            print(f"│ 結算模式: {mode_names[modes.index(selected_mode)]:<23} │")
            print(f"│ 交易筆數: {settlement['total_tx_count']:>25} │")
            print(f"│ 結算金額: ¥{settlement['total_amount']:>24.2f} │")
            print(f"│ 結算狀態: {settlement['status']:<23} │")
            print("└─────────────────────────────────────┘")
        
    except Exception as e:
        print(f"❌ 結算生成失敗: {e}")
```

---

## 🎯 開發實現建議

### 1. 最小可行產品 (MVP) 功能
- **會員端**: 查看卡片 + 生成 QR 碼 + 充值
- **商戶端**: 掃碼收款 + 簡單退款
- **管理端**: 創建會員 + 凍結卡片

### 2. 技術實現重點
- 基於現有 RPC 函數，不需要額外的後端開發
- 使用簡潔的 ASCII 界面，易於在終端中使用
- 完善的錯誤處理，對應 RPC 的各種錯誤碼
- 輸入驗證和操作確認，提升用戶體驗

### 3. 擴展方向
- 添加簡單的數據可視化（ASCII 圖表）
- 支持配置文件管理不同環境
- 添加日誌記錄功能
- 支持批量操作

這個設計完全基於現有的 RPC 功能，提供了實用的文字 UI 來操作 MPS 系統，既不會超出現有範疇，又能滿足基本的業務操作需求。