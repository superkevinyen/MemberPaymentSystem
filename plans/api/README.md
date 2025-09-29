# MPS API 開發計劃總覽

## 📋 項目概述

MPS API 是 Member Payment System 的統一後端服務，基於 FastAPI 構建。它將現有的 Supabase RPC 函數包裝為安全的 HTTP API，解決客戶端直接使用 `service_role_key` 的安全問題，同時為多種客戶端（CLI、小程序、Web 應用）提供統一的接口。

## 🎯 核心價值

### 🔐 安全性提升
- **密鑰隔離**：`service_role_key` 完全隔離在服務端
- **權限控制**：基於 JWT 的細粒度權限管理
- **認證分離**：應用用戶與 Supabase Auth 用戶分離
- **審計追蹤**：完整的操作日誌和審計記錄

### 🏗️ 架構優化
- **統一接口**：所有客戶端使用相同的 HTTP API
- **RPC 保護**：完整保留現有 RPC 函數，僅作安全包裝
- **可擴展性**：易於添加新客戶端和新功能
- **維護性**：業務邏輯集中，代碼結構清晰

### 🚀 業務價值
- **多端支持**：同時支持 CLI、小程序、Web 等多種客戶端
- **快速開發**：新客戶端可快速接入現有 API
- **運維友好**：統一的監控、日誌和告警
- **成本控制**：共享的後端服務，降低維護成本

---

## 📁 文檔結構

### 📚 完整文檔清單

| 文檔名稱 | 內容概述 | 目標讀者 |
|----------|----------|----------|
| **[fastapi_architecture.md](fastapi_architecture.md)** | API 整體架構設計，技術選型，核心組件 | 架構師、開發者 |
| **[implementation_roadmap.md](implementation_roadmap.md)** | 詳細實施計劃，時程安排，工作量評估 | 項目經理、開發者 |
| **[api_endpoints_specification.md](api_endpoints_specification.md)** | 完整的 API 端點規格，請求響應格式 | 前端開發者、測試人員 |
| **[cli_adaptation_guide.md](cli_adaptation_guide.md)** | CLI 客戶端適配指南，修改對照表 | CLI 開發者 |
| **[deployment_operations_guide.md](deployment_operations_guide.md)** | 部署方案，運維指南，監控告警 | 運維工程師、DevOps |
| **[README.md](README.md)** | 項目總覽，快速開始指南 | 所有人員 |

---

## 🔄 RPC 函數與 API 的對應關係

### 📊 完整映射表

基於現有的 [`rpc/mps_rpc.sql`](../../rpc/mps_rpc.sql)，所有 RPC 函數都會被完整保留並通過 API 安全調用：

