import sys
import os
from typing import Dict, Any, List, Optional, Callable
import getpass

# 添加項目根目錄到路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.validators import Validator
from utils.formatters import Formatter

class FormField:
    """表單字段"""
    
    def __init__(self, name: str, label: str, field_type: str = "text",
                 required: bool = True, validator: Optional[Callable] = None,
                 options: Optional[List[str]] = None, default: Any = None,
                 help_text: Optional[str] = None):
        self.name = name
        self.label = label
        self.field_type = field_type
        self.required = required
        self.validator = validator
        self.options = options
        self.default = default
        self.help_text = help_text

class Form:
    """表單組件"""
    
    def __init__(self, title: str, fields: List[FormField]):
        self.title = title
        self.fields = fields
        self.validator = Validator()
    
    def display_and_collect(self) -> Dict[str, Any]:
        """顯示表單並收集數據"""
        print("┌" + "─" * (len(self.title) + 4) + "┐")
        print(f"│  {self.title}  │")
        print("└" + "─" * (len(self.title) + 4) + "┘")
        
        data = {}
        
        for field in self.fields:
            while True:
                value = self._get_field_value(field)
                
                # 檢查必填項
                if field.required and not value:
                    print(f"✗ {field.label} 為必填項")
                    continue
                
                # 如果有值，進行驗證
                if value and field.validator:
                    if not field.validator(value):
                        print(f"✗ {field.label} 格式不正確")
                        if field.help_text:
                            print(f"▸ {field.help_text}")
                        continue
                
                data[field.name] = value
                break
        
        return data
    
    def _get_field_value(self, field: FormField) -> Any:
        """獲取字段值"""
        # 顯示標籤和幫助信息
        prompt = field.label
        if field.default is not None:
            prompt += f" (默認: {field.default})"
        if not field.required:
            prompt += " (可選)"
        prompt += ": "
        
        if field.help_text:
            print(f"▸ {field.help_text}")
        
        if field.field_type == "select":
            return self._get_select_value(field)
        elif field.field_type == "number":
            return self._get_number_value(field)
        elif field.field_type == "decimal":
            return self._get_decimal_value(field)
        elif field.field_type == "password":
            return getpass.getpass(prompt)
        elif field.field_type == "boolean":
            return self._get_boolean_value(field)
        elif field.field_type == "date":
            return self._get_date_value(field)
        else:
            return input(prompt) or field.default
    
    def _get_select_value(self, field: FormField) -> str:
        """獲取選擇項值"""
        if not field.options:
            return input(f"{field.label}: ") or field.default
        
        print(f"\n{field.label}:")
        for i, option in enumerate(field.options, 1):
            print(f"  {i}. {option}")
        
        while True:
            try:
                choice_input = input("請選擇: ").strip()
                if not choice_input and field.default is not None:
                    return field.default
                
                choice = int(choice_input)
                if 1 <= choice <= len(field.options):
                    return field.options[choice - 1]
                print(f"✗ 請選擇 1-{len(field.options)}")
            except ValueError:
                print("✗ 請輸入有效數字")
    
    def _get_number_value(self, field: FormField) -> Optional[int]:
        """獲取數字值"""
        while True:
            try:
                value = input(f"{field.label}: ").strip()
                if not value:
                    if not field.required:
                        return field.default
                    continue
                return int(value)
            except ValueError:
                print("✗ 請輸入有效的整數")
    
    def _get_decimal_value(self, field: FormField) -> Optional[float]:
        """獲取小數值"""
        while True:
            try:
                value = input(f"{field.label}: ").strip()
                if not value:
                    if not field.required:
                        return field.default
                    continue
                return float(value)
            except ValueError:
                print("✗ 請輸入有效的數字")
    
    def _get_boolean_value(self, field: FormField) -> bool:
        """獲取布爾值"""
        while True:
            value = input(f"{field.label} (y/n): ").strip().lower()
            if not value and field.default is not None:
                return field.default
            
            if value in ['y', 'yes', '是', '1', 'true']:
                return True
            elif value in ['n', 'no', '否', '0', 'false']:
                return False
            else:
                print("✗ 請輸入 y/n")
    
    def _get_date_value(self, field: FormField) -> Optional[str]:
        """獲取日期值"""
        while True:
            value = input(f"{field.label} (YYYY-MM-DD): ").strip()
            if not value:
                if not field.required:
                    return field.default
                continue
            
            if self.validator.validate_date_string(value):
                return value
            else:
                print("✗ 請輸入有效的日期格式 (YYYY-MM-DD)")

