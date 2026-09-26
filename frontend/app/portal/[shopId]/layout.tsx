import { use } from "react";
import { CustomerAuthProvider } from "@/lib/customer-auth-context";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Customer Portal",
  description:
    "Customer portal for managing applications, documents, payments, and profile.",
};

export default function PortalLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ shopId: string }>;
}) {
  const resolvedParams = use(params);
  return (
    <CustomerAuthProvider shopId={resolvedParams.shopId}>
      {children}
    </CustomerAuthProvider>
  );
}