| RPC 函數 | 功能描述 | 新 API 端點 | 調用方式變化 |
|----------|----------|-------------|-------------|
| [`create_member_profile`](../../rpc/mps_rpc.sql:15) | 創建會員檔案 | `POST /admin/members` | RPC → HTTP API |
| [`bind_member_to_card`](../../rpc/mps_rpc.sql:74) | 綁定會員到卡片 | `POST /member/bind-card` | RPC → HTTP API |
| [`unbind_member_from_card`](../../rpc/mps_rpc.sql:128) | 解綁會員卡片 | `POST /member/unbind-card` | RPC → HTTP API |
| [`rotate_card_qr`](../../rpc/mps_rpc.sql:158) | 生成/刷新 QR 碼 | `POST /member/qr/generate` | RPC → HTTP API |
| [`revoke_card_qr`](../../rpc/mps_rpc.sql:191) | 撤銷 QR 碼 | `POST /member/qr/revoke` | RPC → HTTP API |
| [`validate_qr_plain`](../../rpc/mps_rpc.sql:206) | 驗證 QR 碼 | `POST /common/qr/validate` | RPC → HTTP API |
| [`cron_rotate_qr_tokens`](../../rpc/mps_rpc.sql:235) | 批量輪換 QR 碼 | `POST /admin/qr/batch-rotate` | RPC → HTTP API |
| [`merchant_charge_by_qr`](../../rpc/mps_rpc.sql:274) | 商戶掃碼收款 | `POST /merchant/charge` | RPC → HTTP API |
| [`merchant_refund_tx`](../../rpc/mps_rpc.sql:401) | 商戶退款交易 | `POST /merchant/refund` | RPC → HTTP API |
| [`user_recharge_card`](../../rpc/mps_rpc.sql:467) | 用戶充值卡片 | `POST /member/recharge` | RPC → HTTP API |
| [`update_points_and_level`](../../rpc/mps_rpc.sql:546) | 更新積分等級 | `POST /admin/points/adjust` | RPC → HTTP API |
| [`freeze_card`](../../rpc/mps_rpc.sql:591) | 凍結卡片 | `POST /admin/cards/freeze` | RPC → HTTP API |
| [`unfreeze_card`](../../rpc/mps_rpc.sql:606) | 解凍卡片 | `POST /admin/cards/unfreeze` | RPC → HTTP API |
| [`admin_suspend_member`](../../rpc/mps_rpc.sql:621) | 管理員暫停會員 | `POST /admin/members/suspend` | RPC → HTTP API |
| [`admin_suspend_merchant`](../../rpc/mps_rpc.sql:636) | 管理員暫停商戶 | `POST /admin/merchants/suspend` | RPC → HTTP API |
| [`generate_settlement`](../../rpc/mps_rpc.sql:655) | 生成結算 | `POST /merchant/settlements` | RPC → HTTP API |
| [`list_settlements`](../../rpc/mps_rpc.sql:690) | 查詢結算列表 | `GET /merchant/settlements` | RPC → HTTP API |
| [`get_member_transactions`](../../rpc/mps_rpc.sql:710) | 獲取會員交易記錄 | `GET /member/transactions` | RPC → HTTP API |
| [`get_merchant_transactions`](../../rpc/mps_rpc.sql:741) | 獲取商戶交易記錄 | `GET /merchant/transactions` | RPC → HTTP API |
| [`get_transaction_detail`](../../rpc/mps_rpc.sql:769) | 獲取交易詳情 | `GET /common/transactions/{tx_no}` | RPC → HTTP API |

**關鍵洞察**：所有現有的 RPC 函數都會被**完整保留**，只是調用方式從客戶端直接調用變為通過安全的 HTTP API 調用。業務邏輯和數據處理邏輯完全不變。

---

## 🚀 快速開始

### 1. 開發環境搭建

```bash
# 1. 創建 API 服務
mkdir mps_api
cd mps_api

# 2. 創建虛擬環境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安裝依賴
pip install fastapi uvicorn supabase pyjwt python-dotenv pydantic

# 4. 創建基礎結構
mkdir -p config auth api services models utils middleware tests
touch main.py requirements.txt .env.example

# 5. 配置環境變量
cp .env.example .env
# 編輯 .env，填入 Supabase 配置

# 6. 啟動開發服務器
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 2. CLI 客戶端適配

```bash
# 1. 修改 CLI 配置
cd ../mps_cli
cp .env.example .env
# 編輯 .env，設置 API_BASE_URL=http://127.0.0.1:8000

# 2. 安裝新依賴
pip install requests

# 3. 測試連接
python main.py test

