import React, { useRef } from 'react';
import {
  Heading2,
  Heading3,
  Bold,
  Italic,
  Sigma,
  Table as TableIcon,
  Quote,
  Trash2,
  Copy,
  Check,
} from 'lucide-react';

interface InputEditorProps {
  value: string;
  onChange: (val: string) => void;
  onClear: () => void;
  disabled?: boolean;
}

export const InputEditor: React.FC<InputEditorProps> = ({
  value,
  onChange,
  onClear,
  disabled = false,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [copied, setCopied] = React.useState(false);

  // Compute live statistics
  const charCount = value.length;
  const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0;
  const lineCount = value ? value.split('\n').length : 0;
  const readingTime = Math.ceil(wordCount / 220);

  const insertSnippet = (prefix: string, suffix = '') => {
    if (disabled || !textareaRef.current) return;
    const el = textareaRef.current;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const selected = value.substring(start, end);
    const replacement = `${prefix}${selected || 'text'}${suffix}`;

    const nextValue = value.substring(0, start) + replacement + value.substring(end);
    onChange(nextValue);

    setTimeout(() => {
      el.focus();
      el.setSelectionRange(start + prefix.length, start + prefix.length + (selected.length || 4));
    }, 10);
  };

  const insertTableTemplate = () => {
    const tableMd = `\n| Metric | Baseline | Proposed Model | Variance |\n| --- | --- | --- | --- |\n| Accuracy (%) | 82.4 | 88.9 | +6.5 |\n| Latency (ms) | 24.1 | 18.2 | -5.9 |\n`;
    insertSnippet(tableMd, '');
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col h-full shadow-sm">
      {/* Editor Header & Markdown Toolbar */}
      <div className="bg-slate-950 px-4 py-2.5 border-b border-slate-800 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1">
          <span className="text-xs font-semibold text-slate-300 mr-2">Input Editor</span>

          {/* Heading Insertions */}
          <div className="flex items-center bg-slate-900 rounded-md p-0.5 border border-slate-800">
            <button
              type="button"
              onClick={() => insertSnippet('## ')}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
              title="Heading 2 (##)"
            >
              <Heading2 className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => insertSnippet('### ')}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
              title="Heading 3 (###)"
            >
              <Heading3 className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Inline Formats */}
          <div className="flex items-center bg-slate-900 rounded-md p-0.5 border border-slate-800 ml-1">
            <button
              type="button"
              onClick={() => insertSnippet('**', '**')}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
              title="Bold (**text**)"
            >
              <Bold className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => insertSnippet('*', '*')}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
              title="Italic (*text*)"
            >
              <Italic className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Academic Entities: Math & Tables */}
          <div className="flex items-center bg-slate-900 rounded-md p-0.5 border border-slate-800 ml-1">
            <button
              type="button"
              onClick={() => insertSnippet('$', '$')}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
              title="Inline Math ($...$)"
            >
              <Sigma className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => insertSnippet('$$\n\\sum_{i=1}^N x_i = ', '\n$$')}
              className="px-1.5 py-1 rounded hover:bg-slate-800 text-[11px] font-mono text-indigo-400 font-bold transition"
              title="Display Math Block ($$...$$)"
            >
              $$
            </button>
            <button
              type="button"
              onClick={insertTableTemplate}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
              title="Insert Table Structure"
            >
              <TableIcon className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => insertSnippet('> ')}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
              title="Blockquote (>)"
            >
              <Quote className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Action Controls: Copy & Clear */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={handleCopy}
            disabled={!value}
            className="flex items-center gap-1 px-2 py-1 text-[11px] text-slate-400 hover:text-slate-200 hover:bg-slate-900 rounded transition disabled:opacity-40 cursor-pointer"
            title="Copy editor content"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          <button
            type="button"
            onClick={onClear}
            disabled={!value || disabled}
            className="flex items-center gap-1 px-2 py-1 text-[11px] text-slate-400 hover:text-rose-400 hover:bg-rose-950/40 rounded transition disabled:opacity-40 cursor-pointer"
            title="Clear editor"
          >
            <Trash2 className="w-3 h-3" />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* Main Textarea */}
      <div className="relative flex-1 min-h-[380px] p-2 bg-slate-950">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="Paste unformatted manuscript text, lecture notes, or exam content here with markdown headings (#, ##) or mathematical notation ($...$)..."
          className="w-full h-full min-h-[380px] p-3 bg-transparent text-slate-200 font-mono text-xs leading-relaxed resize-y focus:outline-none placeholder-slate-600"
          spellCheck={false}
        />
      </div>

      {/* Editor Stats Footer */}
      <div className="bg-slate-950 px-4 py-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
        <div className="flex items-center gap-3 font-mono tabular-nums">
          <span>{wordCount.toLocaleString()} words</span>
          <span aria-hidden="true">·</span>
          <span>{charCount.toLocaleString()} characters</span>
          <span aria-hidden="true">·</span>
          <span>{lineCount} lines</span>
        </div>
        <div className="text-slate-400">
          <span>Est. read time: </span>
          <span className="font-mono text-slate-300 font-medium">{readingTime} min</span>
        </div>
      </div>
    </div>
  );
};
