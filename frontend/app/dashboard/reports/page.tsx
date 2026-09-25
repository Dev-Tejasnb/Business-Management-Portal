"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ProtectedRoute } from "@/components/protected-route";
import { Download, Calendar, ChevronLeft, ChevronRight, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Pagination } from "@/components/ui/pagination";
import { format, subDays, startOfDay, endOfDay, startOfMonth, endOfMonth, startOfWeek, endOfWeek, startOfYear, endOfYear } from "date-fns";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  reportsApi,
  DateRangeRequest,
  DateRangePreset,
  GroupByPeriod,
  SummaryReportResponse,
  RevenueReportResponse,
  CollectionReportResponse,
  PaymentMethodAnalyticsResponse,
  ApplicationReportResponse,
  ServiceReportResponse,
  CustomerReportResponse,
  StaffReportResponse,
  OutstandingReportResponse,
  BillingReportResponse,
  DiscountReportResponse,
  FinancialTrendResponse,
  DocumentAnalyticsResponse,
  OutstandingItem,
  ServiceReportItem,
  StaffReportItem,
  CollectionMethodBreakdown,
  FinancialTrendPoint,
} from "@/lib/api";

const DATE_PRESETS: { value: DateRangePreset; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "yesterday", label: "Yesterday" },
  { value: "last_7_days", label: "Last 7 Days" },
  { value: "last_30_days", label: "Last 30 Days" },
  { value: "this_month", label: "This Month" },
  { value: "last_month", label: "Last Month" },
  { value: "this_year", label: "This Year" },
  { value: "custom", label: "Custom Range" },
];

const GROUP_BY_OPTIONS: { value: GroupByPeriod; label: string }[] = [
  { value: "day", label: "Daily" },
  { value: "week", label: "Weekly" },
  { value: "month", label: "Monthly" },
];

const REPORT_TABS = [
  { id: "summary", label: "Summary", icon: () => <TrendingUp className="h-4 w-4" /> },
  { id: "revenue", label: "Revenue", icon: () => <TrendingUp className="h-4 w-4" /> },
  { id: "collection", label: "Collection", icon: () => <TrendingUp className="h-4 w-4" /> },
  { id: "payment-methods", label: "Payment Methods", icon: () => <TrendingUp className="h-4 w-4" /> },
  { id: "applications", label: "Applications", icon: () => <TrendingUp className="h-4 w-4" /> },
  { id: "services", label: "Services", icon: () => <TrendingUp className="h-4 w-4" /> },
  { id: "customers", label: "Customers", icon: () => <TrendingUp className="h-4 w-4" /> },
  { id: "staff", label: "Staff", icon: () => <TrendingUp className="h-4 w-4" /> },
  { id: "outstanding", label: "Outstanding", icon: () => <TrendingUp className="h-4 w-4" /> },
  { id: "billing", label: "Billing", icon: () => <TrendingUp className="h-4 w-4" /> },
  { id: "discounts", label: "Discounts", icon: () => <TrendingUp className="h-4 w-4" /> },
  { id: "financial-trend", label: "Financial Trend", icon: () => <TrendingUp className="h-4 w-4" /> },
  { id: "documents", label: "Documents", icon: () => <TrendingUp className="h-4 w-4" /> },
] as const;

type ReportTabId = (typeof REPORT_TABS)[number]["id"];

interface DateRangePickerProps {
  value: DateRangeRequest;
  onChange: (value: DateRangeRequest) => void;
  className?: string;
}

