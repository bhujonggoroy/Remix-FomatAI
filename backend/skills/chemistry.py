"""Chemistry Skill.

Detects, validates, and normalizes chemical notation, formulas, and reaction equations:
- Automatically formats molecular subscripts (e.g. H2O -> H₂O, CO2 -> CO₂, C6H12O6 -> C₆H₁₂O₆)
- Converts ASCII reaction arrows to Unicode symbols (-> to →, <=> to ⇌)
- Formats ionic superscripts (e.g. Ca2+ -> Ca²⁺, Cl- -> Cl⁻, SO4 2- -> SO₄²⁻)
"""

import re
import time
from typing import Any, Dict, List, Optional
from backend.skills.base import BaseSkill, SkillExecutionResult, SkillValidationResult


class ChemistrySkill(BaseSkill):
    """Processes chemical formulas, molecular equations, and chemical reactions."""

    @property
    def id(self) -> str:
        return "chemistry"

    @property
    def name(self) -> str:
        return "Chemistry"

    @property
    def description(self) -> str:
        return "Normalizes chemical formulas (H₂O, CO₂), reaction arrows (→, ⇌), and ionic charges."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def priority(self) -> int:
        return 40

    @property
    def category(self) -> str:
        return "stem"

    SUB_MAP = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    SUPER_MAP = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")

    # Common chemical formulas
    COMMON_MOLECULES = [
        "H2O", "CO2", "CH4", "C6H12O6", "O2", "N2", "H2", "NH3", "NaCl", "HCl",
        "H2SO4", "HNO3", "NaOH", "KOH", "CaCO3", "CO", "NO2", "SO2", "SO3", "C2H5OH",
        "C2H6", "C3H8", "C4H10", "CH3OH", "CH3COOH"
    ]

    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillValidationResult:
        issues: List[str] = []
        features: List[str] = []

        # Detect raw unformatted chemical formulas
        unformatted_count = 0
        for mol in self.COMMON_MOLECULES:
            if re.search(r"\b" + re.escape(mol) + r"\b", text):
                features.append(f"molecule_{mol}")
                unformatted_count += 1

        # Detect reaction arrows
        if re.search(r"[A-Za-z0-9₀-₉]\s*->\s*[A-Za-z0-9₀-₉]", text):
            features.append("ascii_reaction_arrow")
            issues.append("Detected ASCII reaction arrow '->' that should use standard '→'.")

        if "<=>" in text:
            features.append("equilibrium_arrow")

        return SkillValidationResult(
            is_valid=True,
            issues=issues,
            detected_features=features,
            confidence_score=0.95 if issues else 1.0,
            metrics={"detected_molecules": unformatted_count},
        )

    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillExecutionResult:
        start_time = time.time()
        diagnostics: List[str] = []
        original_text = text
        processed = text

        # 1. Normalize common chemical formulas by subscripting numbers
        # e.g., H2O -> H₂O, CO2 -> CO₂, etc.
        for mol in sorted(self.COMMON_MOLECULES, key=len, reverse=True):
            # Replace numbers with subscripts
            formatted_mol = re.sub(r"(\d+)", lambda m: m.group(1).translate(self.SUB_MAP), mol)
            # Replace standalone occurrences
            pattern = re.compile(r"\b" + re.escape(mol) + r"\b")
            processed = pattern.sub(formatted_mol, processed)

        # 2. Standardize Ionic Charges: Ca2+ -> Ca²⁺, Cl- -> Cl⁻, Fe3+ -> Fe³⁺
        ion_pattern = re.compile(r"\b([A-Z][a-z]?)([1-4]?[+-])(?![a-zA-Z0-9])")
        def format_ion(m: re.Match) -> str:
            elem = m.group(1)
            charge = m.group(2).translate(self.SUPER_MAP)
            return f"{elem}{charge}"

        processed = ion_pattern.sub(format_ion, processed)

        VALID_ELEMENTS = {
            "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si", "P", "S",
            "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga",
            "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd",
            "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm",
            "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W", "Re", "Os",
            "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th", "Pa", "U"
        }

        # 3. General chemical formula subscripting for patterns like 'Fe2O3', 'Ca(OH)2' (excluding ions and non-elements)
        def subscript_formula(match: re.Match) -> str:
            element = match.group(1)
            num = match.group(2)
            if element not in VALID_ELEMENTS or num == "1":
                return match.group(0)
            return f"{element}{num.translate(self.SUB_MAP)}"

        # Matches Element symbol followed by number (e.g. Fe2, O2) not followed by + or -
        processed = re.sub(r"\b([A-Z][a-z]?)(\d+)(?![+-])\b", subscript_formula, processed)

        # 4. Normalize Reaction Arrows (only when between chemical terms or in equations)
        arrow_sub = re.sub(r"(\b[A-Za-z0-9₀-₉\(\)]+\s*)->(\s*[A-Za-z0-9₀-₉\(\)]+\b)", r"\1→\2", processed)
        if arrow_sub != processed:
            diagnostics.append("Converted ASCII chemical reaction arrows (->) to standard Unicode (→).")
            processed = arrow_sub

        # Equilibrium arrow <=> -> ⇌
        eq_sub = re.sub(r"(\b[A-Za-z0-9₀-₉\(\)]+\s*)<=>(\s*[A-Za-z0-9₀-₉\(\)]+\b)", r"\1⇌\2", processed)
        if eq_sub != processed:
            diagnostics.append("Converted reversible reaction arrow (<=>) to equilibrium symbol (⇌).")
            processed = eq_sub

        duration = (time.time() - start_time) * 1000.0
        is_modified = processed != original_text

        if is_modified and not diagnostics:
            diagnostics.append("Formatted chemical molecular formulas and subscripts.")

        return SkillExecutionResult(
            skill_id=self.id,
            skill_name=self.name,
            version=self.version,
            modified=is_modified,
            text=processed,
            diagnostics=diagnostics,
            metadata={"chemistry_elements_detected": is_modified},
            execution_time_ms=round(duration, 2),
        )
