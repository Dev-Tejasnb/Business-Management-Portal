"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Loader2, Mail, MessageSquare, Phone, Eye } from "lucide-react";
import { receiptApi, type CommunicationHistoryResponse, type CommunicationChannel, type CommunicationStatus } from "@/lib/api";
import { COMMUNICATION_CHANNEL_LABELS, COMMUNICATION_STATUS_LABELS } from "@/src/types/receipt";

interface CommunicationHistoryProps {
  shopId: number;
  onClose: () => void;
}

export function CommunicationHistory({ shopId, onClose }: CommunicationHistoryProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [communications, setCommunications] = useState<CommunicationHistoryResponse[]>([]);
  const [showDetails, setShowDetails] = useState(false);
  const [selectedComm, setSelectedComm] = useState<CommunicationHistoryResponse | null>(null);

  const fetchCommunications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await receiptApi.listCommunications(shopId, {
        limit: 50
      });
      setCommunications(data.items);
    } catch (err) {
      console.error("Failed to fetch communications:", err);
      setError("Failed to load communication history");
    } finally {
      setLoading(false);
    }
  }, [shopId]);

  useEffect(() => {
    fetchCommunications();
  }, [fetchCommunications]);

  const getChannelIcon = (channel: CommunicationChannel) => {
    switch (channel) {
      case "email": return <Mail className="h-4 w-4" />;
      case "whatsapp": return <MessageSquare className="h-4 w-4" />;
      case "sms": return <Phone className="h-4 w-4" />;
      default: return <Mail className="h-4 w-4" />;
    }
  };

  const getStatusBadgeVariant = (status: CommunicationStatus) => {
    switch (status) {
      case "sent": return "success";
      case "pending": return "warning";
      case "queued": return "warning";
      case "failed": return "destructive";
      case "cancelled": return "secondary";
      default: return "secondary";
    }
  };

  const handleViewDetails = (comm: CommunicationHistoryResponse) => {
    setSelectedComm(comm);
    setShowDetails(true);
  };

  if (loading) {
    return (
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Communication History</DialogTitle>
        </DialogHeader>
        <DialogDescription className="mb-4 text-center">
          <Loader2 className="h-8 w-8 mx-auto" />
          <p className="mt-2">Loading communication history...</p>
        </DialogDescription>
      </DialogContent>
    );
  }

  if (error) {
    return (
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Error Loading History</DialogTitle>
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

  return (
    <DialogContent className="max-w-2xl">
      <DialogHeader>
        <DialogTitle>Communication History</DialogTitle>
        <DialogDescription>
          View all sent communications including emails, WhatsApp messages, and SMS.
        </DialogDescription>
      </DialogHeader>
      <DialogDescription className="space-y-6">
        {communications.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-muted-foreground">No communications found.</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-left">Channel</TableHead>
                    <TableHead className="text-left">Recipient</TableHead>
                    <TableHead className="text-left">Subject</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                    <TableHead className="text-center">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {communications.map((comm) => (
                    <TableRow key={comm.id}>
                      <TableCell>
                        {new Date(comm.sent_at || comm.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell className="flex items-center gap-2">
                        {getChannelIcon(comm.channel)}
                        <span className="text-sm font-medium">{COMMUNICATION_CHANNEL_LABELS[comm.channel]}</span>
                      </TableCell>
                      <TableCell className="text-sm font-mono whitespace-nowrap">
                        {comm.recipient}
                      </TableCell>
                      <TableCell className="text-sm">
                        {comm.subject || "-"}
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge variant={getStatusBadgeVariant(comm.status)}>
                          {COMMUNICATION_STATUS_LABELS[comm.status]}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleViewDetails(comm)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {showDetails && selectedComm && (
              <Dialog open={true} onOpenChange={(open) => !open && setShowDetails(false)}>
                <DialogContent className="max-w-md">
                  <DialogHeader>
                    <DialogTitle>Communication Details</DialogTitle>
                  </DialogHeader>
                  <DialogDescription className="space-y-4">
                    <div className="space-y-2">
                      <Label>Channel</Label>
                      <p className="font-mono">{COMMUNICATION_CHANNEL_LABELS[selectedComm.channel]}</p>
                    </div>
                    <div className="space-y-2">
                      <Label>Recipient</Label>
                      <p className="font-mono break-all">{selectedComm.recipient}</p>
                    </div>
                    <div className="space-y-2">
                      <Label>Subject</Label>
                      <p className="font-mono">{selectedComm.subject || "No subject"}</p>
                    </div>
                    <div className="space-y-2">
                      <Label>Status</Label>
                      <p className={`font-mono ${getStatusBadgeVariant(selectedComm.status) === "success" ? "text-green-600" : getStatusBadgeVariant(selectedComm.status) === "destructive" ? "text-red-600" : "text-muted-foreground"}`}>
                        {COMMUNICATION_STATUS_LABELS[selectedComm.status]}
                      </p>
                    </div>
                    {selectedComm.sent_at && (
                      <div className="space-y-2">
                        <Label>Sent At</Label>
                        <p className="font-mono">{new Date(selectedComm.sent_at).toLocaleString()}</p>
                      </div>
                    )}
                    <div className="space-y-2">
                      <Label>Created At</Label>
                      <p className="font-mono">{new Date(selectedComm.created_at).toLocaleString()}</p>
                    </div>
                    {selectedComm.error_message && (
                      <div className="space-y-2">
                        <Label>Error Message</Label>
                        <p className="font-mono text-red-500 break-all">{selectedComm.error_message}</p>
                      </div>
                    )}
                  </DialogDescription>
                  <DialogDescription className="flex justify-end pt-4 border-t">
                    <Button variant="outline" onClick={() => setShowDetails(false)}>
                      Close
                    </Button>
                  </DialogDescription>
                </DialogContent>
              </Dialog>
            )}
          </>
        )}
      </DialogDescription>
      <DialogDescription className="flex justify-end">
        <Button variant="outline" onClick={onClose}>
          Close
        </Button>
      </DialogDescription>
    </DialogContent>
  );
}