export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "13.0.5"
  }
  public: {
    Tables: {
      [_ in never]: never
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      admin_update_user_metadata: {
        Args: {
          p_user_id: string
          p_metadata: Json
        }
        Returns: boolean
      }
      adjust_member_balance: {
        Args: {
          adjustment_amount: number
          adjustment_type: string
          member_uuid: string
          reason?: string
        }
        Returns: {
          error_message: string
          new_balance: number
          success: boolean
          transaction_id: string
        }[]
      }
      calculate_member_discount: {
        Args: { member_uuid: string }
        Returns: {
          discount_rate: number
          discount_source: string
        }[]
      }
      cleanup_expired_qr_codes: {
        Args: Record<PropertyKey, never>
        Returns: number
      }
      cleanup_expired_sessions: {
        Args: Record<PropertyKey, never>
        Returns: number
      }
      cleanup_test_data: {
        Args: Record<PropertyKey, never>
        Returns: {
          deleted_companies: number
          deleted_members: number
          deleted_transactions: number
          reset_refunds: number
        }[]
      }
      company_bind_member: {
        Args: { company_uuid: string; member_uuid: string }
        Returns: {
          message: string
          success: boolean
        }[]
      }
      company_unbind_member: {
        Args: { company_uuid: string; member_uuid: string }
        Returns: {
          message: string
          success: boolean
        }[]
      }
      consume_member_balance: {
        Args: {
          consume_amount: number
          description?: string
          member_uuid: string
        }
        Returns: {
          actual_amount: number
          discount_amount: number
          error_message: string
          new_balance: number
          success: boolean
          transaction_id: string
        }[]
      }
      create_company_with_password: {
        Args: {
          company_name: string
          company_status?: string
          contact_email?: string
          contact_phone?: string
          discount_rate?: number
          plain_password?: string
        }
        Returns: {
          company_code: string
          company_id: string
          error_message: string
          success: boolean
        }[]
      }
      create_member_session: {
        Args: { login_type_input: string; member_uuid: string }
        Returns: {
          expires_at: string
          session_token: string
        }[]
      }
      create_member_with_password: {
        Args: {
          discount_rate?: number
          initial_balance?: number
          member_email?: string
          member_name: string
          member_phone?: string
          member_status?: string
          plain_password?: string
        }
        Returns: {
          error_message: string
          member_code: string
          member_id: string
          success: boolean
        }[]
      }
      freeze_member_balance: {
        Args: { freeze_amount: number; member_uuid: string; reason?: string }
        Returns: {
          available_balance: number
          error_message: string
          new_frozen_amount: number
          success: boolean
        }[]
      }
      generate_card_transaction_no: {
        Args: { transaction_type: string }
        Returns: string
      }
      generate_dynamic_qr_code: {
        Args: { card_uuid: string }
        Returns: string
      }
      generate_member_transaction_no: {
        Args: { transaction_type: string }
        Returns: string
      }
      generate_next_card_code: {
        Args: Record<PropertyKey, never>
        Returns: string
      }
      generate_next_company_code: {
        Args: Record<PropertyKey, never>
        Returns: string
      }
      generate_next_member_code: {
        Args: Record<PropertyKey, never>
        Returns: string
      }
      generate_transaction_no: {
        Args: { transaction_type: string }
        Returns: string
      }
      generate_unique_qr_code: {
        Args: Record<PropertyKey, never>
        Returns: string
      }
      get_all_enterprises_for_admin: {
        Args: Record<PropertyKey, never>
        Returns: {
          balance: number
          card_id: string
          card_no: string
          card_status: Database["public"]["Enums"]["card_status"]
          company_name: string
          created_at: string
          fixed_discount: number
          id: string
        }[]
      }
      get_all_users_for_admin: {
        Args: Record<PropertyKey, never>
        Returns: {
          created_at: string
          email: string
          id: string
          is_admin: boolean
          name: string
        }[]
      }
      get_member_refund_history: {
        Args: {
          limit_count?: number
          member_uuid: string
          offset_count?: number
        }
        Returns: {
          original_amount: number
          original_date: string
          original_transaction_no: string
          refund_amount: number
          refund_date: string
          refund_reason: string
          refund_transaction_id: string
          refund_transaction_no: string
        }[]
      }
      get_qr_code_stats: {
        Args: { end_date?: string; start_date?: string }
        Returns: {
          expired_validations: number
          failed_validations: number
          successful_validations: number
          total_generated: number
          total_validated: number
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
      is_admin: {
        Args: Record<PropertyKey, never>
        Returns: boolean
      }
      log_qr_code_usage: {
        Args: {
          action_input: string
          error_msg?: string
          ip_addr?: string
          member_uuid: string
          qr_code_input: string
          result_input?: string
          user_agent_input?: string
        }
        Returns: undefined
      }
      process_refund: {
        Args: {
          original_transaction_no: string
          refund_amount: number
          refund_reason?: string
        }
        Returns: {
          error_message: string
          new_balance: number
          refund_transaction_id: string
          refundable_remaining: number
          success: boolean
        }[]
      }
      recharge_member_balance: {
        Args: {
          description?: string
          member_uuid: string
          payment_method?: string
          recharge_amount: number
        }
        Returns: {
          error_message: string
          new_balance: number
          success: boolean
          transaction_id: string
        }[]
      }
      refresh_card_qr_code: {
        Args: { card_uuid: string }
        Returns: string
      }
      refresh_member_qr_code: {
        Args: { member_uuid: string }
        Returns: string
      }
      reset_all_test_refund_status: {
        Args: Record<PropertyKey, never>
        Returns: {
          message: string
          reset_count: number
        }[]
      }
      reset_transaction_refund_status: {
        Args: { transaction_no_input: string }
        Returns: {
          message: string
          success: boolean
        }[]
      }
      reset_weekly_password_verification: {
        Args: Record<PropertyKey, never>
        Returns: number
      }
      set_card_password: {
        Args: { card_uuid: string; new_password: string }
        Returns: boolean
      }
      set_company_password: {
        Args: { company_uuid: string; new_password: string }
        Returns: {
          error_message: string
          success: boolean
        }[]
      }
      set_member_password: {
        Args: { member_uuid: string; new_password: string }
        Returns: {
          error_message: string
          success: boolean
        }[]
      }
      unfreeze_member_balance: {
        Args: { member_uuid: string; reason?: string; unfreeze_amount: number }
        Returns: {
          available_balance: number
          error_message: string
          new_frozen_amount: number
          success: boolean
        }[]
      }
      update_company_info: {
        Args: {
          company_uuid: string
          new_discount_rate?: number
          new_email?: string
          new_name?: string
          new_phone?: string
        }
        Returns: {
          error_message: string
          success: boolean
        }[]
      }
      update_member_info: {
        Args: {
          member_uuid: string
          new_discount_rate?: number
          new_email?: string
          new_name?: string
          new_phone?: string
        }
        Returns: {
          error_message: string
          success: boolean
        }[]
      }
      validate_member_session: {
        Args: { session_token_input: string }
        Returns: {
          error_message: string
          is_valid: boolean
          login_type: string
          member_id: string
          needs_password_reauth: boolean
        }[]
      }
      validate_qr_code: {
        Args: { qr_code_input: string }
        Returns: {
          error_message: string
          expires_at: string
          is_valid: boolean
          member_code: string
          member_id: string
        }[]
      }
      validate_refund_eligibility: {
        Args: { original_transaction_no: string }
        Returns: {
          error_message: string
          is_eligible: boolean
          original_amount: number
          refundable_amount: number
          refunded_amount: number
          transaction_date: string
        }[]
      }
      verify_card_password: {
        Args: { card_code_input: string; password_input: string }
        Returns: {
          card_code: string
          card_id: string
          error_message: string
          is_valid: boolean
        }[]
      }
      verify_company_password: {
        Args: { company_code_input: string; password_input: string }
        Returns: {
          company_id: string
          company_name: string
          error_message: string
          is_valid: boolean
        }[]
      }
      verify_member_password: {
        Args: { member_code_input: string; password_input: string }
        Returns: {
          error_message: string
          is_valid: boolean
          member_code: string
          member_id: string
        }[]
      }
    }
    Enums: {
      audit_action:
        | "create"
        | "update"
        | "delete"
        | "login"
        | "logout"
        | "view"
        | "export"
        | "import"
        | "approve"
        | "reject"
        | "cancel"
        | "refund"
        | "recharge"
        | "payment"
        | "other"
      card_status: "active" | "inactive" | "suspended" | "expired" | "deleted"
      card_type: "member" | "enterprise"
      change_type: "earned" | "used" | "expired" | "manual_adjust"
      compensation_status:
        | "pending"
        | "processing"
        | "completed"
        | "failed"
        | "cancelled"
      compensation_type: "retry" | "rollback" | "manual" | "auto_compensate"
      lock_type: "balance" | "transaction" | "binding" | "qr_verification"
      member_status: "active" | "inactive" | "suspended" | "deleted"
      payment_method:
        | "balance"
        | "wechat"
        | "alipay"
        | "cash"
        | "card"
        | "other"
      reconciliation_status:
        | "pending"
        | "matched"
        | "mismatched"
        | "manual_review"
        | "completed"
      refund_method: "original" | "balance" | "cash" | "bank_transfer"
      request_status:
        | "pending"
        | "approved"
        | "rejected"
        | "completed"
        | "cancelled"
      transaction_status:
        | "pending"
        | "processing"
        | "completed"
        | "failed"
        | "cancelled"
        | "refunded"
      transaction_type:
        | "payment"
        | "refund"
        | "recharge"
        | "transfer"
        | "adjustment"
      verification_type: "payment" | "binding" | "login" | "verification"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      audit_action: [
        "create",
        "update",
        "delete",
        "login",
        "logout",
        "view",
        "export",
        "import",
        "approve",
        "reject",
        "cancel",
        "refund",
        "recharge",
        "payment",
        "other",
      ],
      card_status: ["active", "inactive", "suspended", "expired", "deleted"],
      card_type: ["member", "enterprise"],
      change_type: ["earned", "used", "expired", "manual_adjust"],
      compensation_status: [
        "pending",
        "processing",
        "completed",
        "failed",
        "cancelled",
      ],
      compensation_type: ["retry", "rollback", "manual", "auto_compensate"],
      lock_type: ["balance", "transaction", "binding", "qr_verification"],
      member_status: ["active", "inactive", "suspended", "deleted"],
      payment_method: ["balance", "wechat", "alipay", "cash", "card", "other"],
      reconciliation_status: [
        "pending",
        "matched",
        "mismatched",
        "manual_review",
        "completed",
      ],
      refund_method: ["original", "balance", "cash", "bank_transfer"],
      request_status: [
        "pending",
        "approved",
        "rejected",
        "completed",
        "cancelled",
      ],
      transaction_status: [
        "pending",
        "processing",
        "completed",
        "failed",
        "cancelled",
        "refunded",
      ],
      transaction_type: [
        "payment",
        "refund",
        "recharge",
        "transfer",
        "adjustment",
      ],
      verification_type: ["payment", "binding", "login", "verification"],
    },
  },
} as const