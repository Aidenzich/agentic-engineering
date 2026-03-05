# AI-Native Internal Developer Platform
## Phase 1 — Foundation Engineering Specification

| 欄位 | 內容 |
|---|---|
| **版本** | v1.1 |
| **狀態** | Draft |
| **目標讀者** | 工程師（實作）、架構師（技術決策） |
| **前置文件** | ai-native-platform.md (PRD v0.3) |
| **決策前提** | Python (FastAPI) + React (Vite) · Docker Compose (Modular Monolith) |

---

## 目錄

1. [技術棧決策矩陣](#1-技術棧決策矩陣)
2. [系統架構](#2-系統架構)
3. [基礎設施 — Docker Compose](#3-基礎設施--docker-compose)
4. [核心資料模型 — SQLAlchemy Models](#4-核心資料模型--sqlalchemy-models)
5. [API 設計規範](#5-api-設計規範)
6. [認證與授權 (Auth + RBAC)](#6-認證與授權-auth--rbac)
7. [Module 1 — Team Management](#7-module-1--team-management)
8. [Module 2 — Wiki](#8-module-2--wiki)
9. [Module 3 — Scrum + DevOps](#9-module-3--scrum--devops)
10. [Module 4 — Service Catalog](#10-module-4--service-catalog)
11. [Module 5 — Workflow Engine (基礎)](#11-module-5--workflow-engine-基礎)
12. [Cross-Cutting — Search / Notification / WebSocket](#12-cross-cutting--search--notification--websocket)
13. [Plugin — GitHub / Slack / CI/CD](#13-plugin--github--slack--cicd)
14. [開發順序與里程碑](#14-開發順序與里程碑)
15. [測試策略](#15-測試策略)

---

## 1. 技術棧決策矩陣

### 1.1 後端

| 層級 | 選型 | 版本 | 說明 |
|---|---|---|---|
| **Language** | Python | 3.12+ | 團隊主力語言 |
| **Framework** | FastAPI | 0.115+ | async-first；Pydantic v2 native；OpenAPI 自動生成 |
| **ORM** | SQLAlchemy | 2.x (async) | async engine + asyncpg driver；Mapped 型別安全；DATABASE_URL 使用 `postgresql+asyncpg://` scheme |
| **Migration** | Alembic | 1.x | SQLAlchemy 官方 migration 工具 |
| **Validation** | Pydantic | v2 | FastAPI 原生；request/response schema |
| **Primary DB** | PostgreSQL | 16 | JSONB 彈性欄位；內建 FTS + `pg_trgm`；ACID |
| **Cache / PubSub** | Redis | 7.x | Session、WebSocket Pub/Sub、arq broker + result backend |
| **Job Queue** | arq | 0.26+ | Async-native 任務佇列；Redis 作為 broker；輕量替代 Celery，與 FastAPI async 生態一致 |
| **WebSocket** | python-socketio | 5.x | ASGI 整合 FastAPI；前端使用 socket.io-client |
| **File Storage** | MinIO | RELEASE.2024 | S3 相容；Self-hosted；Page 附件存放 |
| **Auth** | python-jose + passlib | — | JWT（access 15min / refresh 7d）；bcrypt 密碼 hash |
| **HTTP Client** | httpx | 0.27+ | 非同步 HTTP；Plugin 呼叫外部 API 用 |
| **Config** | pydantic-settings | 2.x | 環境變數型別安全讀取 |

### 1.2 前端

| 層級 | 選型 | 版本 | 說明 |
|---|---|---|---|
| **Build Tool** | Vite | 5.x | HMR < 50ms；產出純靜態 `dist/`，可直接上 S3 |
| **Framework** | React | 19.x | SPA；所有資料來自 REST API + WebSocket |
| **Routing** | React Router | v7 | File-based routing；純客戶端 |
| **UI Kit** | shadcn/ui + Tailwind CSS | latest | 可組合元件；CVA 型別安全 |
| **Rich Text Editor** | TipTap | 2.x | ProseMirror-based；原生支援 Yjs 協作 |
| **協作 (CRDT)** | Yjs + HocusPocus | latest | Phase 1：記憶體模式（不持久化），30s auto-save 降低風險 |
| **Server State** | TanStack Query | 5.x | Cache、refetch、optimistic update |
| **Client State** | Zustand | 4.x | 全域 UI 狀態（sidebar、modal、theme） |
| **拖拉排序** | @dnd-kit | 6.x | Accessible；鍵盤支援 |
| **Charts** | Recharts | 2.x | Burndown Chart |
| **表單驗證** | React Hook Form + Zod | latest | 型別安全 |
| **WebSocket Client** | socket.io-client | 4.x | 與後端同版本 |

### 1.3 工具鏈

| 工具 | 用途 |
|---|---|
| uv | Python 套件管理（速度遠快於 pip/poetry） |
| pyproject.toml | 後端依賴宣告 |
| pnpm | 前端套件管理 |
| Ruff | Python linter + formatter（取代 flake8 + black） |
| pytest + pytest-asyncio | 後端單元 / 整合測試 |
| ESLint + Prettier | 前端程式碼風格統一 |
| Playwright | 前端 E2E 測試 |
| Docker Compose | 本地開發 + 部署 |
| GitHub Actions | CI Pipeline |
| FastAPI auto OpenAPI | `/docs` 自動生成 Swagger UI（無需額外設定） |

---

## 2. 系統架構

### 2.1 Monorepo 結構

```
/
├── apps/
│   ├── backend/                     # Python FastAPI (Modular Monolith)
│   │   ├── app/
│   │   │   ├── main.py              # FastAPI app 入口、路由掛載
│   │   │   ├── core/
│   │   │   │   ├── config.py        # pydantic-settings 設定
│   │   │   │   ├── database.py      # SQLAlchemy async engine + session
│   │   │   │   ├── redis.py         # Redis 連線（aioredis / redis.asyncio）
│   │   │   │   └── security.py      # JWT encode/decode、password hash
│   │   │   ├── deps/                # FastAPI Dependencies（Guards 等價物）
│   │   │   │   ├── auth.py          # get_current_user
│   │   │   │   └── rbac.py          # require_org_member、require_org_role
│   │   │   ├── models/              # SQLAlchemy ORM models
│   │   │   │   ├── org.py           # Organization, User, OrgMember, Team, AuditLog
│   │   │   │   ├── wiki.py          # Workspace, Page, PageVersion
│   │   │   │   ├── scrum.py         # WorkItem, Sprint, PullRequest
│   │   │   │   ├── service.py       # Service, EntityLink
│   │   │   │   ├── workflow.py      # Workflow, WorkflowExecution
│   │   │   │   └── notification.py  # Notification
│   │   │   ├── schemas/             # Pydantic v2 schemas（request / response）
│   │   │   │   └── ...              # 對應每個 domain
│   │   │   ├── routers/             # FastAPI APIRouter（按 domain 分層）
│   │   │   │   ├── auth.py
│   │   │   │   ├── orgs/
│   │   │   │   │   ├── teams.py
│   │   │   │   │   ├── workspaces.py
│   │   │   │   │   ├── projects.py
│   │   │   │   │   ├── services.py
│   │   │   │   │   ├── workflows.py
│   │   │   │   │   └── ...
│   │   │   │   └── plugins/
│   │   │   │       ├── github.py    # GitHub Webhook endpoint
│   │   │   │       ├── slack.py
│   │   │   │       └── cicd.py
│   │   │   ├── services/            # Business logic layer
│   │   │   │   └── ...              # wiki_service.py, scrum_service.py, ...
│   │   │   ├── events/
│   │   │   │   └── bus.py           # 內部 async 事件匯流排（見 Section 2.4）
│   │   │   ├── workers/
│   │   │   │   ├── settings.py      # arq WorkerSettings 定義
│   │   │   │   └── workflow.py      # Workflow 執行 worker（arq task）
│   │   │   └── realtime/
│   │   │       └── socket.py        # python-socketio ASGI app
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/            # migration 檔案
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   └── integration/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   └── frontend/                    # Vite + React 19 SPA
│       ├── index.html
│       ├── vite.config.ts
│       ├── src/
│       │   ├── main.tsx
│       │   ├── routes/              # React Router v7 file-based routes
│       │   │   ├── _auth/           # login, register（layout: 無 sidebar）
│       │   │   │   ├── login.tsx
│       │   │   │   └── register.tsx
│       │   │   └── $orgSlug/        # 主應用（layout: sidebar + header）
│       │   │       ├── wiki/
│       │   │       ├── projects/
│       │   │       ├── services/
│       │   │       ├── workflows/
│       │   │       └── settings/
│       │   ├── components/
│       │   │   ├── editor/          # TipTap 相關元件
│       │   │   ├── board/           # Kanban Board
│       │   │   ├── charts/          # Burndown, etc.
│       │   │   └── ui/              # shadcn/ui 元件
│       │   ├── lib/
│       │   │   ├── api/             # TanStack Query hooks + axios client
│       │   │   ├── socket.ts        # socket.io-client 初始化
│       │   │   └── store/           # Zustand stores
│       │   └── types/               # API 型別定義（從 OpenAPI spec 生成或手動維護）
│       ├── package.json
│       └── Dockerfile
│
├── docker-compose.yml
├── nginx.conf
├── .env.example
└── README.md
```

> **型別同步策略：** 後端以 Pydantic v2 schemas 為 Single Source of Truth，透過 FastAPI 自動生成 OpenAPI spec（`/docs`）。前端型別可從 OpenAPI spec 手動維護或使用 `openapi-typescript` 等工具自動生成，無需獨立的 shared-types package。

### 2.2 全棧架構總覽

```
Browser (Vite + React SPA)
  │  REST API (axios + TanStack Query)
  │  WebSocket (socket.io-client)
  ▼
nginx (:80)
  ├── /api/*  → FastAPI backend:8000
  ├── /ws/*   → python-socketio backend:8000
  └── /*      → static dist/ (React SPA, served by nginx)

┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                          │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │   Auth   │ │   Team   │ │   Wiki   │ │  Scrum   │ │ Service  │  │
│  │  Router  │ │  Router  │ │  Router  │ │  Router  │ │ Catalog  │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
│       │            │            │             │            │        │
│  ─────┴────────────┴────────────┴─────────────┴────────────┴─────── │
│                   Internal Async Event Bus (見 Section 2.4)          │
│  ─────┬────────────┬────────────┬─────────────┬────────────┬─────── │
│       │            │            │             │            │        │
│  ┌────▼─────┐ ┌────▼─────┐ ┌───▼──────┐ ┌────▼─────┐ ┌────▼─────┐  │
│  │ Workflow │ │Notifica- │ │  Search  │ │ Realtime │ │ Plugins  │  │
│  │  Worker  │ │  tion    │ │  Router  │ │(socketio)│ │  Router  │  │
│  │  (arq)   │ │  Router  │ │          │ │          │ │          │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│          Infrastructure Layer (SQLAlchemy · Redis · arq)            │
└─────────────────────────────────────────────────────────────────────┘
         │                    │                    │
    PostgreSQL              Redis               MinIO
```

**模組邊界規則：**
- Router 間不直接呼叫彼此的 Service，一律透過內部 async event bus 發布事件（見 Section 2.4）
- Auth Dependencies（`get_current_user`、`require_org_member`）透過 FastAPI `Depends()` 注入所有需要認證的路由
- `AsyncSession` 透過 `get_db` dependency 注入，每個 request 使用獨立 session

**跨模組事件命名規範：**
```
{domain}.{entity}.{action}
// 範例：
wiki.page.created
wiki.page.status_changed
scrum.ticket.created
scrum.ticket.status_changed
scrum.sprint.started
scrum.sprint.completed
scrum.pr.merged
plugin.github.pr_opened
plugin.github.pr_merged
plugin.cicd.build_completed
```

### 2.3 Request 生命週期

```
HTTP Request
  → nginx (reverse proxy)
  → FastAPI (Uvicorn ASGI)
    → Exception Handler（全域，統一錯誤格式）
    → Depends(get_current_user)   # JWT 驗證，取得 User 物件
    → Depends(require_org_member) # 驗證 User 屬於 :orgId
    → Depends(require_org_role)   # 驗證角色（需要時）
    → Pydantic v2 request body 自動驗證
    → Router function（Controller 等價）
    → Service function（Business logic）
    → AsyncSession（SQLAlchemy DB 操作）
    → 回傳 Pydantic response model（自動序列化）
  → Response
```

### 2.4 內部 Async Event Bus

使用輕量的 in-process async event dispatcher，不依賴外部套件：

```python
# apps/backend/app/events/bus.py
import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine

EventHandler = Callable[..., Coroutine[Any, Any, None]]

class EventBus:
    """輕量 in-process async event bus。Phase 1 足夠；Phase 2+ 可替換為 Redis Streams。"""

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def on(self, event: str, handler: EventHandler) -> None:
        """註冊事件處理器。"""
        self._handlers[event].append(handler)

    async def emit(self, event: str, **kwargs) -> None:
        """發布事件，所有 handler 並行執行（fire-and-forget，不阻塞主流程）。"""
        handlers = self._handlers.get(event, [])
        if handlers:
            await asyncio.gather(
                *(h(**kwargs) for h in handlers),
                return_exceptions=True,  # handler 失敗不影響其他 handler
            )

# Singleton instance，在 main.py 中初始化
event_bus = EventBus()
```

**使用範例：**
```python
# 註冊（在 app startup 時）
from app.events.bus import event_bus

async def on_ticket_created(**kwargs):
    # 發送通知、觸發 workflow 等
    ...

event_bus.on("scrum.ticket.created", on_ticket_created)

# 發布（在 Service 層）
await event_bus.emit("scrum.ticket.created", work_item=item, actor=current_user)
```

---

## 3. 基礎設施 — Docker Compose

### 3.1 docker-compose.yml

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: idp_db
      POSTGRES_USER: idp_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U idp_user -d idp_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"

  hocuspocus:
    image: ueberdosis/hocuspocus:latest
    environment:
      PORT: 1234
    ports:
      - "1234:1234"
    # Phase 1: 記憶體模式，無持久化

  backend:
    build:
      context: ./apps/backend
      dockerfile: Dockerfile
    environment: &backend-env
      DATABASE_URL: postgresql+asyncpg://idp_user:${POSTGRES_PASSWORD}@postgres:5432/idp_db
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379
      MINIO_ENDPOINT: minio
      MINIO_PORT: 9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
      JWT_SECRET: ${JWT_SECRET}
      JWT_REFRESH_SECRET: ${JWT_REFRESH_SECRET}
      HOCUSPOCUS_URL: ws://hocuspocus:1234
      GITHUB_APP_ID: ${GITHUB_APP_ID}
      GITHUB_APP_PRIVATE_KEY: ${GITHUB_APP_PRIVATE_KEY}
      GITHUB_WEBHOOK_SECRET: ${GITHUB_WEBHOOK_SECRET}
      SLACK_BOT_TOKEN: ${SLACK_BOT_TOKEN}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  arq-worker:
    build:
      context: ./apps/backend
      dockerfile: Dockerfile
    command: arq app.workers.settings.WorkerSettings
    environment:
      <<: *backend-env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - frontend_dist:/usr/share/nginx/html   # 從 frontend build stage 複製
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
  minio_data:
  frontend_dist:    # 由 CI/CD build 階段填充，或本地 pnpm build 後掛載
```

### 3.2 Frontend Build

前端為純靜態 SPA，**不需要獨立的 runtime container**。build 後產出 `dist/` 目錄，由外層 nginx 統一 serve。

```bash
# 本地開發
cd apps/frontend
pnpm install
pnpm dev                # Vite dev server (HMR)

# 生產 build
VITE_API_BASE_URL=http://localhost/api \
VITE_WS_URL=ws://localhost \
pnpm build              # 輸出 dist/
```

**CI/CD 流程**：GitHub Actions 中 `pnpm build` 後，將 `dist/` 複製至 nginx container 的 `/usr/share/nginx/html`。

### 3.3 nginx.conf

```nginx
# nginx.conf（根目錄）
events { worker_connections 1024; }

http {
  include mime.types;

  server {
    listen 80;

    # SPA 靜態檔案
    root /usr/share/nginx/html;
    index index.html;

    # API 反向代理
    location /api/ {
      proxy_pass http://backend:8000;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSocket 反向代理
    location /ws/ {
      proxy_pass http://backend:8000;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
    }

    # SPA fallback — 必須，否則直接訪問深層路由會 404
    location / {
      try_files $uri $uri/ /index.html;
    }

    # 靜態資源快取（Vite 產出的 hashed 檔案）
    location ~* \.(js|css|png|jpg|gif|svg|ico|woff2)$ {
      expires 1y;
      add_header Cache-Control "public, immutable";
    }
  }
}
```

> **S3 部署時**：將 `dist/` 上傳至 S3，在 CloudFront 設定 Error Page 404 → 200 `/index.html`，實現相同的 SPA fallback 效果。

### 3.4 環境變數 (.env.example)

```bash
# Database
POSTGRES_PASSWORD=strong_password_here

# Redis
REDIS_PASSWORD=strong_redis_password

# MinIO
MINIO_ACCESS_KEY=minio_access_key
MINIO_SECRET_KEY=minio_secret_key

# JWT
JWT_SECRET=your_jwt_secret_min_32_chars
JWT_REFRESH_SECRET=your_refresh_secret_min_32_chars

# GitHub App
GITHUB_APP_ID=your_github_app_id
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Slack
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_SIGNING_SECRET=your_slack_signing_secret
```

---

## 4. 核心資料模型 — SQLAlchemy Models

```python
# backend/app/models/base.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def new_id() -> str:
    return str(uuid.uuid4())

class Base(DeclarativeBase):
    pass
```

```python
# backend/app/models/org.py — Auth & Organization
import enum
from sqlalchemy import String, Boolean, ForeignKey, Index, UniqueConstraint, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, new_id, utcnow

class OrgRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"

class TeamRole(str, enum.Enum):
    LEAD = "lead"
    MEMBER = "member"
    VIEWER = "viewer"

class Organization(Base):
    __tablename__ = "organizations"
    id:         Mapped[str]      = mapped_column(String, primary_key=True, default=new_id)
    name:       Mapped[str]      = mapped_column(String, nullable=False)
    slug:       Mapped[str]      = mapped_column(String, unique=True, nullable=False)
    avatar_url: Mapped[str|None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    members:      Mapped[list["OrgMember"]]   = relationship(back_populates="organization", cascade="all, delete-orphan")
    teams:        Mapped[list["Team"]]         = relationship(back_populates="organization", cascade="all, delete-orphan")
    workspaces:   Mapped[list["Workspace"]]    = relationship(back_populates="organization", cascade="all, delete-orphan")
    projects:     Mapped[list["Project"]]      = relationship(back_populates="organization", cascade="all, delete-orphan")
    services:     Mapped[list["Service"]]      = relationship(back_populates="organization", cascade="all, delete-orphan")
    workflows:    Mapped[list["Workflow"]]      = relationship(back_populates="organization", cascade="all, delete-orphan")
    pull_requests:Mapped[list["PullRequest"]]  = relationship(back_populates="organization")

class User(Base):
    __tablename__ = "users"
    id:            Mapped[str]      = mapped_column(String, primary_key=True, default=new_id)
    email:         Mapped[str]      = mapped_column(String, unique=True, nullable=False)
    name:          Mapped[str]      = mapped_column(String, nullable=False)
    avatar_url:    Mapped[str|None] = mapped_column(String)
    password_hash: Mapped[str]      = mapped_column(String, nullable=False)
    created_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    org_memberships:  Mapped[list["OrgMember"]]    = relationship(back_populates="user", cascade="all, delete-orphan")
    team_memberships: Mapped[list["TeamMember"]]   = relationship(back_populates="user", cascade="all, delete-orphan")
    assigned_items:   Mapped[list["WorkItem"]]      = relationship(foreign_keys="WorkItem.assignee_id", back_populates="assignee")
    notifications:    Mapped[list["Notification"]]  = relationship(back_populates="user", cascade="all, delete-orphan")
    refresh_tokens:   Mapped[list["RefreshToken"]]  = relationship(back_populates="user", cascade="all, delete-orphan")

class OrgMember(Base):
    __tablename__ = "org_members"
    id:        Mapped[str]     = mapped_column(String, primary_key=True, default=new_id)
    org_id:    Mapped[str]     = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id:   Mapped[str]     = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role:      Mapped[OrgRole] = mapped_column(SAEnum(OrgRole), default=OrgRole.MEMBER, nullable=False)
    joined_at: Mapped[datetime]= mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="members")
    user:         Mapped["User"]          = relationship(back_populates="org_memberships")

    __table_args__ = (
        UniqueConstraint("org_id", "user_id"),
        Index("ix_org_members_org_id", "org_id"),
    )

class Team(Base):
    __tablename__ = "teams"
    id:          Mapped[str]      = mapped_column(String, primary_key=True, default=new_id)
    org_id:      Mapped[str]      = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name:        Mapped[str]      = mapped_column(String, nullable=False)
    slug:        Mapped[str]      = mapped_column(String, nullable=False)
    description: Mapped[str|None] = mapped_column(String)
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization: Mapped["Organization"]  = relationship(back_populates="teams")
    members:      Mapped[list["TeamMember"]] = relationship(back_populates="team", cascade="all, delete-orphan")
    projects:     Mapped[list["TeamProject"]]= relationship(back_populates="team", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("org_id", "slug"),)

class TeamMember(Base):
    __tablename__ = "team_members"
    team_id: Mapped[str]      = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str]      = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role:    Mapped[TeamRole] = mapped_column(SAEnum(TeamRole), default=TeamRole.MEMBER, nullable=False)

    team: Mapped["Team"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="team_memberships")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id:         Mapped[str]       = mapped_column(String, primary_key=True, default=new_id)
    user_id:    Mapped[str]       = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str]       = mapped_column(String, unique=True, nullable=False)  # bcrypt hash，不存原始 token
    expires_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str|None]  = mapped_column(String)
    ip_address: Mapped[str|None]  = mapped_column(String)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
    __table_args__ = (Index("ix_refresh_tokens_user_id", "user_id"),)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id:            Mapped[str]      = mapped_column(String, primary_key=True, default=new_id)
    org_id:        Mapped[str]      = mapped_column(ForeignKey("organizations.id"), nullable=False)
    actor_id:      Mapped[str]      = mapped_column(String, nullable=False)   # userId 或 "system"
    action:        Mapped[str]      = mapped_column(String, nullable=False)   # e.g. "wiki.page.created"
    resource_type: Mapped[str]      = mapped_column(String, nullable=False)
    resource_id:   Mapped[str]      = mapped_column(String, nullable=False)
    before:        Mapped[dict|None]= mapped_column(JSONB)
    after:         Mapped[dict|None]= mapped_column(JSONB)
    metadata_:     Mapped[dict|None]= mapped_column(JSONB, name="metadata")
    ip_address:    Mapped[str|None] = mapped_column(String)
    created_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_audit_logs_org_created", "org_id", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_actor", "actor_id"),
    )
```

```python
# backend/app/models/wiki.py — Wiki
import enum
from sqlalchemy import String, Boolean, Integer, ForeignKey, Index, UniqueConstraint, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, new_id, utcnow

class PageStatus(str, enum.Enum):
    DRAFT     = "draft"
    IN_REVIEW = "in_review"
    APPROVED  = "approved"
    ARCHIVED  = "archived"

class Workspace(Base):
    __tablename__ = "workspaces"
    id:          Mapped[str]      = mapped_column(String, primary_key=True, default=new_id)
    org_id:      Mapped[str]      = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name:        Mapped[str]      = mapped_column(String, nullable=False)
    slug:        Mapped[str]      = mapped_column(String, nullable=False)
    description: Mapped[str|None] = mapped_column(String)
    is_public:   Mapped[bool]     = mapped_column(Boolean, default=False)
    deleted_at:  Mapped[datetime|None] = mapped_column(DateTime(timezone=True))  # 軟刪除
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="workspaces")
    pages:        Mapped[list["Page"]]    = relationship(back_populates="workspace", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("org_id", "slug"),)

class Page(Base):
    __tablename__ = "pages"
    id:           Mapped[str]        = mapped_column(String, primary_key=True, default=new_id)
    workspace_id: Mapped[str]        = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    parent_id:    Mapped[str|None]   = mapped_column(ForeignKey("pages.id"))
    title:        Mapped[str]        = mapped_column(String, nullable=False)
    content:      Mapped[dict]       = mapped_column(JSONB, nullable=False)      # TipTap JSON
    plain_text:   Mapped[str]        = mapped_column(String, nullable=False)     # FTS 用
    status:       Mapped[PageStatus] = mapped_column(SAEnum(PageStatus), default=PageStatus.DRAFT)
    position:     Mapped[int]        = mapped_column(Integer, default=0)
    created_by_id:Mapped[str]        = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by_id:Mapped[str|None]   = mapped_column(ForeignKey("users.id"))
    created_at:   Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at:   Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    workspace:  Mapped["Workspace"]       = relationship(back_populates="pages")
    parent:     Mapped["Page|None"]       = relationship(remote_side="Page.id", back_populates="children")
    children:   Mapped[list["Page"]]      = relationship(back_populates="parent")
    versions:   Mapped[list["PageVersion"]]= relationship(back_populates="page", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_pages_workspace_parent", "workspace_id", "parent_id"),
        Index("ix_pages_workspace_status", "workspace_id", "status"),
    )

class PageVersion(Base):
    __tablename__ = "page_versions"
    id:           Mapped[str]     = mapped_column(String, primary_key=True, default=new_id)
    page_id:      Mapped[str]     = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    version:      Mapped[int]     = mapped_column(Integer, nullable=False)   # 從 1 遞增
    title:        Mapped[str]     = mapped_column(String, nullable=False)
    content:      Mapped[dict]    = mapped_column(JSONB, nullable=False)
    created_by_id:Mapped[str]     = mapped_column(ForeignKey("users.id"), nullable=False)
    comment:      Mapped[str|None]= mapped_column(String)
    created_at:   Mapped[datetime]= mapped_column(DateTime(timezone=True), default=utcnow)

    page: Mapped["Page"] = relationship(back_populates="versions")
    __table_args__ = (
        UniqueConstraint("page_id", "version"),
        Index("ix_page_versions_page_created", "page_id", "created_at"),
    )
```

```python
# backend/app/models/scrum.py — Scrum + PR
import enum
from sqlalchemy import String, Integer, ForeignKey, Index, UniqueConstraint, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, new_id, utcnow

class WorkItemType(str, enum.Enum):
    EPIC  = "epic"; STORY = "story"; TASK  = "task"; BUG   = "bug"; SPIKE = "spike"

class WorkItemStatus(str, enum.Enum):
    BACKLOG="backlog"; TODO="todo"; IN_PROGRESS="in_progress"
    IN_REVIEW="in_review"; QA="qa"; DONE="done"; CANCELLED="cancelled"

class Priority(str, enum.Enum):
    CRITICAL="critical"; HIGH="high"; MEDIUM="medium"; LOW="low"

class SprintStatus(str, enum.Enum):
    PLANNING="planning"; ACTIVE="active"; COMPLETED="completed"

class PRStatus(str, enum.Enum):
    OPEN="open"; DRAFT="draft"; REVIEW="review"
    APPROVED="approved"; MERGED="merged"; CLOSED="closed"

class Project(Base):
    __tablename__ = "projects"
    id:          Mapped[str]      = mapped_column(String, primary_key=True, default=new_id)
    org_id:      Mapped[str]      = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name:        Mapped[str]      = mapped_column(String, nullable=False)
    slug:        Mapped[str]      = mapped_column(String, nullable=False)
    prefix:      Mapped[str]      = mapped_column(String(10), nullable=False)  # e.g. "PROJ", "BE"，用於 Ticket ID（PROJ-1, BE-42）
    next_number: Mapped[int]      = mapped_column(Integer, default=1)          # 自動遞增計數器，建立 WorkItem 時 +1
    description: Mapped[str|None] = mapped_column(String)
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization: Mapped["Organization"]   = relationship(back_populates="projects")
    work_items:   Mapped[list["WorkItem"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    sprints:      Mapped[list["Sprint"]]   = relationship(back_populates="project", cascade="all, delete-orphan")
    __table_args__ = (
        UniqueConstraint("org_id", "slug"),
        UniqueConstraint("org_id", "prefix"),  # 同一 Org 內 prefix 唯一
    )

class TeamProject(Base):
    __tablename__ = "team_projects"
    team_id:    Mapped[str] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)

class WorkItem(Base):
    __tablename__ = "work_items"
    id:           Mapped[str]            = mapped_column(String, primary_key=True, default=new_id)
    project_id:   Mapped[str]            = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    number:       Mapped[int]            = mapped_column(Integer, nullable=False)  # 自動分配，顯示為 "{project.prefix}-{number}"（e.g. PROJ-42）
    parent_id:    Mapped[str|None]       = mapped_column(ForeignKey("work_items.id"))
    type:         Mapped[WorkItemType]   = mapped_column(SAEnum(WorkItemType), default=WorkItemType.STORY)
    title:        Mapped[str]            = mapped_column(String, nullable=False)
    description:  Mapped[dict|None]      = mapped_column(JSONB)
    status:       Mapped[WorkItemStatus] = mapped_column(SAEnum(WorkItemStatus), default=WorkItemStatus.BACKLOG)
    priority:     Mapped[Priority]       = mapped_column(SAEnum(Priority), default=Priority.MEDIUM)
    assignee_id:  Mapped[str|None]       = mapped_column(ForeignKey("users.id"))
    story_points: Mapped[int|None]       = mapped_column(Integer)
    position:     Mapped[int]            = mapped_column(Integer, default=0)
    labels:       Mapped[list[str]]      = mapped_column(ARRAY(String), default=list)
    custom_fields:Mapped[dict|None]      = mapped_column(JSONB)
    created_by_id:Mapped[str]            = mapped_column(ForeignKey("users.id"), nullable=False)
    deleted_at:   Mapped[datetime|None]  = mapped_column(DateTime(timezone=True))  # 軟刪除；非 null 表示已刪除
    created_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project:  Mapped["Project"]        = relationship(back_populates="work_items")
    parent:   Mapped["WorkItem|None"]  = relationship(remote_side="WorkItem.id", back_populates="children")
    children: Mapped[list["WorkItem"]] = relationship(back_populates="parent")
    assignee: Mapped["User|None"]      = relationship(foreign_keys=[assignee_id])
    sprint_links: Mapped[list["SprintWorkItem"]] = relationship(back_populates="work_item", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("project_id", "number"),  # 同一 Project 內 number 唯一
        Index("ix_work_items_project_status", "project_id", "status"),
        Index("ix_work_items_project_type",   "project_id", "type"),
        Index("ix_work_items_project_parent", "project_id", "parent_id"),
    )

class Sprint(Base):
    __tablename__ = "sprints"
    id:         Mapped[str]          = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str]          = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name:       Mapped[str]          = mapped_column(String, nullable=False)
    goal:       Mapped[str|None]     = mapped_column(String)
    status:     Mapped[SprintStatus] = mapped_column(SAEnum(SprintStatus), default=SprintStatus.PLANNING)
    start_date: Mapped[datetime|None]= mapped_column(DateTime(timezone=True))
    end_date:   Mapped[datetime|None]= mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project:    Mapped["Project"]           = relationship(back_populates="sprints")
    work_items: Mapped[list["SprintWorkItem"]] = relationship(back_populates="sprint", cascade="all, delete-orphan")
    __table_args__ = (Index("ix_sprints_project_status", "project_id", "status"),)

class SprintWorkItem(Base):
    __tablename__ = "sprint_work_items"
    sprint_id:    Mapped[str]     = mapped_column(ForeignKey("sprints.id", ondelete="CASCADE"), primary_key=True)
    work_item_id: Mapped[str]     = mapped_column(ForeignKey("work_items.id", ondelete="CASCADE"), primary_key=True)
    added_at:     Mapped[datetime]= mapped_column(DateTime(timezone=True), default=utcnow)

    sprint:    Mapped["Sprint"]    = relationship(back_populates="work_items")
    work_item: Mapped["WorkItem"]  = relationship(back_populates="sprint_links")

class PullRequest(Base):
    __tablename__ = "pull_requests"
    id:           Mapped[str]      = mapped_column(String, primary_key=True, default=new_id)
    org_id:       Mapped[str]      = mapped_column(ForeignKey("organizations.id"), nullable=False)
    provider_type:Mapped[str]      = mapped_column(String, nullable=False)   # "github"
    external_id:  Mapped[str]      = mapped_column(String, nullable=False)   # GitHub PR node_id
    repo_full_name:Mapped[str]     = mapped_column(String, nullable=False)   # "org/repo"
    number:       Mapped[int]      = mapped_column(Integer, nullable=False)
    title:        Mapped[str]      = mapped_column(String, nullable=False)
    body:         Mapped[str|None] = mapped_column(String)
    status:       Mapped[PRStatus] = mapped_column(SAEnum(PRStatus), default=PRStatus.OPEN)
    author_login: Mapped[str]      = mapped_column(String, nullable=False)
    head_branch:  Mapped[str]      = mapped_column(String, nullable=False)
    base_branch:  Mapped[str]      = mapped_column(String, nullable=False)
    url:          Mapped[str]      = mapped_column(String, nullable=False)
    additions:    Mapped[int]      = mapped_column(Integer, default=0)
    deletions:    Mapped[int]      = mapped_column(Integer, default=0)
    opened_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    merged_at:    Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    closed_at:    Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    ci_status:    Mapped[str|None] = mapped_column(String)   # "pending"|"success"|"failure"
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization: Mapped["Organization"]   = relationship(back_populates="pull_requests")
    comments:     Mapped[list["PRComment"]]= relationship(back_populates="pr", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("org_id", "provider_type", "external_id"),
        Index("ix_pull_requests_org_status", "org_id", "status"),
    )

class PRComment(Base):
    __tablename__ = "pr_comments"
    id:          Mapped[str]      = mapped_column(String, primary_key=True, default=new_id)
    pr_id:       Mapped[str]      = mapped_column(ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[str]      = mapped_column(String, nullable=False)
    body:        Mapped[str]      = mapped_column(String, nullable=False)
    author_login:Mapped[str]      = mapped_column(String, nullable=False)
    path:        Mapped[str|None] = mapped_column(String)   # diff 評論的檔案路徑
    line:        Mapped[int|None] = mapped_column(Integer)
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    pr: Mapped["PullRequest"] = relationship(back_populates="comments")
    __table_args__ = (UniqueConstraint("pr_id", "external_id"),)
```

```python
# backend/app/models/service.py — Service Catalog + EntityLink
import enum
from sqlalchemy import String, ForeignKey, Index, UniqueConstraint, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, new_id, utcnow

class ServiceLifecycle(str, enum.Enum):
    DEVELOPMENT = "development"
    PRODUCTION  = "production"
    DEPRECATED  = "deprecated"

class Service(Base):
    __tablename__ = "services"
    id:           Mapped[str]             = mapped_column(String, primary_key=True, default=new_id)
    org_id:       Mapped[str]             = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name:         Mapped[str]             = mapped_column(String, nullable=False)
    slug:         Mapped[str]             = mapped_column(String, nullable=False)
    description:  Mapped[str|None]        = mapped_column(String)
    lifecycle:    Mapped[ServiceLifecycle]= mapped_column(SAEnum(ServiceLifecycle), default=ServiceLifecycle.DEVELOPMENT)
    tech_stack:   Mapped[list[str]]       = mapped_column(ARRAY(String), default=list)
    owner_team_id:Mapped[str|None]        = mapped_column(ForeignKey("teams.id"))
    repo_url:     Mapped[str|None]        = mapped_column(String)
    metadata_:    Mapped[dict|None]       = mapped_column(JSONB, name="metadata")
    created_at:   Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at:   Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="services")
    __table_args__ = (
        UniqueConstraint("org_id", "slug"),
        Index("ix_services_org_lifecycle", "org_id", "lifecycle"),
    )

# 統一跨實體關聯表
class EntityLink(Base):
    __tablename__ = "entity_links"
    id:                  Mapped[str]      = mapped_column(String, primary_key=True, default=new_id)
    org_id:              Mapped[str]      = mapped_column(String, nullable=False)
    link_type:           Mapped[str]      = mapped_column(String, nullable=False)  # "PAGE_TICKET"|"PAGE_PR"|"TICKET_PR"|"SERVICE_REPO"|...
    source_page_id:      Mapped[str|None] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"))
    source_work_item_id: Mapped[str|None] = mapped_column(ForeignKey("work_items.id", ondelete="CASCADE"))
    source_pr_id:        Mapped[str|None] = mapped_column(ForeignKey("pull_requests.id", ondelete="CASCADE"))
    source_service_id:   Mapped[str|None] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"))
    target_page_id:      Mapped[str|None] = mapped_column(ForeignKey("pages.id", ondelete="SET NULL"))
    target_work_item_id: Mapped[str|None] = mapped_column(ForeignKey("work_items.id", ondelete="SET NULL"))
    target_pr_id:        Mapped[str|None] = mapped_column(ForeignKey("pull_requests.id", ondelete="SET NULL"))
    target_service_id:   Mapped[str|None] = mapped_column(ForeignKey("services.id", ondelete="SET NULL"))
    target_external_url: Mapped[str|None] = mapped_column(String)   # Service→Repo 外部 URL
    created_at:          Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_entity_links_org_type",  "org_id", "link_type"),
        Index("ix_entity_links_source_page","source_page_id"),
        Index("ix_entity_links_source_item","source_work_item_id"),
        Index("ix_entity_links_target_page","target_page_id"),
        Index("ix_entity_links_target_item","target_work_item_id"),
    )
```

```python
# backend/app/models/workflow.py — Workflow Engine
import enum
from sqlalchemy import String, Integer, ForeignKey, Index, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, new_id, utcnow

class WorkflowStatus(str, enum.Enum):
    DRAFT="draft"; ACTIVE="active"; DISABLED="disabled"

class ExecutionStatus(str, enum.Enum):
    RUNNING="running"; COMPLETED="completed"; FAILED="failed"; CANCELLED="cancelled"

# definition JSONB 結構（見 Section 11）：
# { "trigger": {...}, "condition": {...}, "actions": [...] }

class Workflow(Base):
    __tablename__ = "workflows"
    id:          Mapped[str]            = mapped_column(String, primary_key=True, default=new_id)
    org_id:      Mapped[str]            = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name:        Mapped[str]            = mapped_column(String, nullable=False)
    description: Mapped[str|None]       = mapped_column(String)
    status:      Mapped[WorkflowStatus] = mapped_column(SAEnum(WorkflowStatus), default=WorkflowStatus.DRAFT)
    definition:  Mapped[dict]           = mapped_column(JSONB, nullable=False)
    created_by_id:Mapped[str]           = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at:  Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at:  Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization: Mapped["Organization"]        = relationship(back_populates="workflows")
    executions:   Mapped[list["WorkflowExecution"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")
    __table_args__ = (Index("ix_workflows_org_status", "org_id", "status"),)

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"
    id:           Mapped[str]             = mapped_column(String, primary_key=True, default=new_id)
    workflow_id:  Mapped[str]             = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    status:       Mapped[ExecutionStatus] = mapped_column(SAEnum(ExecutionStatus), default=ExecutionStatus.RUNNING)
    trigger_type: Mapped[str]             = mapped_column(String, nullable=False)
    trigger_data: Mapped[dict]            = mapped_column(JSONB, nullable=False)
    started_at:   Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime|None]   = mapped_column(DateTime(timezone=True))
    duration_ms:  Mapped[int|None]        = mapped_column(Integer)
    error:        Mapped[str|None]        = mapped_column(String)

    workflow: Mapped["Workflow"]          = relationship(back_populates="executions")
    steps:    Mapped[list["WorkflowStepLog"]] = relationship(back_populates="execution", cascade="all, delete-orphan")
    __table_args__ = (Index("ix_wf_exec_workflow_started", "workflow_id", "started_at"),)

class WorkflowStepLog(Base):
    __tablename__ = "workflow_step_logs"
    id:           Mapped[str]     = mapped_column(String, primary_key=True, default=new_id)
    execution_id: Mapped[str]     = mapped_column(ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False)
    step_index:   Mapped[int]     = mapped_column(Integer, nullable=False)
    step_type:    Mapped[str]     = mapped_column(String, nullable=False)   # "trigger"|"condition"|"action"
    step_name:    Mapped[str]     = mapped_column(String, nullable=False)
    input_:       Mapped[dict|None]= mapped_column(JSONB, name="input")
    output_:      Mapped[dict|None]= mapped_column(JSONB, name="output")
    status:       Mapped[str]     = mapped_column(String, nullable=False)   # "success"|"skipped"|"failed"
    duration_ms:  Mapped[int|None]= mapped_column(Integer)
    error:        Mapped[str|None]= mapped_column(String)
    created_at:   Mapped[datetime]= mapped_column(DateTime(timezone=True), default=utcnow)

    execution: Mapped["WorkflowExecution"] = relationship(back_populates="steps")

class Notification(Base):
    __tablename__ = "notifications"
    id:            Mapped[str]      = mapped_column(String, primary_key=True, default=new_id)
    user_id:       Mapped[str]      = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    org_id:        Mapped[str]      = mapped_column(String, nullable=False)
    type:          Mapped[str]      = mapped_column(String, nullable=False)
    title:         Mapped[str]      = mapped_column(String, nullable=False)
    body:          Mapped[str|None] = mapped_column(String)
    resource_type: Mapped[str|None] = mapped_column(String)
    resource_id:   Mapped[str|None] = mapped_column(String)
    resource_url:  Mapped[str|None] = mapped_column(String)
    is_read:       Mapped[bool]     = mapped_column(Boolean, default=False)
    created_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="notifications")
    __table_args__ = (
        Index("ix_notifications_user_read_created", "user_id", "is_read", "created_at"),
        Index("ix_notifications_org", "org_id"),
    )
```

---

## 5. API 設計規範

### 5.1 URL 結構

所有 API 以 `/api/v1` 為前綴，Org 範圍的資源一律掛在 `:orgId` 下：

```
/api/v1/auth/...                           # 認證（org 無關）
/api/v1/users/me                           # 當前使用者
/api/v1/orgs/:orgId/...                    # Org 範圍資源
/api/v1/orgs/:orgId/workspaces/:wsId/...   # Wiki
/api/v1/orgs/:orgId/projects/:projectId/...# Scrum
/api/v1/orgs/:orgId/services/...           # Service Catalog
/api/v1/orgs/:orgId/workflows/...          # Workflow
/api/v1/orgs/:orgId/pull-requests/...      # PR
/api/v1/orgs/:orgId/search                 # Search
/api/v1/orgs/:orgId/notifications/...      # Notification
/api/v1/orgs/:orgId/audit-logs             # Audit Log
/api/v1/plugins/github/webhook             # GitHub Webhook（無認證，用 signature 驗證）
/api/v1/plugins/cicd/webhook               # CI/CD Webhook
```

### 5.2 統一回應格式

> **注意：** 以下 API 回應格式使用 TypeScript interface 描述，作為前後端共同的 API 契約文件。後端以 Pydantic v2 schemas 實作相同結構。

```typescript
// 成功 — 單筆
{ data: T }

// 成功 — 列表（含分頁）
{
  data: T[],
  meta: {
    page: number,
    limit: number,
    total: number,
    totalPages: number
  }
}

// 錯誤
{
  error: {
    code: string,    // e.g. "PAGE_NOT_FOUND", "VALIDATION_ERROR"
    message: string, // 人類可讀訊息
    details?: any    // 驗證錯誤時的欄位清單
  }
}
```

### 5.3 HTTP 狀態碼規範

| 狀態碼 | 使用場景 |
|---|---|
| 200 | 成功取得、更新 |
| 201 | 成功建立資源 |
| 204 | 成功刪除（無回應 body） |
| 400 | 請求格式錯誤、DTO 驗證失敗 |
| 401 | 未提供或無效的 JWT |
| 403 | 權限不足 |
| 404 | 資源不存在 |
| 409 | 衝突（重複 slug、版本衝突） |
| 422 | 業務邏輯錯誤（e.g. 無法啟動已有 ACTIVE sprint） |
| 500 | 內部錯誤 |

### 5.4 分頁與排序

```
GET /api/v1/orgs/:orgId/workspaces/:wsId/pages?page=1&limit=20&sort=updatedAt&order=desc
```

---

## 6. 認證與授權 (Auth + RBAC)

### 6.1 Auth Flow

```
┌─────────────────────────────────────────────────────────────┐
│ POST /api/v1/auth/login                                      │
│ Body: { email, password }                                    │
│                                                              │
│ → 驗證密碼 (bcrypt)                                          │
│ → 生成 access_token (JWT, 15min, signed with JWT_SECRET)     │
│ → 生成 refresh_token (random UUID, hash 後存 DB)            │
│ → Set-Cookie: refresh_token=xxx; HttpOnly; Secure; SameSite │
│ → Response: { data: { access_token, user } }                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ POST /api/v1/auth/refresh                                    │
│ Cookie: refresh_token (自動帶上)                             │
│                                                              │
│ → 驗證 cookie 中的 refresh_token hash 是否在 DB 且未 revoked │
│ → 驗證是否在 expiresAt 內                                    │
│ → 生成新 access_token                                        │
│ → Rotate refresh_token (revoke 舊的，生成新的)               │
│ → Response: { data: { access_token } }                       │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 JWT Payload

```typescript
interface JwtPayload {
  sub: string;      // userId
  email: string;
  name: string;
  iat: number;
  exp: number;      // now + 15min
}
// orgId 不放進 JWT，每個 request 從 URL params 取得後驗證成員資格
```

### 6.3 RBAC 矩陣

| 操作 | OrgMember | TeamMember | TeamLead | OrgAdmin | OrgOwner |
|---|:---:|:---:|:---:|:---:|:---:|
| 讀取 Org 資源 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 建立 Workspace | ❌ | ❌ | ❌ | ✅ | ✅ |
| 建立 Page | ✅ | ✅ | ✅ | ✅ | ✅ |
| Approve Page | ❌ | ❌ | ✅ | ✅ | ✅ |
| 建立 WorkItem | ✅ | ✅ | ✅ | ✅ | ✅ |
| 管理 Sprint | ❌ | ❌ | ✅ | ✅ | ✅ |
| 邀請成員 | ❌ | ❌ | ❌ | ✅ | ✅ |
| 建立/啟用 Workflow | ❌ | ❌ | ❌ | ✅ | ✅ |
| 安裝 Plugin | ❌ | ❌ | ❌ | ✅ | ✅ |
| 刪除 Org | ❌ | ❌ | ❌ | ❌ | ✅ |

### 6.4 FastAPI Depends 實作模式

```python
# backend/app/deps/auth.py

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """解析 JWT，回傳當前使用者。Token 無效則 401。"""
    ...

async def get_org_member(
    org_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrgMember:
    """確認使用者為 Org 成員，否則 403。"""
    ...

def require_org_role(*roles: OrgRole):
    """工廠函式：產生特定角色限制的 Depends。"""
    async def _checker(member: OrgMember = Depends(get_org_member)) -> OrgMember:
        if member.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return member
    return _checker

# 路由使用範例：
# backend/app/routers/wiki.py

@router.post("/orgs/{org_id}/workspaces")
async def create_workspace(
    payload: WorkspaceCreate,
    member: OrgMember = Depends(require_org_role(OrgRole.ADMIN, OrgRole.OWNER)),
    db: AsyncSession = Depends(get_db),
):
    ...
```

---

## 7. Module 1 — Team Management

### 7.1 API Endpoints

#### 認證

| Method | Path | 描述 | Auth |
|---|---|---|---|
| POST | `/auth/register` | 註冊（Phase 1：開放註冊；建立帳號後自動登入） | ❌ |
| POST | `/auth/login` | 登入 | ❌ |
| POST | `/auth/logout` | 登出（revoke refresh token） | ✅ |
| POST | `/auth/refresh` | 刷新 access token | Cookie |
| GET | `/users/me` | 取得當前使用者資料 | ✅ |
| PATCH | `/users/me` | 更新個人資料（name, avatarUrl） | ✅ |

#### Organization

| Method | Path | 描述 | 最低權限 |
|---|---|---|---|
| POST | `/orgs` | 建立 Org | 任何已登入使用者 |
| GET | `/orgs/:orgId` | 取得 Org 資訊 | Member |
| PATCH | `/orgs/:orgId` | 更新 Org 資訊 | Admin |
| GET | `/orgs/:orgId/members` | 列出成員（含角色） | Member |
| POST | `/orgs/:orgId/members/invite` | 邀請成員（email） | Admin |
| PATCH | `/orgs/:orgId/members/:userId/role` | 變更成員角色 | Admin |
| DELETE | `/orgs/:orgId/members/:userId` | 移除成員 | Admin |
| GET | `/orgs/:orgId/audit-logs` | 查詢 Audit Log | Admin |

#### Teams

| Method | Path | 描述 | 最低權限 |
|---|---|---|---|
| GET | `/orgs/:orgId/teams` | 列出 Teams | Member |
| POST | `/orgs/:orgId/teams` | 建立 Team | Admin |
| GET | `/orgs/:orgId/teams/:teamId` | 取得 Team 詳情 | Member |
| PATCH | `/orgs/:orgId/teams/:teamId` | 更新 Team | Admin or TeamLead |
| DELETE | `/orgs/:orgId/teams/:teamId` | 刪除 Team | Admin |
| POST | `/orgs/:orgId/teams/:teamId/members` | 新增 Team 成員 | Admin or TeamLead |
| DELETE | `/orgs/:orgId/teams/:teamId/members/:userId` | 移除 Team 成員 | Admin or TeamLead |

### 7.2 關鍵業務規則

- Org 建立者自動成為 OWNER，且 Org 必須至少有一個 OWNER
- 註冊：Phase 1 為開放註冊（email + password + name），建立帳號後回傳 access_token + refresh_token（等同自動登入）
- 邀請成員：若 email 已是系統使用者 → 直接加入；若不是 → Phase 1 簡化為回傳錯誤提示「使用者尚未註冊」，需先自行註冊
- 刪除成員前須確認：不能刪除 OWNER；刪除後其 assign 的 WorkItem 設為 unassigned
- 角色降級限制：不能將唯一的 OWNER 降為 ADMIN

### 7.3 Audit Log 寫入時機

所有寫入操作（Create/Update/Delete）在 Service 層完成後，非同步發布 `audit.log.write` 事件，由 `AuditModule` 統一寫入，不阻塞主流程。

---

## 8. Module 2 — Wiki

### 8.1 API Endpoints

#### Workspaces

| Method | Path | 描述 | 最低權限 |
|---|---|---|---|
| GET | `/orgs/:orgId/workspaces` | 列出 Workspaces | Member |
| POST | `/orgs/:orgId/workspaces` | 建立 Workspace | Admin |
| GET | `/orgs/:orgId/workspaces/:wsId` | 取得 Workspace 詳情 | Member |
| PATCH | `/orgs/:orgId/workspaces/:wsId` | 更新 Workspace | Admin |
| DELETE | `/orgs/:orgId/workspaces/:wsId` | 刪除 Workspace（軟刪除） | Admin |

#### Pages

| Method | Path | 描述 | 最低權限 |
|---|---|---|---|
| GET | `/orgs/:orgId/workspaces/:wsId/pages` | 取得 Page Tree（巢狀結構） | Member |
| POST | `/orgs/:orgId/workspaces/:wsId/pages` | 建立 Page | Member |
| GET | `/orgs/:orgId/workspaces/:wsId/pages/:pageId` | 取得 Page 詳情（含 content） | Member |
| PATCH | `/orgs/:orgId/workspaces/:wsId/pages/:pageId` | 更新 Page（title/content/status/position/parentId） | Member |
| DELETE | `/orgs/:orgId/workspaces/:wsId/pages/:pageId` | 刪除 Page（遞迴刪除子頁面） | Admin or Creator |
| PATCH | `/orgs/:orgId/workspaces/:wsId/pages/:pageId/status` | 單獨變更 Page 狀態 | 依狀態（見下方） |
| POST | `/orgs/:orgId/workspaces/:wsId/pages/:pageId/move` | 移動頁面（變更 parentId 與 position） | Member |

#### Page 版本控制

| Method | Path | 描述 | 最低權限 |
|---|---|---|---|
| GET | `/orgs/:orgId/workspaces/:wsId/pages/:pageId/versions` | 列出所有版本 | Member |
| GET | `/orgs/:orgId/workspaces/:wsId/pages/:pageId/versions/:versionId` | 取得特定版本內容 | Member |
| POST | `/orgs/:orgId/workspaces/:wsId/pages/:pageId/versions/:versionId/restore` | 還原至特定版本 | Member |

#### 跨實體連結

| Method | Path | 描述 | 最低權限 |
|---|---|---|---|
| GET | `/orgs/:orgId/workspaces/:wsId/pages/:pageId/links` | 取得 Page 的所有連結（含 backlinks） | Member |
| POST | `/orgs/:orgId/workspaces/:wsId/pages/:pageId/links` | 建立連結 | Member |
| DELETE | `/orgs/:orgId/workspaces/:wsId/pages/:pageId/links/:linkId` | 刪除連結 | Member |

### 8.2 Page Status 狀態機

```
DRAFT ──────────────► IN_REVIEW ──────────────► APPROVED
  ▲                       │                        │
  │                       │ (reject)                │
  └───────────────────────┘                        │
                                                   ▼
                                               ARCHIVED

狀態轉換規則：
- DRAFT → IN_REVIEW：Creator 或 Member
- IN_REVIEW → APPROVED：TeamLead 或 Admin
- IN_REVIEW → DRAFT：任何人（退回修改）
- APPROVED → ARCHIVED：Admin
- 任何狀態 → ARCHIVED：Admin
```

### 8.3 版本控制機制

- 每次 PATCH page content 時，**自動建立新版本**（非手動觸發）
- 版本號（`version`）從 1 開始自動遞增
- `Page.content` 永遠是最新版本
- Restore 操作：將指定版本的 content 複製至 `Page.content`，並建立新版本（不覆蓋歷史）

### 8.4 Real-time 協作

**Phase 1 策略：Yjs + HocusPocus (記憶體模式)**

```
Browser A                  HocusPocus               Browser B
    │                          │                        │
    │── connect(docId=pageId) ─►│◄── connect(docId) ────│
    │                          │                        │
    │── Y.Doc update ─────────►│─── broadcast ─────────►│
    │                          │                        │
    │                      (in-memory,                  │
    │                      no DB persist)               │
    │                                                   │
    │── user triggers Save ────────────────────────────►│
    │                     REST PATCH /pages/:id          │
    │◄─────── 200 OK ───────────────────────────────────│
```

**限制（Phase 1 已知問題）：**
- HocusPocus server restart → 未儲存的即時狀態丟失
- 無 presence 的 persistent state（重連後其他使用者位置重置）
- **解法：前端每 30 秒自動 auto-save，並在 unload 前強制 save**

### 8.5 Page Tree API 回應格式

```typescript
// GET /workspaces/:wsId/pages → 回傳巢狀樹
interface PageTreeNode {
  id: string;
  title: string;
  status: PageStatus;
  position: number;
  createdById: string;
  updatedAt: string;
  children: PageTreeNode[];  // 遞迴
}
```

---

## 9. Module 3 — Scrum + DevOps

### 9.1 API Endpoints

#### Projects

| Method | Path | 描述 |
|---|---|---|
| GET | `/orgs/:orgId/projects` | 列出 Projects |
| POST | `/orgs/:orgId/projects` | 建立 Project |
| GET | `/orgs/:orgId/projects/:projectId` | 取得 Project 詳情 |
| PATCH | `/orgs/:orgId/projects/:projectId` | 更新 Project |
| POST | `/orgs/:orgId/projects/:projectId/teams` | 關聯 Team 至 Project |

#### Work Items

| Method | Path | 描述 |
|---|---|---|
| GET | `/orgs/:orgId/projects/:projectId/work-items` | 列出 Work Items（支援 filter/sort） |
| POST | `/orgs/:orgId/projects/:projectId/work-items` | 建立 Work Item |
| GET | `/orgs/:orgId/projects/:projectId/work-items/:itemId` | 取得詳情（含 children、links） |
| PATCH | `/orgs/:orgId/projects/:projectId/work-items/:itemId` | 更新（任意欄位） |
| DELETE | `/orgs/:orgId/projects/:projectId/work-items/:itemId` | 刪除（軟刪除） |
| PATCH | `/orgs/:orgId/projects/:projectId/work-items/:itemId/status` | 變更狀態（觸發 Board 即時更新） |
| PATCH | `/orgs/:orgId/projects/:projectId/work-items/reorder` | 批量更新 Backlog position |

#### Sprints

| Method | Path | 描述 | 最低權限 |
|---|---|---|---|
| GET | `/orgs/:orgId/projects/:projectId/sprints` | 列出 Sprints | Member |
| POST | `/orgs/:orgId/projects/:projectId/sprints` | 建立 Sprint | TeamLead |
| PATCH | `/orgs/:orgId/projects/:projectId/sprints/:sprintId` | 更新 Sprint 基本資訊 | TeamLead |
| POST | `/orgs/:orgId/projects/:projectId/sprints/:sprintId/start` | 啟動 Sprint | TeamLead |
| POST | `/orgs/:orgId/projects/:projectId/sprints/:sprintId/complete` | 完成 Sprint | TeamLead |
| GET | `/orgs/:orgId/projects/:projectId/sprints/:sprintId/board` | 取得 Sprint Board（含分欄 work items） | Member |
| GET | `/orgs/:orgId/projects/:projectId/sprints/:sprintId/burndown` | 取得燃盡圖資料 | Member |
| POST | `/orgs/:orgId/projects/:projectId/sprints/:sprintId/items/:itemId` | 將 Work Item 加入 Sprint | TeamLead |
| DELETE | `/orgs/:orgId/projects/:projectId/sprints/:sprintId/items/:itemId` | 從 Sprint 移除 Work Item | TeamLead |

#### Pull Requests

| Method | Path | 描述 |
|---|---|---|
| GET | `/orgs/:orgId/pull-requests` | 列出 PRs（filter: status, repo, assignee） |
| GET | `/orgs/:orgId/pull-requests/:prId` | 取得 PR 詳情（含 comments、linked tickets） |
| GET | `/orgs/:orgId/pull-requests/dashboard` | PR Review Dashboard（依 team/status/risk 分組） |
| POST | `/orgs/:orgId/pull-requests/:prId/links` | 手動建立 PR ↔ Ticket/Page 連結 |

### 9.2 Sprint 狀態機與業務規則

```
PLANNING ──► ACTIVE ──► COMPLETED

業務規則：
1. 同一個 Project 同時只能有一個 ACTIVE Sprint
2. Sprint 啟動需有 startDate 和 endDate
3. Sprint 完成時，未完成的 Work Items 自動移回 BACKLOG（不刪除）
4. Sprint 完成後不可再修改
```

### 9.3 Burndown Chart 資料格式

```typescript
// GET /sprints/:sprintId/burndown
interface BurndownData {
  sprint: {
    id: string;
    startDate: string;
    endDate: string;
    totalPoints: number;
  };
  dailyData: Array<{
    date: string;          // ISO date
    idealRemaining: number; // 理想剩餘點數
    actualRemaining: number;// 實際剩餘點數
    completedPoints: number;
  }>;
}
```

### 9.4 PR Auto-linking 邏輯

當 GitHub Webhook 觸發 `pull_request` 事件時，後端執行：

```python
import re

# 1. Branch name 解析
# Pattern: feat/PROJ-123-description → ticket_key = "PROJ-123"
BRANCH_PATTERN = re.compile(r"(?:feat|fix|chore|hotfix)/([A-Z]+-\d+)", re.IGNORECASE)

# 2. Commit message / PR body 解析
# Pattern: "fixes PROJ-123" or "refs PROJ-123" or "closes PROJ-123"
COMMIT_PATTERN = re.compile(r"(?:fixes?|refs?|closes?)\s+([A-Z]+-\d+)", re.IGNORECASE)

async def auto_link_pr(pr_data: dict, db: AsyncSession) -> list[str]:
    """從 branch name 和 PR body 中解析 ticket key，建立 EntityLink。"""
    ticket_keys: set[str] = set()

    # 從 branch name 解析
    branch_match = BRANCH_PATTERN.search(pr_data["head_branch"])
    if branch_match:
        ticket_keys.add(branch_match.group(1).upper())

    # 從 PR body 解析
    if pr_data.get("body"):
        ticket_keys.update(
            m.group(1).upper() for m in COMMIT_PATTERN.finditer(pr_data["body"])
        )

    # 3. 查詢 WorkItem（ticket_key = "{project.prefix}-{work_item.number}"）
    #    拆分 prefix 和 number → 查詢 Project(prefix) → WorkItem(project_id, number)
    # 4. 建立 EntityLink
    # 5. 發布 scrum.pr.linked 事件 → Notification + Workflow Trigger
    ...
```

### 9.5 Sprint Board API 回應

```typescript
// GET /sprints/:sprintId/board
interface SprintBoard {
  sprint: Sprint;
  columns: Array<{
    status: WorkItemStatus;
    label: string;
    items: WorkItemSummary[];
  }>;
}
// 欄位順序：TODO → IN_PROGRESS → IN_REVIEW → QA → DONE
```

---

## 10. Module 4 — Service Catalog

### 10.1 API Endpoints

| Method | Path | 描述 | 最低權限 |
|---|---|---|---|
| GET | `/orgs/:orgId/services` | 列出 Services（含 filter: lifecycle, owner） | Member |
| POST | `/orgs/:orgId/services` | 建立 Service | Admin |
| GET | `/orgs/:orgId/services/:serviceId` | 取得 Service 詳情（含 links） | Member |
| PATCH | `/orgs/:orgId/services/:serviceId` | 更新 Service | Admin or ownerTeam Lead |
| DELETE | `/orgs/:orgId/services/:serviceId` | 刪除 Service | Admin |
| GET | `/orgs/:orgId/services/dashboard` | Org-wide Service 概覽 | Member |
| POST | `/orgs/:orgId/services/:serviceId/links` | 建立 Service 連結（Repo/Wiki/Ticket/PR） | Admin |
| DELETE | `/orgs/:orgId/services/:serviceId/links/:linkId` | 刪除連結 | Admin |

### 10.2 Service Dashboard 回應格式

```typescript
// GET /orgs/:orgId/services/dashboard
interface ServiceDashboard {
  summary: {
    total: number;
    byLifecycle: Record<ServiceLifecycle, number>;
    byOwnerTeam: Array<{ teamId: string; teamName: string; count: number }>;
  };
  services: Array<{
    id: string;
    name: string;
    slug: string;
    lifecycle: ServiceLifecycle;
    ownerTeam?: { id: string; name: string };
    linkedTicketsCount: number;
    linkedPRsCount: number;
    openIncidentsCount: number;  // Phase 1: always 0
    repoUrl?: string;
    updatedAt: string;
  }>;
}
```

### 10.3 Service 連結類型

| `linkType` | 說明 | Target 欄位 |
|---|---|---|
| `SERVICE_REPO` | Service → GitHub Repo | `targetExternalUrl` |
| `SERVICE_WIKI` | Service → Wiki Page | `targetPageId` |
| `SERVICE_TICKET` | Service → WorkItem | `targetWorkItemId` |
| `SERVICE_PR` | Service → PullRequest | `targetPRId` |

---

## 11. Module 5 — Workflow Engine (基礎)

### 11.1 Phase 1 範圍限制

Phase 1 的 Workflow Engine 為「**API-only 設定 + 線性執行**」模式：
- ❌ 無 Visual Canvas（Phase 2）
- ❌ 無並行分支（Parallel）
- ❌ 無 Sub-workflow
- ❌ 無 AI Agent Node（Phase 2）
- ✅ 單一 Trigger → 可選 Condition → 有序 Actions
- ✅ 完整 Execution Log（每步驟 Input/Output 快照）

### 11.2 API Endpoints

| Method | Path | 描述 | 最低權限 |
|---|---|---|---|
| GET | `/orgs/:orgId/workflows` | 列出 Workflows | Member |
| POST | `/orgs/:orgId/workflows` | 建立 Workflow | Admin |
| GET | `/orgs/:orgId/workflows/:workflowId` | 取得詳情（含 definition） | Member |
| PATCH | `/orgs/:orgId/workflows/:workflowId` | 更新 Workflow（自動 DRAFT 化） | Admin |
| DELETE | `/orgs/:orgId/workflows/:workflowId` | 刪除 Workflow | Admin |
| POST | `/orgs/:orgId/workflows/:workflowId/enable` | 啟用（DRAFT/DISABLED → ACTIVE） | Admin |
| POST | `/orgs/:orgId/workflows/:workflowId/disable` | 停用（ACTIVE → DISABLED） | Admin |
| GET | `/orgs/:orgId/workflows/:workflowId/executions` | 列出執行紀錄 | Member |
| GET | `/orgs/:orgId/workflows/:workflowId/executions/:execId` | 取得執行詳情（含每步驟 log） | Member |
| POST | `/orgs/:orgId/workflows/:workflowId/test` | 手動觸發測試執行（不等待完成） | Admin |

### 11.3 Workflow Definition Schema

```typescript
interface WorkflowDefinition {
  trigger: {
    type: TriggerType;
    filters?: Record<string, unknown>;  // 依 trigger 類型不同
  };
  condition?: {
    // 使用 JSONLogic (jsonlogic.com) 格式
    // e.g. { "===": [{ "var": "trigger.priority" }, "HIGH"] }
    expression: Record<string, unknown>;
  };
  actions: WorkflowAction[];
}

// Phase 1 支援的 Trigger 類型
type TriggerType =
  | 'TICKET_CREATED'
  | 'TICKET_STATUS_CHANGED'
  | 'TICKET_ASSIGNED'
  | 'PR_OPENED'
  | 'PR_MERGED'
  | 'PR_CLOSED'
  | 'WIKI_PAGE_CREATED'
  | 'WIKI_PAGE_STATUS_CHANGED'
  | 'SPRINT_STARTED'
  | 'SPRINT_COMPLETED'
  | 'CICD_BUILD_COMPLETED'
  | 'MANUAL';  // 手動觸發（用於測試）

// Phase 1 支援的 Action 類型
type ActionType =
  | 'SEND_NOTIFICATION'    // 發送 in-app 通知
  | 'SEND_SLACK_MESSAGE'   // 發送 Slack 訊息
  | 'UPDATE_TICKET'        // 更新 WorkItem 欄位
  | 'CREATE_TICKET'        // 建立 WorkItem
  | 'CREATE_WIKI_PAGE'     // 建立 Wiki Page
  | 'ADD_COMMENT'          // 在 Ticket/Page 上加評論
  | 'LINK_ENTITIES'        // 建立實體連結
  | 'HTTP_REQUEST';        // 自定義 HTTP 請求

interface WorkflowAction {
  id: string;         // 唯一識別，用於 log 追蹤
  type: ActionType;
  params: Record<string, unknown>;  // 依 action 類型不同
  // params 中支援模板語法：
  // "{{trigger.id}}" → 替換為 trigger 資料中的欄位值
}
```

### 11.4 完整 Workflow Definition 範例

```json
{
  "trigger": {
    "type": "PR_MERGED",
    "filters": {
      "baseBranch": "main"
    }
  },
  "condition": {
    "expression": {
      "in": [{ "var": "trigger.repoFullName" }, ["org/backend", "org/frontend"]]
    }
  },
  "actions": [
    {
      "id": "a1",
      "type": "SEND_NOTIFICATION",
      "params": {
        "userIds": ["{{trigger.linkedTicket.assigneeId}}"],
        "title": "PR 已合併",
        "body": "PR #{{trigger.number}} 已合併至 main，請更新 Ticket 狀態",
        "resourceType": "PullRequest",
        "resourceId": "{{trigger.id}}"
      }
    },
    {
      "id": "a2",
      "type": "UPDATE_TICKET",
      "params": {
        "workItemId": "{{trigger.linkedTicket.id}}",
        "fields": { "status": "QA" }
      }
    },
    {
      "id": "a3",
      "type": "SEND_SLACK_MESSAGE",
      "params": {
        "channel": "#deployments",
        "text": ":merged: PR #{{trigger.number}} merged: {{trigger.title}}"
      }
    }
  ]
}
```

### 11.5 執行引擎架構

**arq Worker 定義：**

```python
# apps/backend/app/workers/settings.py
from arq.connections import RedisSettings
from app.core.config import settings

class WorkerSettings:
    functions = [execute_workflow]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300  # 5 分鐘超時
```

```python
# apps/backend/app/workers/workflow.py
from arq import Retry
from app.core.database import get_async_session

async def execute_workflow(ctx: dict, workflow_id: str, trigger_data: dict):
    """arq worker function — async-native，直接使用 async session。"""
    async with get_async_session() as db:
        # 1. 建立 WorkflowExecution 紀錄（status: RUNNING）
        # 2. 評估 Trigger filters（是否符合此次事件）
        # 3. 評估 Condition（若有）→ 不符合則 skip，execution status: COMPLETED
        # 4. 依序執行 Actions：
        #    - 每個 Action 執行前：寫入 WorkflowStepLog（input snapshot）
        #    - 執行 Action（HTTP call、Slack notify 等）
        #    - 執行後：更新 WorkflowStepLog（output, duration, status）
        #    - 若 Action 失敗：execution status: FAILED，停止後續 actions
        # 5. 更新 WorkflowExecution（status: COMPLETED/FAILED, duration_ms）
```

**事件到 Queue 的橋接（Event Bus）：**
```python
# apps/backend/app/events/workflow_bridge.py
from arq import create_pool
from arq.connections import RedisSettings
from app.events.bus import event_bus

async def on_domain_event(event_type: str, **kwargs):
    """訂閱 event bus 上的所有領域事件，找到匹配的 ACTIVE Workflow 並 enqueue。"""
    # 1. 查詢所有 ACTIVE 且 trigger.type 匹配 event_type 的 Workflow
    # 2. 對每個匹配的 Workflow：
    pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    await pool.enqueue_job(
        "execute_workflow",
        workflow_id,
        trigger_data,
        _job_id=f"{event_type}-{resource_id}",  # 確保冪等（相同 job_id 不重複）
    )

# 啟動時註冊（在 main.py lifespan 中）
for trigger_type in SUPPORTED_TRIGGERS:
    event_name = TRIGGER_TO_EVENT[trigger_type]
    event_bus.on(event_name, lambda **kw: on_domain_event(event_name, **kw))
```

---

## 12. Cross-Cutting — Search / Notification / WebSocket

### 12.1 Global Search

**策略：PostgreSQL Full-Text Search + `pg_trgm`**

```sql
-- 建立 GIN 索引（在 Alembic migration 中手動加入）
CREATE INDEX idx_pages_fts ON pages
  USING gin(to_tsvector('english', title || ' ' || plain_text));

CREATE INDEX idx_work_items_fts ON work_items
  USING gin(to_tsvector('english', title));

CREATE INDEX idx_services_fts ON services
  USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));
```

```typescript
// GET /orgs/:orgId/search?q=payment&types=page,ticket,service&limit=20
interface SearchResult {
  data: Array<{
    type: 'page' | 'ticket' | 'service' | 'pullrequest';
    id: string;
    title: string;
    excerpt: string;   // 含關鍵字高亮的摘要片段
    url: string;       // 前端跳轉路徑
    updatedAt: string;
  }>;
  meta: { total: number; query: string };
}
```

### 12.2 In-App Notification

**觸發時機（Phase 1）：**

| 事件 | 通知對象 | 通知類型 |
|---|---|---|
| WorkItem assigned | assignee | `ticket_assigned` |
| WorkItem mentioned（@user） | mentioned user | `mention` |
| PR linked to WorkItem | ticket assignee | `pr_linked` |
| PR merged（linked ticket） | ticket assignee | `pr_merged` |
| Page status changed to IN_REVIEW | org admins + team leads | `page_review_required` |
| Workflow execution failed | workflow creator | `workflow_failed` |
| Sprint started | sprint team members | `sprint_started` |

**API：**
```
GET  /orgs/:orgId/notifications?page=1&limit=20&unreadOnly=true
PATCH /orgs/:orgId/notifications/:notifId/read
POST  /orgs/:orgId/notifications/read-all
```

### 12.3 WebSocket Events

**Socket.io Room 策略：**

```typescript
// 使用者連線時自動加入的 Rooms
`org:${orgId}`            // Org 層級（通知）
`project:${projectId}`    // Project 層級（Board 更新）
`page:${pageId}`          // Page 層級（協作游標）
`user:${userId}`          // 個人層級（個人通知）
```

**Server → Client 事件：**

```typescript
// WebSocket 事件型別定義（前端 apps/frontend/src/types/events.ts）

type ServerToClientEvents = {
  // Wiki
  'page:updated': { pageId: string; title: string; updatedById: string };
  'page:status_changed': { pageId: string; status: PageStatus };

  // Scrum
  'ticket:updated': { ticketId: string; fields: Partial<WorkItem> };
  'ticket:moved': { ticketId: string; fromStatus: string; toStatus: string };
  'sprint:updated': { sprintId: string; status: SprintStatus };

  // PR
  'pr:updated': { prId: string; status: PRStatus; ciStatus?: string };

  // Notification
  'notification:new': { notification: Notification };

  // Workflow
  'workflow:execution_completed': {
    workflowId: string;
    executionId: string;
    status: ExecutionStatus;
  };
};
```

---

## 13. Plugin — GitHub / Slack / CI/CD

### 13.1 GitHub Plugin

#### 安裝流程

1. Org Admin 前往 Settings → Plugins → GitHub
2. 點擊「Install GitHub App」→ 跳轉至 GitHub App 安裝頁
3. 選擇要授權的 Repositories
4. GitHub 回調 `GET /api/v1/plugins/github/callback?code=xxx&installation_id=yyy`
5. 後端儲存 `installation_id` 至 Org 設定

#### Webhook Endpoint

```
POST /api/v1/plugins/github/webhook
Headers:
  X-GitHub-Event: pull_request
  X-Hub-Signature-256: sha256=...  (用 GITHUB_WEBHOOK_SECRET 驗證)
```

**處理的事件：**

| GitHub Event | Action | 平台行為 |
|---|---|---|
| `pull_request` | opened | 建立 PullRequest，嘗試 Auto-link |
| `pull_request` | closed (not merged) | 更新狀態為 CLOSED |
| `pull_request` | closed (merged) | 更新狀態為 MERGED，發布 `scrum.pr.merged` 事件 |
| `pull_request` | synchronize | 更新 additions/deletions |
| `pull_request_review` | submitted | 更新 PR review 狀態 |
| `pull_request_review_comment` | created | 建立或更新 PRComment |
| `check_run` | completed | 更新 PR ciStatus |

**Webhook 安全驗證：**
```python
import hashlib
import hmac
from fastapi import Request, HTTPException

async def verify_github_signature(request: Request) -> bytes:
    """驗證 GitHub Webhook 的 X-Hub-Signature-256 header。"""
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    return body
```

### 13.2 Slack Plugin

**Phase 1 功能：僅單向推送（平台 → Slack）**

#### 安裝流程

1. Admin 在 Slack Plugin 設定頁輸入 Bot Token 與目標 Channel
2. 後端驗證 token 有效性（`auth.test` API）
3. 儲存 token（加密後存入 DB）

#### 使用方式（Workflow Action）

```json
{
  "type": "SEND_SLACK_MESSAGE",
  "params": {
    "channel": "#deployments",
    "text": "PR merged: {{trigger.title}}"
  }
}
```

**後端實作：** 使用 Python `slack_sdk`（`pip install slack_sdk`），呼叫 `AsyncWebClient.chat_postMessage`

```python
from slack_sdk.web.async_client import AsyncWebClient

async def send_slack_message(channel: str, text: str, token: str):
    client = AsyncWebClient(token=token)
    await client.chat_postMessage(channel=channel, text=text)
```

### 13.3 CI/CD Connector

**通用 Webhook 接收器**，不綁定特定 CI 平台。

```
POST /api/v1/plugins/cicd/webhook
Headers:
  X-IDP-Secret: {orgCicdWebhookSecret}   // 每個 Org 有獨立 secret
Content-Type: application/json
```

**Payload Schema（標準化格式）：**

```typescript
interface CicdWebhookPayload {
  event: 'build.started' | 'build.succeeded' | 'build.failed' | 'deployment.completed';
  status: 'pending' | 'success' | 'failure';
  repoFullName: string;   // "org/repo"
  branch: string;
  commitSha: string;
  buildUrl?: string;
  environment?: string;   // deployment 事件的部署環境
  triggeredAt: string;    // ISO datetime
}
```

**GitHub Actions 整合範例（`.github/workflows/notify.yml`）：**

```yaml
- name: Notify IDP
  if: always()
  run: |
    curl -X POST https://your-idp.example.com/api/v1/plugins/cicd/webhook \
      -H "X-IDP-Secret: ${{ secrets.IDP_WEBHOOK_SECRET }}" \
      -H "Content-Type: application/json" \
      -d '{
        "event": "build.${{ job.status == 'success' && 'succeeded' || 'failed' }}",
        "status": "${{ job.status == 'success' && 'success' || 'failure' }}",
        "repoFullName": "${{ github.repository }}",
        "branch": "${{ github.ref_name }}",
        "commitSha": "${{ github.sha }}",
        "buildUrl": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}",
        "triggeredAt": "${{ github.event.head_commit.timestamp }}"
      }'
```

---

## 14. 開發順序與里程碑

### 14.1 建議開發序列

Phase 1 採用「由下往上，由核心往邊緣」的建置策略：

```
Month 1-2: Infrastructure & Foundation
─────────────────────────────────────
Week 1-2:
  - Monorepo 建置（pnpm 管理前端、uv 管理後端）
  - Docker Compose 環境（Postgres / Redis / MinIO / HocusPocus）
  - FastAPI 骨架 + SQLAlchemy models + Alembic first migration
  - arq worker 設定
  - GitHub Actions CI pipeline（Ruff lint, pytest, pnpm build）

Week 3-4:
  - Auth Module（登入/登出/refresh/JWT）
  - Team Management Module（Org/Team CRUD + RBAC Guards）
  - AuditLog 機制
  - 前端骨架（Vite + React Router v7）+ shadcn/ui 設定 + Auth pages

Month 3-4: Core Modules
─────────────────────────────────────
Week 5-7:
  - Wiki Module 後端（Workspace/Page CRUD + 版本控制）
  - Page 狀態機
  - EntityLink 機制（通用跨實體連結）
  - Wiki Module 前端（Page Tree + TipTap Editor + 版本歷史）
  - HocusPocus 整合（即時協作）

Week 8-10:
  - Scrum Module 後端（WorkItem / Sprint 全部 API）
  - PR 資料模型（無 GitHub 同步，先 manual CRUD）
  - Scrum Module 前端（Backlog + Kanban Board + Burndown Chart）
  - @dnd-kit 拖拉實作

Month 5-6: Platform & Integration
─────────────────────────────────────
Week 11-12:
  - Service Catalog Module（後端 + 前端）
  - Search Module（PG FTS 索引 + API）
  - Notification Module（後端事件 + 前端通知中心）
  - WebSocket Gateway（Socket.io + Room 管理）

Week 13-15:
  - GitHub Plugin（GitHub App 安裝 + Webhook 處理 + PR Auto-link）
  - Slack Plugin（Bot Token + 訊息推送）
  - CI/CD Connector（Webhook receiver）

Week 16-17:
  - Workflow Engine Module（Definition CRUD + arq Worker）
  - 所有支援 Trigger 類型的事件橋接
  - Execution Log UI

Month 7: Hardening
─────────────────────────────────────
Week 18-20:
  - 整合測試（全鏈路）
  - E2E 測試（Playwright，涵蓋主要 Happy Path）
  - Performance 測試（k6，驗證 P95 API < 500ms）
  - Security review（RBAC 漏洞、Webhook 驗證、SQL injection）
  - Bug fixing & polish
```

### 14.2 里程碑定義

| 里程碑 | 時間點 | 完成標準 |
|---|---|---|
| **M0: Dev Ready** | Week 2 結束 | Docker Compose 可一鍵啟動；CI pass；Auth 可登入 |
| **M1: Team + Wiki** | Week 7 結束 | 可建立 Org/Team；可建立/編輯/版本控制 Wiki；多人游標可見 |
| **M2: Scrum** | Week 10 結束 | 可管理 Backlog、Sprint；Board 拖拉可用；Burndown Chart 正確 |
| **M3: Platform Core** | Week 12 結束 | Service Catalog 可用；Search 可用；Notification 可用；WebSocket 即時更新 |
| **M4: Full Integration** | Week 17 結束 | GitHub PR 自動同步；Slack 通知；CI/CD 事件；Workflow 可建立並執行 |
| **M5: Production Ready** | Week 20 結束 | 所有 E2E 測試 pass；無已知 P0/P1 Bug；RBAC 安全審核通過 |

---

## 15. 測試策略

### 15.1 測試層級

```
E2E Tests (Playwright) ──────────────────── 10% ── 覆蓋主要 User Journey
     ▲
Integration Tests (pytest + httpx TestClient) ─ 30% ── API 層面，含 DB
     ▲
Unit Tests (pytest + pytest-asyncio) ──────── 60% ── Service / 純邏輯
```

### 15.2 強制測試涵蓋清單（每個 Module）

**Unit Tests（Service 層）：**
- [ ] 正常流：CRUD 每個操作的成功路徑
- [ ] 業務規則：狀態機轉換（合法 + 非法路徑）
- [ ] 邊界值：空列表、null 欄位、最大長度字串
- [ ] 權限：無權限操作應拋出 ForbiddenException

**Integration Tests（Router 層，使用 httpx AsyncClient + TestClient）：**
- [ ] JWT 未提供 → 401
- [ ] JWT 有效但非 Org 成員 → 403
- [ ] DTO 驗證失敗 → 400（含 details）
- [ ] 資源不存在 → 404
- [ ] 衝突（重複 slug）→ 409
- [ ] 成功路徑回應格式正確（data + meta）

**E2E Tests（Playwright，涵蓋的 User Journey）：**
- [ ] 使用者完整 Auth 流程（登入→刷新→登出）
- [ ] PM 建立 Workspace → 建立 Page → Submit for Review → Approve
- [ ] RD 建立 Epic → 分解 Story → 建立 Sprint → 啟動 → 移動 Ticket → 完成 Sprint
- [ ] PR 從 GitHub Webhook 進入 → 自動連結 Ticket → Ticket 狀態更新
- [ ] Workflow：PR Merged → Ticket 狀態自動更新 → Slack 通知（mock Slack API）

### 15.3 關鍵邊界條件清單（跨模組）

| 情境 | 預期行為 |
|---|---|
| 刪除有子頁面的 Page | 遞迴刪除所有子頁面（Cascade），並從 EntityLink 中移除對應引用 |
| 刪除 WorkItem（EPIC，有子 Stories） | 子 Stories 的 `parentId` 設為 `null`（不刪除） |
| Sprint 完成時有未完成 Items | 自動移回 BACKLOG，狀態不變 |
| 同時有 2 個 ACTIVE Sprint 的嘗試 | 422 + `SPRINT_ALREADY_ACTIVE` |
| PR Auto-link 找不到對應 Ticket | 靜默忽略（不報錯），寫入 warn log |
| GitHub Webhook signature 不符 | 401，不執行任何邏輯 |
| Workflow Action 失敗（e.g. Slack API down） | 記錄 Step 失敗，整個 Execution 標為 FAILED，後續 Actions 不執行 |
| Workflow 定義更新後自動 DRAFT 化 | 已有的 ACTIVE Execution 不受影響（執行完才 DRAFT） |
| 並發多個 Webhook 事件（同一 PR） | arq `_job_id = f"{event_type}-{pr_id}"` 確保冪等（相同 job_id 不重複加入） |
| 使用者同時被多個分頁編輯同一 Page | HocusPocus CRDT 處理衝突；Page save 使用樂觀鎖（version field check） |

### 15.4 效能目標驗證（k6 腳本）

```
Target: API P95 < 500ms

測試情境：
- 50 concurrent users
- GET /workspaces/:wsId/pages（Page Tree，100 nodes）< 300ms P95
- GET /projects/:projectId/sprints/:sprintId/board < 400ms P95
- POST /work-items（含 Audit Log 非同步寫入）< 500ms P95
- GET /search?q=payment < 500ms P95
```

---

*此規格書版本 v1.1 — 基於 PRD v0.3 Phase 1 範圍。v1.1 修正：統一後端為 Python/FastAPI 生態、Celery 替換為 arq、修復目錄結構/port/event bus 不一致、補齊 register endpoint 及 ticket ID 機制。任何功能範圍變更須同步更新本文件並重新評估里程碑。*