# 4. 測試功能
python main.py
```

---

## 📊 工作量和時程總結

### 🗓️ 完整開發時程

| 階段 | 工作內容 | 工作量 | 負責人 |
|------|----------|--------|--------|
| **第一週** | **API 服務開發** | **5天** | **後端開發者** |
| Day 1 | 項目搭建、基礎配置 | 1天 | 後端開發者 |
| Day 2 | 認證系統實現 | 1天 | 後端開發者 |
| Day 3 | 業務服務層實現 | 1天 | 後端開發者 |
| Day 4 | API 路由實現 | 1天 | 後端開發者 |
| Day 5 | 中間件、錯誤處理 | 1天 | 後端開發者 |
| **第二週** | **CLI 適配和測試** | **3天** | **前端開發者** |
| Day 6 | CLI 客戶端重構 | 1天 | 前端開發者 |
| Day 7 | 服務層適配 | 1天 | 前端開發者 |
| Day 8 | 集成測試和優化 | 1天 | 全體開發者 |
| **第三週** | **部署和運維** | **2天** | **DevOps 工程師** |
| Day 9 | 生產環境部署 | 1天 | DevOps 工程師 |
| Day 10 | 監控告警配置 | 1天 | DevOps 工程師 |

**總工作量：10 天 (2 週)**

### 💰 成本估算

#### 開發成本
- **後端開發**：5 人天 × $500/天 = $2,500
- **前端適配**：3 人天 × $400/天 = $1,200
- **DevOps 部署**：2 人天 × $600/天 = $1,200
- **總開發成本**：$4,900

#### 運維成本 (月度)
- **服務器**：$100/月 (2核4GB × 2實例)
- **負載均衡**：$20/月
- **Redis 緩存**：$30/月
- **監控服務**：$50/月
- **總運維成本**：$200/月

---

## 🎯 里程碑和交付物

### 📋 第一階段交付物 (API 服務)

#### 代碼交付
- [x] 完整的 FastAPI 項目結構
- [x] 認證系統實現
- [x] 所有業務 API 端點
- [x] 完整的錯誤處理
- [x] 單元測試和集成測試

#### 文檔交付
- [x] API 接口文檔 (OpenAPI/Swagger)
- [x] 部署指南
- [x] 運維手冊
- [x] 安全配置指南

#### 環境交付
- [x] 開發環境配置
- [x] 測試環境部署
- [x] 生產環境準備
- [x] CI/CD 流水線

### 📋 第二階段交付物 (CLI 適配)

#### 代碼交付
- [x] 適配後的 CLI 客戶端
- [x] API 客戶端實現
- [x] 更新的配置管理
- [x] 完整的功能測試

#### 驗證交付
- [x] 所有 P0/P1 功能驗證
- [x] 用戶體驗一致性驗證
- [x] 性能基準測試
- [x] 安全性測試

### 📋 第三階段交付物 (生產部署)

#### 部署交付
- [x] 生產環境部署
- [x] 監控系統配置
- [x] 告警規則設置
- [x] 備份恢復流程

#### 運維交付
- [x] 運維操作手冊
- [x] 故障排除指南
- [x] 性能調優建議
- [x] 安全加固方案

---

## 🔧 技術棧總覽

### 🐍 後端技術棧 (mps_api)

| 組件 | 技術選型 | 版本 | 用途 |
|------|----------|------|------|
| **Web 框架** | FastAPI | 0.104+ | HTTP API 服務 |
| **ASGI 服務器** | Uvicorn | 0.24+ | 異步 Web 服務器 |
| **數據庫客戶端** | Supabase Python | 2.3+ | Supabase 連接 |
| **認證** | PyJWT | 2.8+ | JWT Token 處理 |
| **數據驗證** | Pydantic | 2.5+ | 請求響應驗證 |
| **緩存** | Redis | 7.0+ | Session 和數據緩存 |
| **監控** | Prometheus | - | 指標收集 |
| **日誌** | Python Logging | - | 結構化日誌 |

### 💻 客戶端技術棧 (mps_cli)

| 組件 | 技術選型 | 版本 | 用途 |
|------|----------|------|------|
| **HTTP 客戶端** | Requests | 2.31+ | API 調用 |
| **文字 UI** | 原生 Python | 3.8+ | 命令行界面 |
| **中文支持** | wcwidth | 0.2+ | 字符寬度計算 |
| **配置管理** | python-dotenv | 1.0+ | 環境變量管理 |

---

## 📈 性能和擴展性

### 🎯 性能目標

| 指標 | 目標值 | 測量方法 |
|------|--------|----------|
| **API 響應時間** | < 500ms | P95 響應時間 |
| **併發處理能力** | 1000+ QPS | 壓力測試 |
| **可用性** | 99.9% | 月度統計 |
| **錯誤率** | < 0.1% | 錯誤請求比例 |

### 🚀 擴展方案

#### 水平擴展
```yaml
# 增加 API 實例
services:
  mps_api_1:
    build: ./mps_api
    ports: ["8001:8000"]
  
  mps_api_2:
    build: ./mps_api
    ports: ["8002:8000"]
  
  mps_api_3:
    build: ./mps_api
    ports: ["8003:8000"]

