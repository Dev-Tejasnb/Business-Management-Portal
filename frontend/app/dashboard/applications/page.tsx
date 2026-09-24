"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ProtectedRoute } from "@/components/protected-route";
import Link from "next/link";
import {
  Search,
  Filter,
  Plus,
  Users,
  Banknote,
  ChevronLeft,
  ChevronRight,
  Eye,
  Edit,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { format } from "date-fns";
import { ApplicationStatus } from "@/src/types/application";

// Types
interface Application {
  id: number;
  application_number: string;
  customer: {
    name: string;
    mobile: string;
  };
  service: {
    name: string;
  };
  status: ApplicationStatus;
  assigned_staff?: {
    full_name: string;
  } | null;
  created_at: string;
}

interface ApplicationListResponse {
  applications: Application[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

function ApplicationsContent() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState(searchParams?.get("search") || "");
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | ''>(searchParams?.get("status") as ApplicationStatus || '');
  const [serviceFilter, setServiceFilter] = useState(searchParams?.get("service_id") || "");

  const shopIdParam = searchParams?.get("shop_id");
  const [shopId, setShopId] = useState<number | null>(shopIdParam ? parseInt(shopIdParam, 10) : null);

  const fetchApplications = useCallback(async () => {
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
      if (serviceFilter) params.append("service_id", serviceFilter);

      const response = await fetch(`/api/v1/shops/${shopId}/applications?${params}`, {
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          router.push("/login");
          return;
        }
        throw new Error("Failed to fetch applications");
      }

      const data: ApplicationListResponse = await response.json();
      setApplications(data.applications);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  }, [shopId, page, pageSize, search, statusFilter, serviceFilter, router]);

  useEffect(() => {
    fetchApplications();
  }, [fetchApplications]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    const params = new URLSearchParams(searchParams?.toString() || "");
    if (search) params.set("search", search);
    else params.delete("search");
    router.push(`/dashboard/applications?${params.toString()}`);
  };

  const handleFilterChange = (key: string, value: string) => {
    setPage(1);
    const params = new URLSearchParams(searchParams?.toString() || "");
    if (value) params.set(key, value);
    else params.delete(key);
    router.push(`/dashboard/applications?${params.toString()}`);
  };

  const getStatusBadge = (status: ApplicationStatus) => {
    const statusConfigs: Record<ApplicationStatus, { variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info"; label: string }> = {
      enquiry: { variant: "secondary", label: "Enquiry" },
      applied: { variant: "default", label: "Applied" },
      documents_pending: { variant: "warning", label: "Documents Pending" },
      under_processing: { variant: "info", label: "Under Processing" },
      completed: { variant: "success", label: "Completed" },
      rejected: { variant: "destructive", label: "Rejected" },
      cancelled: { variant: "destructive", label: "Cancelled" },
    };

    const config = statusConfigs[status] || { variant: "secondary", label: status };
    return <Badge variant={config.variant}>{config.label}</Badge>;
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
          <h1 className="text-3xl font-bold tracking-tight">Applications</h1>
          <p className="text-muted-foreground mt-1">Manage customer applications for services</p>
        </div>
        <Button asChild>
          <Link href="/dashboard/applications/new">
            <Plus className="mr-2 h-4 w-4" />
            New Application
          </Link>
        </Button>
      </div>

      {/* Search and Filters */}
      <form onSubmit={handleSearch} className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search applications..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex gap-2">
          <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v as ApplicationStatus); handleFilterChange("status", v); }}>
            <SelectTrigger className="w-[180px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Statuses</SelectItem>
              <SelectItem value="enquiry">Enquiry</SelectItem>
              <SelectItem value="applied">Applied</SelectItem>
              <SelectItem value="documents_pending">Documents Pending</SelectItem>
              <SelectItem value="under_processing">Under Processing</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
          <Select value={serviceFilter} onValueChange={(v) => { setServiceFilter(v); handleFilterChange("service_id", v); }}>
            <SelectTrigger className="w-[180px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="All Services" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Services</SelectItem>
              {/* Services would be loaded from API */}
            </SelectContent>
          </Select>
        </div>
      </form>

      {error && (
        <div className="mb-6 p-4 rounded-lg bg-destructive/10 text-destructive">
          {error}
        </div>
      )}

      {/* Applications Table */}
      <div className="rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-20">Application #</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Service</TableHead>
              <TableHead className="w-24">Status</TableHead>
              <TableHead className="w-24">Assigned Staff</TableHead>
              <TableHead className="w-20">Created</TableHead>
              <TableHead className="w-16">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  <div className="flex items-center justify-center gap-2">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary" />
                    Loading...
                  </div>
                </TableCell>
              </TableRow>
            ) : applications.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  No applications found. <Button asChild variant="link" className="p-0"><Link href="/dashboard/applications/new">Create one</Link></Button>
                </TableCell>
              </TableRow>
            ) : (
              applications.map((app) => (
                <TableRow key={app.id} className="hover:bg-accent">
                  <TableCell className="font-mono">{app.application_number}</TableCell>
                  <TableCell>
                    <div className="flex w-full items-center gap-3">
                      <div className="flex-shrink-0 h-8 w-8 rounded bg-muted/50 flex items-center justify-center">
                        <Users className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div>
                        <p className="font-medium">{app.customer.name}</p>
                        <p className="text-xs text-muted-foreground">{app.customer.mobile}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="flex-shrink-0 h-8 w-8 rounded bg-muted/50 flex items-center justify-center">
                        <Banknote className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div>
                        <p className="font-medium">{app.service.name}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(app.status)}
                  </TableCell>
                  <TableCell>
                    {app.assigned_staff ? (
                      <div className="flex items-center gap-2">
                        <div className="flex-shrink-0 h-6 w-6 rounded bg-muted/50 flex items-center justify-center">
                          <Users className="h-3 w-3 text-muted-foreground" />
                        </div>
                        <span className="text-sm">{app.assigned_staff.full_name}</span>
                      </div>
                    ) : (
                      <span className="text-muted-foreground italic">Unassigned</span>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {new Date(app.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="flex flex-col gap-2">
                    <Button variant="ghost" size="icon" asChild>
                      <Link href={`/dashboard/applications/${app.id}`}>
                        <Eye className="h-4 w-4" />
                      </Link>
                    </Button>
                    <Button variant="ghost" size="icon" asChild>
                      <Link href={`/dashboard/applications/${app.id}/edit`}>
                        <Edit className="h-4 w-4" />
                      </Link>
                    </Button>
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

export default function ApplicationsPage() {
  return (
    <ProtectedRoute>
      <ApplicationsContent />
    </ProtectedRoute>
  );
}