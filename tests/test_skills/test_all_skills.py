"""Unit tests for each of the 10 initial modular document-processing skills.

Verifies for each skill:
- Metadata attributes (name, description, version, priority)
- Validation logic on qualifying and non-qualifying inputs
- Processing rules and output transformations
"""

import pytest

from backend.skills.academic_formatting import AcademicFormattingSkill
from backend.skills.mathematics import MathematicsSkill
from backend.skills.statistics import StatisticsSkill
from backend.skills.chemistry import ChemistrySkill
from backend.skills.citation_references import CitationReferencesSkill
from backend.skills.tables import TablesSkill
from backend.skills.exam_questions import ExamQuestionsSkill
from backend.skills.study_notes import StudyNotesSkill
from backend.skills.markdown_cleanup import MarkdownCleanupSkill
from backend.skills.scientific_document import ScientificDocumentSkill


# ---------------------------------------------------------------------------
# 1. Academic Formatting Skill
# ---------------------------------------------------------------------------

def test_academic_formatting_skill():
    skill = AcademicFormattingSkill()
    assert skill.name == "Academic Formatting"
    assert skill.version == "1.0.0"
    assert skill.priority == 20

    # Test skipped heading hierarchy repair (H1 -> H3 fixed to H2)
    bad_hierarchy = "# Title\n### Skipped Subheading\nParagraph text -- with dash..."
    val = skill.validate(bad_hierarchy)
    assert len(val.issues) > 0  # Flags heading jump

    res = skill.process(bad_hierarchy)
    assert res.modified is True
    assert "## Skipped Subheading" in res.text
    assert "—" in res.text  # Em-dash applied
    assert "…" in res.text  # Ellipsis applied


# ---------------------------------------------------------------------------
# 2. Mathematics Skill
# ---------------------------------------------------------------------------

def test_mathematics_skill():
    skill = MathematicsSkill()
    assert skill.name == "Mathematics"
    assert skill.version == "1.0.0"
    assert skill.priority == 30

    # Unbalanced delimiter detection
    val_bad = skill.validate("Value of $x = 5 is incomplete.")
    assert val_bad.is_valid is False
    assert len(val_bad.issues) > 0

    # Operator normalization inside $...$
    math_text = "Let $x <= 10$ and $y >= 20$ with $a +- b$."
    res = skill.process(math_text)
    assert res.modified is True
    assert r"\le" in res.text
    assert r"\ge" in res.text
    assert r"\pm" in res.text


# ---------------------------------------------------------------------------
# 3. Statistics Skill
# ---------------------------------------------------------------------------

def test_statistics_skill():
    skill = StatisticsSkill()
    assert skill.name == "Statistics"
    assert skill.version == "1.0.0"
    assert skill.priority == 35

    stat_text = "Results showed significance (p = 0.04, t(24) = 2.45, 95% CI: [0.12, 0.88])."
    val = skill.validate(stat_text)
    assert len(val.issues) > 0  # Flags leading zero in p-value

    res = skill.process(stat_text)
    assert res.modified is True
    assert "*p* = .04" in res.text  # Stripped leading zero & italicized
    assert "*t*(24) = 2.45" in res.text  # Italicized test symbol
    assert "95% CI [0.12, 0.88]" in res.text  # Normalized CI


# ---------------------------------------------------------------------------
# 4. Chemistry Skill
# ---------------------------------------------------------------------------

def test_chemistry_skill():
    skill = ChemistrySkill()
    assert skill.name == "Chemistry"
    assert skill.version == "1.0.0"
    assert skill.priority == 40

    chem_text = "Combustion: CH4 + 2 O2 -> CO2 + 2 H2O and Ca2+ ions."
    val = skill.validate(chem_text)
    assert "ascii_reaction_arrow" in val.detected_features

    res = skill.process(chem_text)
    assert res.modified is True
    assert "CH₄" in res.text
    assert "O₂" in res.text
    assert "CO₂" in res.text
    assert "H₂O" in res.text
    assert "→" in res.text  # Converted reaction arrow
    assert "Ca²⁺" in res.text  # Formatted ionic charge


# ---------------------------------------------------------------------------
# 5. Citation / References Skill
# ---------------------------------------------------------------------------

