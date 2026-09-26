"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Download, ExternalLink, Loader2 } from "lucide-react";
import { receiptApi } from "@/lib/api";

interface ReceiptViewerProps {
  billingId?: number;
  paymentId?: number;
  shopId: number;
  onClose: () => void;
}

export function ReceiptViewer({
  billingId,
  paymentId,
  shopId,
  onClose,
}: ReceiptViewerProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [signedUrl, setSignedUrl] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [receiptNumber, setReceiptNumber] = useState<string | null>(null);

  const fetchReceipt = useCallback(async () => {
    if (!billingId && !paymentId) {
      setError("No billing or payment ID provided");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let data;
      if (paymentId) {
        data = await receiptApi.getPaymentReceiptPdf(shopId, paymentId);
      } else if (billingId) {
        data = await receiptApi.getInvoicePdf(shopId, billingId);
      }

      if (data) {
        setSignedUrl(data.signed_url);
        setExpiresAt(data.expires_at);
        setReceiptNumber(data.receipt_id.toString());
      }
    } catch (err) {
      console.error("Failed to fetch receipt:", err);
      setError("Failed to load receipt. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [billingId, paymentId, shopId]);

  useEffect(() => {
    fetchReceipt();
  }, [fetchReceipt]);

  const handleDownload = () => {
    if (signedUrl) {
      window.open(signedUrl, '_blank');
    }
  };

  const handleViewInNewTab = () => {
    if (signedUrl) {
      window.open(signedUrl, '_blank');
    }
  };

  if (loading) {
    return (
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Loading Receipt...</DialogTitle>
        </DialogHeader>
        <DialogDescription className="mb-4 text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto" />
          <p className="mt-2">Preparing your receipt for viewing...</p>
        </DialogDescription>
      </DialogContent>
    );
  }

  if (error) {
    return (
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Error Loading Receipt</DialogTitle>
        </DialogHeader>
        <DialogDescription>
          <p>{error}</p>
          <div className="mt-4 flex justify-end">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          </div>
        </DialogDescription>
      </DialogContent>
    );
  }

  // Determine receipt type for display
  const isPaymentReceipt = !!paymentId;
  const receiptTypeLabel = isPaymentReceipt ? "Payment Receipt" : "Invoice";

  return (
    <DialogContent className="max-w-2xl">
      <DialogHeader>
        <DialogTitle>{receiptTypeLabel}</DialogTitle>
        <DialogDescription>
          {receiptNumber && <p className="text-sm font-mono">Receipt ID: {receiptNumber}</p>}
        </DialogDescription>
      </DialogHeader>
      <DialogDescription className="space-y-6">
        <div className="text-center py-8">
          {/* PDF Viewer - using iframe for actual PDF display */}
          {signedUrl ? (
            <iframe
              src={signedUrl}
              title={receiptTypeLabel}
              className="w-full h-96 border rounded-lg shadow-sm"
              sandbox="allow-scripts allow-same-origin"
            />
          ) : (
            <div className="border-2 border-dashed border-muted-foreground rounded-lg p-8">
              <div className="text-muted-foreground">
                <span className="material-icons">picture_as_pdf</span>
                <h3 className="mt-4">{receiptTypeLabel}</h3>
                <p className="mt-2">The PDF would be displayed here.</p>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
            {signedUrl && (
              <>
                <Button variant="outline" onClick={handleViewInNewTab}>
                  <ExternalLink className="h-4 w-4 mr-1" />
                  View in New Tab
                </Button>
                <Button onClick={handleDownload}>
                  <Download className="h-4 w-4 mr-1" />
                  Download PDF
                </Button>
              </>
            )}
          </div>
        </div>
      </DialogDescription>
    </DialogContent>
  );
}