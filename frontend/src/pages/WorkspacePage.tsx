import React, { useState } from 'react';
import { useDocumentFormatter } from '../hooks/useDocumentFormatter.ts';
import { useBackendHealth } from '../hooks/useBackendHealth.ts';
import { useUserSettings } from '../contexts/UserSettingsContext.tsx';
import { Header } from '../components/Header.tsx';
import { ProcessingStatus } from '../components/ProcessingStatus.tsx';
import { ErrorNotifications } from '../components/ErrorNotifications.tsx';
import { InputEditor } from '../components/InputEditor.tsx';
import { FormattingControls } from '../components/FormattingControls.tsx';
import { AIProviderSettings } from '../components/AIProviderSettings.tsx';
import { DocumentPreview } from '../components/DocumentPreview.tsx';
import { ExportControls } from '../components/ExportControls.tsx';
import { SecurityModelModal } from '../components/SecurityModelModal.tsx';
import { SkillsManagerModal } from '../components/SkillsManagerModal.tsx';

export const WorkspacePage: React.FC = () => {
  const [isSecurityModalOpen, setIsSecurityModalOpen] = useState<boolean>(false);
  const [isSkillsModalOpen, setIsSkillsModalOpen] = useState<boolean>(false);

  const { activeSkills } = useUserSettings();

  const {
    rawText,
    setRawText,
    options,
    setOptions,
    preset,
    setPreset,
    filename,
    setFilename,
    analysis,
    structuredDoc,
    executedSkills,
    skippedSkills,
    workflow,
    isProcessing,
    isExporting,
    lastExportedFile,
    error,
    clearError,
    handleAnalyzeOnly,
    handleFullPipeline,
    handleExportDocx,
    handleExportPdf,
    loadSample,
    resetAll,
  } = useDocumentFormatter();

  const { health, isConnecting, refresh: refreshHealth } = useBackendHealth();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Navigation Bar */}
      <Header
        health={health}
        isConnecting={isConnecting}
        onRefreshHealth={refreshHealth}
        onSelectSample={loadSample}
        onOpenSecurityModal={() => setIsSecurityModalOpen(true)}
        onOpenSkillsModal={() => setIsSkillsModalOpen(true)}
      />

      {/* Security & Privacy Center Modal */}
      <SecurityModelModal
        isOpen={isSecurityModalOpen}
        onClose={() => setIsSecurityModalOpen(false)}
      />

      {/* Modular Skills Architecture Modal */}
      <SkillsManagerModal
        isOpen={isSkillsModalOpen}
        onClose={() => setIsSkillsModalOpen(false)}
        executedSkills={executedSkills}
        skippedSkills={skippedSkills}
      />

      {/* Main Workspace Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Status & Error Notification Bar */}
        <div className="space-y-3">
          <ProcessingStatus workflow={workflow} lastExportedFile={lastExportedFile} />
          <ErrorNotifications error={error} onDismiss={clearError} />
        </div>

        {/* 2-Column Professional Academic Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Input, AI Engine, Formatting Controls (5/12 cols) */}
          <div className="lg:col-span-5 space-y-6">
            {/* Input Editor */}
            <InputEditor
              value={rawText}
              onChange={setRawText}
              onClear={resetAll}
              disabled={isProcessing || isExporting}
            />

            {/* Formatting Controls */}
            <FormattingControls
              preset={preset}
              onSelectPreset={setPreset}
              options={options}
              onChangeOptions={setOptions}
              filename={filename}
              onChangeFilename={setFilename}
              disabled={isProcessing || isExporting}
              activeSkillsCount={activeSkills.length}
              onOpenSkillsManager={() => setIsSkillsModalOpen(true)}
            />

            {/* AI Assistant Settings */}
            <AIProviderSettings
              rawText={rawText}
              onInsertGeneratedText={(generated) => {
                setRawText(rawText ? `${rawText}\n\n${generated}` : generated);
              }}
              onError={(msg) => {
                // Surface AI error via workflow state
                workflow.stage = 'failed';
                workflow.label = 'AI Assistant Notice';
                workflow.detail = msg;
              }}
              disabled={isProcessing || isExporting}
            />
          </div>

          {/* Right Column: Live Document Preview & Export (7/12 cols) */}
          <div className="lg:col-span-7 space-y-6">
            {/* Export & Execution Action Panel */}
            <ExportControls
              onAnalyze={handleAnalyzeOnly}
              onFormat={handleFullPipeline}
              onExportDocx={handleExportDocx}
              onExportPdf={handleExportPdf}
              preset={preset}
              filename={filename}
              isProcessing={isProcessing}
              isExporting={isExporting}
              hasContent={Boolean(rawText.trim() || structuredDoc)}
            />

            {/* Document Preview Pane */}
            <DocumentPreview
              document={structuredDoc}
              analysis={analysis}
              preset={preset}
              rawInput={rawText}
              isProcessing={isProcessing}
            />
          </div>
        </div>
      </main>

      {/* Quiet Academic Footer */}
      <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-400 bg-slate-950">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-300">FormatAI Academic</span>
            <span aria-hidden="true">·</span>
            <span>Python FastAPI & ReportLab & python-docx Engine</span>
          </div>
          <div className="flex items-center gap-4 text-[11px] text-slate-400">
            <span>Standard Margin Geometry</span>
            <span>·</span>
            <span>LaTeX Math Delimiters</span>
            <span>·</span>
            <span>OpenXML Compliant</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
