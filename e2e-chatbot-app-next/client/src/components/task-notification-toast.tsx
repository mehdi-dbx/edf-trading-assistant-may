import { Bell } from 'lucide-react';

interface TaskNotificationToastProps {
  onGoToTask: () => void;
}

export function TaskNotificationToast({ onGoToTask }: TaskNotificationToastProps) {
  return (
    <div
      data-testid="toast"
      className="flex w-[320px] flex-col items-center rounded-xl bg-white p-4 shadow-lg dark:bg-slate-900 dark:border dark:border-slate-700"
    >
      <div className="-mt-8 mb-3 flex size-12 items-center justify-center rounded-full border-2 border-white bg-blue-600 shadow dark:border-slate-900">
        <Bell className="size-6 text-white" />
      </div>
      <h3 className="mb-2 text-center font-bold text-slate-900 dark:text-slate-100">
        New Staffing Duty!
      </h3>
      <p className="mb-4 text-center text-sm text-slate-700 dark:text-slate-300">
        You have been assigned a new staffing duty by <strong>Check-in Manager</strong>.
      </p>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onGoToTask();
        }}
        className="w-full rounded-lg bg-blue-600 py-2.5 font-medium text-white hover:bg-blue-700"
      >
        Go to Task
      </button>
    </div>
  );
}
