export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  public: {
    Tables: {
      [_ in never]: never
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      admin_create_member: {
        Args: {
          p_name: string
          p_email: string
          p_phone: string
          p_password: string
        }
        Returns: string
      }
      admin_create_user: {
        Args: {
          p_email: string
          p_password: string
          p_name: string
          p_phone: string
        }
        Returns: string
      }
      admin_create_enterprise_and_card: {
        Args: {
          p_company_name: string
          p_password: string
          p_initial_balance?: number
          p_fixed_discount?: number
        }
        Returns: string
      }
      admin_update_enterprise_card_details: {
        Args: {
          p_card_id: string
          p_company_name: string
          p_fixed_discount: number
        }
        Returns: boolean
      }
      admin_update_enterprise_card_status: {
        Args: {
          p_card_id: string
          p_status: Database["public"]["Enums"]["card_status"]
        }
        Returns: boolean
      }
      admin_update_member_profile: {
        Args: {
          p_member_id: string
          p_name: string
          p_phone: string
        }
        Returns: boolean
      }
      get_all_member_profiles: {
        Args: Record<PropertyKey, never>
        Returns: {
          id: string
          member_no: string
          name: string
          phone: string
          email: string
          password_hash: string
          status: Database["public"]["Enums"]["member_status"]
          created_at: string
          updated_at: string
        }[]
      }
      get_all_enterprises_for_admin: {
        Args: Record<PropertyKey, never>
        Returns: {
          id: string
          company_name: string
          card_id: string
          card_no: string
          balance: number
          fixed_discount: number
          card_status: Database["public"]["Enums"]["card_status"]
          created_at: string
        }[]
      }
      admin_update_user_metadata: {
        Args: {
          p_user_id: string
          p_metadata: Json
        }
        Returns: boolean
      }
      admin_update_member_status: {
        Args: {
          p_member_id: string
          p_status: Database["public"]["Enums"]["member_status"]
        }
        Returns: boolean
      }
      merchant_charge_by_qr: {
        Args: {
          p_merchant_code: string
          p_qr_plain: string
          p_raw_price: number
          p_reason?: string
          p_tag?: Json
          p_idempotency_key?: string
          p_external_order_id?: string
        }
        Returns: {
          tx_id: string
          tx_no: string
          card_type: Database["public"]["Enums"]["card_type"]
          card_id: string
          final_amount: number
          discount: number
        }[]
      }
      merchant_refund_tx: {
        Args: {
          p_merchant_code: string
          p_original_tx_no: string
          p_refund_amount: number
          p_reason?: string
          p_tag?: Json
        }
        Returns: {
          refund_tx_id: string
          refund_tx_no: string
          refunded_amount: number
        }[]
      }
      get_transactions: {
        Args: {
          p_limit?: number
          p_offset?: number
          p_start_date?: string
          p_end_date?: string
        }
        Returns: {
          id: string
          tx_no: string
          card_type: Database["public"]["Enums"]["card_type"]
          card_id: string
          merchant_id: string
          tx_type: Database["public"]["Enums"]["tx_type"]
          final_amount: number
          status: Database["public"]["Enums"]["tx_status"]
          created_at: string
          total_count: number
        }[]
      }
      get_user_cards: {
        Args: Record<PropertyKey, never>
        Returns: {
          card_id: string
          card_type: Database["public"]["Enums"]["card_type"]
          card_no: string
          balance: number
          level: number | null
          discount: number
          status: Database["public"]["Enums"]["card_status"]
          created_at: string
          updated_at: string
        }[]
      }
      authenticate_by_member_no: {
        Args: {
          p_member_no: string
        }
        Returns: {
          email: string
          user_id: string
        }[]
      }
      authenticate_by_phone: {
        Args: {
          p_phone: string
        }
        Returns: {
          email: string
          user_id: string
        }[]
      }
      is_admin: {
        Args: Record<PropertyKey, never>
        Returns: boolean
      }
      get_user_type: {
        Args: Record<PropertyKey, never>
        Returns: string
      }
      admin_create_merchant: {
        Args: {
          p_code: string
          p_name: string
          p_description?: string
        }
        Returns: string
      }
      admin_update_merchant: {
        Args: {
          p_merchant_id: string
          p_name: string
          p_description?: string
          p_active?: boolean
        }
        Returns: boolean
      }
      admin_get_merchants: {
        Args: Record<PropertyKey, never>
        Returns: {
          id: string
          code: string
          name: string
          description: string
          active: boolean
          created_at: string
          updated_at: string
        }[]
      }
      admin_add_merchant_user: {
        Args: {
          p_merchant_id: string
          p_user_id: string
        }
        Returns: boolean
      }
      admin_remove_merchant_user: {
        Args: {
          p_merchant_id: string
          p_user_id: string
        }
        Returns: boolean
      }
      admin_adjust_personal_card_balance: {
        Args: {
          p_card_id: string
          p_amount: number
          p_reason?: string
        }
        Returns: boolean
      }
      admin_adjust_personal_card_points: {
        Args: {
          p_card_id: string
          p_points: number
          p_reason?: string
        }
        Returns: boolean
      }
      admin_update_personal_card_status: {
        Args: {
          p_card_id: string
          p_status: Database["public"]["Enums"]["card_status"]
        }
        Returns: boolean
      }
      admin_create_membership_level: {
        Args: {
          p_level: number
          p_name: string
          p_min_points: number
          p_max_points?: number
          p_discount?: number
        }
        Returns: string
      }
      admin_update_membership_level: {
        Args: {
          p_level_id: string
          p_name: string
          p_min_points: number
          p_max_points?: number
          p_discount?: number
          p_is_active?: boolean
        }
        Returns: boolean
      }
      admin_get_membership_levels: {
        Args: Record<PropertyKey, never>
        Returns: {
          id: string
          level: number
          name: string
          min_points: number
          max_points: number | null
          discount: number
          is_active: boolean
          created_at: string
        }[]
      }
      user_update_profile: {
        Args: {
          p_name: string
          p_phone: string
        }
        Returns: boolean
      }
      enterprise_get_bound_members: {
        Args: {
          p_card_no: string
        }
        Returns: {
          member_id: string
          member_no: string
          name: string
          phone: string
          role: Database["public"]["Enums"]["bind_role"]
          created_at: string
        }[]
      }
      enterprise_update_card_password: {
        Args: {
          p_card_no: string
          p_old_password: string
          p_new_password: string
        }
        Returns: boolean
      }
      user_recharge_personal_card: {
        Args: {
          p_personal_card_id: string
          p_amount: number
          p_payment_method?: Database["public"]["Enums"]["pay_method"]
          p_reason?: string
          p_tag?: Json
          p_idempotency_key?: string
          p_external_order_id?: string
        }
        Returns: {
          tx_id: string
          tx_no: string
          card_id: string
          amount: number
        }[]
      }
      user_recharge_enterprise_card_admin: {
        Args: {
          p_enterprise_card_id: string
          p_amount: number
          p_payment_method?: Database["public"]["Enums"]["pay_method"]
          p_reason?: string
          p_tag?: Json
          p_idempotency_key?: string
          p_external_order_id?: string
        }
        Returns: {
          tx_id: string
          tx_no: string
          card_id: string
          amount: number
        }[]
      }
      rotate_card_qr: {
        Args: {
          p_card_id: string
          p_card_type: Database["public"]["Enums"]["card_type"]
        }
        Returns: {
          qr_plain: string
          qr_expires_at: string
        }[]
      }
      enterprise_set_initial_admin: {
        Args: {
          p_card_no: string
          p_member_no: string
        }
        Returns: boolean
      }
      enterprise_add_member: {
        Args: {
          p_card_no: string
          p_member_no: string
          p_card_password: string
        }
        Returns: boolean
      }
      enterprise_remove_member: {
        Args: {
          p_card_no: string
          p_member_no: string
        }
        Returns: boolean
      }
    }
    Enums: {
      card_type: "personal" | "enterprise"
      tx_type: "payment" | "refund" | "recharge"
      tx_status: "processing" | "completed" | "failed" | "cancelled" | "refunded"
      pay_method: "balance" | "cash" | "wechat" | "alipay"
      bind_role: "admin" | "member"
      member_status: "active" | "inactive" | "suspended" | "deleted"
      card_status: "active" | "inactive" | "lost" | "expired"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type PublicSchema = Database[keyof Database & "public"]

export type Tables<
  PublicTableNameOrOptions extends
    | keyof (PublicSchema["Tables"] & PublicSchema["Views"])
    | { schema: keyof Database },
  TableName extends PublicTableNameOrOptions extends { schema: keyof Database }
    ? keyof (Database[PublicTableNameOrOptions["schema"]]["Tables"] &
        Database[PublicTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = PublicTableNameOrOptions extends { schema: keyof Database }
  ? (Database[PublicTableNameOrOptions["schema"]]["Tables"] &
      Database[PublicTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : PublicTableNameOrOptions extends keyof (PublicSchema["Tables"] &
        PublicSchema["Views"])
    ? (PublicSchema["Tables"] &
        PublicSchema["Views"])[PublicTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  PublicTableNameOrOptions extends
    | keyof PublicSchema["Tables"]
    | { schema: keyof Database },
  TableName extends PublicTableNameOrOptions extends { schema: keyof Database }
    ? keyof Database[PublicTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = PublicTableNameOrOptions extends { schema: keyof Database }
  ? Database[PublicTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : PublicTableNameOrOptions extends keyof PublicSchema["Tables"]
    ? PublicSchema["Tables"][PublicTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  PublicTableNameOrOptions extends
    | keyof PublicSchema["Tables"]
    | { schema: keyof Database },
  TableName extends PublicTableNameOrOptions extends { schema: keyof Database }
    ? keyof Database[PublicTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = PublicTableNameOrOptions extends { schema: keyof Database }
  ? Database[PublicTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : PublicTableNameOrOptions extends keyof PublicSchema["Tables"]
    ? PublicSchema["Tables"][PublicTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  PublicEnumNameOrOptions extends
    | keyof PublicSchema["Enums"]
    | { schema: keyof Database },
  EnumName extends PublicEnumNameOrOptions extends { schema: keyof Database }
    ? keyof Database[PublicEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = PublicEnumNameOrOptions extends { schema: keyof Database }
  ? Database[PublicEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : PublicEnumNameOrOptions extends keyof PublicSchema["Enums"]
    ? PublicSchema["Enums"][PublicEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof PublicSchema["CompositeTypes"]
    | { schema: keyof Database },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends { schema: keyof Database }
  ? Database[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof PublicSchema["CompositeTypes"]
    ? PublicSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never
