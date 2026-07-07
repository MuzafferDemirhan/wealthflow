"use client";

import { useState } from "react";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import type { ExportRead } from "@/lib/types";

const REPORT_TYPES = [
  { value: "income_vs_expenses", label: "Income vs Expenses" },
  { value: "category_breakdown", label: "Category Breakdown" },
  { value: "monthly_trends", label: "Monthly Trends" },
  { value: "net_worth", label: "Net Worth" },
] as const;

interface ExportDialogProps {
  open: boolean;
  onClose: () => void;
  defaultReportType?: string;
}

export function ExportDialog({ open, onClose, defaultReportType = "income_vs_expenses" }: ExportDialogProps) {
  const [reportType, setReportType] = useState(defaultReportType);
  const [format, setFormat] = useState<"pdf" | "csv">("pdf");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [exportResult, setExportResult] = useState<ExportRead | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError("");
    setExportResult(null);

    try {
      const body: Record<string, unknown> = { report_type: reportType, format };
      if (dateFrom) body.date_from = dateFrom;
      if (dateTo) body.date_to = dateTo;

      const result = await api.post<ExportRead>("/exports", body);
      setExportResult(result);

      if (result.status === "completed") {
        downloadExport(result.id, result.filename ?? `report.${format}`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate export");
    } finally {
      setLoading(false);
    }
  };

  const downloadExport = async (exportId: string, filename: string) => {
    try {
      const blob = await api.blob(`/exports/${exportId}/download`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setError("Failed to download export");
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Export Report">
      <div className="space-y-5">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-on-surface">Report Type</label>
          <select
            value={reportType}
            onChange={(e) => setReportType(e.target.value)}
            className="w-full rounded-xl border border-outline bg-surface px-4 py-2.5 text-sm text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            {REPORT_TYPES.map((rt) => (
              <option key={rt.value} value={rt.value}>{rt.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-on-surface">Format</label>
          <div className="flex gap-3">
            <button
              onClick={() => setFormat("pdf")}
              className={`flex-1 rounded-xl border px-4 py-2.5 text-sm font-medium transition-all ${
                format === "pdf"
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-outline text-on-surface-variant hover:border-outline-variant"
              }`}
            >
              PDF
            </button>
            <button
              onClick={() => setFormat("csv")}
              className={`flex-1 rounded-xl border px-4 py-2.5 text-sm font-medium transition-all ${
                format === "csv"
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-outline text-on-surface-variant hover:border-outline-variant"
              }`}
            >
              CSV
            </button>
          </div>
        </div>

        {reportType !== "net_worth" && reportType !== "monthly_trends" && (
          <div className="flex gap-3">
            <Input label="Date From" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            <Input label="Date To" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-error/10 p-3 text-sm text-error">{error}</div>
        )}

        {exportResult && exportResult.status === "failed" && (
          <div className="rounded-lg bg-error/10 p-3 text-sm text-error">
            Export failed: {exportResult.error_message ?? "Unknown error"}
          </div>
        )}

        {exportResult && exportResult.status === "completed" && (
          <div className="rounded-lg bg-success/10 p-3 text-sm text-success">
            Export ready! Download started automatically.
          </div>
        )}

        {exportResult && exportResult.status === "processing" && (
          <div className="rounded-lg bg-primary/10 p-3 text-sm text-primary">
            Export is being generated. Check your notifications when it is ready.
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={handleGenerate} loading={loading}>
            Generate Export
          </Button>
        </div>
      </div>
    </Modal>
  );
}
