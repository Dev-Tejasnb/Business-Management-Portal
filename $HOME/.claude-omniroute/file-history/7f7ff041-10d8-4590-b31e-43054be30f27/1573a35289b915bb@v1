/**
 * Lightweight API client for the backend.
 *
 * - Auth requests are proxied through Next.js API routes so the browser never
 *   talks directly to the backend and HTTP-only cookies flow through the proxy.
 * - Access tokens are held **only** in memory (never localStorage/sessionStorage)
 *   to limit XSS exposure.
 */

let accessToken: string | null = null;
let accessTokenExpiry: number | null = null;

export function setAccessToken(token: string, expiresIn: number) {
  accessToken = token;
  // Set expiry slightly earlier to avoid using an about-to-expire token.
  accessTokenExpiry = Date.now() + (expiresIn - 30) * 1000;
}

export function clearAccessToken() {
  accessToken = null;
  accessTokenExpiry = null;
}

export function getAccessToken(): string | null {
  if (!accessToken || !accessTokenExpiry) return null;
  if (Date.now() >= accessTokenExpiry) return null;
  return accessToken;
}

// Base URL for Next.js API proxy routes (same origin).
const AUTH_PROXY = "/api/auth";

// Base URL for API calls via Next.js rewrites proxy to backend.
// Uses /api/v1 which is rewritten to http://backend:8000/api/v1 by next.config.mjs
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

/** Authenticated fetch against the backend API. */
export async function apiFetch(
  path: string,
  init: RequestInit = {}
): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  headers.set("Content-Type", "application/json");
  return fetch(`${API_BASE}${path}`, { ...init, headers, credentials: "include" });
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface Shop {
  id: number;
  code: string;
  name: string;
  slug: string;
  status: "active" | "inactive" | "suspended";
  created_at: string;
  updated_at: string;
  primary_owner?: {
    id: number;
    email: string;
    full_name: string;
  } | null;
}

