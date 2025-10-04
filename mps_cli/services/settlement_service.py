from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
from .base_service import BaseService
from models.settlement import Settlement

class SettlementService(BaseService):
    """結算服務"""
    
    def generate_settlement(
        self,
        merchant_id: str,
        mode: str,
        period_start: str,
        period_end: str
    ) -> Dict:
        """
        生成結算報表
        
        Args:
            merchant_id: 商戶 ID
            mode: 結算模式 (realtime/t_plus_1/monthly)
            period_start: 期間開始時間
            period_end: 期間結束時間
            
        Returns:
            結算結果字典
        """
        self.log_operation("生成結算", {
            "merchant_id": merchant_id,
            "mode": mode,
            "period": f"{period_start} ~ {period_end}"
        })
        
        params = {
            "p_merchant_id": merchant_id,
            "p_mode": mode,
            "p_period_start": period_start,
            "p_period_end": period_end
        }
        
        try:
            result = self.rpc_call("generate_settlement", params)
            
            if result and len(result) > 0:
                settlement_data = result[0]
                self.logger.info(f"結算生成成功: {settlement_data.get('settlement_no')}")
                return settlement_data
            else:
                raise Exception("結算生成失敗：無返回數據")
                
        except Exception as e:
            self.logger.error(f"結算生成失敗: {e}")
            raise self.handle_service_error("生成結算", e, params)
    
    def list_settlements(
        self,
        merchant_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict:
        """
        查詢結算列表
        
        Args:
            merchant_id: 商戶 ID
            limit: 每頁數量
            offset: 偏移量
            
        Returns:
            結算列表和分頁信息
        """
        self.log_operation("查詢結算列表", {
            "merchant_id": merchant_id,
            "limit": limit,
            "offset": offset
        })
        
        params = {
            "p_merchant_id": merchant_id,
            "p_limit": limit,
            "p_offset": offset
        }
        
        try:
            result = self.rpc_call("list_settlements", params)
            
            settlements = []
            for item in result:
                settlement = Settlement(
                    id=item.get('id'),
                    settlement_no=item.get('settlement_no'),
                    merchant_id=item.get('merchant_id'),
                    settlement_mode=item.get('settlement_mode'),
                    period_start=item.get('period_start'),
                    period_end=item.get('period_end'),
                    total_transactions=item.get('total_transactions'),
                    payment_count=item.get('payment_count'),
                    refund_count=item.get('refund_count'),
                    payment_amount=Decimal(str(item.get('payment_amount', 0))),
                    refund_amount=Decimal(str(item.get('refund_amount', 0))),
                    net_amount=Decimal(str(item.get('net_amount', 0))),
                    fee_amount=Decimal(str(item.get('fee_amount', 0))),
                    settlement_amount=Decimal(str(item.get('settlement_amount', 0))),
                    status=item.get('status'),
                    settled_at=item.get('settled_at'),
                    created_at=item.get('created_at')
                )
                settlements.append(settlement)
            
            return {
                "data": settlements,
                "pagination": {
                    "total": len(settlements),
                    "limit": limit,
                    "offset": offset
                }
            }
            
        except Exception as e:
            self.logger.error(f"查詢結算列表失敗: {e}")
            raise self.handle_service_error("查詢結算列表", e, params)
    
    def get_settlement_detail(self, settlement_id: str) -> Settlement:
        """
        獲取結算詳情
        
        Args:
            settlement_id: 結算 ID
            
        Returns:
            結算對象
        """
        try:
            filters = {"id": settlement_id}
            settlements = self.query_table("settlements", filters, limit=1)
            
            if settlements:
                item = settlements[0]
                return Settlement(
                    id=item.get('id'),
                    settlement_no=item.get('settlement_no'),
                    merchant_id=item.get('merchant_id'),
                    settlement_mode=item.get('settlement_mode'),
                    period_start=item.get('period_start'),
                    period_end=item.get('period_end'),
                    total_transactions=item.get('total_transactions'),
                    payment_count=item.get('payment_count'),
                    refund_count=item.get('refund_count'),
                    payment_amount=Decimal(str(item.get('payment_amount', 0))),
                    refund_amount=Decimal(str(item.get('refund_amount', 0))),
                    net_amount=Decimal(str(item.get('net_amount', 0))),
                    fee_amount=Decimal(str(item.get('fee_amount', 0))),
                    settlement_amount=Decimal(str(item.get('settlement_amount', 0))),
                    status=item.get('status'),
                    settled_at=item.get('settled_at'),
                    created_at=item.get('created_at')
                )
            else:
                raise Exception("結算不存在")
                
        except Exception as e:
            self.logger.error(f"獲取結算詳情失敗: {settlement_id}, 錯誤: {e}")
            raise
