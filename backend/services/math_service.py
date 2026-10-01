"""Dedicated Mathematics Processing Service for FormatAI.

Executes the mathematical processing pipeline:
Raw text → Math detection → Delimiter normalization → LaTeX normalization
→ Mathematical representation (MathML / OMML) → DOCX mathematical output.

Ensures that mathematical formulas are NEVER exposed as raw LaTeX in exported
Microsoft Word (.docx) files, instead compiling them into native Office Math
Markup Language (OMML) equations editable in Microsoft Word Equation Editor.
"""

import re
from typing import List, Optional, Tuple

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Pt, RGBColor

import latex2mathml.converter
import mathml2omml

from backend.core.logging import logger
from backend.models.math import (
    MathConversionResult,
    MathSpan,
    MathType,
    TextSegment,
)
from backend.utils.math_detector import (
    clean_latex,
    detect_math_spans,
    normalize_delimiters,
    segment_text,
)


class MathService:
    """Orchestrates detection, conversion, and Word OpenXML rendering of mathematics."""

    def __init__(self):
        # Cache for converted equations to avoid duplicate compilation
        self._omml_cache: dict[Tuple[str, bool], MathConversionResult] = {}

    def normalize_delimiters(self, text: str) -> str:
        """Converts LaTeX delimiters (\\[...\\], \\(...\\), \\begin{equation}) to canonical forms."""
        return normalize_delimiters(text)

    def detect_math(self, text: str) -> List[MathSpan]:
        """Identifies mathematical regions with offsets, types, and raw text."""
        return detect_math_spans(text)

    def segment_text(self, text: str) -> List[TextSegment]:
        """Divides text into alternating plain prose and mathematical segments."""
        return segment_text(text)

    def latex_to_omml(self, raw_latex: str, is_display: bool = False) -> MathConversionResult:
        """Converts LaTeX math to Word OMML XML markup.

        Gracefully degrades to Unicode representation on syntax errors.
        """
        cleaned_latex = clean_latex(raw_latex)
        cache_key = (cleaned_latex, is_display)
        if cache_key in self._omml_cache:
            return self._omml_cache[cache_key]

        if not cleaned_latex:
            res = MathConversionResult(
                latex="",
                is_display=is_display,
                success=False,
                error_message="Empty LaTeX string",
            )
            self._omml_cache[cache_key] = res
            return res

        # 1. LaTeX Normalization for conversion engine
        normalized_latex = self._preprocess_latex_for_converter(cleaned_latex)

        try:
            # 2. LaTeX -> MathML
            mathml = latex2mathml.converter.convert(normalized_latex)

            # 3. MathML -> OMML
            omml = mathml2omml.convert(mathml)
            omml = self._sanitize_omml(omml)

            # 4. Wrap with proper Office Math namespace and structure
            if is_display:
                # Extract inner content from <m:oMath>...</m:oMath>
                inner_match = re.search(r"<m:oMath>(.*?)</m:oMath>", omml, flags=re.DOTALL)
                inner_content = inner_match.group(1) if inner_match else omml
                final_omml = (
                    f'<m:oMathPara {nsdecls("m")}>'
                    f'<m:oMath>{inner_content}</m:oMath>'
                    f'</m:oMathPara>'
                )
            else:
                final_omml = omml.replace("<m:oMath>", f'<m:oMath {nsdecls("m")}>', 1)

            result = MathConversionResult(
                latex=cleaned_latex,
                is_display=is_display,
                success=True,
                omml=final_omml,
                mathml=mathml,
            )
            self._omml_cache[cache_key] = result
            return result

        except Exception as exc:
            logger.warning(
                f"LaTeX to OMML conversion failed for '{cleaned_latex}': {exc}. Using fallback."
            )
            fallback = self._create_unicode_fallback(cleaned_latex)
            result = MathConversionResult(
                latex=cleaned_latex,
                is_display=is_display,
                success=False,
                unicode_fallback=fallback,
                error_message=str(exc),
            )
            self._omml_cache[cache_key] = result
            return result

    def render_math_to_paragraph(
        self,
        paragraph,
        latex: str,
        is_display: bool = False,
        fallback_font: str = "Cambria Math",
        fallback_size_pt: float = 11.0,
    ) -> bool:
        """Renders a mathematical expression into a python-docx paragraph.

        Appends native OMML XML directly to paragraph._p.
        Returns True if native OMML was rendered, False if fallback was used.
        """
        conversion = self.latex_to_omml(latex, is_display=is_display)

        if conversion.success and conversion.omml:
            try:
                xml_element = parse_xml(conversion.omml)
                paragraph._p.append(xml_element)
                return True
            except Exception as xml_exc:
                # Attempt self-healing sanitization if conversion.omml was loaded from an un-sanitized cache
                try:
                    sanitized_omml = self._sanitize_omml(conversion.omml)
                    xml_element = parse_xml(sanitized_omml)
                    paragraph._p.append(xml_element)
                    return True
                except Exception:
                    pass
                logger.error(f"Failed to parse OMML XML into docx: {xml_exc}. Using fallback.")

        # Fallback: render formatted text run
        fallback_text = conversion.unicode_fallback or latex
        run = paragraph.add_run(fallback_text)
        run.italic = True
        run.font.name = fallback_font
        run.font.size = Pt(fallback_size_pt)
        return False

    def render_display_math_block(
        self,
        doc,
        latex: str,
        style,
    ) -> None:
        """Renders a standalone centered display math equation block."""
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.keep_with_next = True

        self.render_math_to_paragraph(
            paragraph=p,
            latex=latex,
            is_display=True,
            fallback_font=style.fonts.math,
            fallback_size_pt=style.sizes.body,
        )

    # -----------------------------------------------------------------------
    # Internal Preprocessing and Fallbacks
    # -----------------------------------------------------------------------

    @staticmethod
    def _sanitize_omml(omml: str) -> str:
        """Sanitizes generated OMML XML markup.

        Fixes known upstream bugs in mathml2omml such as mismatched closing tags
        (<m:groupChrPr> being closed by </m:groupChr> instead of </m:groupChrPr>).
        """
        # Fix mathml2omml groupChrPr closing tag bug (in MUnder and MOver templates)
        # Specifically: <m:groupChrPr>...props...</m:groupChr><m:e> -> <m:groupChrPr>...props...</m:groupChrPr><m:e>
        return re.sub(
            r"<m:groupChrPr>((?:(?!<m:e>).)*?)</m:groupChr>",
            r"<m:groupChrPr>\1</m:groupChrPr>",
            omml,
            flags=re.DOTALL,
        )

    def _preprocess_latex_for_converter(self, latex: str) -> str:
        """Normalizes LaTeX idioms commonly found in LLM output before passing to MathML."""
        s = latex

        # Replace non-breaking spaces and spacing commands
        s = re.sub(r"\\(?:quad|qquad|\s|,|;|!)", " ", s)

        # Normalize \begin{aligned} or \begin{align} to \begin{matrix} if bare
        s = re.sub(r"\\begin\{aligned\}", r"\\begin{matrix}", s)
        s = re.sub(r"\\end\{aligned\}", r"\\end{matrix}", s)

        # Convert simple \tag{...} to plain text or drop for OMML
        s = re.sub(r"\\tag\{[^{}]+?\}", "", s)

        # Replace \left and \right delimiters if unbalanced
        # latex2mathml handles \left( and \right), but if mismatched, strip them
        left_count = len(re.findall(r"\\left[\[\(\{|\.]", s))
        right_count = len(re.findall(r"\\right[\]\)\}|\.]", s))
        if left_count != right_count:
            s = re.sub(r"\\(?:left|right)\b", "", s)

        return s.strip()

    def _create_unicode_fallback(self, latex: str) -> str:
        """Converts common LaTeX tokens to clean readable Unicode characters."""
        s = latex

        replacements = {
            r"\alpha": "α",
            r"\beta": "β",
            r"\gamma": "γ",
            r"\delta": "δ",
            r"\epsilon": "ε",
            r"\theta": "θ",
            r"\lambda": "λ",
            r"\mu": "μ",
            r"\pi": "π",
            r"\sigma": "σ",
            r"\tau": "τ",
            r"\omega": "ω",
            r"\Delta": "Δ",
            r"\Sigma": "Σ",
            r"\Omega": "Ω",
            r"\infty": "∞",
            r"\approx": "≈",
            r"\neq": "≠",
            r"\le": "≤",
            r"\ge": "≥",
            r"\pm": "±",
            r"\times": "×",
            r"\div": "÷",
            r"\to": "→",
            r"\in": "∈",
            r"\sum": "∑",
            r"\int": "∫",
            r"\sqrt": "√",
        }

        for token, uni in replacements.items():
            s = s.replace(token, uni)

        # Clean common braces
        s = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", s)
        s = re.sub(r"[\{\}]", "", s)
        s = re.sub(r"\\", "", s)

        return s.strip()

    def latex_to_rich_text(self, raw_latex: str, is_display: bool = False) -> str:
        """Converts LaTeX mathematical expression to HTML-style rich text with <sup>, <sub>, and Unicode.

        Preserves mathematical semantics: fractions, exponents, subscripts, roots, Greek symbols,
        n-ary operators, limits, and matrices for PDF rendering engines (ReportLab).
        """
        s = raw_latex.strip()
        s = re.sub(r"^\$\$|\$\$$", "", s)
        s = re.sub(r"^\\\[|\\\]$", "", s)
        s = re.sub(r"^\$|\$$", "", s)
        s = re.sub(r"^\\\(|\\\)$", "", s)
        s = s.strip()

        # Pre-process matrices
        if "matrix" in s:
            s = re.sub(r"\\begin\{(?:pmatrix|bmatrix|vmatrix|matrix)\}", "[ ", s)
            s = re.sub(r"\\end\{(?:pmatrix|bmatrix|vmatrix|matrix)\}", " ]", s)
            s = s.replace(r"\\\\", " ; ")
            s = s.replace("&", "  ")

        symbols = {
            r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
            r"\epsilon": "ε", r"\varepsilon": "ε", r"\zeta": "ζ", r"\eta": "η",
            r"\theta": "θ", r"\vartheta": "θ", r"\iota": "ι", r"\kappa": "κ",
            r"\lambda": "λ", r"\mu": "μ", r"\nu": "ν", r"\xi": "ξ",
            r"\pi": "π", r"\varpi": "ϖ", r"\rho": "ρ", r"\varrho": "ϱ",
            r"\sigma": "σ", r"\varsigma": "ς", r"\tau": "τ", r"\upsilon": "υ",
            r"\phi": "φ", r"\varphi": "ϕ", r"\chi": "χ", r"\psi": "ψ",
            r"\omega": "ω",
            r"\Delta": "Δ", r"\Gamma": "Γ", r"\Theta": "Θ", r"\Lambda": "Λ",
            r"\Xi": "Ξ", r"\Pi": "Π", r"\Sigma": "Σ", r"\Upsilon": "Υ",
            r"\Phi": "Φ", r"\Psi": "Ψ", r"\Omega": "Ω",
            r"\sum": "∑", r"\int": "∫", r"\iint": "∬", r"\iiint": "∭",
            r"\oint": "∮", r"\prod": "∏", r"\coprod": "∐", r"\infty": "∞",
            r"\approx": "≈", r"\neq": "≠", r"\le": "≤", r"\ge": "≥",
            r"\leq": "≤", r"\geq": "≥", r"\ll": "≪", r"\gg": "≫",
            r"\pm": "±", r"\mp": "∓", r"\times": "×", r"\div": "÷",
            r"\cdot": "·", r"\partial": "∂", r"\nabla": "∇", r"\to": "→",
            r"\leftarrow": "←", r"\rightarrow": "→", r"\leftrightarrow": "↔",
            r"\Leftarrow": "⇐", r"\Rightarrow": "⇒", r"\Leftrightarrow": "⇔",
            r"\in": "∈", r"\notin": "∉", r"\subset": "⊂", r"\supset": "⊃",
            r"\subseteq": "⊆", r"\supseteq": "⊇", r"\cup": "∪", r"\cap": "∩",
            r"\forall": "∀", r"\exists": "∃", r"\nexists": "∄",
            r"\hbar": "ħ", r"\sim": "~", r"\equiv": "≡", r"\parallel": "∥",
        }
        for k, v in symbols.items():
            s = s.replace(k, v)

        # Spacing commands
        s = re.sub(r"\\(?:quad|qquad|\s|,|;|!)+", " ", s)

        # Radicals
        s = re.sub(r"\\sqrt\[([^\]]+)\]\{([^{}]+)\}", r"<sup>\1</sup>√(\2)", s)
        s = re.sub(r"\\sqrt\{([^{}]+)\}", r"√(\1)", s)

        # Fractions (3 levels of nesting)
        for _ in range(3):
            s = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", s)

        # Superscripts
        s = re.sub(r"\^\{([^{}]+)\}", r"<sup>\1</sup>", s)
        s = re.sub(r"\^([a-zA-Z0-9α-ωΑ-Ω∞+\-*=])", r"<sup>\1</sup>", s)

        # Subscripts
        s = re.sub(r"_\{([^{}]+)\}", r"<sub>\1</sub>", s)
        s = re.sub(r"_([a-zA-Z0-9α-ωΑ-Ω∞+\-*=])", r"<sub>\1</sub>", s)

        # Styles
        s = re.sub(r"\\(?:mathbf|textbf)\{([^{}]+)\}", r"<b>\1</b>", s)
        s = re.sub(r"\\(?:mathit|textit)\{([^{}]+)\}", r"<i>\1</i>", s)
        s = re.sub(r"\\(?:mathrm|text|operatorname)\{([^{}]+)\}", r"\1", s)
        s = re.sub(r"\\hat\{([^{}]+)\}", r"\1̂", s)
        s = re.sub(r"\\bar\{([^{}]+)\}", r"\1̄", s)
        s = re.sub(r"\\vec\{([^{}]+)\}", r"\1⃗", s)

        # Strip any remaining LaTeX commands & cleanup braces
        s = re.sub(r"\\[a-zA-Z]+", "", s)
        s = s.replace("{", "").replace("}", "").replace(r"\ ", " ")
        s = re.sub(r"\s+", " ", s).strip()
        return s

