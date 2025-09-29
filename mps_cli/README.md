# MPS CLI - Member Payment System 命令行界面

## 簡介

MPS CLI 是一個基於文字界面的會員支付系統客戶端，支持三種角色：
- 👤 會員用戶：查看卡片、生成 QR 碼、充值等
- 🏪 商戶用戶：掃碼收款、退款處理等  
- 👨‍💼 管理員：會員管理、卡片管理等

## 安裝

1. 安裝依賴：
```bash
pip install -r requirements.txt
```

2. 配置環境變量：
```bash
cp .env.example .env
# 編輯 .env 文件，填入正確的 Supabase 配置
```

3. 運行程序：
```bash
python main.py
```

## 功能特性

### P0 核心功能
- ✅ 會員註冊和管理
- ✅ 生成付款 QR 碼
- ✅ 掃碼收款
- ✅ 卡片充值

### P1 重要功能
- ✅ 退款處理
- ✅ 綁定卡片
- ✅ 凍結卡片

## 項目結構

```
mps_cli/
├── main.py                 # 主入口
├── requirements.txt        # 依賴包列表
├── .env.example           # 環境變量示例
├── README.md              # 說明文檔
├── config/                # 配置管理
│   ├── __init__.py
│   ├── settings.py        # 配置管理
│   ├── supabase_client.py # Supabase 客戶端
│   └── constants.py       # 常量定義
├── models/                # 數據模型
│   ├── __init__.py
│   ├── base.py           # 基礎模型類
│   ├── member.py         # 會員模型
│   ├── card.py           # 卡片模型
│   └── transaction.py    # 交易模型
├── services/              # 業務服務
│   ├── __init__.py
│   ├── base_service.py   # 基礎服務類
│   ├── member_service.py # 會員服務
│   ├── payment_service.py# 支付服務
│   ├── merchant_service.py# 商戶服務
│   ├── admin_service.py  # 管理服務
│   └── qr_service.py     # QR 碼服務
├── ui/                   # 用戶界面
│   ├── __init__.py
│   ├── base_ui.py        # 基礎 UI 組件
│   ├── member_ui.py      # 會員界面
│   ├── merchant_ui.py    # 商戶界面
│   ├── admin_ui.py       # 管理員界面
│   └── components/       # UI 組件
│       ├── __init__.py
│       ├── menu.py       # 菜單組件
│       ├── table.py      # 表格組件
│       └── form.py       # 表單組件
├── utils/                # 工具函數
│   ├── __init__.py
│   ├── validators.py     # 驗證器
│   ├── formatters.py     # 格式化器
│   ├── error_handler.py  # 錯誤處理器
│   └── logger.py         # 日誌管理
└── tests/                # 測試文件
    ├── __init__.py
    ├── test_services.py  # 服務層測試
    └── test_ui.py        # UI 層測試
```

## 使用說明

### 會員用戶
1. 選擇「會員用戶」角色
2. 輸入會員 ID 登入
3. 可進行查看卡片、生成 QR 碼、充值等操作

### 商戶用戶  
1. 選擇「商戶用戶」角色
2. 輸入商戶代碼登入
3. 可進行掃碼收款、退款處理等操作

### 管理員
1. 選擇「管理員」角色
2. 進行身份驗證
3. 可進行會員管理、卡片管理等操作

## 技術特性

- 基於 Supabase RPC 函數的後端交互
- 支持中文字符寬度對齊 (wcwidth)
- 完善的錯誤處理和用戶提示
- 模組化的架構設計
- 易於擴展的組件系統

## 開發

### 環境要求
- Python 3.8+
- Supabase 項目

### 開發模式
```bash
# 安裝開發依賴
pip install -r requirements.txt

# 運行測試
python -m pytest tests/

# 運行程序
python main.py