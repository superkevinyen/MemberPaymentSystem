import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# 載入環境變量
load_dotenv()

@dataclass
class DatabaseConfig:
    """數據庫配置"""
    url: str
    service_role_key: str
    anon_key: str
    timeout: int = 30

@dataclass
class UIConfig:
    """UI 配置"""
    page_size: int = 20
    qr_ttl_seconds: int = 900
    auto_refresh: bool = True
    show_colors: bool = True

@dataclass
class LogConfig:
    """日誌配置"""
    level: str = "INFO"
    file_path: str = "logs/mps_cli.log"
    max_size: int = 10485760  # 10MB
    backup_count: int = 5

class Settings:
    """應用設置類"""
    
    def __init__(self):
        self.database = DatabaseConfig(
            url=os.getenv("SUPABASE_URL", ""),
            service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            anon_key=os.getenv("SUPABASE_ANON_KEY", "")
        )
        
        self.ui = UIConfig(
            page_size=int(os.getenv("UI_PAGE_SIZE", "20")),
            qr_ttl_seconds=int(os.getenv("QR_TTL_SECONDS", "900")),
            show_colors=os.getenv("SHOW_COLORS", "true").lower() == "true"
        )
        
        self.logging = LogConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            file_path=os.getenv("LOG_FILE", "logs/mps_cli.log")
        )
    
    def validate(self) -> bool:
        """驗證配置完整性"""
        if not self.database.url:
            raise ValueError("SUPABASE_URL 是必需的")
        if not self.database.service_role_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY 是必需的")
        if not self.database.anon_key:
            raise ValueError("SUPABASE_ANON_KEY 是必需的")
        return True

# 全局配置實例
settings = Settings()