function DateRangePicker({ value, onChange, className }: DateRangePickerProps) {
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [showCustom, setShowCustom] = useState(value.preset === "custom");

  useEffect(() => {
    if (value.preset === "custom") {
      setFromDate(value.from_date || "");
      setToDate(value.to_date || "");
      setShowCustom(true);
    } else {
      setShowCustom(false);
    }
  }, [value.preset, value.from_date, value.to_date]);

  const handlePresetChange = (preset: DateRangePreset) => {
    onChange({ preset, from_date: undefined, to_date: undefined });
    if (preset === "custom") {
      setShowCustom(true);
    }
  };

  const handleCustomDateChange = () => {
    if (fromDate && toDate) {
      onChange({ preset: "custom", from_date: fromDate, to_date: toDate });
    }
  };

  return (
    <div className={className}>
      <Select value={value.preset} onValueChange={handlePresetChange}>
        <SelectTrigger className="w-[180px]">
          <Calendar className="mr-2 h-4 w-4" />
          <SelectValue placeholder="Select period" />
        </SelectTrigger>
        <SelectContent>
          {DATE_PRESETS.map((preset) => (
            <SelectItem key={preset.value} value={preset.value}>
              {preset.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {showCustom && (
        <div className="flex items-center gap-2 ml-2">
          <Input
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            placeholder="From"
            className="w-[150px]"
          />
          <span className="text-muted-foreground">to</span>
          <Input
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            placeholder="To"
            className="w-[150px]"
          />
          <Button variant="outline" size="sm" onClick={handleCustomDateChange}>
            Apply
          </Button>
        </div>
      )}
    </div>
  );
}

function KPICard({ title, value, subtitle, trend, icon }: {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: { value: number; label: string; isPositive: boolean };
  icon?: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        {icon && <div className="text-muted-foreground">{icon}</div>}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <div className="flex items-center gap-2 mt-2 text-sm text-muted-foreground">
          {subtitle && <span>{subtitle}</span>}
          {trend && (
            <span className={`flex items-center gap-1 ${trend.isPositive ? "text-green-600" : "text-red-600"}`}>
              {trend.isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {trend.value.toFixed(1)}% {trend.label}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function LineChartComponent({ data, xKey, yKeys, colors, height = 300 }: {
  data: any[];
  xKey: string;
  yKeys: string[];
  colors: string[];
  height?: number;
}) {
  if (!data.length) return <div className="h-[300px] flex items-center justify-center text-muted-foreground">No data available</div>;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        {yKeys.map((key, index) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={colors[index % colors.length]}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

function BarChartComponent({ data, xKey, yKeys, colors, height = 300 }: {
  data: any[];
  xKey: string;
  yKeys: string[];
  colors: string[];
  height?: number;
}) {
  if (!data.length) return <div className="h-[300px] flex items-center justify-center text-muted-foreground">No data available</div>;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        {yKeys.map((key, index) => (
          <Bar key={key} dataKey={key} fill={colors[index % colors.length]} radius={[4, 4, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

function PieChartComponent({ data, dataKey, nameKey, colors, height = 300 }: {
  data: any[];
  dataKey: string;
  nameKey: string;
  colors: string[];
  height?: number;
}) {
  if (!data.length) return <div className="h-[300px] flex items-center justify-center text-muted-foreground">No data available</div>;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={100}
          dataKey={dataKey}
          nameKey={nameKey}
          label={({ name, percent }) => `${name} ${percent ? (percent * 100).toFixed(0) : 0}%`}
        >
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
}

function ExportButton({ onExport, disabled, label = "Export CSV" }: { onExport: () => void; disabled?: boolean; label?: string }) {
  return (
    <Button variant="outline" size="sm" onClick={onExport} disabled={disabled}>
      <Download className="mr-2 h-4 w-4" />
      {label}
    </Button>
  );
}

function Input({ ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" {...props} />;
}

function ReportsContent() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const shopIdParam = searchParams?.get("shop_id");
  const [shopId, setShopId] = useState<number | null>(shopIdParam ? parseInt(shopIdParam, 10) : null);

  const [activeTab, setActiveTab] = useState<ReportTabId>("summary");
  const [dateRange, setDateRange] = useState<DateRangeRequest>({
    preset: (searchParams?.get("preset") as DateRangePreset) || "this_month",
    from_date: searchParams?.get("from_date") || undefined,
    to_date: searchParams?.get("to_date") || undefined,
  });
  const [groupBy, setGroupBy] = useState<GroupByPeriod>((searchParams?.get("group_by") as GroupByPeriod) || "day");
  const [outstandingPage, setOutstandingPage] = useState(1);
  const [outstandingSearch, setOutstandingSearch] = useState("");
  const [outstandingStatus, setOutstandingStatus] = useState("");

  // Data states
  const [summary, setSummary] = useState<SummaryReportResponse | null>(null);
  const [revenue, setRevenue] = useState<RevenueReportResponse | null>(null);
  const [collection, setCollection] = useState<CollectionReportResponse | null>(null);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethodAnalyticsResponse | null>(null);
  const [applications, setApplications] = useState<ApplicationReportResponse | null>(null);
  const [services, setServices] = useState<ServiceReportResponse | null>(null);
  const [customers, setCustomers] = useState<CustomerReportResponse | null>(null);
  const [staff, setStaff] = useState<StaffReportResponse | null>(null);
  const [outstanding, setOutstanding] = useState<OutstandingReportResponse | null>(null);
  const [billing, setBilling] = useState<BillingReportResponse | null>(null);
  const [discounts, setDiscounts] = useState<DiscountReportResponse | null>(null);
  const [financialTrend, setFinancialTrend] = useState<FinancialTrendResponse | null>(null);
  const [documents, setDocuments] = useState<DocumentAnalyticsResponse | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const updateUrlParams = useCallback(() => {
    const params = new URLSearchParams(searchParams?.toString() || "");
    params.set("preset", dateRange.preset);
    if (dateRange.from_date) params.set("from_date", dateRange.from_date);
    if (dateRange.to_date) params.set("to_date", dateRange.to_date);
    if (["applications", "financial-trend"].includes(activeTab)) {
      params.set("group_by", groupBy);
    }
    router.push(`/dashboard/reports?${params.toString()}`);
  }, [dateRange, activeTab, groupBy, router, searchParams]);

  const fetchData = useCallback(async () => {
    if (!shopId) return;

    setLoading(true);
    setError(null);

    try {
      const params = { preset: dateRange.preset, from_date: dateRange.from_date, to_date: dateRange.to_date };

      // Fetch all reports in parallel
      const [
        summaryRes,
        revenueRes,
        collectionRes,
        paymentMethodsRes,
        applicationsRes,
        servicesRes,
        customersRes,
        staffRes,
        outstandingRes,
        billingRes,
        discountsRes,
        financialTrendRes,
        documentsRes,
      ] = await Promise.allSettled([
        reportsApi.getSummary(shopId, params),
        reportsApi.getRevenue(shopId, params),
        reportsApi.getCollection(shopId, params),
        reportsApi.getPaymentMethods(shopId, params),
        reportsApi.getApplications(shopId, { ...params, group_by: groupBy }),
        reportsApi.getServices(shopId, params),
        reportsApi.getCustomers(shopId, params),
        reportsApi.getStaff(shopId, params),
        reportsApi.getOutstanding(shopId, { ...params, page: outstandingPage, page_size: 10, search: outstandingSearch, payment_status: outstandingStatus }),
        reportsApi.getBilling(shopId, params),
        reportsApi.getDiscounts(shopId, params),
        reportsApi.getFinancialTrend(shopId, { ...params, group_by: groupBy }),
        reportsApi.getDocuments(shopId, params),
      ]);

      if (summaryRes.status === "fulfilled") setSummary(summaryRes.value);
      if (revenueRes.status === "fulfilled") setRevenue(revenueRes.value);
      if (collectionRes.status === "fulfilled") setCollection(collectionRes.value);
      if (paymentMethodsRes.status === "fulfilled") setPaymentMethods(paymentMethodsRes.value);
      if (applicationsRes.status === "fulfilled") setApplications(applicationsRes.value);
      if (servicesRes.status === "fulfilled") setServices(servicesRes.value);
      if (customersRes.status === "fulfilled") setCustomers(customersRes.value);
      if (staffRes.status === "fulfilled") setStaff(staffRes.value);
      if (outstandingRes.status === "fulfilled") setOutstanding(outstandingRes.value);
      if (billingRes.status === "fulfilled") setBilling(billingRes.value);
      if (discountsRes.status === "fulfilled") setDiscounts(discountsRes.value);
      if (financialTrendRes.status === "fulfilled") setFinancialTrend(financialTrendRes.value);
      if (documentsRes.status === "fulfilled") setDocuments(documentsRes.value);

      const failed = [summaryRes, revenueRes, collectionRes, paymentMethodsRes, applicationsRes, servicesRes, customersRes, staffRes, outstandingRes, billingRes, discountsRes, financialTrendRes, documentsRes]
        .filter((r) => r.status === "rejected");
      if (failed.length > 0) {
        setError("Some reports failed to load");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch reports");
    } finally {
      setLoading(false);
    }
  }, [shopId, dateRange, groupBy, outstandingPage, outstandingSearch, outstandingStatus]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    updateUrlParams();
  }, [updateUrlParams]);

  const handleDateRangeChange = (newRange: DateRangeRequest) => {
    setDateRange(newRange);
    setOutstandingPage(1);
  };

  const handleGroupByChange = (newGroupBy: GroupByPeriod) => {
    setGroupBy(newGroupBy);
  };

  const handleOutstandingPageChange = (page: number) => {
    setOutstandingPage(page);
  };

  const handleOutstandingSearch = (search: string) => {
    setOutstandingSearch(search);
    setOutstandingPage(1);
  };

  const handleOutstandingStatusChange = (status: string) => {
    setOutstandingStatus(status);
    setOutstandingPage(1);
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!shopId) {
    return (
      <div className="container mx-auto py-8 text-center">
        <h1 className="text-2xl font-bold">Select a shop to view reports</h1>
      </div>
    );
  }

  const formatCurrency = (value: string) => {
    const num = parseFloat(value);
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2 }).format(num);
  };

  const formatNumber = (value: number) => new Intl.NumberFormat("en-IN").format(value);

  const CHART_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"];

  // Summary KPIs
  const summaryKPIs = useMemo(() => {
    if (!summary) return [];
    return [
      { title: "Total Customers", value: formatNumber(summary.total_customers), subtitle: `${summary.new_customers} new this period` },
      { title: "Total Applications", value: formatNumber(summary.total_applications), subtitle: `${summary.pending_applications} pending, ${summary.completed_applications} completed` },
      { title: "Total Billed", value: formatCurrency(summary.total_billed), subtitle: "Invoices issued" },
      { title: "Total Collected", value: formatCurrency(summary.total_collected), subtitle: "Payments received" },
      { title: "Outstanding Balance", value: formatCurrency(summary.outstanding_balance), subtitle: "Amount pending collection" },
    ];
  }, [summary]);

  const renderTabContent = () => {
    switch (activeTab) {
      case "summary": {
        if (!summary) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>;
        return (
          <div className="space-y-6">
            {/* KPI Grid */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
              {summaryKPIs.map((kpi, i) => (
                <KPICard key={i} {...kpi} />
              ))}
            </div>

            {/* Revenue vs Collection Trend */}
            {financialTrend && (
              <Card>
                <CardHeader>
                  <CardTitle>Revenue vs Collection Trend</CardTitle>
                </CardHeader>
                <CardContent>
                  <LineChartComponent
                    data={financialTrend.trend.map((t) => ({
                      period: t.period,
                      billed: parseFloat(t.billed),
                      collected: parseFloat(t.collected),
                    }))}
                    xKey="period"
                    yKeys={["billed", "collected"]}
                    colors={["#3b82f6", "#10b981"]}
                  />
                </CardContent>
              </Card>
            )}

            {/* Collection by Method */}
            {collection && (
              <Card>
                <CardHeader>
                  <CardTitle>Collection by Payment Method</CardTitle>
                </CardHeader>
                <CardContent>
                  <PieChartComponent
                    data={collection.by_method.map((m) => ({ method: m.method, amount: parseFloat(m.total_amount) }))}
                    dataKey="amount"
                    nameKey="method"
                    colors={CHART_COLORS}
                    height={300}
                  />
                </CardContent>
              </Card>
            )}
          </div>
        );
      }

      case "revenue": {
        if (!revenue) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>;
        return (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-4">
              <KPICard title="Total Billed" value={formatCurrency(revenue.total_billed)} subtitle={`${revenue.invoice_count} invoices`} />
              <KPICard title="Total Collected" value={formatCurrency(revenue.total_collected)} subtitle="Payments received" />
              <KPICard title="Outstanding" value={formatCurrency(revenue.total_outstanding)} subtitle="Pending collection" />
              <KPICard title="Total Discounts" value={formatCurrency(revenue.total_discounts)} subtitle="Discounts given" />
            </div>
            <Card>
              <CardHeader>
                <CardTitle>Revenue Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <BarChartComponent
                  data={[{ label: "Billed", value: parseFloat(revenue.total_billed) }, { label: "Collected", value: parseFloat(revenue.total_collected) }, { label: "Outstanding", value: parseFloat(revenue.total_outstanding) }, { label: "Discounts", value: parseFloat(revenue.total_discounts) }]}
                  xKey="label"
                  yKeys={["value"]}
                  colors={["#3b82f6", "#10b981", "#ef4444", "#f59e0b"]}
                />
              </CardContent>
            </Card>
          </div>
        );
      }

      case "collection": {
        if (!collection) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>;
        return (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              <KPICard title="Total Collected" value={formatCurrency(collection.total_collected)} subtitle={`${collection.payment_count} payments`} />
              <KPICard title="Average Payment" value={formatCurrency(collection.average_payment)} subtitle="Per transaction" />
              <KPICard title="Payment Methods" value={collection.by_method.length} subtitle="Active methods" />
            </div>
            <div className="grid gap-6 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Collection by Method</CardTitle>
                </CardHeader>
                <CardContent>
                  <PieChartComponent
                    data={collection.by_method.map((m) => ({ method: m.method, amount: parseFloat(m.total_amount), count: m.count }))}
                    dataKey="amount"
                    nameKey="method"
                    colors={CHART_COLORS}
                    height={300}
                  />
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Payment Count by Method</CardTitle>
                </CardHeader>
                <CardContent>
                  <BarChartComponent
                    data={collection.by_method.map((m) => ({ method: m.method, count: m.count }))}
                    xKey="method"
                    yKeys={["count"]}
                    colors={CHART_COLORS}
                    height={300}
                  />
                </CardContent>
              </Card>
            </div>
          </div>
        );
      }

      case "payment-methods": {
        if (!paymentMethods) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>;
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Payment Method Analytics</CardTitle>
                <ExportButton
                  onExport={async () => {
                    const blob = await reportsApi.exportPaymentMethodsCsv(shopId!, dateRange);
                    downloadBlob(blob, `payment-methods-${format(new Date(), "yyyy-MM-dd")}.csv`);
                  }}
                  disabled={!paymentMethods.methods.length}
                />
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Method</TableHead>
                      <TableHead className="text-right">Count</TableHead>
                      <TableHead className="text-right">Total Amount</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paymentMethods.methods.map((method) => (
                      <TableRow key={method.method}>
                        <TableCell className="capitalize">{method.method}</TableCell>
                        <TableCell className="text-right">{formatNumber(method.count)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(method.total_amount)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        );
      }

      case "applications": {
        if (!applications) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>;
        return (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              <KPICard title="Total Applications" value={formatNumber(applications.total_applications)} />
              <KPICard title="Completed" value={formatNumber(applications.by_status.find(s => s.status === "completed")?.count || 0)} subtitle="Applications completed" />
              <KPICard title="Pending" value={formatNumber(applications.by_status.find(s => s.status === "pending")?.count || 0)} subtitle="Applications pending" />
            </div>
            <div className="grid gap-6 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Applications by Status</CardTitle>
                </CardHeader>
                <CardContent>
                  <PieChartComponent
                    data={applications.by_status.map((s) => ({ status: s.status, count: s.count }))}
                    dataKey="count"
                    nameKey="status"
                    colors={CHART_COLORS}
                    height={300}
                  />
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Application Trend</CardTitle>
                  <Select value={groupBy} onValueChange={handleGroupByChange}>
                    <SelectTrigger className="w-[140px]">
                      <SelectValue placeholder="Group by" />
                    </SelectTrigger>
                    <SelectContent>
                      {GROUP_BY_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </CardHeader>
                <CardContent>
                  <LineChartComponent
                    data={applications.trend.map((t) => ({ period: t.period, count: t.count }))}
                    xKey="period"
                    yKeys={["count"]}
                    colors={["#3b82f6"]}
                    height={300}
                  />
                </CardContent>
              </Card>
            </div>
          </div>
        );
      }

      case "services": {
        if (!services) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>;
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Service Performance</CardTitle>
                <ExportButton
                  onExport={async () => {
                    const blob = await reportsApi.exportServicesCsv(shopId!, dateRange);
                    downloadBlob(blob, `services-${format(new Date(), "yyyy-MM-dd")}.csv`);
                  }}
                  disabled={!services.services.length}
                />
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Service</TableHead>
                      <TableHead className="text-right">Applications</TableHead>
                      <TableHead className="text-right">Completed</TableHead>
                      <TableHead className="text-right">Billed</TableHead>
                      <TableHead className="text-right">Collected</TableHead>
                      <TableHead className="text-right">Outstanding</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {services.services.map((service: ServiceReportItem) => (
                      <TableRow key={service.service_id}>
                        <TableCell className="font-medium">{service.service_name}</TableCell>
                        <TableCell className="text-right">{formatNumber(service.application_count)}</TableCell>
                        <TableCell className="text-right">{formatNumber(service.completed_count)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(service.billed_amount)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(service.collected_amount)}</TableCell>
                        <TableCell className="text-right text-red-600">{formatCurrency(service.outstanding_amount)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        );
      }

      case "customers": {
        if (!customers) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>;
        return (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-4">
              <KPICard title="Total Customers" value={formatNumber(customers.total_customers)} subtitle={`${customers.new_customers} new`} />
              <KPICard title="Active" value={formatNumber(customers.active_customers)} subtitle="Currently active" />
              <KPICard title="With Unpaid Balances" value={formatNumber(customers.customers_with_unpaid_balances)} subtitle="Need follow-up" />
              <KPICard title="Completed Applications" value={formatNumber(customers.customers_with_completed_applications)} subtitle="Have completed apps" />
            </div>
            <Card>
              <CardHeader>
                <CardTitle>Customer Status Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <PieChartComponent
                  data={[
                    { status: "Active", count: customers.active_customers },
                    { status: "Inactive", count: customers.inactive_customers },
                    { status: "Archived", count: customers.archived_customers },
                  ].filter((d) => d.count > 0)}
                  dataKey="count"
                  nameKey="status"
                  colors={["#10b981", "#6b7280", "#ef4444"]}
                  height={300}
                />
              </CardContent>
            </Card>
          </div>
        );
      }

      case "staff": {
        if (!staff) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>;
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Staff Performance</CardTitle>
                <ExportButton
                  onExport={async () => {
                    const blob = await reportsApi.exportStaffCsv(shopId!, dateRange);
                    downloadBlob(blob, `staff-${format(new Date(), "yyyy-MM-dd")}.csv`);
                  }}
                  disabled={!staff.staff.length}
                />
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Staff</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead className="text-right">Assigned</TableHead>
                      <TableHead className="text-right">Created</TableHead>
                      <TableHead className="text-right">Completed</TableHead>
                      <TableHead className="text-right">Payments</TableHead>
                      <TableHead className="text-right">Collected</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {staff.staff.map((s: StaffReportItem) => (
                      <TableRow key={s.staff_id}>
                        <TableCell className="font-medium">{s.staff_name}</TableCell>
                        <TableCell><Badge variant="secondary">{s.role}</Badge></TableCell>
                        <TableCell className="text-right">{formatNumber(s.applications_assigned)}</TableCell>
                        <TableCell className="text-right">{formatNumber(s.applications_created)}</TableCell>
                        <TableCell className="text-right">{formatNumber(s.applications_completed)}</TableCell>
                        <TableCell className="text-right">{formatNumber(s.payments_recorded)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(s.total_collected)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        );
      }

      case "outstanding": {
        if (!outstanding) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>;
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Outstanding Payments</CardTitle>
                <div className="flex items-center gap-2">
                  <ExportButton
                    onExport={async () => {
                      const blob = await reportsApi.exportOutstandingCsv(shopId!, { ...dateRange, search: outstandingSearch, payment_status: outstandingStatus });
                      downloadBlob(blob, `outstanding-${format(new Date(), "yyyy-MM-dd")}.csv`);
                    }}
                    disabled={!outstanding.items.length}
                  />
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col sm:flex-row gap-4 mb-4">
                  <Input
                    placeholder="Search by customer, invoice, application..."
                    value={outstandingSearch}
                    onChange={(e) => handleOutstandingSearch(e.target.value)}
                    className="max-w-md"
                  />
                  <Select value={outstandingStatus} onValueChange={handleOutstandingStatusChange}>
                    <SelectTrigger className="w-[180px]">
                      <SelectValue placeholder="All Statuses" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">All Statuses</SelectItem>
                      <SelectItem value="unpaid">Unpaid</SelectItem>
                      <SelectItem value="partially_paid">Partially Paid</SelectItem>
                      <SelectItem value="paid">Paid</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Invoice</TableHead>
                      <TableHead>Application</TableHead>
                      <TableHead>Customer</TableHead>
                      <TableHead>Service</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead className="text-right">Paid</TableHead>
                      <TableHead className="text-right">Balance</TableHead>
                      <TableHead>Payment Status</TableHead>
                      <TableHead>Billing Status</TableHead>
                      <TableHead>Date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {outstanding.items.map((item: OutstandingItem) => (
                      <TableRow key={item.billing_id}>
                        <TableCell className="font-mono">{item.invoice_number}</TableCell>
                        <TableCell className="font-mono">{item.application_number}</TableCell>
                        <TableCell>{item.customer_name}</TableCell>
                        <TableCell>{item.service_name}</TableCell>
                        <TableCell className="text-right">{formatCurrency(item.total_amount)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(item.paid_amount)}</TableCell>
                        <TableCell className="text-right text-red-600 font-medium">{formatCurrency(item.balance_amount)}</TableCell>
                        <TableCell>
                          <Badge variant={item.payment_status === "paid" ? "default" : item.payment_status === "partially_paid" ? "secondary" : "destructive"}>
                            {item.payment_status.replace("_", " ")}
                          </Badge>
                        </TableCell>
                        <TableCell><Badge variant="outline">{item.billing_status}</Badge></TableCell>
                        <TableCell>{format(new Date(item.invoice_date), "MMM dd, yyyy")}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {outstanding.total_pages > 1 && (
                  <div className="mt-6 flex items-center justify-center">
                    <Pagination
                      totalPages={outstanding.total_pages}
                      currentPage={outstanding.page}
                      onPageChange={handleOutstandingPageChange}
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        );
      }

      case "billing": {
        if (!billing) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>;
        return (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-4">
              <KPICard title="Total Invoices" value={formatNumber(billing.total_invoices)} />
              <KPICard title="Total Billed" value={formatCurrency(billing.total_billed)} />
              <KPICard title="Total Discounts" value={formatCurrency(billing.total_discounted)} />
              <KPICard title="Additional Charges" value={formatCurrency(billing.total_additional_charges)} />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <KPICard title="Total Collected" value={formatCurrency(billing.total_collected)} />
              <KPICard title="Total Outstanding" value={formatCurrency(billing.total_outstanding)} subtitle="Pending collection" />
            </div>
            <Card>
              <CardHeader>
                <CardTitle>Billing Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <BarChartComponent
                  data={[
                    { label: "Billed", value: parseFloat(billing.total_billed) },
                    { label: "Collected", value: parseFloat(billing.total_collected) },
                    { label: "Outstanding", value: parseFloat(billing.total_outstanding) },
                    { label: "Discounts", value: parseFloat(billing.total_discounted) },
                    { label: "Add. Charges", value: parseFloat(billing.total_additional_charges) },
                  ]}
                  xKey="label"
                  yKeys={["value"]}
                  colors={["#3b82f6", "#10b981", "#ef4444", "#f59e0b", "#8b5cf6"]}
                />
              </CardContent>
            </Card>
          </div>
        );
      }

      case "discounts": {
        if (!discounts) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>;
        return (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              <KPICard title="Total Discounts" value={formatCurrency(discounts.total_discount_amount)} subtitle={`${discounts.invoices_with_discount} invoices`} />
              <KPICard title="Invoices with Discount" value={formatNumber(discounts.invoices_with_discount)} />
            </div>
            {discounts.by_date.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Discounts by Date</CardTitle>
                </CardHeader>
                <CardContent>
                  <BarChartComponent
                    data={discounts.by_date.map((d) => ({ date: d.date, amount: parseFloat(d.amount) }))}
                    xKey="date"
                    yKeys={["amount"]}
                    colors={["#f59e0b"]}
                    height={300}
                  />
                </CardContent>
              </Card>
            )}
          </div>
        );
      }

      case "financial-trend": {
        if (!financialTrend) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>;
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Financial Trend</CardTitle>
                <Select value={groupBy} onValueChange={handleGroupByChange}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="Group by" />
                  </SelectTrigger>
                  <SelectContent>
                    {GROUP_BY_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </CardHeader>
              <CardContent>
                <LineChartComponent
                  data={financialTrend.trend.map((t: FinancialTrendPoint) => ({
                    period: t.period,
                    billed: parseFloat(t.billed),
                    collected: parseFloat(t.collected),
                  }))}
                  xKey="period"
                  yKeys={["billed", "collected"]}
                  colors={["#3b82f6", "#10b981"]}
                  height={400}
                />
              </CardContent>
            </Card>
          </div>
        );
      }

      case "documents": {
        if (!documents) return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>;
        return (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-5">
              <KPICard title="Total Documents" value={formatNumber(documents.total_documents)} />
              <KPICard title="Verified" value={formatNumber(documents.verified)} subtitle="Approved" icon={<TrendingUp className="h-4 w-4 text-green-600" />} />
              <KPICard title="Rejected" value={formatNumber(documents.rejected)} subtitle="Rejected" icon={<TrendingDown className="h-4 w-4 text-red-600" />} />
              <KPICard title="Pending" value={formatNumber(documents.pending)} subtitle="Under review" icon={<Minus className="h-4 w-4 text-yellow-600" />} />
              <KPICard title="Missing" value={formatNumber(documents.missing)} subtitle="Not uploaded" icon={<Minus className="h-4 w-4 text-gray-600" />} />
            </div>
            <Card>
              <CardHeader>
                <CardTitle>Document Status Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <PieChartComponent
                  data={[
                    { status: "Verified", count: documents.verified },
                    { status: "Rejected", count: documents.rejected },
                    { status: "Pending", count: documents.pending },
                    { status: "Missing", count: documents.missing },
                  ].filter((d) => d.count > 0)}
                  dataKey="count"
                  nameKey="status"
                  colors={["#10b981", "#ef4444", "#f59e0b", "#6b7280"]}
                  height={300}
                />
              </CardContent>
            </Card>
          </div>
        );
      }

      default:
        return <div className="text-center py-12 text-muted-foreground">Select a report tab</div>;
    }
  };

  return (
    <div className="container mx-auto py-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Reports & Financial Analytics</h1>
          <p className="text-muted-foreground mt-1">Comprehensive business insights and financial reporting</p>
        </div>
        <DateRangePicker value={dateRange} onChange={handleDateRangeChange} />
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-lg bg-destructive/10 text-destructive">
          {error}
        </div>
      )}

      {/* Report Tabs */}
      <div className="mb-6 overflow-x-auto">
        <nav className="flex gap-1" role="tablist" aria-label="Report types">
          {REPORT_TABS.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => { setActiveTab(tab.id); setOutstandingPage(1); }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              }`}
            >
              <span className="flex items-center gap-2">
                <tab.icon />
                {tab.label}
              </span>
            </button>
          ))}
        </nav>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : (
        renderTabContent()
      )}
    </div>
  );
}

export default function ReportsPage() {
  return (
    <ProtectedRoute>
      <ReportsContent />
    </ProtectedRoute>
  );
}