# MPS 系統架構圖集

## 1. 整體系統架構圖

```mermaid
graph TB
    subgraph "客戶端層"
        MA[會員 App/小程序]
        MP[商戶 POS 系統]
        AC[管理員控制台]
    end
    
    subgraph "API 層"
        SB[Supabase PostgREST API]
        RPC[RPC Functions]
    end
    
    subgraph "業務邏輯層"
        subgraph "核心服務"
            MS[會員服務]
            CS[卡片服務]
            PS[支付服務]
            QS[QR 碼服務]
            SS[結算服務]
        end
    end
    
    subgraph "數據層"
        subgraph "Supabase PostgreSQL"
            subgraph "app schema"
                MP_T[member_profiles]
                MC_T[member_cards]
                TX_T[transactions]
                MR_T[merchants]
                ST_T[settlements]
            end
            subgraph "audit schema"
                AL_T[event_log]
            end
        end
    end
    
    subgraph "外部系統"
        WX[微信支付]
        ALI[支付寶]
        BANK[銀行系統]
    end
    
    MA --> SB
    MP --> SB
    AC --> SB
    SB --> RPC
    RPC --> MS
    RPC --> CS
    RPC --> PS
    RPC --> QS
    RPC --> SS
    MS --> MP_T
    CS --> MC_T
    PS --> TX_T
    QS --> MC_T
    SS --> ST_T
    PS --> AL_T
    PS --> WX
    PS --> ALI
    SS --> BANK
```

## 2. 數據庫 ER 關係圖

```mermaid
erDiagram
    MEMBER_PROFILES {
        uuid id PK
        text member_no UK
        text name
        text phone UK
        text email UK
        text status
        timestamptz created_at
        timestamptz updated_at
    }
    
    MEMBER_EXTERNAL_IDENTITIES {
        uuid id PK
        uuid member_id FK
        text provider
        text external_id
        jsonb meta
        timestamptz created_at
    }
    
    MEMBER_CARDS {
        uuid id PK
        text card_no UK
        card_type card_type
        uuid owner_member_id FK
        numeric balance
        int points
        int level
        numeric discount_rate
        text binding_password_hash
        card_status status
        timestamptz expires_at
        timestamptz created_at
        timestamptz updated_at
    }
    
    CARD_BINDINGS {
        uuid id PK
        uuid card_id FK
        uuid member_id FK
        bind_role role
        timestamptz created_at
    }
    
    CARD_QR_STATE {
        uuid card_id PK
        text qr_hash
        timestamptz issued_at
        timestamptz expires_at
        timestamptz updated_at
    }
    
    CARD_QR_HISTORY {
        uuid id PK
        uuid card_id FK
        text qr_hash
        timestamptz issued_at
        timestamptz expires_at
    }
    
    MERCHANTS {
        uuid id PK
        text code UK
        text name
        text contact
        boolean active
        timestamptz created_at
        timestamptz updated_at
    }
    
    MERCHANT_USERS {
        uuid id PK
        uuid merchant_id FK
        uuid user_id FK
        text role
        timestamptz created_at
    }
    
    TRANSACTIONS {
        uuid id PK
        text tx_no UK
        tx_type tx_type
        uuid card_id FK
        uuid merchant_id FK
        numeric raw_amount
        numeric discount_applied
        numeric final_amount
        int points_earned
        tx_status status
        text reason
        pay_method payment_method
        jsonb tag
        timestamptz created_at
        timestamptz updated_at
    }
    
    POINT_LEDGER {
        uuid id PK
        uuid card_id FK
        uuid tx_id FK
        int change
        int balance_before
        int balance_after
        text reason
        timestamptz created_at
    }
    
    SETTLEMENTS {
        uuid id PK
        uuid merchant_id FK
        settlement_mode mode
        timestamptz period_start
        timestamptz period_end
        numeric total_amount
        int total_tx_count
        settlement_status status
        jsonb payload
        timestamptz created_at
        timestamptz updated_at
    }
    
    MEMBERSHIP_LEVELS {
        uuid id PK
        int level UK
        text name
        int min_points
        int max_points
        numeric discount
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    
    AUDIT_EVENT_LOG {
        bigint id PK
        timestamptz happened_at
        uuid actor_user_id
        text action
        text object_type
        uuid object_id
        jsonb context
    }
    
    %% 關係定義
    MEMBER_PROFILES ||--o{ MEMBER_EXTERNAL_IDENTITIES : "has"
    MEMBER_PROFILES ||--o{ MEMBER_CARDS : "owns"
    MEMBER_PROFILES ||--o{ CARD_BINDINGS : "binds_to"
    MEMBER_CARDS ||--o{ CARD_BINDINGS : "bound_by"
    MEMBER_CARDS ||--|| CARD_QR_STATE : "has_current_qr"
    MEMBER_CARDS ||--o{ CARD_QR_HISTORY : "qr_history"
    MEMBER_CARDS ||--o{ TRANSACTIONS : "used_in"
    MEMBER_CARDS ||--o{ POINT_LEDGER : "point_changes"
    MERCHANTS ||--o{ MERCHANT_USERS : "has_users"
    MERCHANTS ||--o{ TRANSACTIONS : "processes"
    MERCHANTS ||--o{ SETTLEMENTS : "settled_for"
    TRANSACTIONS ||--o{ POINT_LEDGER : "generates_points"
    MEMBERSHIP_LEVELS ||--o{ MEMBER_CARDS : "determines_level"
```