def test_citation_references_skill():
    skill = CitationReferencesSkill()
    assert skill.name == "Citation/References"
    assert skill.version == "1.0.0"
    assert skill.priority == 50

    cite_text = "Prior studies (Smith and Jones, 2021) and [ 1 ] demonstrated this.\n\nBibliography\nEntry 1."
    val = skill.validate(cite_text)
    assert "apa_in_text_citations" in val.detected_features

    res = skill.process(cite_text)
    assert res.modified is True
    assert "(Smith & Jones, 2021)" in res.text
    assert "[1]" in res.text  # Bracket spacing cleaned
    assert "## Bibliography" in res.text  # Standardized heading


# ---------------------------------------------------------------------------
# 6. Tables Skill
# ---------------------------------------------------------------------------

def test_tables_skill():
    skill = TablesSkill()
    assert skill.name == "Tables"
    assert skill.version == "1.0.0"
    assert skill.priority == 45

    table_text = (
        "Table 1: Experimental Matrix\n"
        "| Sample | Metric |\n"
        "| :--- | :---: |\n"
        "| LongSampleNameA | 42.1 |\n"
        "| B | 1.0 |\n"
    )
    val = skill.validate(table_text)
    assert val.is_valid is True
    assert "table_1" in val.detected_features

    res = skill.process(table_text)
    assert res.modified is True
    assert "**Table 1.** *Experimental Matrix*" in res.text
    assert "| LongSampleNameA |" in res.text


# ---------------------------------------------------------------------------
# 7. Exam Questions Skill
# ---------------------------------------------------------------------------

def test_exam_questions_skill():
    skill = ExamQuestionsSkill()
    assert skill.name == "Exam Questions"
    assert skill.version == "1.0.0"
    assert skill.priority == 60

    exam_text = (
        "Q1: What is the speed of light? (5 pts)\n"
        "A) 3 x 10^8 m/s\n"
        "B) 5 x 10^6 m/s\n"
    )
    val = skill.validate(exam_text)
    assert "1_questions_detected" in val.detected_features

    res = skill.process(exam_text)
    assert res.modified is True
    assert "### Question 1:" in res.text
    assert "  (A)" in res.text
    assert "  (B)" in res.text
    assert "[5 points]" in res.text


# ---------------------------------------------------------------------------
# 8. Study Notes Skill
# ---------------------------------------------------------------------------

def test_study_notes_skill():
    skill = StudyNotesSkill()
    assert skill.name == "Study Notes"
    assert skill.version == "1.0.0"
    assert skill.priority == 65

    notes_text = (
        "# Biology Lecture\n"
        "Definition: Osmosis is the passive transport of water across a membrane.\n"
        "Summary\n"
        "Key point 1."
    )
    val = skill.validate(notes_text)
    assert "unformatted_callouts" in val.detected_features

    res = skill.process(notes_text)
    assert res.modified is True
    assert "> **Definition:** Osmosis" in res.text
    assert "## Summary" in res.text


# ---------------------------------------------------------------------------
# 9. Markdown Cleanup Skill
# ---------------------------------------------------------------------------

def test_markdown_cleanup_skill():
    skill = MarkdownCleanupSkill()
    assert skill.name == "Markdown Cleanup"
    assert skill.version == "1.0.0"
    assert skill.priority == 10

    chat_text = (
        "Here is the formatted paper as requested:\n\n"
        "# Scientific Report\n\n\n\n\n"
        "Content text with trailing spaces   \n"
        "Hope this helps!"
    )
    val = skill.validate(chat_text)
    assert "conversational_preamble" in val.detected_features

    res = skill.process(chat_text)
    assert res.modified is True
    assert "Here is the formatted paper" not in res.text
    assert "Hope this helps" not in res.text
    assert "\n\n\n\n" not in res.text


# ---------------------------------------------------------------------------
# 10. Scientific Document Formatting Skill
# ---------------------------------------------------------------------------

def test_scientific_document_skill():
    skill = ScientificDocumentSkill()
    assert skill.name == "Scientific Document Formatting"
    assert skill.version == "1.0.0"
    assert skill.priority == 70

    paper_text = (
        "# Deep Learning Convergence\n\n"
        "Keywords: neural networks, optimization, gradient descent\n\n"
        "1. Introduction\n"
        "Background details.\n\n"
        "2. Methodology\n"
        "Experimental steps."
    )
    val = skill.validate(paper_text)
    assert "keywords_block" in val.detected_features

    res = skill.process(paper_text)
    assert res.modified is True
    assert "**Keywords:** neural networks, optimization, gradient descent" in res.text
    assert "## Introduction" in res.text
    assert "## Methodology" in res.text
