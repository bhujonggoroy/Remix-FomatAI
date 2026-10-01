# FormatAI

FormatAI is an AI-powered academic document formatting application. It transforms raw AI-generated content (from ChatGPT, Gemini, NotebookLM, Claude, Copilot, Perplexity, etc.) into professionally formatted, publication-grade academic documents (primary export target: editable DOCX and PDF).

## Clean & Modular Repository Architecture

```text
FormatAI/
├── backend/
│   ├── __init__.py                  # Python package initializer
│   ├── main.py                      # FastAPI application entry point with lifespan & CORS
│   ├── requirements.txt             # Pinned backend dependencies (FastAPI, python-docx, latex2mathml, etc.)
│   ├── api/                         # FastAPI route layer only (no business logic)
│   │   ├── __init__.py
│   │   ├── deps.py                  # Dependency injection providers (Settings, Services, MathService)
│   │   ├── router.py                # Master API router aggregating sub-routers
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py            # Route handlers for /api/health and /
│   │       ├── ai.py                # POST /api/ai/generate endpoint
│   │       └── document.py          # POST /api/document/process, /analyze, & /api/documents/docx
│   ├── services/                    # Business logic layer
│   │   ├── __init__.py
│   │   ├── math_service.py          # Dedicated Mathematics Processing & OMML synthesis engine
│   │   ├── docx_service.py          # Professional DOCX synthesis engine (python-docx + OMML)
│   │   ├── document_service.py      # Core document pipeline orchestrator
│   │   ├── content_cleanup_service.py # Strips AI conversational chatter & normalizes math delimiters
│   │   ├── formatting_service.py    # Enforces heading hierarchy, typography & list rules
│   │   ├── ai_service.py            # AIService using BaseAIProvider abstraction
│   │   ├── health_service.py        # Health diagnostics & system status logic
│   │   └── provider_service.py      # AI provider status discovery and validation logic
│   ├── providers/                   # External AI provider implementations
│   │   ├── __init__.py
│   │   ├── base.py                  # BaseAIProvider abstract interface & ProviderError hierarchy
│   │   ├── gemini.py                # Google Gemini provider implementation (google-genai SDK)
│   │   └── factory.py               # Dynamic provider registry and factory resolver
│   ├── models/                      # Pydantic schemas and data contracts
│   │   ├── __init__.py
│   │   ├── math.py                  # MathSpan, MathType, TextSegment, MathConversionResult
│   │   ├── document.py              # DocumentStructure, DocumentElement, TableData, InlineEntity
│   │   ├── ai.py                    # AIGenerateRequest, AIGenerateResponse, AIErrorResponse
│   │   ├── health.py                # HealthResponse and RootResponse schemas
│   │   └── provider.py              # AIModelInfo and AIProviderInfo schemas
│   ├── utils/                       # Reusable utility functions
│   │   ├── __init__.py
│   │   ├── math_detector.py         # Math delimiter normalization, span detection & prose protection
│   │   ├── markdown.py              # Markdown table, list, code block & heading parser
│   │   ├── text_processing.py       # Typography normalization & inline entity extraction
│   │   └── text.py                  # Word counting & whitespace normalization
│   └── core/                        # Application-level configuration and settings
│       ├── __init__.py
│       ├── config.py                # Pydantic-settings safe environment configuration
│       ├── logging.py               # Centralized structured logger setup
│       └── styles.py                # Centralized typography & formatting presets
├── frontend/
│   ├── index.html                   # HTML5 entry point for Vite React
│   ├── package.json                 # Frontend dependencies and npm scripts
│   ├── tsconfig.json                # TypeScript configuration
│   ├── vite.config.ts               # Vite configuration with API reverse proxy
│   └── src/
│       ├── App.tsx                  # Status dashboard displaying backend health & architecture
│       ├── main.tsx                 # React root mounting
│       └── index.css                # Tailwind CSS styles
├── server.ts                        # Full-stack process supervisor & reverse proxy
├── tests/
│   ├── __init__.py                  # Python test package initializer
│   ├── test_math_pipeline.py        # 15 tests verifying math detection, OMML synthesis & LaTeX handling
│   ├── test_docx_pipeline.py        # 12 tests verifying DOCX generation & Microsoft Word OpenXML
│   ├── test_document_pipeline.py    # 13 tests verifying all academic content types & pipeline
│   ├── test_ai_provider.py          # 9 tests verifying Gemini provider & AI API validation
│   ├── test_architecture.py         # 5 tests verifying Core, Services, Providers & Utils
│   └── test_health.py               # 2 tests verifying FastAPI health & root endpoints
├── .env.example                     # Template for environment variables (no secrets)
├── .gitignore                       # Ignored files for Python, Node, and environment files
└── README.md                        # Project documentation and architecture guide
```

