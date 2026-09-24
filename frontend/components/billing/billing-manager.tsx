"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { formatCurrency } from "@/lib/utils";
import { Plus, Edit, Trash2, Save, X, Eye, Receipt, DollarSign,
  Minus, AlertCircle, CheckCircle, Loader2, CreditCard, Banknote,
  ArrowLeft, ArrowRight, RefreshCw, FileText, Shield, AlertTriangle,
  ChevronDown, ChevronUp
} from "lucide-react";
import {
  BillingResponse,
  BillingItemResponse,
  PaymentResponse,
  BillingItemCreate,
  BillingItemUpdate,
  PaymentCreate,
  PaymentFormData,
  PaymentMethod,
  BillingStatus,
  PaymentStatus,
  BillingFormData,
  PAYMENT_METHOD_LABELS,
  PAYMENT_STATUS_LABELS,
  BILLING_STATUS_LABELS,
  DISCOUNT_TYPE_LABELS,
  DiscountType,
  BillingCalculationPreview,
} from "@/src/types/billing";
import { billingApi } from "@/lib/api";

interface BillingManagerProps {
  shopId: number;
  applicationId: number;
  applicationNumber: string;
  serviceName: string;
  serviceBasePrice: number;
  customerName: string;
  canCreate: boolean;
  canUpdate: boolean;
  canDiscount: boolean;
  canCharge: boolean;
  canVoid: boolean;
  canPaymentCreate: boolean;
  canPaymentView: boolean;
  onBillingCreated?: () => void;
}

