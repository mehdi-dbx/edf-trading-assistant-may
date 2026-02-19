import React, { useMemo, useState } from 'react';
import { Check } from 'lucide-react';
import { Button } from './ui/button';
import { cn } from '@/lib/utils';
import { toast } from './toast';

export interface EmailRecipient {
  airline_name: string;
  contact_name: string;
  to_email: string;
  pdf_path: string;
  period_label: string;
}

function extractEmailRecipients(text: string): EmailRecipient[] | null {
  const jsonBlock = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (!jsonBlock) return null;
  try {
    const parsed = JSON.parse(jsonBlock[1].trim()) as { email_recipients?: EmailRecipient[] };
    const list = parsed?.email_recipients;
    if (!Array.isArray(list) || list.length === 0) return null;
    const valid = list.every(
      (r) =>
        typeof r?.airline_name === 'string' &&
        typeof r?.contact_name === 'string' &&
        typeof r?.to_email === 'string' &&
        typeof r?.pdf_path === 'string' &&
        typeof r?.period_label === 'string',
    );
    return valid ? list : null;
  } catch {
    return null;
  }
}

export { extractEmailRecipients };

interface EmailRecipientChecklistProps {
  recipients: EmailRecipient[];
  onCancel?: () => void;
  onSent?: () => void;
  className?: string;
}

export function EmailRecipientChecklist({
  recipients,
  onCancel,
  onSent,
  className,
}: EmailRecipientChecklistProps) {
  const [selected, setSelected] = useState<Set<number>>(() => new Set(recipients.map((_, i) => i)));
  const [sending, setSending] = useState(false);
  const [sentCount, setSentCount] = useState<number | null>(null);

  const toggle = (i: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  const selectAll = () => setSelected(new Set(recipients.map((_, i) => i)));
  const selectedList = useMemo(
    () => recipients.filter((_, i) => selected.has(i)),
    [recipients, selected],
  );

  const handleConfirm = async () => {
    if (selectedList.length === 0) {
      toast({ title: 'No recipients selected', variant: 'destructive' });
      return;
    }
    setSending(true);
    try {
      const response = await fetch('/api/send-report-emails', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipients: selectedList.map((r) => ({
            airline_name: r.airline_name,
            contact_name: r.contact_name,
            to_email: r.to_email,
            pdf_path: r.pdf_path,
            period_label: r.period_label,
          })),
        }),
      });
      if (!response.ok) {
        const err = await response.text();
        toast({ title: 'Send failed', description: err || response.statusText, variant: 'destructive' });
        return;
      }
      const raw = await response.text();
      let data: { sent: number; results?: { airline_name: string; result: string }[] };
      try {
        data = raw ? (JSON.parse(raw) as { sent: number; results?: { airline_name: string; result: string }[] }) : { sent: 0, results: [] };
      } catch {
        toast({ title: 'Send failed', description: 'Invalid response from server', variant: 'destructive' });
        return;
      }
      const failed = data.results?.filter((r) => r.result.startsWith('Error') || r.result.startsWith('Resend error')) ?? [];
      if (failed.length > 0) {
        toast({
          title: `${data.sent - failed.length} sent, ${failed.length} failed`,
          description: failed.map((f) => `${f.airline_name}: ${f.result}`).join('; '),
          variant: 'destructive',
        });
      } else {
        setSentCount(data.sent);
        toast({ title: 'Emails sent', description: `${data.sent} report(s) sent.` });
        onSent?.();
      }
    } catch (e) {
      toast({ title: 'Send failed', description: String(e), variant: 'destructive' });
    } finally {
      setSending(false);
    }
  };

  return (
    <div
      className={cn(
        'rounded-lg border border-border bg-card p-4 shadow-sm',
        className,
      )}
      data-testid="email-recipient-checklist"
    >
      <h3 className="mb-3 text-sm font-semibold text-foreground">
        Email Recipients List ({recipients.length})
      </h3>
      <div className="mb-4 max-h-64 overflow-y-auto rounded border border-border bg-muted/30">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-muted/50">
            <tr className="border-b border-border">
              <th className="w-10 px-2 py-2 text-left font-medium text-muted-foreground" />
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Airline</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Contact Name</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Email</th>
            </tr>
          </thead>
          <tbody>
            {recipients.map((r, i) => (
              <tr
                key={i}
                className={cn(
                  'border-b border-border/50 last:border-0',
                  selected.has(i) && 'bg-background/50',
                )}
              >
                <td className="w-10 px-2 py-2">
                  <input
                    type="checkbox"
                    checked={selected.has(i)}
                    onChange={() => toggle(i)}
                    className="h-4 w-4 rounded border-input text-primary focus:ring-primary"
                    aria-label={`Select ${r.airline_name}`}
                  />
                </td>
                <td className="px-3 py-2 text-foreground">{r.airline_name}</td>
                <td className="px-3 py-2 text-foreground">{r.contact_name}</td>
                <td className="px-3 py-2 text-muted-foreground">{r.to_email}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {sentCount == null ? (
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" variant="outline" size="sm" onClick={selectAll}>
            Select all
          </Button>
          <span className="text-muted-foreground text-xs">
            {selected.size} of {recipients.length} selected
          </span>
          <div className="ml-auto flex gap-2">
            <Button type="button" variant="outline" size="sm" onClick={onCancel} disabled={sending}>
              Cancel
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={handleConfirm}
              disabled={sending || selected.size === 0}
            >
              {sending ? 'Sending…' : 'Confirm and Send Email'}
            </Button>
          </div>
        </div>
      ) : (
        <div
          className="mt-3 rounded-lg border-2 border-green-200 bg-green-50/90 p-4 dark:border-green-800 dark:bg-green-950/50"
          data-testid="email-sent-success"
        >
          <div className="flex items-start gap-3">
            <Check className="size-5 shrink-0 text-green-600 dark:text-green-400" />
            <p className="min-w-0 flex-1 text-sm font-medium text-foreground">
              Emails sent successfully. {sentCount} report{sentCount === 1 ? '' : 's'} sent.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
