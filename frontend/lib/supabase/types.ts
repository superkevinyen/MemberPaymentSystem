// lib/supabase/types.ts
export type CardType = 'personal' | 'enterprise';

export interface MerchantChargeResult {
  tx_id: string;
  tx_no: string;
  card_type: CardType;
  card_id: string;
  final_amount: number;
  discount: number;
}