export interface ShopListResponse {
  items: Shop[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreateShopPayload {
  name: string;
  slug: string;
  owner_user_id?: number;
}

export interface UpdateShopPayload {
  name?: string;
  slug?: string;
}

export interface ShopManager {
  id: number;
  user_id: number;
  shop_id: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  user: {
    id: number;
    email: string;
    full_name: string;
    platform_role: string;
  };
}

export interface StaffMember {
  membership_id: number;
  user_id: number;
  shop_id: number;
  role: "shop_owner" | "shop_manager" | "staff" | "financial_staff";
  is_active: boolean;
  created_at: string;
  updated_at: string;
  user_email: string;
  user_name: string;
}

export interface StaffListResponse {
  items: StaffMember[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreateStaffPayload {
  email: string;
  full_name: string;
  password: string;
  role: "shop_manager" | "staff" | "financial_staff";
}

export interface UpdateStaffPayload {
  full_name?: string;
}

export interface ChangeStaffRolePayload {
  role: "shop_owner" | "shop_manager" | "staff" | "financial_staff";
}

export interface PaginatedParams {
  page?: number;
  page_size?: number;
  search?: string;
  role?: string;
  status?: string;
  is_active?: boolean;
}

// ── Auth API (proxied through Next.js for cookie management) ──────────────

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  platform_role: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export async function login(
  email: string,
  password: string
): Promise<LoginResponse> {
  const res = await fetch(`${AUTH_PROXY}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    credentials: "include",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body?.error?.message ?? "Login failed");
  }
  const data: LoginResponse = await res.json();
  setAccessToken(data.access_token, data.expires_in);
  return data;
}

export async function refreshToken(): Promise<LoginResponse | null> {
  const res = await fetch(`${AUTH_PROXY}/refresh`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) return null;
  const data: LoginResponse = await res.json();
  setAccessToken(data.access_token, data.expires_in);
  return data;
}

export async function logout(): Promise<void> {
  await fetch(`${AUTH_PROXY}/logout`, {
    method: "POST",
    credentials: "include",
    headers: accessToken
      ? { Authorization: `Bearer ${accessToken}` }
      : undefined,
  });
  clearAccessToken();
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const token = getAccessToken();
  if (!token) throw new ApiError(401, "Not authenticated");
  const res = await fetch(`${AUTH_PROXY}/me`, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: "include",
  });
  if (!res.ok) throw new ApiError(res.status, "Failed to load user");
  return res.json();
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// ── Platform Shops API ──────────────────────────────────────────────────────

export const platformApi = {
  /** List shops with search, status filter, pagination */
  async listShops(params: PaginatedParams = {}): Promise<ShopListResponse> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set("page", String(params.page));
    if (params.page_size) searchParams.set("page_size", String(params.page_size));
    if (params.search) searchParams.set("search", params.search);
    if (params.status) searchParams.set("status", params.status);
    const res = await apiFetch(`/platform/shops?${searchParams.toString()}`);
    if (!res.ok) throw new ApiError(res.status, "Failed to list shops");
    return res.json();
  },

  /** Create a new shop */
  async createShop(payload: CreateShopPayload): Promise<Shop> {
    const res = await apiFetch("/platform/shops", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body?.error?.message ?? "Failed to create shop");
    }
    return res.json();
  },

  /** Get shop by ID */
  async getShop(shopId: number): Promise<Shop> {
    const res = await apiFetch(`/platform/shops/${shopId}`);
    if (!res.ok) throw new ApiError(res.status, "Failed to fetch shop");
    return res.json();
  },

  /** Update shop name/slug */
  async updateShop(shopId: number, payload: UpdateShopPayload): Promise<Shop> {
    const res = await apiFetch(`/platform/shops/${shopId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to update shop");
    return res.json();
  },

  /** Activate a shop */
  async activateShop(shopId: number): Promise<Shop> {
    const res = await apiFetch(`/platform/shops/${shopId}/activate`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to activate shop");
    return res.json();
  },

  /** Deactivate or suspend a shop */
  async deactivateShop(shopId: number, status: "inactive" | "suspended" = "inactive"): Promise<Shop> {
    const res = await apiFetch(`/platform/shops/${shopId}/deactivate`, {
      method: "POST",
      body: JSON.stringify({ status }),
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to deactivate shop");
    return res.json();
  },

  /** Change shop owner */
  async changeOwner(shopId: number, newOwnerUserId: number): Promise<Shop> {
    const res = await apiFetch(`/platform/shops/${shopId}/owner`, {
      method: "POST",
      body: JSON.stringify({ new_owner_user_id: newOwnerUserId }),
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to change owner");
    return res.json();
  },

  /** List assigned platform managers for a shop */
  async listManagers(shopId: number): Promise<ShopManager[]> {
    const res = await apiFetch(`/platform/shops/${shopId}/managers`);
    if (!res.ok) throw new ApiError(res.status, "Failed to list managers");
    return res.json();
  },

  /** Assign a platform manager to a shop */
  async assignManager(shopId: number, userId: number, isActive = true): Promise<ShopManager> {
    const res = await apiFetch(`/platform/shops/${shopId}/managers`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId, is_active: isActive }),
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to assign manager");
    return res.json();
  },

  /** Unassign a platform manager from a shop */
  async unassignManager(shopId: number, userId: number): Promise<void> {
    const res = await apiFetch(`/platform/shops/${shopId}/managers/${userId}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to unassign manager");
  },

  /** Update manager assignment status */
  async updateManager(shopId: number, userId: number, isActive: boolean): Promise<ShopManager> {
    const res = await apiFetch(`/platform/shops/${shopId}/managers/${userId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to update manager");
    return res.json();
  },
};

// ── Staff API (shop-scoped) ──────────────────────────────────────────────────

export const staffApi = {
  /** List staff members with search, role, active filters */
  async listStaff(shopId: number, params: PaginatedParams = {}): Promise<StaffListResponse> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set("page", String(params.page));
    if (params.page_size) searchParams.set("page_size", String(params.page_size));
    if (params.search) searchParams.set("search", params.search);
    if (params.role) searchParams.set("role", params.role);
    if (params.is_active !== undefined) searchParams.set("is_active", String(params.is_active));
    const res = await apiFetch(`/shops/${shopId}/staff?${searchParams.toString()}`);
    if (!res.ok) throw new ApiError(res.status, "Failed to list staff");
    return res.json();
  },

  /** Create a new staff member */
  async createStaff(shopId: number, payload: CreateStaffPayload): Promise<StaffMember> {
    const res = await apiFetch(`/shops/${shopId}/staff`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body?.error?.message ?? "Failed to create staff");
    }
    return res.json();
  },

  /** Get staff member by membership ID */
  async getStaff(shopId: number, membershipId: number): Promise<StaffMember> {
    const res = await apiFetch(`/shops/${shopId}/staff/${membershipId}`);
    if (!res.ok) throw new ApiError(res.status, "Failed to fetch staff");
    return res.json();
  },

  /** Update staff profile */
  async updateStaff(shopId: number, membershipId: number, payload: UpdateStaffPayload): Promise<StaffMember> {
    const res = await apiFetch(`/shops/${shopId}/staff/${membershipId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to update staff");
    return res.json();
  },

  /** Change staff role */
  async changeRole(shopId: number, membershipId: number, role: ChangeStaffRolePayload["role"]): Promise<StaffMember> {
    const res = await apiFetch(`/shops/${shopId}/staff/${membershipId}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to change role");
    return res.json();
  },

  /** Activate staff membership */
  async activateStaff(shopId: number, membershipId: number): Promise<StaffMember> {
    const res = await apiFetch(`/shops/${shopId}/staff/${membershipId}/activate`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to activate staff");
    return res.json();
  },

  /** Deactivate staff membership */
  async deactivateStaff(shopId: number, membershipId: number): Promise<StaffMember> {
    const res = await apiFetch(`/shops/${shopId}/staff/${membershipId}/deactivate`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to deactivate staff");
    return res.json();
  },
};

// ── Authenticated user's shop membership ──────────────────────────────────────

export async function getMyMembership(shopId: number): Promise<StaffMember> {
  const res = await apiFetch(`/shops/${shopId}/memberships/me`);
  if (!res.ok) throw new ApiError(res.status, "Failed to fetch membership");
  return res.json();
}

// ── Billing & Payments API (shop-scoped) ───────────────────────────────────────

export interface BillingItemCreate {
  name: string;
  description?: string;
  amount: number;
  is_service_item: boolean;
  service_id?: number;
  sort_order: number;
}

export interface BillingItemUpdate {
  name?: string;
  description?: string;
  amount?: number;
  is_service_item?: boolean;
  service_id?: number;
  sort_order?: number;
}

export interface BillingItemResponse extends BillingItemCreate {
  id: number;
  billing_id: number;
  created_at: string;
  updated_at?: string;
}

export type PaymentMethod = "cash" | "upi" | "card" | "bank_transfer" | "other";
export type PaymentStatus = "unpaid" | "partially_paid" | "paid";
export type BillingStatus = "draft" | "issued" | "void";
export type DiscountType = "fixed" | "percentage";

export interface BillingCreate {
  application_id: number;
  items: BillingItemCreate[];
  discount_type?: DiscountType;
  discount_value?: number;
  discount_reason?: string;
  notes?: string;
}

export interface BillingUpdate {
  notes?: string;
  discount_type?: DiscountType;
  discount_value?: number;
  discount_reason?: string;
}

export interface BillingResponse {
  id: number;
  shop_id: number;
  application_id: number;
  customer_id: number;
  invoice_number: string;
  service_amount: number;
  non_service_charges: number;
  subtotal: number;
  discount_type?: DiscountType;
  discount_value?: number;
  discount_amount: number;
  discount_reason?: string;
  total_amount: number;
  amount_paid: number;
  balance_amount: number;
  payment_status: PaymentStatus;
  billing_status: BillingStatus;
  created_by: number;
  updated_by?: number;
  created_at: string;
  updated_at?: string;
  items: BillingItemResponse[];
  application_number?: string;
  customer_name?: string;
  service_name?: string;
}

export interface BillingListResponse {
  items: BillingResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PaymentCreate {
  amount: number;
  payment_method: PaymentMethod;
  reference_number?: string;
  reference_exception: boolean;
  reference_exception_reason?: string;
  notes?: string;
}

export interface PaymentUpdate {
  amount?: number;
  payment_method?: PaymentMethod;
  reference_number?: string;
  reference_exception?: boolean;
  reference_exception_reason?: string;
  notes?: string;
}

export interface PaymentResponse {
  id: number;
  shop_id: number;
  billing_id: number;
  recorded_by: number;
  paid_at: string;
  created_at: string;
  updated_at?: string;
  amount: number;
  payment_method: PaymentMethod;
  reference_number?: string;
  reference_exception: boolean;
  reference_exception_reason?: string;
  notes?: string;
  recorder_name?: string;
}

export interface PaymentListResponse {
  items: PaymentResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface BillingCalculationPreview {
  service_amount: number;
  non_service_charges: number;
  subtotal: number;
  discount_type?: DiscountType;
  discount_value?: number;
  discount_amount: number;
  total_amount: number;
}

export const billingApi = {
  /** Get billing for an application */
  async getBilling(shopId: number, applicationId: number): Promise<BillingResponse | null> {
    const res = await apiFetch(`/shops/${shopId}/applications/${applicationId}/billing`);
    if (res.status === 404) return null;
    if (!res.ok) throw new ApiError(res.status, "Failed to fetch billing");
    return res.json();
  },

  /** Create billing for an application */
  async createBilling(shopId: number, applicationId: number, payload: BillingCreate): Promise<BillingResponse> {
    const res = await apiFetch(`/shops/${shopId}/applications/${applicationId}/billing`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body?.error?.message ?? "Failed to create billing");
    }
    return res.json();
  },

  /** Update billing (notes, discount) */
  async updateBilling(shopId: number, billingId: number, payload: BillingUpdate): Promise<BillingResponse> {
    const res = await apiFetch(`/shops/${shopId}/applications/billing/${billingId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to update billing");
    return res.json();
  },

  /** Issue billing (draft -> issued) */
  async issueBilling(shopId: number, billingId: number): Promise<BillingResponse> {
    const res = await apiFetch(`/shops/${shopId}/applications/billing/${billingId}/issue`, {
      method: "POST",
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to issue billing");
    return res.json();
  },

  /** Void billing */
  async voidBilling(shopId: number, billingId: number): Promise<BillingResponse> {
    const res = await apiFetch(`/shops/${shopId}/applications/billing/${billingId}/void`, {
      method: "POST",
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to void billing");
    return res.json();
  },

  /** Preview billing calculation */
  async previewBilling(shopId: number, payload: { items: BillingItemCreate[]; discount_type?: DiscountType; discount_value?: number }): Promise<BillingCalculationPreview> {
    const res = await apiFetch(`/shops/${shopId}/applications/billing/preview`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to preview billing");
    return res.json();
  },

  /** List billing items */
  async listBillingItems(shopId: number, billingId: number): Promise<BillingItemResponse[]> {
    const res = await apiFetch(`/shops/${shopId}/applications/billing/${billingId}/items`);
    if (!res.ok) throw new ApiError(res.status, "Failed to list billing items");
    return res.json();
  },

  /** Add billing item */
  async addBillingItem(shopId: number, billingId: number, payload: BillingItemCreate): Promise<BillingItemResponse> {
    const res = await apiFetch(`/shops/${shopId}/applications/billing/${billingId}/items`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to add billing item");
    return res.json();
  },

  /** Update billing item */
  async updateBillingItem(shopId: number, billingId: number, itemId: number, payload: BillingItemUpdate): Promise<BillingItemResponse> {
    const res = await apiFetch(`/shops/${shopId}/applications/billing/${billingId}/items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to update billing item");
    return res.json();
  },

  /** Delete billing item */
  async deleteBillingItem(shopId: number, billingId: number, itemId: number): Promise<void> {
    const res = await apiFetch(`/shops/${shopId}/applications/billing/${billingId}/items/${itemId}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to delete billing item");
  },

  /** List payments for a billing */
  async listPayments(shopId: number, billingId: number, params: { page?: number; page_size?: number } = {}): Promise<PaymentListResponse> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set("page", String(params.page));
    if (params.page_size) searchParams.set("page_size", String(params.page_size));
    const res = await apiFetch(`/shops/${shopId}/applications/billing/${billingId}/payments?${searchParams.toString()}`);
    if (!res.ok) throw new ApiError(res.status, "Failed to list payments");
    return res.json();
  },

  /** Create payment */
  async createPayment(shopId: number, billingId: number, payload: PaymentCreate): Promise<PaymentResponse> {
    const res = await apiFetch(`/shops/${shopId}/applications/billing/${billingId}/payments`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body?.error?.message ?? "Failed to create payment");
    }
    return res.json();
  },

  /** Get payment by ID */
  async getPayment(shopId: number, billingId: number, paymentId: number): Promise<PaymentResponse> {
    const res = await apiFetch(`/shops/${shopId}/applications/billing/${billingId}/payments/${paymentId}`);
    if (!res.ok) throw new ApiError(res.status, "Failed to fetch payment");
    return res.json();
  },

  /** Update payment */
  async updatePayment(shopId: number, billingId: number, paymentId: number, payload: PaymentUpdate): Promise<PaymentResponse> {
    const res = await apiFetch(`/shops/${shopId}/applications/billing/${billingId}/payments/${paymentId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to update payment");
    return res.json();
  },

  /** Get next invoice number */
  async getNextInvoiceNumber(shopId: number): Promise<{ invoice_number: string }> {
    const res = await apiFetch(`/shops/${shopId}/applications/billing/next-invoice-number`);
    if (!res.ok) throw new ApiError(res.status, "Failed to get next invoice number");
    return res.json();
  },
};
