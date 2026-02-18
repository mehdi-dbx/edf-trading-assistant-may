import { type ComponentProps, memo } from 'react';
import { DatabricksMessageCitationStreamdownIntegration } from '../databricks-message-citation';
import { reportTableComponents } from '../report-table/report-table-components';
import { Streamdown } from 'streamdown';

type ResponseProps = ComponentProps<typeof Streamdown>;

export const Response = memo(
  (props: ResponseProps) => {
    return (
      <Streamdown
        components={{
          ...reportTableComponents,
          a: DatabricksMessageCitationStreamdownIntegration,
        }}
        className="flex flex-col gap-4"
        {...props}
      />
    );
  },
  (prevProps, nextProps) => prevProps.children === nextProps.children,
);

Response.displayName = 'Response';
