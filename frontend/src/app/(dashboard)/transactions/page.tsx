"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Table, type Column } from "@/components/ui/Table";
import { Pagination } from "@/components/ui/Pagination";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import type {
  TransactionRead, CategoryRead, AccountRead,
} from "@/lib/types";

const statusVariant: Record<string, "success" | "warning" | "neutral"> = {
  booked: "success",
  pending: "warning",
};

export default function TransactionsPage() {
  const { toast } = useToast();

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [accountId, setAccountId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [offset, setOffset] = useState(0);
  const limit = 50;

  const [transactions, setTransactions] = useState<TransactionRead[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState<AccountRead[]>([]);
  const [categories, setCategories] = useState<CategoryRead[]>([]);
  const [error, setError] = useState("");

  const [selectedTx, setSelectedTx] = useState<TransactionRead | null>(null);
  const [editCategoryId, setEditCategoryId] = useState("");
  const [savingCategory, setSavingCategory] = useState(false);

  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({
    account_id: "",
    amount: "",
    currency: "PLN",
    booking_date: "",
    description: "",
    counterparty_name: "",
  });
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    api.get<AccountRead[]>("/accounts").then(setAccounts).catch(() => {});
    api.get<CategoryRead[]>("/categories").then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const params: Record<string, string | number | undefined> = {
          offset, limit,
          search: search || undefined,
          status: status || undefined,
          account_id: accountId || undefined,
          category_id: categoryId || undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        };
        const data = await api.get<TransactionRead[]>("/transactions", params);
        setTransactions(data);
        setTotal(data.length < limit ? offset + data.length : offset + limit + 1);
      } catch (e) {
        setError(e instanceof ApiError ? e.detail : "Failed to load transactions");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [offset, limit, search, status, accountId, categoryId, dateFrom, dateTo]);

  const handleFilter = () => { setOffset(0); };

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

  const columns: Column<TransactionRead>[] = [
    { key: "booking_date", header: "Date", render: (t) => t.booking_date },
    {
      key: "description", header: "Description",
      render: (t) => <span className="font-medium text-on-surface">{t.description || "-"}</span>,
    },
    { key: "counterparty_name", header: "Counterparty" },
    {
      key: "amount", header: "Amount",
      render: (t) => (
        <span className={`font-semibold ${t.amount < 0 ? "text-error" : "text-success"}`}>
          {formatCurrency(Math.abs(t.amount))}
        </span>
      ),
    },
    {
      key: "category_id", header: "Category",
      render: (t) => {
        const cat = categories.find((c) => c.id === t.category_id);
        return cat ? <Badge variant="info">{cat.name}</Badge> : <Badge variant="neutral">Uncategorized</Badge>;
      },
    },
    {
      key: "status", header: "Status",
      render: (t) => <Badge variant={statusVariant[t.status] ?? "neutral"}>{t.status}</Badge>,
    },
  ];

  const openDetail = (tx: TransactionRead) => {
    setSelectedTx(tx);
    setEditCategoryId(tx.category_id ?? "");
  };

  const saveCategory = async () => {
    if (!selectedTx) return;
    setSavingCategory(true);
    try {
      const updated = await api.patch<TransactionRead>(`/transactions/${selectedTx.id}`, {
        category_id: editCategoryId,
        category_source: "user",
      });
      setTransactions((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      toast("Category updated", "success");
      setSelectedTx(null);
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to update category", "error");
    } finally {
      setSavingCategory(false);
    }
  };

  const reload = async () => {
    try {
      const params: Record<string, string | number | undefined> = {
        offset, limit,
        search: search || undefined,
        status: status || undefined,
        account_id: accountId || undefined,
        category_id: categoryId || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      };
      const data = await api.get<TransactionRead[]>("/transactions", params);
      setTransactions(data);
      setTotal(data.length < limit ? offset + data.length : offset + limit + 1);
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to refresh transactions", "error");
    }
  };

  const handleAdd = async () => {
    if (!addForm.account_id || !addForm.amount || !addForm.booking_date) {
      toast("Account, amount and date are required", "error");
      return;
    }
    setAdding(true);
    try {
      await api.post("/transactions", {
        account_id: addForm.account_id,
        amount: parseFloat(addForm.amount),
        currency: addForm.currency,
        booking_date: addForm.booking_date,
        description: addForm.description || undefined,
        counterparty_name: addForm.counterparty_name || undefined,
      });
      toast("Transaction added", "success");
      setShowAdd(false);
      setAddForm({ account_id: "", amount: "", currency: "PLN", booking_date: "", description: "", counterparty_name: "" });
      reload();
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to add transaction", "error");
    } finally {
      setAdding(false);
    }
  };

  const accountOpts = accounts.map((a) => ({ value: a.id, label: a.display_name }));
  const categoryOpts = categories.map((c) => ({ value: c.id, label: c.name }));

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-medium tracking-tight text-on-surface">Transactions</h1>
        <Button onClick={() => setShowAdd(true)}>Add Manual</Button>
      </div>

      {/* Filters */}
      <Card>
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <Input label="Search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Description..." />
          <Select label="Status" options={[{ value: "booked", label: "Booked" }, { value: "pending", label: "Pending" }]} placeholder="All" value={status} onChange={(e) => setStatus(e.target.value)} />
          <Select label="Account" options={accountOpts} placeholder="All" value={accountId} onChange={(e) => setAccountId(e.target.value)} />
          <Select label="Category" options={categoryOpts} placeholder="All" value={categoryId} onChange={(e) => setCategoryId(e.target.value)} />
          <Input label="From" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <Input label="To" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </div>
        <div className="mt-4 flex justify-end">
          <Button variant="secondary" onClick={handleFilter}>Apply Filters</Button>
        </div>
      </Card>

      {/* Table */}
      <Card>
        {error ? (
          <div className="rounded-lg bg-error/10 p-4 text-sm text-error">{error}</div>
        ) : (
          <>
            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : (
              <Table
                columns={columns}
                data={transactions}
                onRowClick={openDetail}
                keyExtractor={(t) => t.id}
                emptyMessage="No transactions found"
              />
            )}
            <Pagination offset={offset} limit={limit} total={total} onChange={setOffset} />
          </>
        )}
      </Card>

      {/* Detail / Edit Category Modal */}
      <Modal open={!!selectedTx} onClose={() => setSelectedTx(null)} title="Transaction Detail">
        {selectedTx && (
          <div className="space-y-4">
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-on-surface-variant">Date</span><span className="text-on-surface">{selectedTx.booking_date}</span></div>
              <div className="flex justify-between"><span className="text-on-surface-variant">Description</span><span className="text-on-surface">{selectedTx.description || "-"}</span></div>
              <div className="flex justify-between"><span className="text-on-surface-variant">Counterparty</span><span className="text-on-surface">{selectedTx.counterparty_name || "-"}</span></div>
              <div className="flex justify-between"><span className="text-on-surface-variant">Amount</span><span className={selectedTx.amount < 0 ? "text-error" : "text-success"}>{formatCurrency(Math.abs(selectedTx.amount))}</span></div>
              <div className="flex justify-between"><span className="text-on-surface-variant">Status</span><Badge variant={statusVariant[selectedTx.status] ?? "neutral"}>{selectedTx.status}</Badge></div>
              {selectedTx.category_source && (
                <div className="flex justify-between"><span className="text-on-surface-variant">Source</span><span className="text-on-surface">{selectedTx.category_source}</span></div>
              )}
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-on-surface-variant">Category</label>
              <Select
                options={categoryOpts}
                placeholder="Select category"
                value={editCategoryId}
                onChange={(e) => setEditCategoryId(e.target.value)}
              />
              <Button onClick={saveCategory} loading={savingCategory} className="w-full">Save</Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Add Manual Transaction Modal */}
      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Manual Transaction">
        <div className="space-y-4">
          <Select label="Account" options={accountOpts} placeholder="Select account" value={addForm.account_id} onChange={(e) => setAddForm((f) => ({ ...f, account_id: e.target.value }))} />
          <Input label="Amount" type="number" step="0.01" value={addForm.amount} onChange={(e) => setAddForm((f) => ({ ...f, amount: e.target.value }))} placeholder="0.00" />
          <Input label="Currency" value={addForm.currency} onChange={(e) => setAddForm((f) => ({ ...f, currency: e.target.value }))} />
          <Input label="Date" type="date" value={addForm.booking_date} onChange={(e) => setAddForm((f) => ({ ...f, booking_date: e.target.value }))} />
          <Input label="Description" value={addForm.description} onChange={(e) => setAddForm((f) => ({ ...f, description: e.target.value }))} />
          <Input label="Counterparty" value={addForm.counterparty_name} onChange={(e) => setAddForm((f) => ({ ...f, counterparty_name: e.target.value }))} />
          <Button onClick={handleAdd} loading={adding} className="w-full">Add Transaction</Button>
        </div>
      </Modal>
    </div>
  );
}
