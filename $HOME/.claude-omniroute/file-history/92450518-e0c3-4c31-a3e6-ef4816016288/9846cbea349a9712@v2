"use client";

import * as React from "react";
import { createPortal } from "react-dom";

export function Portal({ children }: { children: React.ReactNode }) {
  return createPortal(
    <div>{children}</div>,
    document.body
  );
}