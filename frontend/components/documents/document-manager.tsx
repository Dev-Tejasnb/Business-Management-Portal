"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  FileText,
  Upload,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Download,
  ExternalLink,
  Trash2,
  Edit2,
  RefreshCw,
  Eye,
  FileCheck,
  ShieldCheck,
  AlertCircle,
  Loader2,
  Plus,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useToast } from "@/components/ui/use-toast";
import {
  ApplicationDocumentChecklistResponse,
  DocumentChecklistRequirement,
  DocumentResponse,
  DocumentStatus,
} from "@/src/types/document";

interface DocumentManagerProps {
  shopId: number;
  applicationId: number;
  canUpload?: boolean;
  canVerify?: boolean;
  canReject?: boolean;
  canDelete?: boolean;
  onChecklistUpdated?: () => void;
}

export function DocumentManager({
  shopId,
  applicationId,
  canUpload = true,
  canVerify = true,
  canReject = true,
  canDelete = true,
  onChecklistUpdated,
}: DocumentManagerProps) {
  const { toast } = useToast();
  const [checklist, setChecklist] = useState<ApplicationDocumentChecklistResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Upload dialog state
  const [uploadDialogOpen, setUploadDialogOpen] = useState<boolean>(false);
  const [selectedRequirement, setSelectedRequirement] = useState<DocumentChecklistRequirement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadNotes, setUploadNotes] = useState<string>("");
  const [uploading, setUploading] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Verify dialog state
  const [verifyDialogOpen, setVerifyDialogOpen] = useState<boolean>(false);
  const [targetDocToVerify, setTargetDocToVerify] = useState<DocumentResponse | null>(null);
  const [verifyNotes, setVerifyNotes] = useState<string>("");
  const [verifying, setVerifying] = useState<boolean>(false);

  // Reject dialog state
  const [rejectDialogOpen, setRejectDialogOpen] = useState<boolean>(false);
  const [targetDocToReject, setTargetDocToReject] = useState<DocumentResponse | null>(null);
  const [rejectionReason, setRejectionReason] = useState<string>("");
  const [rejectNotes, setRejectNotes] = useState<string>("");
  const [rejecting, setRejecting] = useState<boolean>(false);

  // Delete / Archive dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState<boolean>(false);
  const [targetDocToDelete, setTargetDocToDelete] = useState<DocumentResponse | null>(null);
  const [hardDelete, setHardDelete] = useState<boolean>(false);
  const [deleting, setDeleting] = useState<boolean>(false);

  // Edit notes dialog state
  const [notesDialogOpen, setNotesDialogOpen] = useState<boolean>(false);
  const [targetDocToEditNotes, setTargetDocToEditNotes] = useState<DocumentResponse | null>(null);
  const [docNotes, setDocNotes] = useState<string>("");
  const [savingNotes, setSavingNotes] = useState<boolean>(false);

  // Preview / Download state
  const [downloadingDocId, setDownloadingDocId] = useState<number | null>(null);

  const getAuthToken = () => {
    return localStorage.getItem("access_token") || "";
  };

  const fetchChecklist = useCallback(async (isRefresh = false) => {
    if (!shopId || !applicationId) return;
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/v1/shops/${shopId}/applications/${applicationId}/documents/checklist`,
        {
          headers: {
            Authorization: `Bearer ${getAuthToken()}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData?.error?.message || errorData?.detail || "Failed to load documents checklist");
      }

      const data: ApplicationDocumentChecklistResponse = await response.json();
      setChecklist(data);
      if (onChecklistUpdated) {
        onChecklistUpdated();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [shopId, applicationId, onChecklistUpdated]);

  useEffect(() => {
    fetchChecklist();
  }, [fetchChecklist]);

  const formatFileSize = (bytes: number) => {
    if (!bytes || bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const openUploadModal = (requirement: DocumentChecklistRequirement | null = null) => {
    setSelectedRequirement(requirement);
    setSelectedFile(null);
    setUploadNotes("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    setUploadDialogOpen(true);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      // Optional client-side checks
      if (selectedRequirement?.max_file_size_mb) {
        const maxBytes = selectedRequirement.max_file_size_mb * 1024 * 1024;
        if (file.size > maxBytes) {
          toast({
            variant: "destructive",
            title: "File too large",
            description: `Maximum allowed size is ${selectedRequirement.max_file_size_mb} MB. Selected file is ${formatFileSize(file.size)}.`,
          });
          e.target.value = "";
          setSelectedFile(null);
          return;
        }
      }
      setSelectedFile(file);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      toast({
        variant: "destructive",
        title: "No file selected",
        description: "Please choose a file to upload.",
      });
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      if (selectedRequirement?.required_document_id) {
        formData.append("required_document_id", selectedRequirement.required_document_id.toString());
      }
      if (uploadNotes.trim()) {
        formData.append("notes", uploadNotes.trim());
      }

      const response = await fetch(
        `/api/v1/shops/${shopId}/applications/${applicationId}/documents`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${getAuthToken()}`,
          },
          body: formData,
        }
      );

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || errJson?.detail || "Upload failed");
      }

      toast({
        variant: "success",
        title: "Document uploaded successfully",
        description: `${selectedFile.name} has been attached to the application.`,
      });

      setUploadDialogOpen(false);
      setSelectedFile(null);
      setUploadNotes("");
      await fetchChecklist(true);
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Upload failed",
        description: err instanceof Error ? err.message : "Failed to upload document",
      });
    } finally {
      setUploading(false);
    }
  };

  const handleVerifySubmit = async () => {
    if (!targetDocToVerify) return;
    setVerifying(true);
    try {
      const response = await fetch(
        `/api/v1/shops/${shopId}/documents/${targetDocToVerify.id}/verify`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getAuthToken()}`,
          },
          body: JSON.stringify({
            notes: verifyNotes.trim() || undefined,
          }),
        }
      );

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || errJson?.detail || "Verification failed");
      }

      toast({
        variant: "success",
        title: "Document verified",
        description: `Document marked as verified successfully.`,
      });

      setVerifyDialogOpen(false);
      setTargetDocToVerify(null);
      setVerifyNotes("");
      await fetchChecklist(true);
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Verification failed",
        description: err instanceof Error ? err.message : "Failed to verify document",
      });
    } finally {
      setVerifying(false);
    }
  };

  const handleRejectSubmit = async () => {
    if (!targetDocToReject) return;
    if (!rejectionReason.trim()) {
      toast({
        variant: "destructive",
        title: "Reason required",
        description: "Please specify a rejection reason.",
      });
      return;
    }

    setRejecting(true);
    try {
      const response = await fetch(
        `/api/v1/shops/${shopId}/documents/${targetDocToReject.id}/reject`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getAuthToken()}`,
          },
          body: JSON.stringify({
            rejection_reason: rejectionReason.trim(),
            notes: rejectNotes.trim() || undefined,
          }),
        }
      );

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || errJson?.detail || "Rejection failed");
      }

      toast({
        variant: "destructive",
        title: "Document rejected",
        description: `Document status updated to rejected.`,
      });

      setRejectDialogOpen(false);
      setTargetDocToReject(null);
      setRejectionReason("");
      setRejectNotes("");
      await fetchChecklist(true);
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Rejection failed",
        description: err instanceof Error ? err.message : "Failed to reject document",
      });
    } finally {
      setRejecting(false);
    }
  };

  const handleDeleteSubmit = async () => {
    if (!targetDocToDelete) return;
    setDeleting(true);
    try {
      const response = await fetch(
        `/api/v1/shops/${shopId}/documents/${targetDocToDelete.id}?hard_delete=${hardDelete}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${getAuthToken()}`,
          },
        }
      );

      if (!response.ok && response.status !== 204) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || errJson?.detail || "Deletion failed");
      }

      toast({
        title: hardDelete ? "Document permanently deleted" : "Document archived",
        description: `Document has been removed from active view.`,
      });

      setDeleteDialogOpen(false);
      setTargetDocToDelete(null);
      setHardDelete(false);
      await fetchChecklist(true);
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Action failed",
        description: err instanceof Error ? err.message : "Failed to delete/archive document",
      });
    } finally {
      setDeleting(false);
    }
  };

  const handleNotesSubmit = async () => {
    if (!targetDocToEditNotes) return;
    setSavingNotes(true);
    try {
      const response = await fetch(
        `/api/v1/shops/${shopId}/documents/${targetDocToEditNotes.id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getAuthToken()}`,
          },
          body: JSON.stringify({
            notes: docNotes.trim() || null,
          }),
        }
      );

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || errJson?.detail || "Failed to update notes");
      }

      toast({
        title: "Notes updated",
        description: "Document notes saved successfully.",
      });

      setNotesDialogOpen(false);
      setTargetDocToEditNotes(null);
      setDocNotes("");
      await fetchChecklist(true);
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Update failed",
        description: err instanceof Error ? err.message : "Failed to update notes",
      });
    } finally {
      setSavingNotes(false);
    }
  };

  const handleViewOrDownload = async (doc: DocumentResponse, directDownload = false) => {
    try {
      setDownloadingDocId(doc.id);
      // Fetch presigned URL
      const response = await fetch(
        `/api/v1/shops/${shopId}/documents/${doc.id}/url?expires_seconds=900`,
        {
          headers: {
            Authorization: `Bearer ${getAuthToken()}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        if (data.url) {
          window.open(data.url, "_blank", "noopener,noreferrer");
          return;
        }
      }

      // Fallback to streaming download endpoint if presigned URL is unavailable
      const downloadEndpoint = `/api/v1/shops/${shopId}/documents/${doc.id}/download`;
      window.open(downloadEndpoint, "_blank");
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Error accessing file",
        description: "Could not generate download link for document.",
      });
    } finally {
      setDownloadingDocId(null);
    }
  };

  const renderStatusBadge = (status: DocumentStatus) => {
    switch (status) {
      case "verified":
        return (
          <Badge variant="success" className="flex items-center gap-1 font-medium">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Verified
          </Badge>
        );
      case "rejected":
        return (
          <Badge variant="destructive" className="flex items-center gap-1 font-medium">
            <XCircle className="h-3.5 w-3.5" />
            Rejected
          </Badge>
        );
      case "uploaded":
        return (
          <Badge variant="default" className="flex items-center gap-1 font-medium bg-amber-500 hover:bg-amber-600 text-white">
            <Clock className="h-3.5 w-3.5" />
            Pending Verification
          </Badge>
        );
      case "archived":
        return (
          <Badge variant="outline" className="flex items-center gap-1 font-medium text-muted-foreground">
            Archived
          </Badge>
        );
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Document Management
          </CardTitle>
          <CardDescription>Loading document requirements and uploaded files...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <AlertCircle className="h-5 w-5" />
            Document Management Error
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">{error}</p>
          <Button variant="outline" onClick={() => fetchChecklist(false)}>
            <RefreshCw className="mr-2 h-4 w-4" /> Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  const requirements = checklist?.requirements || [];
  const additionalDocs = checklist?.additional_documents || [];
  const totalMandatory = checklist?.mandatory_required || 0;
  const verifiedMandatory = checklist?.mandatory_verified || 0;
  const uploadedMandatory = checklist?.mandatory_uploaded || 0;
  const allVerified = checklist?.all_mandatory_verified || false;

  return (
    <div className="space-y-6">
      {/* Header Overview Card */}
      <Card className="border-l-4 border-l-primary shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2 text-xl">
                <FileCheck className="h-5 w-5 text-primary" />
                Required Documents Checklist
              </CardTitle>
              <CardDescription className="mt-1">
                Service: <span className="font-semibold text-foreground">{checklist?.service_name || "Application"}</span>
              </CardDescription>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Button
                variant="outline"
                size="sm"
                onClick={() => fetchChecklist(true)}
                disabled={refreshing}
              >
                <RefreshCw className={`h-4 w-4 mr-1 ${refreshing ? "animate-spin" : ""}`} />
                Refresh
              </Button>
              {canUpload && (
                <Button size="sm" onClick={() => openUploadModal(null)}>
                  <Plus className="h-4 w-4 mr-1" />
                  Upload Additional Document
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Progress summary banner */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-lg bg-muted/40 border">
            <div>
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Required</p>
              <p className="text-2xl font-bold mt-0.5">{totalMandatory}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Uploaded</p>
              <p className="text-2xl font-bold mt-0.5 text-blue-600 dark:text-blue-400">
                {uploadedMandatory} <span className="text-sm font-normal text-muted-foreground">/ {totalMandatory}</span>
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Verified</p>
              <p className="text-2xl font-bold mt-0.5 text-green-600 dark:text-green-400">
                {verifiedMandatory} <span className="text-sm font-normal text-muted-foreground">/ {totalMandatory}</span>
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Checklist Status</p>
              <div className="mt-1">
                {allVerified ? (
                  <Badge variant="success" className="px-2.5 py-1 text-xs font-semibold flex items-center gap-1 w-fit">
                    <ShieldCheck className="h-3.5 w-3.5" /> All Verified
                  </Badge>
                ) : uploadedMandatory === totalMandatory ? (
                  <Badge variant="default" className="px-2.5 py-1 text-xs font-semibold bg-amber-500 hover:bg-amber-600 text-white flex items-center gap-1 w-fit">
                    <Clock className="h-3.5 w-3.5" /> Pending Verification
                  </Badge>
                ) : (
                  <Badge variant="destructive" className="px-2.5 py-1 text-xs font-semibold flex items-center gap-1 w-fit">
                    <AlertTriangle className="h-3.5 w-3.5" /> Documents Missing
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Service Requirements List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Service Document Requirements</CardTitle>
          <CardDescription>
            Documents configured for this service that must be collected and verified.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {requirements.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground italic border border-dashed rounded-lg">
              No specific document requirements configured for this service.
            </div>
          ) : (
            <div className="space-y-4">
              {requirements.map((req) => {
                const doc = req.uploaded_document;
                const isUploaded = !!doc;
                const isVerified = doc?.status === "verified";
                const isRejected = doc?.status === "rejected";

                return (
                  <div
                    key={req.required_document_id}
                    className={`p-4 rounded-lg border transition-colors ${
                      isVerified
                        ? "bg-green-50/40 dark:bg-green-950/20 border-green-200 dark:border-green-900/40"
                        : isRejected
                        ? "bg-red-50/40 dark:bg-red-950/20 border-red-200 dark:border-red-900/40"
                        : isUploaded
                        ? "bg-amber-50/30 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/40"
                        : "bg-card border-border"
                    }`}
                  >
                    <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                      {/* Left: Requirement Info */}
                      <div className="space-y-1.5 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="font-semibold text-base text-foreground">{req.name}</h4>
                          {req.is_mandatory ? (
                            <Badge variant="destructive" className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5">
                              Mandatory
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="text-[10px] uppercase tracking-wider px-1.5 py-0.5">
                              Optional
                            </Badge>
                          )}
                          {doc && renderStatusBadge(doc.status)}
                        </div>

                        {req.description && (
                          <p className="text-sm text-muted-foreground">{req.description}</p>
                        )}

                        <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap pt-1">
                          {req.allowed_file_types && req.allowed_file_types.length > 0 && (
                            <span>
                              Allowed types:{" "}
                              <span className="font-medium text-foreground uppercase">
                                {req.allowed_file_types.join(", ")}
                              </span>
                            </span>
                          )}
                          {req.max_file_size_mb && (
                            <span>
                              Max size:{" "}
                              <span className="font-medium text-foreground">
                                {req.max_file_size_mb} MB
                              </span>
                            </span>
                          )}
                        </div>

                        {/* Uploaded File Details Box */}
                        {doc && (
                          <div className="mt-3 p-3 rounded-md bg-background/80 border text-sm space-y-2">
                            <div className="flex items-center justify-between flex-wrap gap-2">
                              <div className="flex items-center gap-2 font-medium break-all">
                                <FileText className="h-4 w-4 text-primary shrink-0" />
                                <span>{doc.original_filename}</span>
                                <span className="text-xs text-muted-foreground font-normal">
                                  ({formatFileSize(doc.file_size)})
                                </span>
                              </div>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground">
                              <div>
                                Uploaded by: <span className="text-foreground">{doc.uploader_name || `User #${doc.uploaded_by}`}</span>
                              </div>
                              <div>
                                Uploaded at: <span className="text-foreground">{new Date(doc.created_at).toLocaleString()}</span>
                              </div>
                              {doc.verified_by && (
                                <div>
                                  Verified by: <span className="text-foreground">{doc.verifier_name || `User #${doc.verified_by}`}</span>
                                </div>
                              )}
                              {doc.verified_at && (
                                <div>
                                  Verified at: <span className="text-foreground">{new Date(doc.verified_at).toLocaleString()}</span>
                                </div>
                              )}
                            </div>

                            {/* Rejection reason alert */}
                            {doc.status === "rejected" && doc.rejection_reason && (
                              <div className="p-2.5 rounded bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 text-xs font-medium border border-red-200 dark:border-red-800 flex items-start gap-2">
                                <AlertCircle className="h-4 w-4 shrink-0 text-red-600 dark:text-red-400 mt-0.5" />
                                <div>
                                  <span className="font-bold">Rejection Reason: </span>
                                  {doc.rejection_reason}
                                </div>
                              </div>
                            )}

                            {/* Notes */}
                            {doc.notes && (
                              <div className="text-xs text-muted-foreground italic bg-muted/30 p-2 rounded">
                                <span className="font-semibold text-foreground">Notes: </span>
                                {doc.notes}
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Right: Actions */}
                      <div className="flex flex-wrap lg:flex-col items-center lg:items-end gap-2 shrink-0">
                        {doc ? (
                          <>
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleViewOrDownload(doc)}
                                disabled={downloadingDocId === doc.id}
                              >
                                {downloadingDocId === doc.id ? (
                                  <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
                                ) : (
                                  <Eye className="h-3.5 w-3.5 mr-1" />
                                )}
                                View
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleViewOrDownload(doc, true)}
                                disabled={downloadingDocId === doc.id}
                              >
                                <Download className="h-3.5 w-3.5 mr-1" />
                                Download
                              </Button>
                              {canUpload && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => openUploadModal(req)}
                                  title="Replace with a new document upload"
                                >
                                  <Upload className="h-3.5 w-3.5 mr-1" />
                                  Replace
                                </Button>
                              )}
                            </div>

                            <div className="flex items-center gap-1.5 flex-wrap pt-1">
                              {canVerify && doc.status !== "verified" && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="border-green-600 text-green-700 hover:bg-green-50 dark:hover:bg-green-950/40"
                                  onClick={() => {
                                    setTargetDocToVerify(doc);
                                    setVerifyNotes("");
                                    setVerifyDialogOpen(true);
                                  }}
                                >
                                  <CheckCircle2 className="h-3.5 w-3.5 mr-1 text-green-600" />
                                  Verify
                                </Button>
                              )}
                              {canReject && doc.status !== "rejected" && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="border-red-500 text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40"
                                  onClick={() => {
                                    setTargetDocToReject(doc);
                                    setRejectionReason("");
                                    setRejectNotes("");
                                    setRejectDialogOpen(true);
                                  }}
                                >
                                  <XCircle className="h-3.5 w-3.5 mr-1 text-red-500" />
                                  Reject
                                </Button>
                              )}
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                  setTargetDocToEditNotes(doc);
                                  setDocNotes(doc.notes || "");
                                  setNotesDialogOpen(true);
                                }}
                                title="Edit internal notes"
                              >
                                <Edit2 className="h-3.5 w-3.5" />
                              </Button>
                              {canDelete && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="text-destructive hover:text-destructive hover:bg-destructive/10"
                                  onClick={() => {
                                    setTargetDocToDelete(doc);
                                    setHardDelete(false);
                                    setDeleteDialogOpen(true);
                                  }}
                                  title="Archive or delete document"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </Button>
                              )}
                            </div>
                          </>
                        ) : (
                          canUpload && (
                            <Button
                              variant="default"
                              size="sm"
                              onClick={() => openUploadModal(req)}
                              className="w-full lg:w-auto"
                            >
                              <Upload className="h-4 w-4 mr-1.5" />
                              Upload {req.name}
                            </Button>
                          )
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Additional / Uncategorized Uploads */}
      {additionalDocs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center justify-between">
              <span>Additional Documents</span>
              <Badge variant="secondary">{additionalDocs.length}</Badge>
            </CardTitle>
            <CardDescription>
              Supporting documents uploaded for this application outside the predefined service checklist.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {additionalDocs.map((doc) => (
                <div
                  key={doc.id}
                  className="p-4 rounded-lg border bg-card flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <FileText className="h-4 w-4 text-primary shrink-0" />
                      <span className="font-semibold text-foreground">{doc.original_filename}</span>
                      <span className="text-xs text-muted-foreground">({formatFileSize(doc.file_size)})</span>
                      {renderStatusBadge(doc.status)}
                    </div>
                    <div className="text-xs text-muted-foreground flex items-center gap-4 flex-wrap">
                      <span>Uploaded by: {doc.uploader_name || `User #${doc.uploaded_by}`}</span>
                      <span>{new Date(doc.created_at).toLocaleString()}</span>
                    </div>
                    {doc.rejection_reason && (
                      <p className="text-xs text-red-600 dark:text-red-400 font-medium">
                        Rejection Reason: {doc.rejection_reason}
                      </p>
                    )}
                    {doc.notes && (
                      <p className="text-xs text-muted-foreground italic">
                        Notes: {doc.notes}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleViewOrDownload(doc)}
                      disabled={downloadingDocId === doc.id}
                    >
                      <Eye className="h-3.5 w-3.5 mr-1" />
                      View
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleViewOrDownload(doc, true)}
                      disabled={downloadingDocId === doc.id}
                    >
                      <Download className="h-3.5 w-3.5 mr-1" />
                      Download
                    </Button>
                    {canVerify && doc.status !== "verified" && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-green-600 text-green-700 hover:bg-green-50 dark:hover:bg-green-950/40"
                        onClick={() => {
                          setTargetDocToVerify(doc);
                          setVerifyNotes("");
                          setVerifyDialogOpen(true);
                        }}
                      >
                        <CheckCircle2 className="h-3.5 w-3.5 mr-1 text-green-600" />
                        Verify
                      </Button>
                    )}
                    {canReject && doc.status !== "rejected" && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-red-500 text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40"
                        onClick={() => {
                          setTargetDocToReject(doc);
                          setRejectionReason("");
                          setRejectNotes("");
                          setRejectDialogOpen(true);
                        }}
                      >
                        <XCircle className="h-3.5 w-3.5 mr-1 text-red-500" />
                        Reject
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setTargetDocToEditNotes(doc);
                        setDocNotes(doc.notes || "");
                        setNotesDialogOpen(true);
                      }}
                    >
                      <Edit2 className="h-3.5 w-3.5" />
                    </Button>
                    {canDelete && (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive hover:text-destructive hover:bg-destructive/10"
                        onClick={() => {
                          setTargetDocToDelete(doc);
                          setHardDelete(false);
                          setDeleteDialogOpen(true);
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <form onSubmit={handleUploadSubmit}>
            <DialogHeader>
              <DialogTitle>
                {selectedRequirement ? `Upload ${selectedRequirement.name}` : "Upload Document"}
              </DialogTitle>
              <DialogDescription>
                {selectedRequirement
                  ? `Attach document for requirement: ${selectedRequirement.name}`
                  : "Upload a general document attachment for this application."}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {selectedRequirement?.uploaded_document && (
                <div className="p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-md text-xs text-amber-800 dark:text-amber-200">
                  <span className="font-semibold">Note:</span> Uploading a new file will automatically archive the currently active file (
                  {selectedRequirement.uploaded_document.original_filename}).
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="file-upload">Select File</Label>
                <Input
                  id="file-upload"
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  required
                />
                {selectedRequirement && (
                  <p className="text-xs text-muted-foreground">
                    {selectedRequirement.allowed_file_types && (
                      <>Allowed types: {selectedRequirement.allowed_file_types.join(", ").toUpperCase()}. </>
                    )}
                    {selectedRequirement.max_file_size_mb && (
                      <>Max size: {selectedRequirement.max_file_size_mb} MB.</>
                    )}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="upload-notes">Notes (Optional)</Label>
                <Textarea
                  id="upload-notes"
                  placeholder="Add any context or notes about this document..."
                  value={uploadNotes}
                  onChange={(e) => setUploadNotes(e.target.value)}
                  rows={3}
                />
              </div>
            </div>

            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                type="button"
                variant="outline"
                onClick={() => setUploadDialogOpen(false)}
                disabled={uploading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={uploading || !selectedFile}>
                {uploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 h-4 w-4" />
                    Upload File
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Verify Dialog */}
      <Dialog open={verifyDialogOpen} onOpenChange={setVerifyDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-green-700 dark:text-green-400">
              <CheckCircle2 className="h-5 w-5" />
              Verify Document
            </DialogTitle>
            <DialogDescription>
              Confirm that you have reviewed and approved this document:{" "}
              <span className="font-semibold text-foreground">
                {targetDocToVerify?.original_filename}
              </span>
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-3">
            <div className="space-y-2">
              <Label htmlFor="verify-notes">Verification Notes (Optional)</Label>
              <Textarea
                id="verify-notes"
                placeholder="E.g., Verified valid expiry date, clear photograph, valid government seal..."
                value={verifyNotes}
                onChange={(e) => setVerifyNotes(e.target.value)}
                rows={3}
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setVerifyDialogOpen(false)}
              disabled={verifying}
            >
              Cancel
            </Button>
            <Button
              className="bg-green-600 hover:bg-green-700 text-white"
              onClick={handleVerifySubmit}
              disabled={verifying}
            >
              {verifying ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Verifying...
                </>
              ) : (
                <>
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Confirm Verification
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <XCircle className="h-5 w-5" />
              Reject Document
            </DialogTitle>
            <DialogDescription>
              Rejecting document:{" "}
              <span className="font-semibold text-foreground">
                {targetDocToReject?.original_filename}
              </span>
              . You must provide a clear reason for the customer or staff.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-3">
            <div className="space-y-2">
              <Label htmlFor="rejection-reason" className="text-destructive font-medium">
                Rejection Reason (Mandatory) *
              </Label>
              <Input
                id="rejection-reason"
                placeholder="E.g., Blurred image, expired validity, wrong document type..."
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="reject-notes">Internal Notes (Optional)</Label>
              <Textarea
                id="reject-notes"
                placeholder="Additional internal notes..."
                value={rejectNotes}
                onChange={(e) => setRejectNotes(e.target.value)}
                rows={2}
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setRejectDialogOpen(false)}
              disabled={rejecting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleRejectSubmit}
              disabled={rejecting || !rejectionReason.trim()}
            >
              {rejecting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Rejecting...
                </>
              ) : (
                <>
                  <XCircle className="mr-2 h-4 w-4" />
                  Confirm Rejection
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete / Archive Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <Trash2 className="h-5 w-5" />
              Delete / Archive Document
            </DialogTitle>
            <DialogDescription>
              Manage retention for document:{" "}
              <span className="font-semibold text-foreground">
                {targetDocToDelete?.original_filename}
              </span>
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-3">
            <p className="text-sm text-muted-foreground">
              By default, documents are softly archived to maintain an audit trail. You can also choose to permanently purge the file if you are an authorized manager or owner.
            </p>

            <div className="flex items-center gap-2 pt-2">
              <input
                type="checkbox"
                id="hard-delete-check"
                checked={hardDelete}
                onChange={(e) => setHardDelete(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-destructive focus:ring-destructive"
              />
              <Label htmlFor="hard-delete-check" className="cursor-pointer text-sm font-medium text-destructive">
                Permanently delete from storage & database (irreversible)
              </Label>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteSubmit}
              disabled={deleting}
            >
              {deleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : hardDelete ? (
                "Permanently Delete"
              ) : (
                "Archive Document"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Notes Dialog */}
      <Dialog open={notesDialogOpen} onOpenChange={setNotesDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit2 className="h-5 w-5" />
              Edit Document Notes
            </DialogTitle>
            <DialogDescription>
              Update internal notes for:{" "}
              <span className="font-semibold text-foreground">
                {targetDocToEditNotes?.original_filename}
              </span>
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-3">
            <div className="space-y-2">
              <Label htmlFor="edit-doc-notes">Internal Notes</Label>
              <Textarea
                id="edit-doc-notes"
                placeholder="Internal notes regarding this document..."
                value={docNotes}
                onChange={(e) => setDocNotes(e.target.value)}
                rows={4}
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setNotesDialogOpen(false)}
              disabled={savingNotes}
            >
              Cancel
            </Button>
            <Button onClick={handleNotesSubmit} disabled={savingNotes}>
              {savingNotes ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                "Save Notes"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