---

## Dedicated Mathematics Processing Pipeline

FormatAI converts mathematical expressions into native Microsoft Word Office Math Markup Language (OMML) equations, ensuring that raw LaTeX source code is **never** exposed in exported documents.

### Pipeline Stages
```text
Raw Text
   │
   ▼
Math Detection & Demarcation (detect_math_spans, segment_text)
   │
   ▼
Delimiter Normalization (normalize_delimiters: \[, \begin{equation}, \( -> $$, $)
   │
   ▼
LaTeX Canonicalization & Sanitization (clean_latex, spacing & environment normalization)
   │
   ▼
Mathematical Representation (LaTeX -> MathML via latex2mathml -> OMML via mathml2omml)
   │
   ▼
DOCX OpenXML Synthesis (<m:oMathPara> for display equations, <m:oMath> for inline equations)
```

### Supported Mathematical Constructs
1. **Fractions**: Simple fractions (`\frac{x}{y}`) and nested multi-tier fractions (`\frac{\frac{a}{b}}{\frac{c}{d}}`).
2. **Exponents & Indices**: Superscripts (`x^2`, `e^{-x}`), subscripts (`x_i`, `a_{ij}`), and combined sub/superscripts (`\sigma_1^2`).
3. **Radicals**: Square roots (`\sqrt{x}`) and nth-order roots (`\sqrt[3]{8}`).
4. **Greek Letters**: Both lowercase and uppercase symbols (`\alpha, \beta, \gamma, \sigma, \mu, \lambda, \Delta, \Omega`).
5. **N-ary Operators**: Summation (`\sum_{i=1}^n x_i`), integrals (`\int_0^\infty e^{-x} dx`), products (`\prod`).
6. **Calculus & Limits**: Limits (`\lim_{x \to 0} \frac{\sin x}{x}`), partial derivatives (`\frac{\partial f}{\partial x}`).
7. **Linear Algebra**: Matrices and vectors (`\begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix}`, `\begin{matrix}`).
8. **Prose Protection**: Ordinary text containing `/` (e.g., `"5/10 students"`, `"3/4 of people"`, URLs) is strictly preserved as plain text and not converted into fractions.
9. **Currency Protection**: Currency amounts (`$100 million`, `$50.00`) are protected from being treated as inline math.

---

### Known Limitations & Edge Cases

1. **Non-Standard TeX Macros**: Custom user-defined LaTeX macros (`\newcommand`) and specialized TikZ/PGF diagrams are not supported by MathML converters and will gracefully fall back to formatted Unicode representations.
2. **Multi-Line Numbered Equation Systems**: Multi-line `align` environments with individual per-line equation numbering tags (`\tag{1}`) are simplified to aligned matrix blocks without discrete right-aligned numbering tags.
3. **LaTeX Text Inset Font Styling**: Complex nested `\text{\textbf{...}}` blocks inside deep math expressions are converted to standard text runs within the MathML stream.
4. **Equation Numbering Alignment**: Microsoft Word right-aligned equation numbers typically require custom Word field tabs or tables; OMML equations are currently centered without automatic decimal/right tab alignment stops for equation numbers.
5. **Chemical Markup**: Chemistry extensions (`\ce{H2O}`) require dedicated chemical notation handlers; they are handled via standard sub/superscript notation.

---

## Export Endpoints

- **`POST /api/documents/docx`**:
  Accepts either a structured `DocumentStructure` model or `raw_text` along with an optional style `preset` and custom `filename`. Returns a valid `.docx` attachment.
  ```json
  {
    "raw_text": "# Quantum Mechanics\n\n## Wave Mechanics\n\nThe Schrödinger equation is:\n\n$$i\\hbar\\frac{\\partial}{\\partial t}\\Psi = \\hat{H}\\Psi$$\n\nwhere $\\Psi$ represents the state vector.",
    "preset": "academic",
    "filename": "quantum_mechanics"
  }
  ```

---

## How to Run & Test

```bash
# Run complete test suite (56 tests)
python3 -m pytest tests/

# Run dev server with full-stack supervisor (starts Python FastAPI + Vite on port 3000)
npm run dev
```
