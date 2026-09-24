"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ProtectedRoute } from "@/components/protected-route";
import Link from "next/link";
import { Plus, Search, Filter, ChevronLeft, ChevronRight, Edit, Archive, Eye, RotateCcw } from "lucide-react";
import { format } from "date-fns";

interface Customer {
  id: number;
  name: string;
  mobile: string;
  email: string | null;
  address: string | null;
  notes: string | null;
  status: string;
  primary_staff_id: number | null;
  primary_staff_name: string | null;
  shop_id: number;
  created_at: string;
  updated_at: string;
}

interface CustomerListResponse {
  items: Customer[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

function CustomersContent() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState(searchParams?.get("search") || "");
  const [statusFilter, setStatusFilter] = useState(searchParams?.get("status") || "");
  const [staffFilter, setStaffFilter] = useState(searchParams?.get("primary_staff_id") || "");

  const shopIdParam = searchParams?.get("shop_id");
  const [shopId, setShopId] = useState<number | null>(shopIdParam ? parseInt(shopIdParam, 10) : null);

  const fetchCustomers = useCallback(async () => {
    if (!shopId) return;

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });

      if (search) params.append("search", search);
      if (statusFilter) params.append("status", statusFilter);
      if (staffFilter) params.append("primary_staff_id", staffFilter);

      const response = await fetch(`/api/v1/shops/${shopId}/customers?${params}`, {
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          router.push("/login");
          return;
        }
        throw new Error("Failed to fetch customers");
      }

      const data: CustomerListResponse = await response.json();
      setCustomers(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  }, [shopId, page, pageSize, search, statusFilter, staffFilter, router]);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    const params = new URLSearchParams(searchParams?.toString() || "");
    if (search) params.set("search", search);
    else params.delete("search");
    router.push(`/dashboard/customers?${params.toString()}`);
  };

  const handleFilterChange = (key: string, value: string) => {
    setPage(1);
    const params = new URLSearchParams(searchParams?.toString() || "");
    if (value) params.set(key, value);
    else params.delete(key);
    router.push(`/dashboard/customers?${params.toString()}`);
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      active: "default",
      inactive: "secondary",
      archived: "destructive",
    };
    return (
      <Badge variant={variants[status] || "outline"} className="capitalize">
        {status}
      </Badge>
    );
  };

  const handleArchive = async (customerId: number) => {
    if (!confirm("Archive this customer?")) return;
    const resp = await fetch(`/api/v1/shops/${shopId}/customers/${customerId}/archive`, {
      method: "PATCH",
      headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` },
    });
    if (resp.ok) fetchCustomers();
  };

  const handleRestore = async (customerId: number) => {
    if (!confirm("Restore this customer?")) return;
    const resp = await fetch(`/api/v1/shops/${shopId}/customers/${customerId}/restore`, {
      method: "PATCH",
      headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` },
    });
    if (resp.ok) fetchCustomers();
  };

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Customers</h1>
          <p className="text-muted-foreground mt-1">Manage your customer database</p>
        </div>
        <Button asChild>
          <Link href="/dashboard/customers/new">
            <Plus className="mr-2 h-4 w-4" />
            New Customer
          </Link>
        </Button>
      </div>

      {/* Search and Filters */}
      <form onSubmit={handleSearch} className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by name, mobile, or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex gap-2">
          <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); handleFilterChange("status", v); }}>
            <SelectTrigger className="w-[180px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="inactive">Inactive</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
            </SelectContent>
          </Select>
          <Select value={staffFilter} onValueChange={(v) => { setStaffFilter(v); handleFilterChange("primary_staff_id", v); }}>
            <SelectTrigger className="w-[180px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="All Staff" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Staff</SelectItem>
              {/* Staff would be loaded from API */}
            </SelectContent>
          </Select>
        </div>
      </form>

      {error && (
        <div className="mb-6 p-4 rounded-lg bg-destructive/10 text-destructive">
          {error}
        </div>
      )}

      {/* Customers Table */}
      <div className="rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Mobile</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Primary Staff</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  <div className="flex items-center justify-center gap-2">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary" />
                    Loading...
                  </div>
                </TableCell>
              </TableRow>
            ) : customers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                  No customers found. <Button asChild variant="link" className="p-0"><Link href="/dashboard/customers/new">Create one</Link></Button>
                </TableCell>
              </TableRow>
            ) : (
              customers.map((customer) => (
                <TableRow key={customer.id}>
                  <TableCell className="font-medium">{customer.name}</TableCell>
                  <TableCell className="font-mono">{customer.mobile}</TableCell>
                  <TableCell>{customer.email || "—"}</TableCell>
                  <TableCell>{customer.primary_staff_name || "—"}</TableCell>
                  <TableCell>{getStatusBadge(customer.status)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button variant="ghost" size="icon" asChild>
                        <Link href={`/dashboard/customers/${customer.id}`}>
                          <Eye className="h-4 w-4" />
                        </Link>
                      </Button>
                      <Button variant="ghost" size="icon" asChild>
                        <Link href={`/dashboard/customers/${customer.id}/edit`}>
                          <Edit className="h-4 w-4" />
                        </Link>
                      </Button>
                      {customer.status !== "archived" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleArchive(customer.id)}
                        >
                          <Archive className="h-4 w-4" />
                        </Button>
                      )}
                      {customer.status === "archived" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleRestore(customer.id)}
                        >
                          <RotateCcw className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="px-4 text-sm text-muted-foreground">
            Page {page} of {totalPages} ({total} total)
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}

export default function CustomersPage() {
  return (
    <ProtectedRoute>
      <CustomersContent />
    </ProtectedRoute>
  );
}