export function BillingManager({
  shopId,
  applicationId,
  applicationNumber,
  serviceName,
  serviceBasePrice,
  customerName,
  canCreate,
  canUpdate,
  canDiscount,
  canCharge,
  canVoid,
  canPaymentCreate,
  canPaymentView,
  onBillingCreated,
}: BillingManagerProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [billing, setBilling] = useState<BillingResponse | null>(null);
  const [payments, setPayments] = useState<PaymentResponse[]>([]);
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [creatingPayment, setCreatingPayment] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showPaymentDialog, setShowPaymentDialog] = useState(false);
  const [showPreviewDialog, setShowPreviewDialog] = useState(false);
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [previewData, setPreviewData] = useState<BillingCalculationPreview | null>(null);

  // Form states
  const [createForm, setCreateForm] = useState<BillingFormData>({
    items: [
      {
        name: serviceName,
        description: `Service: ${serviceName}`,
        amount: serviceBasePrice,
        is_service_item: true,
        service_id: undefined,
        sort_order: 0,
      },
    ],
    discount_type: undefined,
    discount_value: undefined,
    discount_reason: "",
    notes: "",
  });

  const [editForm, setEditForm] = useState<Partial<BillingFormData>>({});

  const [itemForm, setItemForm] = useState<BillingItemCreate>({
    name: "",
    description: "",
    amount: 0,
    is_service_item: false,
    service_id: undefined,
    sort_order: 0,
  });

  const [paymentForm, setPaymentForm] = useState<PaymentFormData>({
    amount: 0,
    payment_method: "cash",
    reference_number: "",
    reference_exception: false,
    reference_exception_reason: "",
    notes: "",
  });

  const isDigitalPayment = (method: PaymentMethod) =>
    method !== "cash";

  const requiresReference = (method: PaymentMethod) =>
    isDigitalPayment(method);

  const fetchBilling = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await billingApi.getBilling(shopId, applicationId);
      setBilling(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  }, [shopId, applicationId]);

  const fetchPayments = useCallback(async () => {
    if (!billing) return;
    try {
      const data = await billingApi.listPayments(shopId, billing.id);
      setPayments(data.items);
    } catch (err) {
      console.error("Failed to fetch payments:", err);
    }
  }, [shopId, billing]);

  useEffect(() => {
    fetchBilling();
  }, [fetchBilling]);

  useEffect(() => {
    fetchPayments();
  }, [fetchPayments]);

  const handlePreviewCalculation = async () => {
    if (createForm.items.length === 0) return;
    try {
      const data = await billingApi.previewBilling(shopId, {
        items: createForm.items,
        discount_type: createForm.discount_type,
        discount_value: createForm.discount_value,
      });
      setPreviewData(data);
      setShowPreviewDialog(true);
    } catch (err) {
      console.error("Failed to preview calculation:", err);
    }
  };

  const handleCreateBilling = async () => {
    if (createForm.items.length === 0) {
      setError("At least one line item is required");
      return;
    }
    if (createForm.discount_type && createForm.discount_value && !createForm.discount_reason) {
      setError("Discount reason is required");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      const data = await billingApi.createBilling(shopId, applicationId, {
        application_id: applicationId,
        ...createForm,
      });
      setBilling(data);
      setShowCreateDialog(false);
      onBillingCreated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateBilling = async () => {
    if (!billing) return;
    setSaving(true);
    setError(null);
    try {
      const data = await billingApi.updateBilling(shopId, billing.id, editForm);
      setBilling(data);
      setShowEditDialog(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setSaving(false);
    }
  };

  const handleAddItem = async () => {
    if (!billing || itemForm.name.trim() === "" || itemForm.amount <= 0) return;
    setSaving(true);
    try {
      const data = await billingApi.addBillingItem(shopId, billing.id, itemForm);
      setBilling(prev => prev ? { ...prev, items: [...prev.items, data] } : null);
      setItemForm({ name: "", description: "", amount: 0, is_service_item: false, sort_order: 0 });
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateItem = async () => {
    if (!billing || editingItemId === null) return;
    setSaving(true);
    try {
      const data = await billingApi.updateBillingItem(shopId, billing.id, editingItemId, itemForm);
      setBilling(prev => prev ? {
        ...prev,
        items: prev.items.map(i => i.id === editingItemId ? data : i)
      } : null);
      setEditingItemId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteItem = async (itemId: number) => {
    if (!billing || !confirm("Delete this line item?")) return;
    setSaving(true);
    try {
      await billingApi.deleteBillingItem(shopId, billing.id, itemId);
      setBilling(prev => prev ? { ...prev, items: prev.items.filter(i => i.id !== itemId) } : null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setSaving(false);
    }
  };

  const startEditItem = (item: BillingItemResponse) => {
    setItemForm({
      name: item.name,
      description: item.description || "",
      amount: item.amount,
      is_service_item: item.is_service_item,
      service_id: item.service_id,
      sort_order: item.sort_order,
    });
    setEditingItemId(item.id);
  };

  const handleCreatePayment = async () => {
    if (!billing) return;
    if (paymentForm.amount <= 0) {
      setError("Payment amount must be greater than zero");
      return;
    }
    if (paymentForm.amount > (billing.balance_amount || 0)) {
      setError("Payment amount exceeds outstanding balance");
      return;
    }
    if (requiresReference(paymentForm.payment_method) && !paymentForm.reference_exception && !paymentForm.reference_number?.trim()) {
      setError("Reference number is required for digital payments");
      return;
    }
    if (paymentForm.reference_exception && !paymentForm.reference_exception_reason?.trim()) {
      setError("Exception reason is required when reference is unavailable");
      return;
    }
    setCreatingPayment(true);
    setError(null);
    try {
      const data = await billingApi.createPayment(shopId, billing.id, paymentForm);
      setPayments(prev => [...prev, data]);
      setBilling(prev => prev ? {
        ...prev,
        amount_paid: data.amount + (prev.amount_paid || 0),
        balance_amount: Math.max(0, (prev.balance_amount || 0) - data.amount),
        payment_status: data.amount + (prev.amount_paid || 0) >= (prev.total_amount || 0) ? "paid" :
          data.amount + (prev.amount_paid || 0) > 0 ? "partially_paid" : "unpaid",
      } : null);
      setShowPaymentDialog(false);
      setPaymentForm({ amount: 0, payment_method: "cash", reference_number: "", reference_exception: false, reference_exception_reason: "", notes: "" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setCreatingPayment(false);
    }
  };

  const handleIssueBilling = async () => {
    if (!billing || !confirm("Issue this billing? This will change status from Draft to Issued.")) return;
    setSaving(true);
    try {
      const data = await billingApi.issueBilling(shopId, billing.id);
      setBilling(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setSaving(false);
    }
  };

  const handleVoidBilling = async () => {
    if (!billing || !confirm("Void this billing? This action cannot be undone.")) return;
    setSaving(true);
    try {
      const data = await billingApi.voidBilling(shopId, billing.id);
      setBilling(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setSaving(false);
    }
  };

  const getStatusBadge = (status: string, type: "billing" | "payment") => {
    if (type === "billing") {
      const config: Record<BillingStatus, { variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info"; label: string }> = {
        draft: { variant: "secondary", label: "Draft" },
        issued: { variant: "default", label: "Issued" },
        void: { variant: "destructive", label: "Void" },
      };
      const c = config[status as BillingStatus] || { variant: "secondary", label: status };
      return <Badge variant={c.variant}>{c.label}</Badge>;
    } else {
      const config: Record<PaymentStatus, { variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info"; label: string }> = {
        unpaid: { variant: "destructive", label: "Unpaid" },
        partially_paid: { variant: "warning", label: "Partially Paid" },
        paid: { variant: "success", label: "Paid" },
      };
      const c = config[status as PaymentStatus] || { variant: "secondary", label: status };
      return <Badge variant={c.variant}>{c.label}</Badge>;
    }
  };

  const paymentMethodLabel = (method: PaymentMethod) =>
    PAYMENT_METHOD_LABELS.find(l => l.value === method)?.label || method;

  const isDigital = (method: PaymentMethod) => isDigitalPayment(method);

  if (loading) {
    return (
      <Card className="mt-6">
        <CardContent className="py-8 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-2" />
          <p className="text-muted-foreground">Loading billing...</p>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="mt-6 border-destructive">
        <CardContent className="p-4 text-destructive">
          <AlertCircle className="h-5 w-5 mr-2 inline" />
          {error}
        </CardContent>
      </Card>
    );
  }

  if (!billing) {
    if (!canCreate) {
      return (
        <Card className="mt-6">
          <CardContent className="py-8 text-center">
            <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">No Billing Record</h3>
            <p className="text-muted-foreground mb-4">Create a billing record to track payments for this application.</p>
          </CardContent>
        </Card>
      );
    }

    return (
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Create Billing for {applicationNumber}
          </CardTitle>
          <CardDescription>Set up invoice with service amount, additional charges, and discounts</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Service Item (non-editable price) */}
          <div className="bg-muted/50 p-4 rounded-lg border">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
              <Shield className="h-4 w-4" />
              <span>Service price is loaded from service configuration and cannot be freely edited</span>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="sm:col-span-2">
                <Label className="text-xs text-muted-foreground">Service</Label>
                <Input value={serviceName} disabled />
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Base Price</Label>
                <Input value={formatCurrency(serviceBasePrice)} disabled />
              </div>
            </div>
          </div>

          {/* Line Items */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <Label>Line Items</Label>
              <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
                <DialogTrigger asChild>
                  <Button size="sm"><Plus className="h-4 w-4 mr-1" /> Add Charge</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add Additional Charge</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="item-name">Charge Name</Label>
                      <Input
                        id="item-name"
                        value={itemForm.name}
                        onChange={e => setItemForm(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="e.g., Printing, Courier, Service Fee"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="item-description">Description (Optional)</Label>
                      <Textarea
                        id="item-description"
                        value={itemForm.description}
                        onChange={e => setItemForm(prev => ({ ...prev, description: e.target.value }))}
                        rows={2}
                      />
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-2">
                        <Label htmlFor="item-amount">Amount</Label>
                        <Input
                          id="item-amount"
                          type="number"
                          step="0.01"
                          min="0"
                          value={itemForm.amount}
                          onChange={e => setItemForm(prev => ({ ...prev, amount: parseFloat(e.target.value) || 0 }))}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Type</Label>
                        <Select value={itemForm.is_service_item ? "service" : "charge"} onValueChange={v => setItemForm(prev => ({ ...prev, is_service_item: v === "service" }))}>
                          <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="charge">Non-Service Charge</SelectItem>
                            <SelectItem value="service">Service Item</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="flex justify-end gap-2 pt-4 border-t">
                      <Button variant="outline" onClick={() => { setShowCreateDialog(false); setItemForm({ name: "", description: "", amount: 0, is_service_item: false, sort_order: 0 }); }}>Cancel</Button>
                      <Button onClick={handleAddItem} disabled={saving || itemForm.name.trim() === "" || itemForm.amount <= 0}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Add"}</Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
            {createForm.items.map((item, index) => (
              <div key={index} className="flex items-center gap-3 p-3 border rounded-lg bg-background mb-2">
                <div className="flex-1 min-w-0">
                  <p className="font-medium">{item.name} {item.is_service_item && <Badge variant="secondary" className="ml-2 text-xs">Service</Badge>}</p>
                  {item.description && <p className="text-sm text-muted-foreground">{item.description}</p>}
                </div>
                <div className="font-mono text-right whitespace-nowrap">{formatCurrency(item.amount)}</div>
                {index > 0 && (
                  <Button variant="ghost" size="icon" onClick={() => {
                    const newItems = [...createForm.items];
                    newItems.splice(index, 1);
                    setCreateForm(prev => ({ ...prev, items: newItems }));
                  }}><Trash2 className="h-4 w-4 text-destructive" /></Button>
                )}
              </div>
            ))}
          </div>

          {/* Discount */}
          <div>
            <Label>Discount</Label>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="discount-type">Type</Label>
                <Select value={createForm.discount_type || ""} onValueChange={v => setCreateForm(prev => ({ ...prev, discount_type: v as DiscountType || undefined }))}>
                  <SelectTrigger><SelectValue placeholder="Select discount type" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="fixed">Fixed Amount</SelectItem>
                    <SelectItem value="percentage">Percentage</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="discount-value">Value</Label>
                <Input
                  id="discount-value"
                  type="number"
                  step="0.01"
                  min="0"
                  value={createForm.discount_value || ""}
                  onChange={e => setCreateForm(prev => ({ ...prev, discount_value: parseFloat(e.target.value) || undefined }))}
                  placeholder={createForm.discount_type === "percentage" ? "e.g., 10" : "e.g., 50"}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="discount-reason">Reason (Required)</Label>
                <Input
                  id="discount-reason"
                  value={createForm.discount_reason}
                  onChange={e => setCreateForm(prev => ({ ...prev, discount_reason: e.target.value }))}
                  placeholder="e.g., Student discount, Loyalty, Manager approval"
                />
              </div>
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Internal Notes</Label>
            <Textarea
              id="notes"
              value={createForm.notes}
              onChange={e => setCreateForm(prev => ({ ...prev, notes: e.target.value }))}
              rows={3}
              placeholder="Optional internal notes..."
            />
          </div>

          {/* Preview & Create */}
          <div className="flex gap-3 pt-4 border-t">
            <Button variant="outline" onClick={handlePreviewCalculation}><Eye className="h-4 w-4 mr-1" /> Preview</Button>
            <Button onClick={handleCreateBilling} disabled={creating} className="ml-auto">
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : "Create Billing"}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Render existing billing
  return (
    <div className="mt-6 space-y-6">
      {/* Billing Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-5 w-5" />
                Billing: {billing.invoice_number}
              </CardTitle>
              <CardDescription>Application: {applicationNumber} | Service: {serviceName} | Customer: {customerName}</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {getStatusBadge(billing.billing_status, "billing")}
              {getStatusBadge(billing.payment_status, "payment")}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Summary */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="p-4 bg-muted/50 rounded-lg">
              <Label className="text-xs text-muted-foreground">Subtotal</Label>
              <p className="text-2xl font-bold">{formatCurrency(billing.subtotal)}</p>
            </div>
            <div className="p-4 bg-muted/50 rounded-lg">
              <Label className="text-xs text-muted-foreground">Discount</Label>
              <p className="text-2xl font-bold text-green-600">-{formatCurrency(billing.discount_amount)}</p>
            </div>
            <div className="p-4 bg-primary/10 rounded-lg border border-primary/20">
              <Label className="text-xs text-muted-foreground">Total</Label>
              <p className="text-2xl font-bold text-primary">{formatCurrency(billing.total_amount)}</p>
            </div>
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <Label className="text-xs text-muted-foreground">Paid</Label>
              <p className="text-2xl font-bold text-green-600">{formatCurrency(billing.amount_paid)}</p>
            </div>
          </div>

          <hr className="my-4 border-muted" />

          {/* Balance */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
              <Label className="text-xs text-muted-foreground">Balance Due</Label>
              <p className="text-2xl font-bold text-amber-600">{formatCurrency(billing.balance_amount)}</p>
            </div>
            <div className="p-4 bg-muted/50 rounded-lg">
              <Label className="text-xs text-muted-foreground">Status</Label>
              <div className="flex items-center gap-2">
                {getStatusBadge(billing.payment_status, "payment")}
              </div>
            </div>
          </div>

          {/* Line Items Table */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <Label>Line Items</Label>
              {canCharge && billing.billing_status === "draft" && billing.amount_paid === 0 && (
                <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
                  <DialogTrigger asChild>
                    <Button size="sm" variant="outline"><Plus className="h-4 w-4 mr-1" /> Add Charge</Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Add Additional Charge</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                      <div className="space-y-2">
                        <Label htmlFor="item-name">Charge Name</Label>
                        <Input
                          id="item-name"
                          value={itemForm.name}
                          onChange={e => setItemForm(prev => ({ ...prev, name: e.target.value }))}
                          placeholder="e.g., Printing, Courier, Service Fee"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="item-description">Description (Optional)</Label>
                        <Textarea
                          id="item-description"
                          value={itemForm.description}
                          onChange={e => setItemForm(prev => ({ ...prev, description: e.target.value }))}
                          rows={2}
                        />
                      </div>
                      <div className="grid gap-4 sm:grid-cols-2">
                        <div className="space-y-2">
                          <Label htmlFor="item-amount">Amount</Label>
                          <Input
                            id="item-amount"
                            type="number"
                            step="0.01"
                            min="0"
                            value={itemForm.amount}
                            onChange={e => setItemForm(prev => ({ ...prev, amount: parseFloat(e.target.value) || 0 }))}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Type</Label>
                          <Select value={itemForm.is_service_item ? "service" : "charge"} onValueChange={v => setItemForm(prev => ({ ...prev, is_service_item: v === "service" }))}>
                            <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="charge">Non-Service Charge</SelectItem>
                              <SelectItem value="service">Service Item</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div className="flex justify-end gap-2 pt-4 border-t">
                        <Button variant="outline" onClick={() => { setShowCreateDialog(false); setItemForm({ name: "", description: "", amount: 0, is_service_item: false, sort_order: 0 }); }}>Cancel</Button>
                        <Button onClick={handleAddItem} disabled={saving || itemForm.name.trim() === "" || itemForm.amount <= 0}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Add"}</Button>
                      </div>
                    </div>
                  </DialogContent>
                </Dialog>
              )}
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Item</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead className="text-center">Type</TableHead>
                    {billing.billing_status === "draft" && billing.amount_paid === 0 && canCharge && <TableHead className="text-center">Actions</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {billing.items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{item.name}</p>
                          {item.description && <p className="text-sm text-muted-foreground">{item.description}</p>}
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-right">{formatCurrency(item.amount)}</TableCell>
                      <TableCell className="text-center">
                        <Badge variant={item.is_service_item ? "secondary" : "outline"}>
                          {item.is_service_item ? "Service" : "Charge"}
                        </Badge>
                      </TableCell>
                      {billing.billing_status === "draft" && billing.amount_paid === 0 && canCharge && (
                        <TableCell className="text-center">
                          <div className="flex items-center justify-center gap-1">
                            <Button variant="ghost" size="icon" onClick={() => startEditItem(item)}><Edit className="h-4 w-4" /></Button>
                            <Button variant="ghost" size="icon" onClick={() => handleDeleteItem(item.id)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
                          </div>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>

          {/* Discount Display */}
          {billing.discount_amount > 0 && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-green-600" />
                  <div>
                    <p className="font-medium">Discount Applied</p>
                    <p className="text-sm text-green-700">
                      {DISCOUNT_TYPE_LABELS[billing.discount_type as DiscountType] || billing.discount_type}: {billing.discount_value}
                      {billing.discount_type === "percentage" ? "%" : formatCurrency(billing.discount_value || 0)}
                    </p>
                  </div>
                </div>
                <div className="font-mono text-green-600">-{formatCurrency(billing.discount_amount)}</div>
              </div>
              {billing.discount_reason && (
                <p className="mt-2 text-sm text-green-700"><strong>Reason:</strong> {billing.discount_reason}</p>
              )}
            </div>
          )}

          {/* Notes */}
          {billing.notes && (
            <div className="bg-muted/50 rounded-lg p-4">
              <Label className="text-xs text-muted-foreground">Notes</Label>
              <p>{billing.notes}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-wrap gap-3 pt-4 border-t">
            {canUpdate && billing.billing_status === "draft" && billing.amount_paid === 0 && (
              <Button variant="outline" onClick={() => {
                setEditForm({
                  notes: billing.notes,
                  discount_type: billing.discount_type,
                  discount_value: billing.discount_value,
                  discount_reason: billing.discount_reason,
                });
                setShowEditDialog(true);
              }}>
                <Edit className="h-4 w-4 mr-1" /> Edit Details
              </Button>
            )}
            {canVoid && billing.billing_status !== "void" && billing.amount_paid === 0 && (
              <Button variant="destructive" onClick={handleVoidBilling} disabled={saving}>
                <Shield className="h-4 w-4 mr-1" /> Void Billing
              </Button>
            )}
            {billing.billing_status === "draft" && (
              <Button variant="secondary" onClick={handleIssueBilling} disabled={saving}>
                <FileText className="h-4 w-4 mr-1" /> Issue Billing
              </Button>
            )}
            {canPaymentCreate && billing.balance_amount > 0 && billing.billing_status !== "void" && (
              <Button onClick={() => setShowPaymentDialog(true)}>
                <CreditCard className="h-4 w-4 mr-1" /> Record Payment
              </Button>
            )}
            {canPaymentView && payments.length > 0 && (
              <Button variant="outline" asChild>
                <a href={`/dashboard/applications/${applicationId}/billing/${billing.id}/receipt`} target="_blank" rel="noopener noreferrer">
                  <Receipt className="h-4 w-4 mr-1" /> View Receipt
                </a>
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Payments History */}
      {canPaymentView && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Banknote className="h-5 w-5" />
              Payment History ({payments.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {payments.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">No payments recorded yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Amount</TableHead>
                      <TableHead>Method</TableHead>
                      <TableHead>Reference</TableHead>
                      <TableHead>Recorded By</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {payments.map((payment) => (
                      <TableRow key={payment.id}>
                        <TableCell>{new Date(payment.paid_at).toLocaleString()}</TableCell>
                        <TableCell className="font-mono">{formatCurrency(payment.amount)}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{paymentMethodLabel(payment.payment_method)}</Badge>
                        </TableCell>
                        <TableCell>
                          {payment.reference_exception ? (
                            <span className="text-sm text-amber-600">Exception: {payment.reference_exception_reason}</span>
                          ) : (
                            payment.reference_number || <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell>{payment.recorder_name || payment.recorded_by}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Edit Billing Dialog */}
      {showEditDialog && billing && (
        <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Edit Billing Details</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="edit-notes">Notes</Label>
                <Textarea
                  id="edit-notes"
                  value={editForm.notes || ""}
                  onChange={e => setEditForm(prev => ({ ...prev, notes: e.target.value }))}
                  rows={3}
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="edit-discount-type">Discount Type</Label>
                  <Select value={editForm.discount_type || ""} onValueChange={v => setEditForm(prev => ({ ...prev, discount_type: v as DiscountType || undefined }))}>
                    <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="fixed">Fixed Amount</SelectItem>
                      <SelectItem value="percentage">Percentage</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-discount-value">Discount Value</Label>
                  <Input
                    id="edit-discount-value"
                    type="number"
                    step="0.01"
                    min="0"
                    value={editForm.discount_value || ""}
                    onChange={e => setEditForm(prev => ({ ...prev, discount_value: parseFloat(e.target.value) || undefined }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-discount-reason">Reason</Label>
                  <Input
                    id="edit-discount-reason"
                    value={editForm.discount_reason || ""}
                    onChange={e => setEditForm(prev => ({ ...prev, discount_reason: e.target.value }))}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button variant="outline" onClick={() => setShowEditDialog(false)}>Cancel</Button>
                <Button onClick={handleUpdateBilling} disabled={saving}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save Changes"}</Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Payment Dialog */}
      {showPaymentDialog && billing && (
        <Dialog open={showPaymentDialog} onOpenChange={setShowPaymentDialog}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Record Payment</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              {/* Balance Info */}
              <div className="bg-muted/50 p-4 rounded-lg">
                <div className="grid gap-2 sm:grid-cols-3 text-sm">
                  <div><Label className="text-muted-foreground">Invoice Total</Label> <p className="font-mono">{formatCurrency(billing.total_amount)}</p></div>
                  <div><Label className="text-muted-foreground">Already Paid</Label> <p className="font-mono text-green-600">{formatCurrency(billing.amount_paid)}</p></div>
                  <div><Label className="text-muted-foreground">Balance Due</Label> <p className="font-mono text-amber-600">{formatCurrency(billing.balance_amount)}</p></div>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="payment-amount">Amount <span className="text-destructive">*</span></Label>
                <Input
                  id="payment-amount"
                  type="number"
                  step="0.01"
                  min="0.01"
                  max={billing.balance_amount}
                  value={paymentForm.amount}
                  onChange={e => setPaymentForm(prev => ({ ...prev, amount: parseFloat(e.target.value) || 0 }))}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="payment-method">Payment Method <span className="text-destructive">*</span></Label>
                <Select value={paymentForm.payment_method} onValueChange={v => setPaymentForm(prev => ({ ...prev, payment_method: v as PaymentMethod }))}>
                  <SelectTrigger><SelectValue placeholder="Select payment method" /></SelectTrigger>
                  <SelectContent>
                    {PAYMENT_METHOD_LABELS.map(m => (
                      <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {isDigital(paymentForm.payment_method) && !paymentForm.reference_exception && (
                <div className="space-y-2">
                  <Label htmlFor="payment-reference">Reference Number <span className="text-destructive">*</span></Label>
                  <Input
                    id="payment-reference"
                    value={paymentForm.reference_number}
                    onChange={e => setPaymentForm(prev => ({ ...prev, reference_number: e.target.value }))}
                    placeholder={paymentForm.payment_method === "upi" ? "UPI Transaction ID" : paymentForm.payment_method === "card" ? "Card Transaction ID" : "Reference Number"}
                  />
                </div>
              )}

              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={paymentForm.reference_exception}
                    onChange={e => setPaymentForm(prev => ({ ...prev, reference_exception: e.target.checked, reference_number: e.target.checked ? "" : prev.reference_number }))}
                    className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                  />
                  Reference number not available
                </Label>
              </div>

              {paymentForm.reference_exception && (
                <div className="space-y-2">
                  <Label htmlFor="payment-exception-reason">Exception Reason <span className="text-destructive">*</span></Label>
                  <Textarea
                    id="payment-exception-reason"
                    value={paymentForm.reference_exception_reason}
                    onChange={e => setPaymentForm(prev => ({ ...prev, reference_exception_reason: e.target.value }))}
                    rows={2}
                    placeholder="e.g., Customer didn't provide it, Reference number unavailable, Payment verified manually"
                  />
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="payment-notes">Notes</Label>
                <Textarea
                  id="payment-notes"
                  value={paymentForm.notes}
                  onChange={e => setPaymentForm(prev => ({ ...prev, notes: e.target.value }))}
                  rows={2}
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button variant="outline" onClick={() => { setShowPaymentDialog(false); setPaymentForm({ amount: 0, payment_method: "cash", reference_number: "", reference_exception: false, reference_exception_reason: "", notes: "" }); }}>Cancel</Button>
                <Button onClick={handleCreatePayment} disabled={creatingPayment}>{creatingPayment ? <Loader2 className="h-4 w-4 animate-spin" /> : "Record Payment"}</Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Preview Dialog */}
      {showPreviewDialog && previewData && (
        <Dialog open={showPreviewDialog} onOpenChange={setShowPreviewDialog}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Billing Calculation Preview</DialogTitle>
            </DialogHeader>
            <div className="space-y-3 py-4">
              <div className="flex justify-between"><span>Service Amount</span> <span className="font-mono">{formatCurrency(previewData.service_amount)}</span></div>
              <div className="flex justify-between"><span>Additional Charges</span> <span className="font-mono">{formatCurrency(previewData.non_service_charges)}</span></div>
              <hr className="my-4 border-muted" />
              <div className="flex justify-between"><span>Subtotal</span> <span className="font-mono font-medium">{formatCurrency(previewData.subtotal)}</span></div>
              {previewData.discount_type && (
                <>
                  <div className="flex justify-between text-green-600">
                    <span>Discount ({DISCOUNT_TYPE_LABELS[previewData.discount_type]}: {previewData.discount_value}{previewData.discount_type === "percentage" ? "%" : ""})</span>
                    <span className="font-mono">-{formatCurrency(previewData.discount_amount)}</span>
                  </div>
                  <hr className="my-4 border-muted" />
                </>
              )}
              <div className="flex justify-between text-lg font-bold">
                <span>Total</span> <span className="font-mono text-primary">{formatCurrency(previewData.total_amount)}</span>
              </div>
            </div>
            <div className="flex justify-end pt-4 border-t">
              <Button onClick={() => setShowPreviewDialog(false)}>Close</Button>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Edit Item Dialog */}
      {editingItemId !== null && billing && (
        <Dialog open={true} onOpenChange={(open) => !open && setEditingItemId(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Line Item</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="edit-item-name">Name</Label>
                <Input
                  id="edit-item-name"
                  value={itemForm.name}
                  onChange={e => setItemForm(prev => ({ ...prev, name: e.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-item-description">Description</Label>
                <Textarea
                  id="edit-item-description"
                  value={itemForm.description}
                  onChange={e => setItemForm(prev => ({ ...prev, description: e.target.value }))}
                  rows={2}
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="edit-item-amount">Amount</Label>
                  <Input
                    id="edit-item-amount"
                    type="number"
                    step="0.01"
                    min="0"
                    value={itemForm.amount}
                    onChange={e => setItemForm(prev => ({ ...prev, amount: parseFloat(e.target.value) || 0 }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Type</Label>
                  <Select value={itemForm.is_service_item ? "service" : "charge"} onValueChange={v => setItemForm(prev => ({ ...prev, is_service_item: v === "service" }))}>
                    <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="charge">Non-Service Charge</SelectItem>
                      <SelectItem value="service">Service Item</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button variant="outline" onClick={() => setEditingItemId(null)}>Cancel</Button>
                <Button onClick={handleUpdateItem} disabled={saving}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}</Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}