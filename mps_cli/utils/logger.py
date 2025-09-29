import logging
import os
from logging.handlers import RotatingFileHandler
from config.settings import settings

def setup_logging():
    """設置日誌系統"""
    # 創建日誌目錄
    log_dir = os.path.dirname(settings.logging.file_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 配置根日誌器
    logging.basicConfig(
        level=getattr(logging, settings.logging.level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # 控制台處理器
            logging.StreamHandler(),
            # 文件處理器（輪轉）
            RotatingFileHandler(
                settings.logging.file_path,
                maxBytes=settings.logging.max_size,
                backupCount=settings.logging.backup_count,
                encoding='utf-8'
            )
        ]
    )
    
    # 設置第三方庫的日誌級別
    logging.getLogger('supabase').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """獲取日誌器"""
    return logging.getLogger(name)

class UILogger:
    """UI 專用日誌器，用於記錄用戶操作"""
    
    def __init__(self):
        self.logger = get_logger('mps_cli.ui')
    
    def log_user_action(self, action: str, details: dict = None):
        """記錄用戶操作"""
        message = f"用戶操作: {action}"
        if details:
            message += f" - {details}"
        self.logger.info(message)
    
    def log_login(self, role: str, identifier: str):
        """記錄登入操作"""
        self.log_user_action("登入", {
            "role": role,
            "identifier": identifier[:8] + "..." if len(identifier) > 8 else identifier
        })
    
    def log_logout(self, role: str):
        """記錄登出操作"""
        self.log_user_action("登出", {"role": role})
    
    def log_transaction(self, tx_type: str, amount: float = None, tx_no: str = None):
        """記錄交易操作"""
        details = {"type": tx_type}
        if amount:
            details["amount"] = amount
        if tx_no:
            details["tx_no"] = tx_no
        self.log_user_action("交易操作", details)
    
    def log_error(self, error: str, context: dict = None):
        """記錄錯誤"""
        message = f"錯誤: {error}"
        if context:
            message += f" - 上下文: {context}"
        self.logger.error(message)
    
    def log_warning(self, warning: str, context: dict = None):
        """記錄警告"""
        message = f"警告: {warning}"
        if context:
            message += f" - 上下文: {context}"
        self.logger.warning(message)

# 全局 UI 日誌器實例
ui_logger = UILogger()