"use client";

import { useState, useEffect, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ProtectedRoute } from "@/components/protected-route";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { toast } from "@/components/ui/use-toast";
import { staffApi, getMyMembership, type CreateStaffPayload } from "@/lib/api";
import { Plus, Search, Loader2, MoreHorizontal, Edit, Trash2, Eye, UserPlus, ShieldCheck, ShieldX, Crown, Users, ChevronLeft, ChevronRight } from "lucide-react";

const ROLE_BADGE_VARIANTS: Record<string, "default" | "success" | "warning" | "destructive" | "muted" | "info"> = {
  shop_owner: "success",
  shop_manager: "info",
  staff: "default",
  financial_staff: "warning",
};

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function StaffManagementContent() {
  const { user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  // Get shop_id from URL params or user's current membership
  const shopIdParam = searchParams?.get("shop_id");
  const [shopId, setShopId] = useState<number | null>(shopIdParam ? parseInt(shopIdParam, 10) : null);
  const [myMembership, setMyMembership] = useState<any>(null);
  const [myShopId, setMyShopId] = useState<number | null>(null);

  const [staff, setStaff] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [activeFilter, setActiveFilter] = useState<"true" | "false" | "">("");
  const [loading, setLoading] = useState(false);

  // Dialogs
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createForm, setCreateForm] = useState<CreateStaffPayload>({ email: "", full_name: "", password: "", role: "staff" });
  const [createLoading, setCreateLoading] = useState(false);

  const [roleDialogOpen, setRoleDialogOpen] = useState(false);
  const [roleForm, setRoleForm] = useState<{ membership_id: number; role: CreateStaffPayload["role"] }>({ membership_id: 0, role: "staff" });
  const [roleLoading, setRoleLoading] = useState(false);

  // Fetch my membership to determine shop access
  useEffect(() => {
    if (!shopId && user?.id) {
      // Try to get user's current shop membership
      // For now, we'll just require shop_id in URL
    }
  }, [user]);

  // Fetch shop from membership if no shopId in URL
  useEffect(() => {
    if (!shopId && user?.id && !myShopId) {
      // We need to redirect to a shop context or show shop selector
      // For now, we'll just check if user has a default shop
    }
  }, [user, shopId, myShopId]);

  const fetchStaff = useCallback(async () => {
    if (!shopId) return;
    setLoading(true);
    try {
      const res = await staffApi.listStaff(shopId, {
        page,
        page_size: pageSize,
        search: search || undefined,
        role: roleFilter || undefined,
        is_active: activeFilter === "" ? undefined : activeFilter === "true",
      });
      setStaff(res.items);
      setTotal(res.total);
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to load staff", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [shopId, page, pageSize, search, roleFilter, activeFilter]);

  useEffect(() => {
    if (shopId) fetchStaff();
  }, [fetchStaff, shopId]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchStaff();
  };

  const handleCreateStaff = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!shopId) return;
    setCreateLoading(true);
    try {
      await staffApi.createStaff(shopId, createForm);
      toast({ title: "Success", description: "Staff member created" });
      setCreateDialogOpen(false);
      setCreateForm({ email: "", full_name: "", password: "", role: "staff" });
      fetchStaff();
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to create staff", variant: "destructive" });
    } finally {
      setCreateLoading(false);
    }
  };

  const handleChangeRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!shopId) return;
    setRoleLoading(true);
    try {
      await staffApi.changeRole(shopId, roleForm.membership_id, roleForm.role);
      toast({ title: "Success", description: "Role updated" });
      setRoleDialogOpen(false);
      fetchStaff();
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to change role", variant: "destructive" });
    } finally {
      setRoleLoading(false);
    }
  };

  const handleActivate = async (membershipId: number) => {
    if (!shopId) return;
    try {
      await staffApi.activateStaff(shopId, membershipId);
      toast({ title: "Success", description: "Staff activated" });
      fetchStaff();
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to activate staff", variant: "destructive" });
    }
  };

  const handleDeactivate = async (membershipId: number) => {
    if (!shopId) return;
    if (!confirm("Are you sure you want to deactivate this staff member? They will lose access to this shop but their user account will remain.")) return;
    try {
      await staffApi.deactivateStaff(shopId, membershipId);
      toast({ title: "Success", description: "Staff deactivated" });
      fetchStaff();
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to deactivate staff", variant: "destructive" });
    }
  };

  const openRoleDialog = (membershipId: number, currentRole: string) => {
    setRoleForm({ membership_id: membershipId, role: currentRole as CreateStaffPayload["role"] });
    setRoleDialogOpen(true);
  };

  const totalPages = Math.ceil(total / pageSize);

  // If no shopId, show shop selector or redirect message
  if (!shopId) {
    return (
      <div className="container mx-auto py-8 flex flex-col items-center justify-center min-h-[60vh] text-center">
        <Users className="h-16 w-16 text-muted-foreground mb-4" />
        <h1 className="text-2xl font-bold mb-2">Select a Shop</h1>
        <p className="text-muted-foreground mb-6 max-w-md">
          Please select a shop to manage staff. Navigate from the Platform Shops page or add <code>?shop_id=X</code> to the URL.
        </p>
        <Button onClick={() => router.push("/platform/shops")}>
          <ChevronLeft className="mr-2 h-4 w-4" />
          Go to Platform Shops
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Shop Staff</h1>
          <p className="text-muted-foreground">Manage staff members for shop ID: {shopId}</p>
        </div>
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <UserPlus className="mr-2 h-4 w-4" />
              Add Staff
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Staff Member</DialogTitle>
              <DialogDescription>
                Creates a new user account and adds them as staff to this shop.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateStaff}>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <label htmlFor="email" className="text-sm font-medium">Email</label>
                  <Input
                    id="email"
                    type="email"
                    value={createForm.email}
                    onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                    placeholder="staff@example.com"
                    required
                    disabled={createLoading}
                  />
                </div>
                <div className="grid gap-2">
                  <label htmlFor="full_name" className="text-sm font-medium">Full Name</label>
                  <Input
                    id="full_name"
                    value={createForm.full_name}
                    onChange={(e) => setCreateForm({ ...createForm, full_name: e.target.value })}
                    placeholder="John Doe"
                    required
                    disabled={createLoading}
                  />
                </div>
                <div className="grid gap-2">
                  <label htmlFor="password" className="text-sm font-medium">Password</label>
                  <Input
                    id="password"
                    type="password"
                    value={createForm.password}
                    onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                    placeholder="••••••••"
                    required
                    disabled={createLoading}
                    minLength={8}
                  />
                </div>
                <div className="grid gap-2">
                  <label htmlFor="role" className="text-sm font-medium">Role</label>
                  <Select value={createForm.role} onValueChange={(v) => setCreateForm({ ...createForm, role: v as CreateStaffPayload["role"] })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select role" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="shop_manager">Shop Manager</SelectItem>
                      <SelectItem value="staff">Staff</SelectItem>
                      <SelectItem value="financial_staff">Financial Staff</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setCreateDialogOpen(false)} disabled={createLoading}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createLoading}>
                  {createLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Add Staff
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
            placeholder="Search by name or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={roleFilter} onValueChange={setRoleFilter}>
          <SelectTrigger className="w-full sm:w-[160px]">
            <SelectValue placeholder="All Roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Roles</SelectItem>
            <SelectItem value="shop_owner">Shop Owner</SelectItem>
            <SelectItem value="shop_manager">Shop Manager</SelectItem>
            <SelectItem value="staff">Staff</SelectItem>
            <SelectItem value="financial_staff">Financial Staff</SelectItem>
          </SelectContent>
        </Select>
        <Select value={activeFilter} onValueChange={(v) => setActiveFilter(v as "true" | "false" | "")}>
          <SelectTrigger className="w-full sm:w-[160px]">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Status</SelectItem>
            <SelectItem value="true">Active</SelectItem>
            <SelectItem value="false">Inactive</SelectItem>
          </SelectContent>
        </Select>
      </form>

      {/* Staff Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Member</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Joined</TableHead>
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
            ) : staff.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                  No staff members found. Add your first staff member to get started.
                </TableCell>
              </TableRow>
            ) : (
              staff.map((member) => (
                <TableRow key={member.membership_id}>
                  <TableCell className="font-medium">{member.user_name}</TableCell>
                  <TableCell>{member.user_email}</TableCell>
                  <TableCell>
                    <Badge variant={ROLE_BADGE_VARIANTS[member.role] || "default"}>
                      {member.role.replace("_", " ").replace(/\b\w/g, (l: string) => l.toUpperCase())}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={member.is_active ? "success" : "muted"}>
                      {member.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell>{formatDate(member.created_at)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => openRoleDialog(member.membership_id, member.role)}
                        title="Change Role"
                        disabled={!member.is_active}
                      >
                        <Crown className="h-4 w-4" />
                      </Button>
                      {member.is_active ? (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeactivate(member.membership_id)}
                          title="Deactivate"
                          className="text-red-600 hover:text-red-700"
                        >
                          <ShieldX className="h-4 w-4" />
                        </Button>
                      ) : (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleActivate(member.membership_id)}
                          title="Activate"
                          className="text-green-600 hover:text-green-700"
                        >
                          <ShieldCheck className="h-4 w-4" />
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
              <ChevronLeft className="mr-2 h-4 w-4" />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages || loading}
            >
              Next
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Change Role Dialog */}
      <Dialog open={roleDialogOpen} onOpenChange={setRoleDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change Staff Role</DialogTitle>
            <DialogDescription>
              Select a new role for this staff member.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleChangeRole}>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <label htmlFor="role" className="text-sm font-medium">New Role</label>
                <Select value={roleForm.role} onValueChange={(v) => setRoleForm({ ...roleForm, role: v as CreateStaffPayload["role"] })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="shop_owner">Shop Owner</SelectItem>
                    <SelectItem value="shop_manager">Shop Manager</SelectItem>
                    <SelectItem value="staff">Staff</SelectItem>
                    <SelectItem value="financial_staff">Financial Staff</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setRoleDialogOpen(false)} disabled={roleLoading}>
                Cancel
              </Button>
              <Button type="submit" disabled={roleLoading}>
                {roleLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Update Role
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function StaffManagementPage() {
  return (
    <ProtectedRoute>
      <StaffManagementContent />
    </ProtectedRoute>
  );
}