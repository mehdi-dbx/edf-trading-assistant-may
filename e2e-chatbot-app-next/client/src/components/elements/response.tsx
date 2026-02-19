import type { AnchorHTMLAttributes } from 'react';
import { type ComponentProps, memo } from 'react';
import { DatabricksMessageCitationStreamdownIntegration } from '../databricks-message-citation';
import { reportTableComponents } from '../report-table/report-table-components';
import { Streamdown } from 'streamdown';

type ResponseProps = ComponentProps<typeof Streamdown>;

function LinkOrCitation(props: AnchorHTMLAttributes<HTMLAnchorElement>) {
  if (props.href?.includes('reports.zip')) {
    return (
      <a
        {...props}
        className="inline-flex rounded-md border-2 border-blue-500 bg-transparent px-4 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 dark:border-blue-400 dark:text-blue-400 dark:hover:bg-blue-950/50"
      >
        Download All Reports
      </a>
    );
  }
  return <DatabricksMessageCitationStreamdownIntegration {...props} />;
}

export const Response = memo(
  (props: ResponseProps) => {
    return (
      <Streamdown
        components={{
          ...reportTableComponents,
          a: LinkOrCitation,
        }}
        className="flex flex-col gap-4"
        {...props}
      />
    );
  },
  (prevProps, nextProps) => prevProps.children === nextProps.children,
);

Response.displayName = 'Response';
