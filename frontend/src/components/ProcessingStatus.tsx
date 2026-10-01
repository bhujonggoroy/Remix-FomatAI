import React from 'react';
import { WorkflowProgress, WorkflowStage } from '../types/document.ts';
import {
  FileSearch,
  Sparkles,
  LayoutTemplate,
  Eye,
  Download,
  CheckCircle2,
  AlertTriangle,
  Loader2,
} from 'lucide-react';

interface ProcessingStatusProps {
  workflow: WorkflowProgress;
  lastExportedFile: { filename: string; format: 'docx' | 'pdf'; sizeBytes: number } | null;
  onDismissError?: () => void;
}

const STAGES: { id: WorkflowStage; label: string; icon: React.ElementType }[] = [
  { id: 'analyzing', label: '1. Analyze', icon: FileSearch },
  { id: 'cleaning', label: '2. Clean', icon: Sparkles },
  { id: 'formatting', label: '3. Format', icon: LayoutTemplate },
  { id: 'previewing', label: '4. Preview', icon: Eye },
  { id: 'exporting', label: '5. Export', icon: Download },
];

export const ProcessingStatus: React.FC<ProcessingStatusProps> = ({
  workflow,
  lastExportedFile,
}) => {
  const isRunning =
    workflow.stage === 'analyzing' ||
    workflow.stage === 'cleaning' ||
    workflow.stage === 'formatting' ||
    workflow.stage === 'exporting';

  const isFailed = workflow.stage === 'failed';
  const isCompleted = workflow.stage === 'completed' || workflow.stage === 'previewing';

  // Determine active step index
  const activeStepIdx = STAGES.findIndex((s) => s.id === workflow.stage);

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
      {/* Workflow Stepper Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          {isRunning ? (
            <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
          ) : isFailed ? (
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          ) : isCompleted ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          ) : (
            <div className="w-2 h-2 rounded-full bg-slate-600" />
          )}

          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <span>{workflow.label}</span>
              {isRunning && (
                <span className="text-[11px] font-mono text-indigo-400 font-normal">
                  ({workflow.progressPercent}%)
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-400 max-w-xl">{workflow.detail}</p>
          </div>
        </div>

        {/* Export Completion Notification */}
        {lastExportedFile && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-950/60 border border-emerald-800/50 text-xs text-emerald-300">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <div className="truncate">
              <span className="font-semibold uppercase text-[10px] tracking-wider bg-emerald-800/60 px-1.5 py-0.5 rounded mr-1.5">
                {lastExportedFile.format}
              </span>
              <span className="font-mono">{lastExportedFile.filename}</span>
              <span className="text-emerald-400/80 ml-1.5">
                ({(lastExportedFile.sizeBytes / 1024).toFixed(1)} KB)
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Visual Step Trail */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-3">
        {STAGES.map((step, idx) => {
          const StepIcon = step.icon;
          const isCurrent = workflow.stage === step.id;
          const isPassed = activeStepIdx > idx || (isCompleted && !isRunning && !isFailed);

          return (
            <div
              key={step.id}
              className={`flex items-center gap-2 p-2 rounded-lg text-xs transition border ${
                isCurrent
                  ? 'bg-indigo-950/60 border-indigo-700 text-indigo-200'
                  : isPassed
                  ? 'bg-slate-900 border-emerald-900/40 text-emerald-400'
                  : 'bg-slate-950/50 border-slate-800/60 text-slate-500'
              }`}
            >
              <div
                className={`w-6 h-6 rounded flex items-center justify-center shrink-0 ${
                  isCurrent
                    ? 'bg-indigo-600 text-white'
                    : isPassed
                    ? 'bg-emerald-900/60 text-emerald-300'
                    : 'bg-slate-800 text-slate-400'
                }`}
              >
                {isCurrent && isRunning ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : isPassed ? (
                  <CheckCircle2 className="w-3.5 h-3.5" />
                ) : (
                  <StepIcon className="w-3.5 h-3.5" />
                )}
              </div>
              <span className="font-medium truncate">{step.label}</span>
            </div>
          );
        })}
      </div>

      {/* Progress Track */}
      {isRunning && (
        <div className="mt-3 w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
          <div
            className="bg-indigo-500 h-full transition-all duration-300 rounded-full"
            style={{ width: `${workflow.progressPercent}%` }}
          />
        </div>
      )}
    </div>
  );
};