class QuickForm:
    """快速表單組件"""
    
    @staticmethod
    def get_amount(prompt: str = "請輸入金額", min_amount: float = 0.01, 
                   max_amount: float = 50000) -> float:
        """獲取金額輸入"""
        while True:
            try:
                amount_str = input(f"{prompt} (¥{min_amount:.2f} - ¥{max_amount:.2f}): ¥").strip()
                if not amount_str:
                    continue
                
                amount = float(amount_str)
                
                if amount < min_amount:
                    print(f"✗ 金額不能小於 ¥{min_amount:.2f}")
                    continue
                if amount > max_amount:
                    print(f"✗ 金額不能超過 ¥{max_amount:.2f}")
                    continue
                
                return amount
                
            except ValueError:
                print("✗ 請輸入有效的數字")
            except KeyboardInterrupt:
                raise
    
    @staticmethod
    def get_qr_input(prompt: str = "請輸入 QR 碼") -> str:
        """QR 碼輸入驗證"""
        while True:
            qr_code = input(f"{prompt}: ").strip()
            
            if not qr_code:
                print("✗ QR 碼不能為空")
                continue
            
            if len(qr_code) < 16:
                print("✗ QR 碼格式不正確（長度不足）")
                continue
            
            return qr_code
    
    @staticmethod
    def get_confirmation(message: str, default: bool = False) -> bool:
        """獲取確認輸入"""
        default_text = "Y/n" if default else "y/N"
        response = input(f"{message} ({default_text}): ").strip().lower()
        
        if not response:
            return default
        
        return response in ['y', 'yes', '是', '確認']
    
    @staticmethod
    def get_choice(prompt: str, choices: List[str], default: Optional[int] = None) -> int:
        """獲取選擇"""
        print(f"\n{prompt}:")
        for i, choice in enumerate(choices, 1):
            print(f"  {i}. {choice}")
        
        while True:
            try:
                choice_input = input("請選擇: ").strip()
                if not choice_input and default is not None:
                    return default
                
                choice = int(choice_input)
                if 1 <= choice <= len(choices):
                    return choice
                print(f"✗ 請選擇 1-{len(choices)}")
            except ValueError:
                print("✗ 請輸入有效數字")
    
    @staticmethod
    def get_text(prompt: str, required: bool = True, 
                 validator: Optional[Callable] = None,
                 help_text: Optional[str] = None) -> str:
        """獲取文本輸入"""
        if help_text:
            print(f"▸ {help_text}")
        
        while True:
            value = input(f"{prompt}: ").strip()
            
            if required and not value:
                print("✗ 此項為必填")
                continue
            
            if value and validator and not validator(value):
                print("✗ 輸入格式不正確")
                if help_text:
                    print(f"▸ {help_text}")
                continue
            
            return value

class WizardForm:
    """嚮導式表單"""
    
    def __init__(self, title: str, steps: List[Dict[str, Any]]):
        self.title = title
        self.steps = steps
        self.current_step = 0
        self.data = {}
    
    def run(self) -> Dict[str, Any]:
        """運行嚮導"""
        print(f"\n🧙‍♂️ {self.title}")
        print("=" * 50)
        
        while self.current_step < len(self.steps):
            step = self.steps[self.current_step]
            
            print(f"\n步驟 {self.current_step + 1}/{len(self.steps)}: {step['title']}")
            print("-" * 30)
            
            if 'description' in step:
                print(f"📝 {step['description']}")
            
            # 處理步驟字段
            step_data = {}
            for field in step['fields']:
                if isinstance(field, FormField):
                    form = Form("", [field])
                    field_data = form.display_and_collect()
                    step_data.update(field_data)
                else:
                    # 簡單字段定義
                    value = QuickForm.get_text(
                        field.get('prompt', field['name']),
                        field.get('required', True),
                        field.get('validator'),
                        field.get('help_text')
                    )
                    step_data[field['name']] = value
            
            self.data.update(step_data)
            
            # 確認當前步驟
            if self.current_step < len(self.steps) - 1:
                if not QuickForm.get_confirmation("繼續下一步？", True):
                    if self.current_step > 0:
                        if QuickForm.get_confirmation("返回上一步？", False):
                            self.current_step -= 1
                            continue
                    else:
                        break
            
            self.current_step += 1
        
        if self.current_step >= len(self.steps):
            print("\n▸ 嚮導完成！")
            self._show_summary()
        
        return self.data
    
    def _show_summary(self):
        """顯示摘要"""
        print("\n📋 輸入摘要:")
        print("-" * 30)
        for key, value in self.data.items():
            print(f"{key}: {value}")
        print("-" * 30)

class ValidationForm:
    """帶驗證的表單"""
    
    @staticmethod
    def create_member_form() -> Dict[str, Any]:
        """創建會員表單"""
        fields = [
            FormField("name", "會員姓名", "text", True, 
                     Validator.validate_name, help_text="2-50位中文或英文字符"),
            FormField("phone", "手機號碼", "text", True, 
                     Validator.validate_phone, help_text="11位中國大陸手機號"),
            FormField("email", "電子郵件", "text", True, 
                     Validator.validate_email, help_text="有效的郵箱地址"),
            FormField("bind_external", "是否綁定外部身份", "boolean", False, default=False),
        ]
        
        form = Form("創建新會員", fields)
        data = form.display_and_collect()
        
        # 如果選擇綁定外部身份，收集額外信息
        if data.get("bind_external"):
            external_fields = [
                FormField("provider", "外部平台", "select", True, 
                         options=["wechat", "alipay", "line"]),
                FormField("external_id", "外部用戶 ID", "text", True, 
                         Validator.validate_external_id, help_text="3-100位字符")
            ]
            
            external_form = Form("外部身份綁定", external_fields)
            external_data = external_form.display_and_collect()
            data.update(external_data)
        
        return data
    
    @staticmethod
    def create_recharge_form() -> Dict[str, Any]:
        """創建充值表單"""
        fields = [
            FormField("amount", "充值金額", "decimal", True, 
                     Validator.validate_amount, help_text="0.01-999999.99"),
            FormField("payment_method", "支付方式", "select", True,
                     options=["wechat", "alipay", "bank"], default="wechat")
        ]
        
        form = Form("卡片充值", fields)
        return form.display_and_collect()