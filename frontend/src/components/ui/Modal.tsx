"use client";

import { useEffect, type ReactNode } from "react";
import { clsx } from "clsx";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  className?: string;
}

export function Modal({ open, onClose, title, children, className }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-surface/60 backdrop-blur-sm" onClick={onClose} />
      <div
        className={clsx(
          "relative z-10 w-full max-w-md rounded-xl border border-outline-variant bg-surface p-6 shadow-lg",
          className,
        )}
      >
        {title && (
          <div className="mb-5 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-on-surface">{title}</h2>
            <button
              onClick={onClose}
              className="text-on-surface-variant hover:text-on-surface transition-colors"
              aria-label="Close"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
