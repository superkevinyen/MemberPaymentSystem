from supabase import create_client, Client
from typing import Any, Dict, List, Optional
import logging
from .settings import settings

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Supabase 客戶端封裝類"""
    
    def __init__(self):
        self.url = settings.database.url
        self.service_role_key = settings.database.service_role_key
        self.anon_key = settings.database.anon_key
        self.client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化 Supabase 客戶端"""
        try:
            self.client = create_client(self.url, self.service_role_key)
            logger.info("Supabase 客戶端初始化成功")
        except Exception as e:
            logger.error(f"Supabase 客戶端初始化失敗: {e}")
            raise Exception(f"無法連接到 Supabase: {e}")
    
    def rpc(self, function_name: str, params: Dict[str, Any]) -> Any:
        """調用 RPC 函數"""
        if not self.client:
            raise Exception("Supabase 客戶端未初始化")
        
        try:
            logger.debug(f"調用 RPC: {function_name}, 參數: {params}")
            response = self.client.rpc(function_name, params).execute()
            
            # 檢查響應
            if hasattr(response, 'data'):
                logger.debug(f"RPC 調用成功: {function_name}")
                return response.data
            else:
                logger.warning(f"RPC 響應格式異常: {function_name}")
                return response
                
        except Exception as e:
            logger.error(f"RPC 調用失敗: {function_name}, 錯誤: {e}")
            raise Exception(f"RPC 調用失敗: {e}")
    
    def query(self, table: str):
        """查詢表格數據"""
        if not self.client:
            raise Exception("Supabase 客戶端未初始化")
        
        try:
            return self.client.table(table)
        except Exception as e:
            logger.error(f"查詢表格失敗: {table}, 錯誤: {e}")
            raise Exception(f"查詢表格失敗: {e}")
    
    def select(self, table: str, columns: str = "*", 
               filters: Optional[Dict[str, Any]] = None,
               limit: Optional[int] = None,
               offset: Optional[int] = None) -> List[Dict]:
        """簡化的查詢方法"""
        try:
            query = self.query(table).select(columns)
            
            # 應用過濾條件
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            # 應用分頁
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            response = query.execute()
            return getattr(response, 'data', [])
            
        except Exception as e:
            logger.error(f"查詢失敗: {table}, 錯誤: {e}")
            raise Exception(f"查詢失敗: {e}")
    
    def insert(self, table: str, data: Dict[str, Any]) -> Dict:
        """插入數據"""
        try:
            response = self.query(table).insert(data).execute()
            return getattr(response, 'data', {})[0] if getattr(response, 'data', []) else {}
        except Exception as e:
            logger.error(f"插入數據失敗: {table}, 錯誤: {e}")
            raise Exception(f"插入數據失敗: {e}")
    
    def update(self, table: str, data: Dict[str, Any], 
               filters: Dict[str, Any]) -> List[Dict]:
        """更新數據"""
        try:
            query = self.query(table)
            
            # 應用過濾條件
            for key, value in filters.items():
                query = query.eq(key, value)
            
            response = query.update(data).execute()
            return getattr(response, 'data', [])
            
        except Exception as e:
            logger.error(f"更新數據失敗: {table}, 錯誤: {e}")
            raise Exception(f"更新數據失敗: {e}")
    
    def delete(self, table: str, filters: Dict[str, Any]) -> List[Dict]:
        """刪除數據"""
        try:
            query = self.query(table)
            
            # 應用過濾條件
            for key, value in filters.items():
                query = query.eq(key, value)
            
            response = query.delete().execute()
            return getattr(response, 'data', [])
            
        except Exception as e:
            logger.error(f"刪除數據失敗: {table}, 錯誤: {e}")
            raise Exception(f"刪除數據失敗: {e}")
    
    def test_connection(self) -> bool:
        """測試連接"""
        try:
            # 嘗試查詢一個簡單的表來測試連接
            self.select("member_profiles", "id", limit=1)
            logger.info("Supabase 連接測試成功")
            return True
        except Exception as e:
            logger.error(f"Supabase 連接測試失敗: {e}")
            return False

# 全局 Supabase 客戶端實例
supabase_client = SupabaseClient()