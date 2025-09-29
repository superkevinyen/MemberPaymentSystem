from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Type, TypeVar
from datetime import datetime

T = TypeVar('T', bound='BaseModel')

@dataclass
class BaseModel:
    """基礎模型類"""
    
    id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """從字典創建模型實例"""
        if not data:
            return cls()
        
        # 獲取類的字段
        field_names = {field.name for field in cls.__dataclass_fields__.values()}
        
        # 過濾出有效字段
        filtered_data = {k: v for k, v in data.items() if k in field_names}
        
        return cls(**filtered_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return asdict(self)
    
    def update_from_dict(self, data: Dict[str, Any]):
        """從字典更新模型"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def is_valid(self) -> bool:
        """檢查模型是否有效"""
        return self.id is not None
    
    def get_display_name(self) -> str:
        """獲取顯示名稱"""
        if hasattr(self, 'name') and self.name:
            return self.name
        elif hasattr(self, 'title') and self.title:
            return self.title
        elif self.id:
            return f"ID: {self.id[:8]}..."
        else:
            return "未知"
    
    def format_datetime(self, field_name: str) -> str:
        """格式化日期時間字段"""
        value = getattr(self, field_name, None)
        if not value:
            return ""
        
        if isinstance(value, str):
            try:
                if value.endswith('Z'):
                    value = value[:-1] + '+00:00'
                dt = datetime.fromisoformat(value)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                return value
        
        return str(value)
    
    def format_date(self, field_name: str) -> str:
        """格式化日期字段"""
        value = getattr(self, field_name, None)
        if not value:
            return ""
        
        if isinstance(value, str):
            try:
                if value.endswith('Z'):
                    value = value[:-1] + '+00:00'
                dt = datetime.fromisoformat(value)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                return value
        
        return str(value)
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}({self.get_display_name()})"
    
    def __repr__(self) -> str:
        """詳細字符串表示"""
        return f"{self.__class__.__name__}(id={self.id})"

@dataclass
class TimestampMixin:
    """時間戳混入類"""
    
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def get_created_datetime(self) -> Optional[datetime]:
        """獲取創建時間"""
        if not self.created_at:
            return None
        
        try:
            if self.created_at.endswith('Z'):
                time_str = self.created_at[:-1] + '+00:00'
            else:
                time_str = self.created_at
            return datetime.fromisoformat(time_str)
        except ValueError:
            return None
    
    def get_updated_datetime(self) -> Optional[datetime]:
        """獲取更新時間"""
        if not self.updated_at:
            return None
        
        try:
            if self.updated_at.endswith('Z'):
                time_str = self.updated_at[:-1] + '+00:00'
            else:
                time_str = self.updated_at
            return datetime.fromisoformat(time_str)
        except ValueError:
            return None
    
    def is_recent(self, hours: int = 24) -> bool:
        """檢查是否是最近創建的"""
        created = self.get_created_datetime()
        if not created:
            return False
        
        from datetime import timedelta
        now = datetime.now(created.tzinfo)
        return (now - created) <= timedelta(hours=hours)

@dataclass
class StatusMixin:
    """狀態混入類"""
    
    status: Optional[str] = None
    
    def is_active(self) -> bool:
        """檢查是否激活"""
        return self.status == "active"
    
    def is_inactive(self) -> bool:
        """檢查是否未激活"""
        return self.status == "inactive"
    
    def is_suspended(self) -> bool:
        """檢查是否暫停"""
        return self.status == "suspended"
    
    def get_status_display(self, status_map: Dict[str, str]) -> str:
        """獲取狀態顯示名稱"""
        return status_map.get(self.status, self.status or "未知")

class ModelValidator:
    """模型驗證器"""
    
    @staticmethod
    def validate_required_fields(model: BaseModel, required_fields: List[str]) -> List[str]:
        """驗證必填字段"""
        errors = []
        for field in required_fields:
            value = getattr(model, field, None)
            if not value:
                errors.append(f"{field} 為必填項")
        return errors
    
    @staticmethod
    def validate_field_types(model: BaseModel, field_types: Dict[str, type]) -> List[str]:
        """驗證字段類型"""
        errors = []
        for field, expected_type in field_types.items():
            value = getattr(model, field, None)
            if value is not None and not isinstance(value, expected_type):
                errors.append(f"{field} 類型錯誤，期望 {expected_type.__name__}")
        return errors

class ModelFactory:
    """模型工廠"""
    
    @staticmethod
    def create_from_db_row(model_class: Type[T], row: Dict[str, Any]) -> T:
        """從數據庫行創建模型"""
        return model_class.from_dict(row)
    
    @staticmethod
    def create_list_from_db_rows(model_class: Type[T], rows: List[Dict[str, Any]]) -> List[T]:
        """從數據庫行列表創建模型列表"""
        return [model_class.from_dict(row) for row in rows]