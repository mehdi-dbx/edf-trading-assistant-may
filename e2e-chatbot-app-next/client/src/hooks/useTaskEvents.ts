import { useEffect, useRef } from 'react';

/**
 * Subscribe to SSE staffing/task events. When a staffing duty is created for the given assigned_to_id,
 * the onTaskCreated callback is invoked.
 */
export function useTaskEvents(
  assignedTo: string | null,
  onTaskCreated: () => void,
): void {
  const onTaskCreatedRef = useRef(onTaskCreated);
  onTaskCreatedRef.current = onTaskCreated;

  useEffect(() => {
    if (!assignedTo) return;

    const url = `/api/events/tasks?assigned_to=${encodeURIComponent(assignedTo)}`;
    const es = new EventSource(url);

    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as { type?: string };
        if (data.type === 'task_created') {
          onTaskCreatedRef.current();
        }
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      es.close();
    };

    return () => {
      es.close();
    };
  }, [assignedTo]);
}
