"use client";
import { useEffect } from "react";
import type { ReactNode } from "react";

interface FormModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
}

export function FormModal({ open, onClose, title, children }: FormModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-lg bg-carbon-light p-6 shadow-neon-blue"
        onClick={(e) => e.stopPropagation()}
      >
        {title ? <h2 className="card-title mb-4">{title}</h2> : null}
        {children}
      </div>
    </div>
  );
}

export default FormModal;
