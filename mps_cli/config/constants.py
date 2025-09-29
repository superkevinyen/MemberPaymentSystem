# MPS CLI 常量定義

# 卡片類型
CARD_TYPES = {
    'standard': '標準卡',
    'prepaid': '預付卡',
    'corporate': '企業卡',
    'voucher': '優惠券卡'
}

# 卡片狀態
CARD_STATUS = {
    'active': '激活',
    'inactive': '未激活',
    'lost': '掛失',
    'expired': '過期',
    'suspended': '暫停',
    'closed': '關閉'
}

# 交易類型
TRANSACTION_TYPES = {
    'payment': '支付',
    'refund': '退款',
    'recharge': '充值'
}

# 交易狀態
TRANSACTION_STATUS = {
    'processing': '處理中',
    'completed': '已完成',
    'failed': '失敗',
    'cancelled': '已取消',
    'refunded': '已退款'
}

# 支付方式
PAYMENT_METHODS = {
    'balance': '餘額',
    'cash': '現金',
    'wechat': '微信',
    'alipay': '支付寶'
}

# 綁定角色
BIND_ROLES = {
    'owner': '擁有者',
    'admin': '管理員',
    'member': '成員',
    'viewer': '查看者'
}

# 會員狀態
MEMBER_STATUS = {
    'active': '激活',
    'inactive': '未激活',
    'suspended': '暫停',
    'deleted': '已刪除'
}

# 結算模式
SETTLEMENT_MODES = {
    'realtime': '實時結算',
    't_plus_1': 'T+1結算',
    'monthly': '月結算'
}

# 錯誤碼對應的中文提示
ERROR_MESSAGES = {
    "INSUFFICIENT_BALANCE": "餘額不足，請充值後再試",
    "QR_EXPIRED_OR_INVALID": "QR 碼已過期或無效，請重新生成",
    "MERCHANT_NOT_FOUND_OR_INACTIVE": "商戶不存在或已停用",
    "NOT_MERCHANT_USER": "您沒有此商戶的操作權限",
    "CARD_NOT_FOUND_OR_INACTIVE": "卡片不存在或未激活",
    "EXTERNAL_ID_ALREADY_BOUND": "外部身份已被其他會員綁定",
    "INVALID_BINDING_PASSWORD": "綁定密碼錯誤",
    "REFUND_EXCEEDS_REMAINING": "退款金額超過可退金額",
    "CARD_TYPE_NOT_SHAREABLE": "此類型卡片不支持共享",
    "CANNOT_REMOVE_LAST_OWNER": "不能移除最後一個擁有者",
    "UNSUPPORTED_CARD_TYPE_FOR_RECHARGE": "此卡片類型不支持充值",
    "ONLY_COMPLETED_PAYMENT_REFUNDABLE": "只能退款已完成的支付交易",
    "INVALID_PRICE": "無效的金額",
    "CARD_NOT_ACTIVE": "卡片未激活",
    "CARD_EXPIRED": "卡片已過期",
    "INVALID_QR": "無效的 QR 碼",
    "INVALID_REFUND_AMOUNT": "無效的退款金額",
    "ORIGINAL_TX_NOT_FOUND": "找不到原交易",
    "INVALID_RECHARGE_AMOUNT": "無效的充值金額",
    "UNSUPPORTED_CARD_TYPE_FOR_PAYMENT": "此卡片類型不支持支付",
    "UNSUPPORTED_CARD_TYPE_FOR_POINTS": "此卡片類型不支持積分",
    "TX_NOT_FOUND": "交易不存在"
}

# UI 相關常量
UI_CONSTANTS = {
    "BORDER_CHAR": "─",
    "CORNER_CHAR": "┌┐└┘",
    "VERTICAL_CHAR": "│",
    "CROSS_CHAR": "┼",
    "T_CHAR": "├┤┬┴",
    "DEFAULT_WIDTH": 40,
    "MAX_TABLE_WIDTH": 80
}

# 會員等級配置
MEMBERSHIP_LEVELS = {
    0: {"name": "普通會員", "min_points": 0, "max_points": 999, "discount": 1.000},
    1: {"name": "銀卡會員", "min_points": 1000, "max_points": 4999, "discount": 0.950},
    2: {"name": "金卡會員", "min_points": 5000, "max_points": 9999, "discount": 0.900},
    3: {"name": "鑽石會員", "min_points": 10000, "max_points": None, "discount": 0.850}
}