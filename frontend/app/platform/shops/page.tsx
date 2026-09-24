"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ProtectedRoute } from "@/components/protected-route";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { toast } from "@/components/ui/use-toast";
import { platformApi } from "@/lib/api";
import { Plus, Search, Loader2, MoreHorizontal, Edit, Trash2, Eye, ShieldCheck, ShieldX } from "lucide-react";

const STATUS_BADGE_VARIANTS: Record<string, "default" | "success" | "warning" | "destructive" | "muted"> = {
  active: "success",
  inactive: "muted",
  suspended: "destructive",
};

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function PlatformShopsContent() {
  const { user } = useAuth();
  const router = useRouter();
  const [shops, setShops] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createForm, setCreateForm] = useState({ name: "", slug: "" });
  const [createLoading, setCreateLoading] = useState(false);

  const fetchShops = useCallback(async () => {
    setLoading(true);
    try {
      const res = await platformApi.listShops({
        page,
        page_size: pageSize,
        search: search || undefined,
        status: statusFilter || undefined,
      });
      setShops(res.items);
      setTotal(res.total);
    } catch (err: any) {
      toast({
        title: "Error",
        description: err.message || "Failed to load shops",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, statusFilter]);

  // Initial load and when page/search/status changes
  const [initialized, setInitialized] = useState(false);
  if (!initialized) {
    fetchShops();
    setInitialized(true);
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchShops();
  };

  const handleCreateShop = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLoading(true);
    try {
      await platformApi.createShop(createForm);
      toast({ title: "Success", description: "Shop created successfully" });
      setCreateDialogOpen(false);
      setCreateForm({ name: "", slug: "" });
      fetchShops();
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to create shop", variant: "destructive" });
    } finally {
      setCreateLoading(false);
    }
  };

  const handleActivate = async (shopId: number) => {
    try {
      await platformApi.activateShop(shopId);
      toast({ title: "Success", description: "Shop activated" });
      fetchShops();
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to activate shop", variant: "destructive" });
    }
  };

  const handleDeactivate = async (shopId: number, status: "inactive" | "suspended") => {
    try {
      await platformApi.deactivateShop(shopId, status);
      toast({ title: "Success", description: `Shop ${status}` });
      fetchShops();
    } catch (err: any) {
      toast({ title: "Error", description: err.message || `Failed to ${status} shop`, variant: "destructive" });
    }
  };

  const handleViewShop = (shopId: number) => {
    router.push(`/platform/shops/${shopId}`);
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="container mx-auto py-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Platform Shops</h1>
          <p className="text-muted-foreground">Manage all shops on the platform</p>
        </div>
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create Shop
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Shop</DialogTitle>
              <DialogDescription>
                Enter shop details. A unique code (SHOP-XXXXXX) will be generated automatically.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateShop}>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <label htmlFor="name" className="text-sm font-medium">
                    Shop Name
                  </label>
                  <Input
                    id="name"
                    value={createForm.name}
                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                    placeholder="e.g., Main Street CSC Center"
                    required
                    disabled={createLoading}
                  />
                </div>
                <div className="grid gap-2">
                  <label htmlFor="slug" className="text-sm font-medium">
                    Slug (URL-friendly)
                  </label>
                  <Input
                    id="slug"
                    value={createForm.slug}
                    onChange={(e) => setCreateForm({ ...createForm, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "") })}
                    placeholder="e.g., main-street-csc"
                    required
                    disabled={createLoading}
                  />
                  <p className="text-xs text-muted-foreground">
                    Lowercase, alphanumeric, hyphens only. Used in URLs.
                  </p>
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setCreateDialogOpen(false)} disabled={createLoading}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createLoading}>
                  {createLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Create Shop
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search and Filters */}
      <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by name, code, or slug..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-full sm:w-[180px]">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Statuses</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="inactive">Inactive</SelectItem>
            <SelectItem value="suspended">Suspended</SelectItem>
          </SelectContent>
        </Select>
      </form>

      {/* Shops Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Code</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Slug</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
                </TableCell>
              </TableRow>
            ) : shops.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                  No shops found. Create your first shop to get started.
                </TableCell>
              </TableRow>
            ) : (
              shops.map((shop) => (
                <TableRow key={shop.id}>
                  <TableCell className="font-mono font-medium">{shop.code}</TableCell>
                  <TableCell>{shop.name}</TableCell>
                  <TableCell className="font-mono text-sm">{shop.slug}</TableCell>
                  <TableCell>
                    <Badge variant={STATUS_BADGE_VARIANTS[shop.status] || "default"}>
                      {shop.status.charAt(0).toUpperCase() + shop.status.slice(1)}
                    </Badge>
                  </TableCell>
                  <TableCell>{formatDate(shop.created_at)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button variant="ghost" size="icon" onClick={() => handleViewShop(shop.id)} title="View Details">
                        <Eye className="h-4 w-4" />
                      </Button>
                      {shop.status !== "active" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleActivate(shop.id)}
                          title="Activate"
                          className="text-green-600 hover:text-green-700"
                        >
                          <ShieldCheck className="h-4 w-4" />
                        </Button>
                      )}
                      {shop.status === "active" && (
                        <>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeactivate(shop.id, "inactive")}
                            title="Deactivate"
                            className="text-yellow-600 hover:text-yellow-700"
                          >
                            <ShieldX className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeactivate(shop.id, "suspended")}
                            title="Suspend"
                            className="text-red-600 hover:text-red-700"
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </>
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
        <div className="flex items-center justify-between mt-4">
          <p className="text-sm text-muted-foreground">
            Page {page} of {totalPages} — {total} total
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || loading}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages || loading}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function PlatformShopsPage() {
  return (
    <ProtectedRoute>
      <PlatformShopsContent />
    </ProtectedRoute>
  );
}