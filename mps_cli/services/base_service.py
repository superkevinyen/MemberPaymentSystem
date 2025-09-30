from abc import ABC
from typing import Any, Dict, List, Optional
from config.supabase_client import supabase_client
from utils.error_handler import error_handler
from utils.logger import get_logger

class BaseService(ABC):
    """基礎服務類"""
    
    def __init__(self):
        self.client = supabase_client
        self.logger = get_logger(self.__class__.__name__)
        self.error_handler = error_handler
        self.auth_service = None
    
    def rpc_call(self, function_name: str, params: Dict[str, Any]) -> Any:
        """安全的 RPC 調用"""
        try:
            self.logger.info(f"調用 RPC: {function_name}")
            self.logger.debug(f"RPC 參數: {params}")
            
            result = self.client.rpc(function_name, params)
            
            self.logger.info(f"RPC 調用成功: {function_name}")
            self.logger.debug(f"RPC 結果: {result}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"RPC 調用失敗: {function_name}, 錯誤: {e}")
            raise self.error_handler.handle_rpc_error(e)
    
    def query_table(self, table: str, filters: Optional[Dict] = None,
                   limit: Optional[int] = None, offset: Optional[int] = None,
                   order_by: Optional[str] = None, ascending: bool = True) -> List[Dict]:
        """查詢表格數據"""
        try:
            # 直接使用表名（public schema）
            self.logger.debug(f"查詢表格: {table}, 過濾條件: {filters}")
            
            query = self.client.query(table).select("*")
            
            # 應用過濾條件
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            # 排序
            if order_by:
                query = query.order(order_by, desc=not ascending)
            
            # 分頁
            if limit:
                query = query.limit(limit)
            
            if offset:
                query = query.offset(offset)
            
            result = query.execute()
            data = getattr(result, "data", [])
            
            self.logger.debug(f"查詢成功: {table}, 返回 {len(data)} 條記錄")
            return data
            
        except Exception as e:
            self.logger.error(f"查詢失敗: {table}, 錯誤: {e}")
            raise self.error_handler.handle_query_error(e)
    
    def insert_record(self, table: str, data: Dict[str, Any]) -> Dict:
        """插入記錄"""
        try:
            self.logger.info(f"插入記錄到表: {table}")
            self.logger.debug(f"插入數據: {data}")
            
            result = self.client.insert(table, data)
            
            self.logger.info(f"插入成功: {table}")
            return result
            
        except Exception as e:
            self.logger.error(f"插入失敗: {table}, 錯誤: {e}")
            raise self.error_handler.handle_rpc_error(e)
    
    def update_record(self, table: str, data: Dict[str, Any], 
                     filters: Dict[str, Any]) -> List[Dict]:
        """更新記錄"""
        try:
            self.logger.info(f"更新記錄: {table}")
            self.logger.debug(f"更新數據: {data}, 過濾條件: {filters}")
            
            result = self.client.update(table, data, filters)
            
            self.logger.info(f"更新成功: {table}")
            return result
            
        except Exception as e:
            self.logger.error(f"更新失敗: {table}, 錯誤: {e}")
            raise self.error_handler.handle_rpc_error(e)
    
    def delete_record(self, table: str, filters: Dict[str, Any]) -> List[Dict]:
        """刪除記錄"""
        try:
            self.logger.info(f"刪除記錄: {table}")
            self.logger.debug(f"刪除條件: {filters}")
            
            result = self.client.delete(table, filters)
            
            self.logger.info(f"刪除成功: {table}")
            return result
            
        except Exception as e:
            self.logger.error(f"刪除失敗: {table}, 錯誤: {e}")
            raise self.error_handler.handle_rpc_error(e)
    
    def count_records(self, table: str, filters: Optional[Dict] = None) -> int:
        """統計記錄數量"""
        try:
            query = self.client.query(table).select("id", count="exact")
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            result = query.execute()
            return getattr(result, "count", 0) or 0
            
        except Exception as e:
            self.logger.error(f"統計失敗: {table}, 錯誤: {e}")
            return 0
    
    def exists_record(self, table: str, filters: Dict[str, Any]) -> bool:
        """檢查記錄是否存在"""
        try:
            records = self.query_table(table, filters, limit=1)
            return len(records) > 0
        except Exception:
            return False
    
    def get_single_record(self, table: str, filters: Dict[str, Any]) -> Optional[Dict]:
        """獲取單條記錄"""
        try:
            records = self.query_table(table, filters, limit=1)
            return records[0] if records else None
        except Exception as e:
            self.logger.error(f"獲取單條記錄失敗: {table}, 錯誤: {e}")
            return None
    
    def validate_uuid(self, uuid_str: str) -> bool:
        """驗證 UUID 格式"""
        from utils.validators import Validator
        return Validator.validate_card_id(uuid_str)  # UUID 格式相同
    
    def validate_required_params(self, params: Dict[str, Any], 
                                required_keys: List[str]) -> List[str]:
        """驗證必需參數"""
        errors = []
        for key in required_keys:
            if key not in params or params[key] is None:
                errors.append(f"缺少必需參數: {key}")
        return errors
    
    def log_operation(self, operation: str, details: Dict[str, Any] = None):
        """記錄操作"""
        message = f"執行操作: {operation}"
        if details:
            message += f" - 詳情: {details}"
        self.logger.info(message)
    
    def handle_service_error(self, operation: str, error: Exception, 
                           context: Dict[str, Any] = None) -> Exception:
        """處理服務錯誤"""
        self.logger.error(f"服務操作失敗: {operation}, 錯誤: {error}")
        
        if context:
            return Exception(self.error_handler.handle_with_context(error, context))
        else:
            return self.error_handler.handle_rpc_error(error)
    
    def set_auth_service(self, auth_service):
        """設定認證服務"""
        self.auth_service = auth_service
    
    def require_role(self, required_role: str):
        """要求特定角色權限"""
        if not self.auth_service:
            raise Exception("AUTH_SERVICE_NOT_INITIALIZED")
        
        if not self.auth_service.check_permission(required_role):
            raise Exception(f"PERMISSION_DENIED: {required_role} role required")
    
    def get_current_user_id(self) -> Optional[str]:
        """取得當前用戶 ID"""
        if not self.auth_service or not self.auth_service.current_user:
            return None
        
        role = self.auth_service.current_role
        user = self.auth_service.current_user
        
        if role in ["admin", "super_admin"]:
            return user.get("id")
        elif role == "merchant":
            return user.get("merchant_id")
        elif role == "member":
            return user.get("member_id")
        
        return None

class QueryService(BaseService):
    """查詢服務基類"""
    
    def get_paginated_data(self, table: str, page: int = 0, page_size: int = 20,
                          filters: Optional[Dict] = None,
                          order_by: Optional[str] = None) -> Dict[str, Any]:
        """獲取分頁數據"""
        offset = page * page_size
        
        # 獲取總數
        total_count = self.count_records(table, filters)
        
        # 獲取數據
        data = self.query_table(table, filters, page_size, offset, order_by)
        
        # 計算分頁信息
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "data": data,
            "pagination": {
                "current_page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages - 1,
                "has_prev": page > 0
            }
        }
    
    def search_records(self, table: str, search_fields: List[str],
                      keyword: str, limit: int = 50) -> List[Dict]:
        """搜索記錄"""
        if not keyword:
            return []
        
        try:
            # 這裡簡化實現，實際可能需要使用全文搜索
            # 目前使用 ilike 進行模糊搜索
            query = self.client.query(table).select("*")
            
            # 對每個搜索字段進行 OR 查詢
            for i, field in enumerate(search_fields):
                if i == 0:
                    query = query.ilike(field, f"%{keyword}%")
                else:
                    query = query.or_(f"{field}.ilike.%{keyword}%")
            
            if limit:
                query = query.limit(limit)
            
            result = query.execute()
            return getattr(result, "data", [])
            
        except Exception as e:
            self.logger.error(f"搜索失敗: {table}, 錯誤: {e}")
            return []

class CacheService:
    """緩存服務"""
    
    def __init__(self):
        self._cache = {}
        self.logger = get_logger(self.__class__.__name__)
    
    def get(self, key: str) -> Any:
        """獲取緩存"""
        return self._cache.get(key)
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """設置緩存"""
        import time
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl
        }
    
    def is_expired(self, key: str) -> bool:
        """檢查是否過期"""
        import time
        if key not in self._cache:
            return True
        
        return time.time() > self._cache[key]["expires_at"]
    
    def clear_expired(self):
        """清理過期緩存"""
        import time
        current_time = time.time()
        
        expired_keys = [
            key for key, data in self._cache.items()
            if current_time > data["expires_at"]
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            self.logger.debug(f"清理了 {len(expired_keys)} 個過期緩存")
    
    def clear_all(self):
        """清理所有緩存"""
        self._cache.clear()
        self.logger.debug("清理了所有緩存")

# 全局緩存服務實例
cache_service = CacheService()