# 負載均衡配置
nginx:
  upstream:
    - mps_api_1:8000
    - mps_api_2:8000
    - mps_api_3:8000
```

#### 垂直擴展
```yaml
# 增加資源配置
services:
  mps_api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

---

## 🔒 安全考量

### 🛡️ 安全措施

#### 1. 密鑰管理
- **服務端隔離**：`service_role_key` 僅在 API 服務端使用
- **環境變量**：敏感配置通過環境變量管理
- **密鑰輪換**：定期更換 JWT 密鑰
- **訪問控制**：嚴格的服務器訪問權限

#### 2. 認證安全
- **Token 過期**：JWT Token 24小時自動過期
- **權限最小化**：每個角色僅獲得必需權限
- **Session 管理**：支持強制登出和 Session 撤銷
- **登入限流**：防止暴力破解攻擊

#### 3. 傳輸安全
- **HTTPS 強制**：所有 API 調用強制使用 HTTPS
- **安全頭**：完整的 HTTP 安全頭配置
- **CORS 控制**：嚴格的跨域訪問控制
- **輸入驗證**：所有輸入數據嚴格驗證

#### 4. 數據安全
- **敏感數據脫敏**：日誌中不記錄敏感信息
- **審計追蹤**：完整的操作審計記錄
- **數據加密**：傳輸和存儲數據加密
- **備份安全**：加密的數據備份

---

## 📊 風險評估和應對

### ⚠️ 主要風險

| 風險項目 | 風險等級 | 影響 | 應對策略 |
|----------|----------|------|----------|
| **API 服務故障** | 高 | 所有客戶端不可用 | 多實例部署、健康檢查、自動重啟 |
| **數據庫連接失敗** | 高 | 業務功能不可用 | 連接池、重試機制、故障轉移 |
| **認證系統故障** | 中 | 用戶無法登入 | JWT 無狀態設計、多密鑰備份 |
| **網絡延遲** | 中 | 用戶體驗下降 | 緩存策略、CDN 加速 |
| **安全漏洞** | 高 | 數據洩露風險 | 安全審計、定期更新、監控告警 |

### 🛠️ 應對措施

#### 高可用性設計
```python
# 服務健康檢查
@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database_connection(),
        "redis": await check_redis_connection(),
        "rpc_functions": await check_rpc_functions()
    }
    
    if all(checks.values()):
        return {"status": "healthy", "checks": checks}
    else:
        raise HTTPException(status_code=503, detail={"status": "unhealthy", "checks": checks})

# 自動重試機制
async def call_rpc_with_retry(function_name: str, params: Dict, max_retries: int = 3):
    for attempt in range(max_retries + 1):
        try:
            return await supabase.rpc(function_name, params).execute()
        except Exception as e:
            if attempt == max_retries:
                raise
            await asyncio.sleep(2 ** attempt)  # 指數退避
```

#### 故障恢復流程
```bash
# 自動故障恢復腳本
#!/bin/bash
# scripts/auto_recovery.sh

# 檢查 API 服務健康狀態
if ! curl -f http://localhost:8000/health; then
    echo "API 服務異常，嘗試重啟..."
    
    # 重啟服務
    docker-compose restart mps_api
    
    # 等待服務啟動
    sleep 30
    
    # 再次檢查
    if curl -f http://localhost:8000/health; then
        echo "服務恢復成功"
        # 發送恢復通知
        curl -X POST "https://hooks.slack.com/..." -d '{"text":"MPS API 服務已恢復"}'
    else
        echo "服務恢復失敗，需要人工介入"
        # 發送告警通知
        curl -X POST "https://hooks.slack.com/..." -d '{"text":"MPS API 服務恢復失敗，需要緊急處理"}'
    fi
fi
```

