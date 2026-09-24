import * as React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";

const paginationVariants = cva(
  "inline-flex items-center justify-center gap-1 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow hover:bg-primary/90",
        outline:
          "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground",
        secondary:
          "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
      },
    },
    defaultVariants: {
      variant: "outline",
    },
  }
);

interface PaginationProps {
  totalPages: number;
  currentPage: number;
  onPageChange: (page: number) => void;
  className?: string;
}

export function Pagination({
  totalPages,
  currentPage,
  onPageChange,
  className,
}: PaginationProps) {
  if (totalPages <= 1) return null;

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages && page !== currentPage) {
      onPageChange(page);
    }
  };

  const renderPageNumber = (page: number) => {
    const isActive = page === currentPage;
    return (
      <button
        key={page}
        onClick={() => handlePageChange(page)}
        className={cn(
          paginationVariants({ variant: "outline" }),
          isActive && "bg-primary text-primary-foreground",
          !isActive && "hover:bg-accent hover:text-accent-foreground"
        )}
        aria-current={isActive ? "page" : undefined}
      >
        {page}
      </button>
    );
  };

  return (
    <nav className={cn("flex items-center justify-center gap-1", className)} aria-label="Pagination">
      {/* Previous button */}
      <button
        onClick={() => handlePageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className={cn(
          paginationVariants({ variant: "outline" }),
          currentPage === 1 && "opacity-50 cursor-not-allowed",
          currentPage > 1 && "hover:bg-accent hover:text-accent-foreground"
        )}
      >
        <ChevronLeft className="h-3 w-3" />
      </button>

      {/* Page numbers */}
      {totalPages <= 5 ? (
        <>
          {[...Array(totalPages)].map((_, i) => i + 1).map(renderPageNumber)}
        </>
      ) : (
        <>
          {/* First page */}
          {currentPage > 3 && (
            <>
              {renderPageNumber(1)}
              {currentPage > 4 && <span className="px-2">…</span>}
            </>
          )}
          {/* Pages around current */}
          {[...Array(Math.min(3, totalPages - 2))]
            .map((_, i) => i + 2)
            .map((page) => {
              const start = Math.max(2, Math.min(currentPage - 1, totalPages - 3));
              const actualPage = start + (page - 2);
              return renderPageNumber(actualPage);
            })}
          {/* Last page */}
          {currentPage < totalPages - 2 && (
            <>
              {currentPage < totalPages - 3 && <span className="px-2">…</span>}
              {renderPageNumber(totalPages)}
            </>
          )}
        </>
      )}

      {/* Next button */}
      <button
        onClick={() => handlePageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className={cn(
          paginationVariants({ variant: "outline" }),
          currentPage === totalPages && "opacity-50 cursor-not-allowed",
          currentPage < totalPages && "hover:bg-accent hover:text-accent-foreground"
        )}
      >
        <ChevronRight className="h-3 w-3" />
      </button>
    </nav>
  );
}

// Helper function for class variance authority
function cva(
  baseClass: string,
  config: {
    variants: Record<string, Record<string, string>>;
    defaultVariants?: Record<string, string>;
  }
) {
  return Object.assign(
    function (variants: Record<string, string> = {}, className: string = "") {
      let output = baseClass;
      Object.entries(config.variants).forEach(([key, values]) => {
        const variant = variants[key];
        if (variant && values[variant]) {
          output += ` ${values[variant]}`;
        }
      });
      if (config.defaultVariants) {
        Object.entries(config.defaultVariants).forEach(([key, value]) => {
          if (!variants[key]) {
            output += ` ${value}`;
          }
        });
      }
      if (className) {
        output += ` ${className}`;
      }
      return output.trim();
    },
    { config }
  );
}