## 3. 卡片類型與權限矩陣

```mermaid
graph TD
    subgraph "卡片類型分類"
        STD[標準卡 Standard]
        PPD[預付卡 Prepaid]
        COR[企業卡 Corporate]
        VCH[優惠券卡 Voucher]
    end
    
    subgraph "權限角色"
        OWN[Owner 擁有者]
        ADM[Admin 管理員]
        MEM[Member 成員]
        VIE[Viewer 查看者]
    end
    
    subgraph "功能權限"
        PAY[支付功能]
        RCG[充值功能]
        SHR[共享功能]
        PWD[密碼保護]
        PTS[積分累積]
        DIS[折扣享受]
    end
    
    STD --> OWN
    STD --> PAY
    STD --> PTS
    STD --> DIS
    STD -.-> |不支持| SHR
    STD -.-> |不支持| RCG
    STD -.-> |不需要| PWD
    
    PPD --> OWN
    PPD --> ADM
    PPD --> MEM
    PPD --> PAY
    PPD --> RCG
    PPD --> SHR
    PPD --> PWD
    PPD --> PTS
    PPD --> DIS
    
    COR --> OWN
    COR --> ADM
    COR --> MEM
    COR --> VIE
    COR --> PAY
    COR --> RCG
    COR --> SHR
    COR --> PWD
    COR --> DIS
    COR -.-> |不支持| PTS
    
    VCH --> OWN
    VCH --> DIS
    VCH -.-> |不支持| PAY
    VCH -.-> |不支持| RCG
    VCH -.-> |不支持| SHR
    VCH -.-> |不支持| PTS
```

## 4. QR 碼生命週期圖

```mermaid
stateDiagram-v2
    [*] --> 生成請求
    生成請求 --> QR生成中 : rotate_card_qr()
    QR生成中 --> QR有效 : 生成成功
    QR有效 --> QR掃描 : 商戶掃描
    QR掃描 --> 驗證中 : validate_qr_plain()
    驗證中 --> 支付處理 : 驗證成功
    驗證中 --> QR無效 : 驗證失敗
    支付處理 --> 交易完成 : 支付成功
    支付處理 --> 支付失敗 : 餘額不足等
    
    QR有效 --> QR過期 : TTL 到期
    QR有效 --> QR撤銷 : revoke_card_qr()
    QR過期 --> [*]
    QR撤銷 --> [*]
    QR無效 --> [*]
    交易完成 --> [*]
    支付失敗 --> [*]
    
    note right of QR生成中
        - 生成 32 字節隨機數
        - bcrypt 加密存儲
        - 設置 TTL
        - 記錄歷史
    end note
    
    note right of 驗證中
        - 檢查過期時間
        - bcrypt 驗證
        - 返回 card_id
    end note
```

## 5. 支付流程序列圖

```mermaid
sequenceDiagram
    participant Member as 會員 App
    participant POS as 商戶 POS
    participant API as Supabase API
    participant DB as PostgreSQL
    participant Audit as 審計日誌
    
    Member->>API: rotate_card_qr(card_id, ttl)
    API->>DB: 生成 QR hash 並存儲
    DB-->>API: 返回 plain QR
    API-->>Member: QR 碼數據
    Member->>Member: 顯示 QR 碼
    
    POS->>POS: 掃描 QR 碼
    POS->>API: merchant_charge_by_qr(merchant_code, qr_plain, amount)
    
    API->>DB: validate_qr_plain(qr_plain)
    DB-->>API: 返回 card_id
    
    API->>DB: pg_advisory_xact_lock(card_id)
    Note over DB: 鎖定卡片防止並發
    
    API->>DB: 檢查商戶權限
    API->>DB: 檢查卡片狀態和餘額
    API->>DB: 計算折扣和最終金額
    
    API->>DB: 插入交易記錄 (processing)
    API->>DB: 更新卡片餘額和積分
    API->>DB: 更新交易狀態 (completed)
    API->>Audit: 記錄支付事件
    
    DB-->>API: 交易成功
    API-->>POS: 返回交易結果
    POS->>POS: 顯示支付成功