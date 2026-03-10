import { useEffect, useRef } from 'react';

export interface TaskCreatedPayload {
  assigned_to_id: string;
  agent_name?: string;
  manager_name?: string;
}

/**
 * Subscribe to SSE staffing/task events. When a staffing duty is created for the given assigned_to_id,
 * the onTaskCreated callback is invoked with the event payload (agent_name, manager_name).
 */
export function useTaskEvents(
  assignedTo: string | null,
  onTaskCreated: (payload: TaskCreatedPayload) => void,
): void {
  const onTaskCreatedRef = useRef(onTaskCreated);
  onTaskCreatedRef.current = onTaskCreated;

  useEffect(() => {
    if (!assignedTo) return;

    const url = `/api/events/tasks?assigned_to=${encodeURIComponent(assignedTo)}`;
    const es = new EventSource(url);

    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as {
          type?: string;
          assigned_to_id?: string;
          agent_name?: string;
          manager_name?: string;
        };
        if (data.type === 'task_created') {
          onTaskCreatedRef.current({
            assigned_to_id: data.assigned_to_id ?? assignedTo,
            agent_name: data.agent_name,
            manager_name: data.manager_name,
          });
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
