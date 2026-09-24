"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ProtectedRoute } from "@/components/protected-route";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { toast } from "@/components/ui/use-toast";
import { platformApi } from "@/lib/api";
import { Loader2, ArrowLeft, UserPlus, ShieldCheck, ShieldX, MoreHorizontal, Edit, Trash2, Eye, Settings, Crown, Users } from "lucide-react";

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
    hour: "2-digit",
    minute: "2-digit",
  });
}

function ShopDetailContent() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const shopId = params?.id ? parseInt(params.id as string, 10) : 0;

  const [shop, setShop] = useState<any>(null);
  const [managers, setManagers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "managers">("overview");

  // Edit shop dialog
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editForm, setEditForm] = useState({ name: "", slug: "" });
  const [editLoading, setEditLoading] = useState(false);

  // Assign manager dialog
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [assignForm, setAssignForm] = useState({ user_id: "", is_active: true });
  const [assignLoading, setAssignLoading] = useState(false);

  // Change owner dialog
  const [ownerDialogOpen, setOwnerDialogOpen] = useState(false);
  const [ownerForm, setOwnerForm] = useState({ new_owner_user_id: "" });
  const [ownerLoading, setOwnerLoading] = useState(false);

  const fetchShop = useCallback(async () => {
    if (!shopId) return;
    try {
      const data = await platformApi.getShop(shopId);
      setShop(data);
      setEditForm({ name: data.name, slug: data.slug });
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to load shop", variant: "destructive" });
      router.push("/platform/shops");
    } finally {
      setLoading(false);
    }
  }, [shopId, router]);

  const fetchManagers = useCallback(async () => {
    if (!shopId) return;
    try {
      const data = await platformApi.listManagers(shopId);
      setManagers(data);
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to load managers", variant: "destructive" });
    }
  }, [shopId]);

  useEffect(() => {
    fetchShop();
    fetchManagers();
  }, [fetchShop, fetchManagers]);

  const handleEditShop = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!shopId) return;
    setEditLoading(true);
    try {
      await platformApi.updateShop(shopId, editForm);
      toast({ title: "Success", description: "Shop updated" });
      setEditDialogOpen(false);
      fetchShop();
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to update shop", variant: "destructive" });
    } finally {
      setEditLoading(false);
    }
  };

  const handleActivate = async () => {
    if (!shopId) return;
    try {
      await platformApi.activateShop(shopId);
      toast({ title: "Success", description: "Shop activated" });
      fetchShop();
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to activate shop", variant: "destructive" });
    }
  };

  const handleDeactivate = async (status: "inactive" | "suspended") => {
    if (!shopId) return;
    try {
      await platformApi.deactivateShop(shopId, status);
      toast({ title: "Success", description: `Shop ${status}` });
      fetchShop();
    } catch (err: any) {
      toast({ title: "Error", description: err.message || `Failed to ${status} shop`, variant: "destructive" });
    }
  };

  const handleAssignManager = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!shopId) return;
    setAssignLoading(true);
    try {
      await platformApi.assignManager(shopId, parseInt(assignForm.user_id, 10), assignForm.is_active);
      toast({ title: "Success", description: "Manager assigned" });
      setAssignDialogOpen(false);
      setAssignForm({ user_id: "", is_active: true });
      fetchManagers();
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to assign manager", variant: "destructive" });
    } finally {
      setAssignLoading(false);
    }
  };

  const handleUnassignManager = async (userId: number) => {
    if (!shopId) return;
    if (!confirm("Are you sure you want to unassign this manager?")) return;
    try {
      await platformApi.unassignManager(shopId, userId);
      toast({ title: "Success", description: "Manager unassigned" });
      fetchManagers();
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to unassign manager", variant: "destructive" });
    }
  };

  const handleToggleManager = async (manager: any) => {
    if (!shopId) return;
    try {
      await platformApi.updateManager(shopId, manager.user_id, !manager.is_active);
      toast({ title: "Success", description: `Manager ${!manager.is_active ? "activated" : "deactivated"}` });
      fetchManagers();
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to update manager", variant: "destructive" });
    }
  };

  const handleChangeOwner = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!shopId) return;
    setOwnerLoading(true);
    try {
      await platformApi.changeOwner(shopId, parseInt(ownerForm.new_owner_user_id, 10));
      toast({ title: "Success", description: "Owner changed successfully" });
      setOwnerDialogOpen(false);
      setOwnerForm({ new_owner_user_id: "" });
      fetchShop();
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to change owner", variant: "destructive" });
    } finally {
      setOwnerLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto py-8 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!shop) return null;

  return (
    <div className="container mx-auto py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/platform/shops")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{shop.name}</h1>
            <p className="text-muted-foreground">Code: {shop.code} • Slug: {shop.slug}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Badge variant={STATUS_BADGE_VARIANTS[shop.status] || "default"} className="text-sm">
            {shop.status.charAt(0).toUpperCase() + shop.status.slice(1)}
          </Badge>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 mb-6 border-b">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "overview"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab("managers")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "managers"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          Platform Managers <span className="ml-2 px-2 py-0.5 text-xs bg-muted rounded-full">{managers.length}</span>
        </button>
      </div>

      {/* Overview Tab */}
      {activeTab === "overview" && (
        <div className="grid gap-6 md:grid-cols-2">
          {/* Shop Details */}
          <div className="rounded-lg border bg-card p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Shop Details
            </h2>
            <dl className="space-y-4">
              <div>
                <dt className="text-sm text-muted-foreground">Code</dt>
                <dd className="font-mono font-medium text-lg">{shop.code}</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">Name</dt>
                <dd className="font-medium">{shop.name}</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">Slug</dt>
                <dd className="font-mono text-sm">{shop.slug}</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">Status</dt>
                <dd className="flex items-center gap-2">
                  <Badge variant={STATUS_BADGE_VARIANTS[shop.status] || "default"}>
                    {shop.status.charAt(0).toUpperCase() + shop.status.slice(1)}
                  </Badge>
                </dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">Created</dt>
                <dd>{formatDate(shop.created_at)}</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">Updated</dt>
                <dd>{formatDate(shop.updated_at)}</dd>
              </div>
            </dl>

            <div className="mt-6 flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => setEditDialogOpen(true)}>
                <Edit className="mr-2 h-4 w-4" />
                Edit Details
              </Button>
              {shop.status !== "active" && (
                <Button onClick={handleActivate} variant="default">
                  <ShieldCheck className="mr-2 h-4 w-4" />
                  Activate
                </Button>
              )}
              {shop.status === "active" && (
                <>
                  <Button variant="outline" onClick={() => handleDeactivate("inactive")}>
                    <ShieldX className="mr-2 h-4 w-4" />
                    Deactivate
                  </Button>
                  <Button variant="destructive" onClick={() => handleDeactivate("suspended")}>
                    <MoreHorizontal className="mr-2 h-4 w-4" />
                    Suspend
                  </Button>
                </>
              )}
            </div>
          </div>

          {/* Primary Owner */}
          <div className="rounded-lg border bg-card p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Crown className="h-5 w-5" />
              Primary Owner
            </h2>
            {shop.primary_owner ? (
              <>
                <dl className="space-y-4">
                  <div>
                    <dt className="text-sm text-muted-foreground">Name</dt>
                    <dd className="font-medium">{shop.primary_owner.full_name}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground">Email</dt>
                    <dd className="font-medium">{shop.primary_owner.email}</dd>
                  </div>
                </dl>
                <div className="mt-6">
                  <Button variant="outline" onClick={() => setOwnerDialogOpen(true)}>
                    <Crown className="mr-2 h-4 w-4" />
                    Transfer Ownership
                  </Button>
                </div>
              </>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <p>No primary owner assigned.</p>
                <Button variant="outline" className="mt-4" onClick={() => setOwnerDialogOpen(true)}>
                  <Crown className="mr-2 h-4 w-4" />
                  Assign Owner
                </Button>
              </div>
            )}
          </div>

          {/* Staff Management Link */}
          <div className="md:col-span-2 rounded-lg border bg-card p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Shop Staff Management
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  View and manage staff members for this shop
                </p>
              </div>
              <Button onClick={() => router.push(`/dashboard/staff?shop_id=${shopId}`)}>
                <Eye className="mr-2 h-4 w-4" />
                Manage Staff
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Managers Tab */}
      {activeTab === "managers" && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold">Assigned Platform Managers</h2>
            <Button onClick={() => setAssignDialogOpen(true)}>
              <UserPlus className="mr-2 h-4 w-4" />
              Assign Manager
            </Button>
          </div>

          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Manager</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Assigned</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {managers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                      No platform managers assigned to this shop.
                    </TableCell>
                  </TableRow>
                ) : (
                  managers.map((manager) => (
                    <TableRow key={manager.id}>
                      <TableCell className="font-medium">{manager.user.full_name}</TableCell>
                      <TableCell>{manager.user.email}</TableCell>
                      <TableCell>
                        <Badge variant={manager.is_active ? "success" : "muted"}>
                          {manager.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatDate(manager.created_at)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleToggleManager(manager)}
                            title={manager.is_active ? "Deactivate" : "Activate"}
                            className={manager.is_active ? "text-yellow-600" : "text-green-600"}
                          >
                            {manager.is_active ? <ShieldX className="h-4 w-4" /> : <ShieldCheck className="h-4 w-4" />}
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleUnassignManager(manager.user_id)}
                            title="Unassign"
                            className="text-red-600"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {/* Edit Shop Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Shop</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEditShop}>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <label htmlFor="edit-name" className="text-sm font-medium">Name</label>
                <Input
                  id="edit-name"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  required
                  disabled={editLoading}
                />
              </div>
              <div className="grid gap-2">
                <label htmlFor="edit-slug" className="text-sm font-medium">Slug</label>
                <Input
                  id="edit-slug"
                  value={editForm.slug}
                  onChange={(e) => setEditForm({ ...editForm, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "") })}
                  required
                  disabled={editLoading}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEditDialogOpen(false)} disabled={editLoading}>
                Cancel
              </Button>
              <Button type="submit" disabled={editLoading}>
                {editLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Save Changes
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Assign Manager Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign Platform Manager</DialogTitle>
            <DialogDescription>
              Enter the User ID of a platform manager to assign them to this shop.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleAssignManager}>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <label htmlFor="manager-user-id" className="text-sm font-medium">User ID</label>
                <Input
                  id="manager-user-id"
                  type="number"
                  value={assignForm.user_id}
                  onChange={(e) => setAssignForm({ ...assignForm, user_id: e.target.value })}
                  placeholder="e.g., 5"
                  required
                  disabled={assignLoading}
                />
              </div>
              <div className="flex items-center gap-2">
                <Input
                  type="checkbox"
                  id="manager-active"
                  checked={assignForm.is_active}
                  onChange={(e) => setAssignForm({ ...assignForm, is_active: e.target.checked })}
                />
                <label htmlFor="manager-active" className="text-sm">
                  Active assignment
                </label>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setAssignDialogOpen(false)} disabled={assignLoading}>
                Cancel
              </Button>
              <Button type="submit" disabled={assignLoading}>
                {assignLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Assign Manager
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Change Owner Dialog */}
      <Dialog open={ownerDialogOpen} onOpenChange={setOwnerDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Transfer Ownership</DialogTitle>
            <DialogDescription>
              Enter the User ID of an active shop member to become the new primary owner.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleChangeOwner}>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <label htmlFor="new-owner-id" className="text-sm font-medium">New Owner User ID</label>
                <Input
                  id="new-owner-id"
                  type="number"
                  value={ownerForm.new_owner_user_id}
                  onChange={(e) => setOwnerForm({ ...ownerForm, new_owner_user_id: e.target.value })}
                  placeholder="e.g., 12"
                  required
                  disabled={ownerLoading}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOwnerDialogOpen(false)} disabled={ownerLoading}>
                Cancel
              </Button>
              <Button type="submit" disabled={ownerLoading} variant="destructive">
                {ownerLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Transfer Ownership
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function ShopDetailPage() {
  return (
    <ProtectedRoute>
      <ShopDetailContent />
    </ProtectedRoute>
  );
}