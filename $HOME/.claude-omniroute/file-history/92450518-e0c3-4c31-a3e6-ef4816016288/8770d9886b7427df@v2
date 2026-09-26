"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Mail, MessageSquare, Phone, CheckCircle, AlertCircle } from "lucide-react";
import { receiptApi, type SendReceiptRequest, type CommunicationChannel } from "@/lib/api";
import { COMMUNICATION_CHANNEL_LABELS } from "@/src/types/receipt";

interface SendReceiptDialogProps {
  receiptId: number;
  shopId: number;
  receiptType: "invoice" | "payment_receipt";
  defaultRecipient?: string;
  onClose: () => void;
  onSent: () => void;
}

export function SendReceiptDialog({
  receiptId,
  shopId,
  receiptType,
  defaultRecipient,
  onClose,
  onSent,
}: SendReceiptDialogProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [channel, setChannel] = useState<CommunicationChannel>("email");
  const [recipient, setRecipient] = useState(defaultRecipient || "");
  const [subject, setSubject] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recipient.trim()) {
      setError("Recipient is required");
      return;
    }
    if (channel === "email" && !subject.trim()) {
      setError("Subject is required for email");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const payload: SendReceiptRequest = {
        channel,
        recipient: recipient.trim(),
        subject: subject.trim() || undefined,
      };

      await receiptApi.sendReceipt(shopId, receiptId, payload);
      setSuccess(true);
      setTimeout(() => {
        onSent();
        setSuccess(false);
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send receipt");
    } finally {
      setLoading(false);
    }
  };

  const channelOptions: { value: CommunicationChannel; label: string; icon: React.ReactNode }[] = [
    { value: "email", label: COMMUNICATION_CHANNEL_LABELS.email, icon: <Mail className="h-4 w-4" /> },
    { value: "whatsapp", label: COMMUNICATION_CHANNEL_LABELS.whatsapp, icon: <MessageSquare className="h-4 w-4" /> },
    { value: "sms", label: COMMUNICATION_CHANNEL_LABELS.sms, icon: <Phone className="h-4 w-4" /> },
  ];

  return (
    <Dialog open={true} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Send {receiptType === "invoice" ? "Invoice" : "Payment Receipt"}</DialogTitle>
          <DialogDescription>
            Choose a channel and enter recipient details to send the receipt.
          </DialogDescription>
        </DialogHeader>

        {success && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-green-700">
            <CheckCircle className="h-5 w-5 flex-shrink-0" />
            <span>Receipt sent successfully!</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Channel</Label>
            <Select value={channel} onValueChange={(v) => setChannel(v as CommunicationChannel)}>
              <SelectTrigger>
                <SelectValue placeholder="Select channel" />
              </SelectTrigger>
              <SelectContent>
                {channelOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    <div className="flex items-center gap-2">
                      {opt.icon}
                      <span>{opt.label}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="recipient">Recipient <span className="text-destructive">*</span></Label>
            <Input
              id="recipient"
              type={channel === "email" ? "email" : channel === "sms" ? "tel" : "text"}
              value={recipient}
              onChange={(e) => setRecipient(e.target.value)}
              placeholder={
                channel === "email"
                  ? "customer@example.com"
                  : channel === "sms"
                  ? "+1234567890"
                  : "WhatsApp number"
              }
              disabled={success}
            />
          </div>

          {channel === "email" && (
            <div className="space-y-2">
              <Label htmlFor="subject">Subject <span className="text-destructive">*</span></Label>
              <Input
                id="subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder={receiptType === "invoice" ? "Your Invoice" : "Your Payment Receipt"}
                disabled={success}
              />
            </div>
          )}

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button type="button" variant="outline" onClick={onClose} disabled={loading || success}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading || success}>
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                  Sending...
                </>
              ) : (
                "Send Receipt"
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}