# Member Payment System (MPS) - System Architecture

This document provides a high-level overview of the Member Payment System's architecture, detailing the core components, user roles, and interaction flows.

## System Architecture Diagram

The following diagram illustrates the key parts of the system, including user actors, the Next.js frontend application, the Supabase backend services, and their relationships.

```mermaid
graph TD
    subgraph "使用者 (Actors)"
        A[會員 Member]
        B[企業管理員 Enterprise Admin]
        C[商戶收銀員 Merchant User]
    end

    subgraph "前端 (Next.js Application)"
        direction LR
        subgraph " "
            D[認證頁面 (Auth)]
        end
        subgraph " "
            U[會員專區 (User Pages)]
            U1[儀表板]
            U2[我的卡片]
            U3[顯示QR碼]
            U4[儲值]
        end
        subgraph " "
            E[企業專區 (Enterprise Pages)]
            E1[管理員設定]
            E2[成員管理]
            E3[企業儲值]
        end
        subgraph " "
            M[商戶專區 (Merchant Pages)]
            M1[掃碼收款]
            M2[交易退款]
            M3[交易查詢]
        end
    end

    subgraph "後端 (Supabase)"
        direction LR
        subgraph " "
            S_Auth[Auth Service]
        end
        subgraph " "
            S_API[PostgREST API]
        end
        subgraph " "
            S_DB[Postgres Database]
            
            subgraph "DB Schemas"
                DB_APP[app schema<br/>- tables<br/>- views<br/>- RPCs]
                DB_AUDIT[audit schema<br/>- event_log]
                DB_SEC[sec schema<br/>- helpers]
            end
            S_DB --- DB_APP & DB_AUDIT & DB_SEC
        end
    end
    
    %% Frontend to Backend Connections
    D --- S_Auth
    U & E & M --- S_API

    %% User Interactions
    A --- D & U
    B --- D & E
    C --- D & M
    
    %% API to Database
    S_API -- RLS-protected Reads --> DB_APP
    S_API -- Calls --> DB_APP
    
    classDef user fill:#c9f,stroke:#333,stroke-width:2px;
    classDef frontend fill:#9cf,stroke:#333,stroke-width:2px;
    classDef backend fill:#f99,stroke:#333,stroke-width:2px;

    class A,B,C user;
    class D,U,E,M,U1,U2,U3,U4,E1,E2,E3,M1,M2,M3 frontend
    class S_Auth,S_API,S_DB,DB_APP,DB_AUDIT,DB_SEC backend
```

### Architecture Overview

1.  **Users (Actors)**: The system defines three primary frontend user roles: `Member`, `Enterprise Admin`, and `Merchant User`. Each role interacts with specific sections of the frontend application.

2.  **Frontend (Next.js Application)**:
    *   The application's pages are logically grouped by user role (`(user)`, `(enterprise)`, `(merchant)`), aligning with the project's existing `app/` directory structure.
    *   All users authenticate through a unified `Auth` module.

3.  **Backend (Supabase)**:
    *   **Auth Service**: Manages user registration, login, and session handling.
    *   **PostgREST API**: Serves as the primary gateway for frontend-backend communication. The frontend uses it for data reads (protected by RLS) and write operations (by invoking RPCs).
    *   **Postgres Database**:
        *   The database is organized into three distinct schemas: `app` (core business logic), `audit` (logging), and `sec` (security helpers), promoting separation of concerns.
        *   The `app` schema is central, containing all core tables, views, and crucial **RPC functions**. These RPCs encapsulate all business-critical logic.

### Core Flow

*   Users interact with the system via the Next.js frontend.
*   The frontend uses Supabase Auth for identity verification.
*   Post-login, the frontend renders pages based on the authenticated user's role.
*   All **read operations** (e.g., fetching transaction history) are sent through the PostgREST API and are governed by **Row-Level Security (RLS)** policies, ensuring users can only access data they are authorized to see.
*   All **write operations** (e.g., payments, refunds, recharges) are exclusively handled by invoking **Remote Procedure Calls (RPCs)** within the `app` schema. These functions are defined with `SECURITY DEFINER` privileges, allowing them to safely execute transactions, manage locks, update balances, and write to the audit log within a secure context.

This architecture establishes a clear separation between the frontend and backend, securely encapsulating all sensitive and complex business logic at the database level. This approach significantly enhances the system's security and data integrity.