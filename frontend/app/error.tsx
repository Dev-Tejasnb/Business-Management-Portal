"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Home, RefreshCw } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md text-center space-y-4">
        <h1 className="text-4xl font-bold text-destructive">Something went wrong!</h1>
        <p className="text-muted-foreground">
          An unexpected error occurred. Please try again or navigate back to the dashboard.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button onClick={reset}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Try Again
          </Button>
          <Button variant="outline" asChild>
            <Link href="/dashboard">
              <Home className="mr-2 h-4 w-4" />
              Go to Dashboard
            </Link>
          </Button>
        </div>
        {process.env.NODE_ENV === "development" && (
          <details className="text-left text-sm text-muted-foreground">
            <summary>Error Details</summary>
            <pre className="mt-2 p-4 bg-muted rounded overflow-auto">{error.message}</pre>
          </details>
        )}
      </div>
    </div>
  );
}
