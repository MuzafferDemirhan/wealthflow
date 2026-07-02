// ──────────────────────────────────────────────
// Enums
// ──────────────────────────────────────────────

export enum AccountType {
  CHECKING = "checking",
  SAVINGS = "savings",
  CREDIT_CARD = "credit_card",
  LOAN = "loan",
  INVESTMENT = "investment",
  OTHER = "other",
}

export enum TransactionStatus {
  PENDING = "pending",
  BOOKED = "booked",
}

export enum CategorySource {
  ML = "ml",
  RULE = "rule",
  USER = "user",
}

export enum AssetType {
  STOCK = "stock",
  ETF = "etf",
  MUTUAL_FUND = "mutual_fund",
  BOND = "bond",
  CRYPTO = "crypto",
  CASH = "cash",
  OTHER = "other",
}

export enum ConnectionStatus {
  PENDING = "pending",
  LINKED = "linked",
  EXPIRED = "expired",
  REVOKED = "revoked",
  ERROR = "error",
}

export enum BankProvider {
  NORDIGEN = "nordigen",
  PLAID = "plaid",
}

export enum UserRole {
  USER = "user",
  ADMIN = "admin",
}

// ──────────────────────────────────────────────
// Auth
// ──────────────────────────────────────────────

export interface UserRead {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface LogoutRequest {
  refresh_token: string;
}

// ──────────────────────────────────────────────
// Accounts
// ──────────────────────────────────────────────

export interface AccountRead {
  id: string;
  user_id: string;
  bank_connection_id: string;
  external_account_id: string;
  display_name: string;
  account_type: AccountType;
  iban?: string;
  currency: string;
  current_balance: number;
  balance_as_of?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ──────────────────────────────────────────────
// Categories
// ──────────────────────────────────────────────

export interface CategoryRead {
  id: string;
  name: string;
  slug: string;
  icon?: string;
  is_system: boolean;
  parent_id?: string;
  user_id?: string;
}

// ──────────────────────────────────────────────
// Transactions
// ──────────────────────────────────────────────

export interface TransactionRead {
  id: string;
  account_id: string;
  category_id?: string;
  external_id?: string;
  dedupe_hash: string;
  amount: number;
  currency: string;
  booking_date: string;
  value_date?: string;
  status: TransactionStatus;
  description: string;
  counterparty_name?: string;
  category_source?: CategorySource;
  category_confidence?: number;
  created_at: string;
  updated_at: string;
}

export interface TransactionCreate {
  account_id: string;
  amount: number;
  currency: string;
  booking_date: string;
  description: string;
  counterparty_name?: string;
  category_id?: string;
}

export interface TransactionUpdate {
  category_id: string;
  category_source?: CategorySource;
}

export interface TransactionListParams {
  account_id?: string;
  category_id?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  status?: TransactionStatus;
  offset?: number;
  limit?: number;
}

// ──────────────────────────────────────────────
// Budgets
// ──────────────────────────────────────────────

export interface BudgetRead {
  id: string;
  user_id: string;
  category_id?: string;
  period_month: string;
  amount_limit: number;
  currency: string;
  created_at: string;
  updated_at: string;
  spent: number;
  remaining: number;
  progress_pct: number;
}

export interface BudgetCreate {
  category_id?: string;
  period_month: string;
  amount_limit: number;
  currency: string;
}

export interface BudgetUpdate {
  amount_limit?: number;
  category_id?: string;
}

// ──────────────────────────────────────────────
// Portfolio / Holdings
// ──────────────────────────────────────────────

export interface HoldingRead {
  id: string;
  user_id: string;
  account_id?: string;
  symbol: string;
  name: string;
  asset_type: AssetType;
  currency: string;
  quantity: number;
  cost_basis?: number;
  current_price?: number;
  market_value?: number;
  as_of_date?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface HoldingCreate {
  symbol: string;
  name: string;
  asset_type: AssetType;
  currency: string;
  quantity: number;
  cost_basis?: number;
  current_price?: number;
  as_of_date?: string;
  account_id?: string;
  notes?: string;
}

export interface HoldingUpdate {
  symbol?: string;
  name?: string;
  asset_type?: AssetType;
  currency?: string;
  quantity?: number;
  cost_basis?: number;
  current_price?: number;
  as_of_date?: string;
  account_id?: string;
  notes?: string;
}

export interface PortfolioSummary {
  total_market_value: number;
  total_cost_basis?: number;
  total_gain_loss?: number;
  total_gain_loss_pct?: number;
  holdings_count: number;
  allocation: Record<string, number>;
}

// ──────────────────────────────────────────────
// Connect / Open Banking
// ──────────────────────────────────────────────

export interface InstitutionRead {
  id: string;
  name: string;
  logo?: string;
  country: string;
}

export interface RequisitionCreate {
  institution_id: string;
  redirect_uri: string;
}

export interface RequisitionCreateResponse {
  id: string;
  requisition_id: string;
  link: string;
  status: ConnectionStatus;
}

export interface RequisitionRead {
  id: string;
  requisition_id: string;
  status: ConnectionStatus;
  institution_id: string;
  institution_name: string;
  accounts_created: string[];
}

export interface ConnectionRead {
  id: string;
  user_id: string;
  provider: string;
  institution_id: string;
  institution_name: string;
  external_reference: string;
  status: ConnectionStatus;
  consent_expires_at?: string;
  last_synced_at?: string;
  created_at: string;
  updated_at: string;
}

// ──────────────────────────────────────────────
// Reports
// ──────────────────────────────────────────────

export interface CategoryBreakdownItem {
  category_id?: string;
  category_name: string;
  category_slug?: string;
  category_icon?: string;
  total_amount: number;
  transaction_count: number;
  percentage: number;
}

export interface ReportCategoryBreakdown {
  date_from: string;
  date_to: string;
  total_income: number;
  total_expenses: number;
  net: number;
  categories: CategoryBreakdownItem[];
}

export interface MonthlyBreakdown {
  month: string;
  income: number;
  expenses: number;
  net: number;
}

export interface ReportIncomeVsExpenses {
  date_from: string;
  date_to: string;
  total_income: number;
  total_expenses: number;
  net: number;
  monthly_breakdown?: MonthlyBreakdown[];
}

export interface ReportMonthlyTrends {
  months: number;
  data: MonthlyBreakdown[];
}

export interface AccountTypeBreakdown {
  account_type: AccountType;
  count: number;
  total_balance: number;
}

export interface ReportNetWorth {
  as_of_date: string;
  total_assets: number;
  total_liabilities: number;
  net_worth: number;
  by_account_type: AccountTypeBreakdown[];
  portfolio_market_value: number;
}

// ──────────────────────────────────────────────
// API Error
// ──────────────────────────────────────────────

export interface ApiError {
  detail: string;
}