---

## 🎯 成功標準

### ✅ 技術成功標準

#### 功能完整性
- 所有現有 RPC 函數通過 API 正常調用
- 所有 P0/P1 功能完全可用
- 用戶操作流程保持一致
- 錯誤處理和提示準確友好

#### 性能表現
- API 響應時間 P95 < 500ms
- 支持 1000+ 併發請求
- 99.9% 服務可用性
- 內存使用 < 1GB per instance

#### 安全保障
- 客戶端完全無敏感密鑰
- JWT Token 安全機制正常
- 權限控制精確有效
- 審計日誌完整準確

### ✅ 業務成功標準

#### 用戶體驗
- CLI 用戶操作無感知變化
- 響應速度無明顯下降
- 錯誤提示清晰有用
- 功能穩定可靠

#### 運維效率
- 部署流程自動化
- 監控告警及時準確
- 故障排查便捷快速
- 擴容操作簡單

#### 擴展能力
- 新客戶端接入容易
- 新功能開發高效
- API 文檔完整清晰
- 第三方集成友好

---

## 📚 相關資源

### 🔗 技術文檔
- [FastAPI 官方文檔](https://fastapi.tiangolo.com/)
- [Supabase Python 客戶端](https://supabase.com/docs/reference/python/introduction)
- [PyJWT 文檔](https://pyjwt.readthedocs.io/)
- [Pydantic 文檔](https://docs.pydantic.dev/)

### 🛠️ 開發工具
- [Postman](https://www.postman.com/) - API 測試
- [Swagger UI](https://swagger.io/tools/swagger-ui/) - API 文檔
- [Docker](https://www.docker.com/) - 容器化部署
- [Prometheus](https://prometheus.io/) - 監控指標

### 📖 最佳實踐
- [FastAPI 最佳實踐](https://github.com/zhanymkanov/fastapi-best-practices)
- [API 設計指南](https://github.com/microsoft/api-guidelines)
- [JWT 安全最佳實踐](https://auth0.com/blog/a-look-at-the-latest-draft-for-jwt-bcp/)
- [Docker 安全指南](https://docs.docker.com/engine/security/)

---

## 🎉 總結

MPS API 項目將為整個 MPS 系統帶來以下核心價值：

### 🔐 **安全性革命性提升**
通過將 `service_role_key` 從客戶端完全移除，並實施基於 JWT 的認證機制，系統安全性得到根本性改善。

### 🏗️ **架構現代化升級**  
從單體客戶端架構升級為標準的前後端分離架構，為未來的多端支持奠定堅實基礎。

### 🚀 **業務擴展能力增強**
統一的 HTTP API 接口使得新客戶端（小程序、Web 應用）的開發變得簡單快捷。

### 🔧 **運維效率大幅提升**
集中化的後端服務、完善的監控告警、標準化的部署流程，大大降低了運維複雜度。

### 💡 **技術債務清理**
通過這次重構，不僅解決了安全問題，還建立了更加規範和可維護的代碼結構。

**這個 API 層的建設是 MPS 系統發展的關鍵里程碑，它不僅解決了當前的安全問題，更為系統的長期發展和擴展提供了強有力的技術支撐。**

---

## 📞 聯繫和支持

### 👥 項目團隊
- **架構師**：負責整體設計和技術決策
- **後端開發**：負責 API 服務實現
- **前端開發**：負責 CLI 適配
- **DevOps**：負責部署和運維
- **測試工程師**：負責質量保證

### 📧 技術支持
- **開發問題**：技術討論和代碼審查
- **部署問題**：環境配置和部署支持  
- **運維問題**：監控告警和故障處理
- **安全問題**：安全審計和漏洞修復

通過這個完整的計劃，MPS 系統將實現從安全性、可擴展性到可維護性的全面升級，為業務的長期發展提供堅實的技術保障。