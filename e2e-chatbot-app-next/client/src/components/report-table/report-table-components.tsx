import { Eye, Download } from 'lucide-react';
import type {
  ComponentType,
  HTMLAttributes,
  ReactNode,
} from 'react';
import { cn } from '@/lib/utils';

/** Minimal hast-like types for table node (Streamdown passes node from rehype). */
type HastText = { type: 'text'; value?: string };
type HastElement = {
  type: 'element';
  tagName?: string;
  children?: (HastElement | HastText)[];
};
type HastNode = HastElement | HastText;
type Element = HastElement;
type ElementContent = HastNode;
const HEADER_BG = 'bg-[#e6f0ff]';
const ROW_ALT = 'bg-[#f9f9f9]';
const STATUS_EXCELLENT = 'bg-green-50 text-green-800 border-green-200';
const STATUS_GOOD = 'bg-blue-50 text-blue-700 border-blue-200';
const STATUS_NEEDS_ATTENTION = 'bg-orange-50 text-orange-700 border-orange-200';
const STATUS_DEFAULT = 'bg-muted text-muted-foreground border-border';

function getTextContent(node: ElementContent): string {
  if (node.type === 'text') return (node as HastText).value ?? '';
  if (node.type === 'element') {
    return ((node as Element).children ?? [])
      .map(getTextContent)
      .join('');
  }
  return '';
}

function isElement(node: ElementContent): node is Element {
  return node.type === 'element';
}

function findChild(element: Element, tagName: string): Element | undefined {
  return (element.children ?? []).find(
    (c): c is Element => isElement(c) && c.tagName === tagName
  ) as Element | undefined;
}

function getChildElements(element: Element, tagName: string): Element[] {
  return (element.children ?? []).filter(
    (c): c is Element => isElement(c) && c.tagName === tagName
  );
}

function getHeaderLabels(tableNode: Element): string[] {
  const thead = findChild(tableNode, 'thead');
  if (!thead) return [];
  const firstRow = getChildElements(thead, 'tr')[0];
  if (!firstRow) return [];
  return getChildElements(firstRow, 'th').map((th) =>
    getTextContent(th).trim().toLowerCase()
  );
}

function getColumnIndices(
  headers: string[]
): { status: number | null; action: number | null } {
  let status: number | null = null;
  let action: number | null = null;
  headers.forEach((h, i) => {
    const n = h.trim().toLowerCase();
    if (n === 'status') status = i;
    if (n === 'action' || n === 'actions') action = i;
  });
  return { status, action };
}

function isNumericColumn(header: string): boolean {
  const n = header.toLowerCase();
  return (
    n.includes('check-in') ||
    n.includes('avg') ||
    n.includes('load factor') ||
    n === 'sla' ||
    n.includes('time')
  );
}

function StatusCapsule({ children }: { children: string }) {
  const value = String(children).trim().toLowerCase();
  const variant =
    value === 'excellent'
      ? STATUS_EXCELLENT
      : value === 'good'
        ? STATUS_GOOD
        : value.includes('attention') || value === 'needs attention'
          ? STATUS_NEEDS_ATTENTION
          : STATUS_DEFAULT;
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium',
        variant
      )}
    >
      {children}
    </span>
  );
}

function ActionIcons() {
  return (
    <span className="inline-flex items-center gap-2">
      <a
        href="#"
        onClick={(e) => e.preventDefault()}
        className="text-blue-600 hover:text-blue-800"
        aria-label="View"
      >
        <Eye className="size-4" />
      </a>
      <a
        href="#"
        onClick={(e) => e.preventDefault()}
        className="text-blue-600 hover:text-blue-800"
        aria-label="Download"
      >
        <Download className="size-4" />
      </a>
    </span>
  );
}

function renderCellContent(
  cellElement: Element,
  columnIndex: number,
  headers: string[],
  statusColumnIndex: number | null,
  actionColumnIndex: number | null
): ReactNode {
  const text = getTextContent(cellElement).trim();
  if (statusColumnIndex !== null && columnIndex === statusColumnIndex) {
    return <StatusCapsule>{text || '—'}</StatusCapsule>;
  }
  if (actionColumnIndex !== null && columnIndex === actionColumnIndex) {
    return <ActionIcons />;
  }
  return text || '—';
}

type TableProps = HTMLAttributes<HTMLTableElement> & { node?: Element };

export const reportTableComponents = {
  table: ((props: TableProps) => {
    const { node, children, className, ...rest } = props;
    if (!node || node.tagName !== 'table') {
      return (
        <table className={className} {...rest}>
          {children}
        </table>
      );
    }

    const headers = getHeaderLabels(node);
    const { status: statusColumnIndex, action: actionColumnIndex } =
      getColumnIndices(headers);

    const thead = findChild(node, 'thead');
    const tbody = findChild(node, 'tbody');

    return (
      <div
        className="overflow-hidden rounded-lg border border-border bg-card shadow-sm"
        data-streamdown="table-wrapper"
      >
        <table
          className={cn('w-full border-collapse text-sm', className)}
          {...rest}
        >
          {thead && (
            <thead>
              {getChildElements(thead, 'tr').map((tr, rowIdx) => (
                <tr key={rowIdx} className={cn(HEADER_BG, 'font-semibold')}>
                  {getChildElements(tr, 'th').map((th, i) => (
                    <th
                      key={i}
                      className={cn(
                        'border-b border-border px-4 py-3 text-left text-foreground',
                        isNumericColumn(headers[i] ?? '') && 'text-right'
                      )}
                    >
                      {getTextContent(th).trim() || '—'}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
          )}
          {tbody && (
            <tbody>
              {getChildElements(tbody, 'tr').map((tr, rowIdx) => (
                <tr
                  key={rowIdx}
                  className={cn(
                    'border-b border-border last:border-b-0',
                    rowIdx % 2 === 1 && ROW_ALT
                  )}
                >
                  {getChildElements(tr, 'td').map((td, i) => (
                    <td
                      key={i}
                      className={cn(
                        'px-4 py-3 text-muted-foreground',
                        i === 0 || !isNumericColumn(headers[i] ?? '')
                          ? 'text-left'
                          : 'text-right'
                      )}
                    >
                      {renderCellContent(
                        td,
                        i,
                        headers,
                        statusColumnIndex,
                        actionColumnIndex
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          )}
        </table>
      </div>
    );
  }) as ComponentType<TableProps>,
};
