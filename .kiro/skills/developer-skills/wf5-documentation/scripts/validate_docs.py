"""Validate generated documentation for completeness, accuracy, and formatting.

This script is used by the WF5 Documentation workflow to perform automated
validation checks on generated documentation files. It verifies that docs
meet the standards defined in references/doc-standards.md and the completeness
criteria defined in references/completeness-criteria.md.

Usage:
    python validate_docs.py <docs_path> [--codebase <codebase_path>] [--types api,architecture,onboarding]
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationResult:
    """Result of a single validation check."""

    criterion: str
    passed: bool
    details: str
    doc_type: str


@dataclass
class ValidationReport:
    """Aggregated validation report across all checks."""

    results: list = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total number of checks performed."""
        return len(self.results)

    @property
    def passed(self) -> int:
        """Number of checks that passed."""
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        """Number of checks that failed."""
        return sum(1 for r in self.results if not r.passed)

    @property
    def pass_rate(self) -> float:
        """Percentage of checks that passed."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100

    def add(self, result: ValidationResult) -> None:
        """Add a validation result to the report."""
        self.results.append(result)

    def to_dict(self) -> dict:
        """Convert report to a dictionary for JSON serialization."""
        return {
            "summary": {
                "total_checks": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "pass_rate": round(self.pass_rate, 1),
            },
            "results": [
                {
                    "criterion": r.criterion,
                    "passed": r.passed,
                    "details": r.details,
                    "doc_type": r.doc_type,
                }
                for r in self.results
            ],
        }


def find_markdown_files(docs_path: Path) -> list[Path]:
    """Find all Markdown files in the documentation directory."""
    return sorted(docs_path.rglob("*.md"))


def validate_markdown_formatting(file_path: Path) -> list[ValidationResult]:
    """Validate Markdown formatting standards for a single file."""
    results = []
    content = file_path.read_text(encoding="utf-8")
    relative = str(file_path)

    # Check for heading hierarchy (should start with # or ##)
    headings = re.findall(r"^(#{1,6})\s+", content, re.MULTILINE)
    if headings:
        results.append(ValidationResult(
            criterion=f"Heading hierarchy in {relative}",
            passed=True,
            details="Headings found with proper Markdown syntax",
            doc_type="formatting",
        ))
    else:
        results.append(ValidationResult(
            criterion=f"Heading hierarchy in {relative}",
            passed=False,
            details="No Markdown headings found in file",
            doc_type="formatting",
        ))

    # Check code blocks have language identifiers
    code_blocks = re.findall(r"```(\w*)\n", content)
    unlabeled = [b for b in code_blocks if not b]
    if code_blocks and not unlabeled:
        results.append(ValidationResult(
            criterion=f"Code block language labels in {relative}",
            passed=True,
            details=f"All {len(code_blocks)} code blocks have language identifiers",
            doc_type="formatting",
        ))
    elif unlabeled:
        results.append(ValidationResult(
            criterion=f"Code block language labels in {relative}",
            passed=False,
            details=f"{len(unlabeled)} of {len(code_blocks)} code blocks missing language identifiers",
            doc_type="formatting",
        ))

    return results


def validate_api_docs(docs_path: Path, codebase_path: Path | None) -> list[ValidationResult]:
    """Validate API documentation completeness and accuracy."""
    results = []
    api_files = list(docs_path.rglob("*api*"))
    api_files += list(docs_path.rglob("*API*"))
    # Deduplicate
    api_files = list(set(f for f in api_files if f.suffix == ".md"))

    if not api_files:
        results.append(ValidationResult(
            criterion="API documentation files exist",
            passed=False,
            details="No API documentation files found",
            doc_type="api",
        ))
        return results

    results.append(ValidationResult(
        criterion="API documentation files exist",
        passed=True,
        details=f"Found {len(api_files)} API documentation file(s)",
        doc_type="api",
    ))

    for api_file in api_files:
        content = api_file.read_text(encoding="utf-8")
        relative = str(api_file)

        # Check for function/method signatures
        has_signatures = bool(
            re.search(r"(def |function |class |interface |```)", content)
        )
        results.append(ValidationResult(
            criterion=f"API signatures present in {relative}",
            passed=has_signatures,
            details="Signatures found" if has_signatures else "No function/class signatures found",
            doc_type="api",
        ))

        # Check for parameter documentation
        has_params = bool(
            re.search(r"(param|parameter|argument|args|:param|@param|\| *Name)", content, re.IGNORECASE)
        )
        results.append(ValidationResult(
            criterion=f"Parameter documentation in {relative}",
            passed=has_params,
            details="Parameter documentation found" if has_params else "No parameter documentation found",
            doc_type="api",
        ))

        # Check for return type documentation
        has_returns = bool(
            re.search(r"(return|returns|:returns|@returns|Return Type)", content, re.IGNORECASE)
        )
        results.append(ValidationResult(
            criterion=f"Return type documentation in {relative}",
            passed=has_returns,
            details="Return type documentation found" if has_returns else "No return type documentation found",
            doc_type="api",
        ))

        # Check for examples
        has_examples = bool(
            re.search(r"(example|usage|```)", content, re.IGNORECASE)
        )
        results.append(ValidationResult(
            criterion=f"Usage examples in {relative}",
            passed=has_examples,
            details="Examples found" if has_examples else "No usage examples found",
            doc_type="api",
        ))

    # Cross-reference with codebase if provided
    if codebase_path and codebase_path.exists():
        results.extend(_validate_api_against_codebase(api_files, codebase_path))

    return results


def _validate_api_against_codebase(
    api_files: list[Path], codebase_path: Path
) -> list[ValidationResult]:
    """Cross-reference API docs against actual source code."""
    results = []

    # Collect all documented symbols from API docs
    documented_symbols = set()
    for api_file in api_files:
        content = api_file.read_text(encoding="utf-8")
        # Match common patterns: `function_name`, **function_name**, ### function_name
        symbols = re.findall(r"(?:`|#{1,4}\s+|\*\*)(\w+)(?:`|\*\*)", content)
        documented_symbols.update(symbols)

    # Collect public symbols from source code
    source_symbols = set()
    for ext in ("*.py", "*.js", "*.ts", "*.java"):
        for src_file in codebase_path.rglob(ext):
            src_content = src_file.read_text(encoding="utf-8", errors="ignore")
            # Python public functions/classes
            if ext == "*.py":
                funcs = re.findall(r"^def (\w+)", src_content, re.MULTILINE)
                classes = re.findall(r"^class (\w+)", src_content, re.MULTILINE)
                public = [s for s in funcs + classes if not s.startswith("_")]
                source_symbols.update(public)
            # JS/TS exports
            elif ext in ("*.js", "*.ts"):
                exports = re.findall(r"export\s+(?:function|class|const|let)\s+(\w+)", src_content)
                source_symbols.update(exports)
            # Java public classes/methods
            elif ext == "*.java":
                publics = re.findall(r"public\s+(?:class|interface|static\s+)?\s*(\w+)", src_content)
                source_symbols.update(publics)

    if source_symbols:
        covered = documented_symbols & source_symbols
        coverage = (len(covered) / len(source_symbols)) * 100 if source_symbols else 0
        results.append(ValidationResult(
            criterion="API coverage against codebase",
            passed=coverage >= 80,
            details=f"{len(covered)}/{len(source_symbols)} public symbols documented ({coverage:.0f}%)",
            doc_type="api",
        ))

    return results


def validate_architecture_docs(docs_path: Path) -> list[ValidationResult]:
    """Validate architecture diagram documentation."""
    results = []
    all_md_files = find_markdown_files(docs_path)

    # Search for Mermaid diagrams across all doc files
    mermaid_count = 0
    diagram_files = []
    for md_file in all_md_files:
        content = md_file.read_text(encoding="utf-8")
        diagrams = re.findall(r"```mermaid", content)
        if diagrams:
            mermaid_count += len(diagrams)
            diagram_files.append(md_file)

    # Also check for architecture-specific files
    arch_files = [f for f in all_md_files if "architect" in f.stem.lower() or "diagram" in f.stem.lower()]

    has_diagrams = mermaid_count > 0 or len(arch_files) > 0
    results.append(ValidationResult(
        criterion="Architecture diagrams present",
        passed=has_diagrams,
        details=f"Found {mermaid_count} Mermaid diagram(s) across {len(diagram_files)} file(s)"
        if has_diagrams
        else "No architecture diagrams found",
        doc_type="architecture",
    ))

    # Check minimum diagram count (4 required per standards)
    results.append(ValidationResult(
        criterion="Minimum diagram count (4 required)",
        passed=mermaid_count >= 4,
        details=f"Found {mermaid_count} diagrams (minimum 4 required)",
        doc_type="architecture",
    ))

    # Check diagrams have descriptions
    for md_file in diagram_files:
        content = md_file.read_text(encoding="utf-8")
        relative = str(md_file)
        # Check if there's text before each mermaid block
        sections = content.split("```mermaid")
        described = sum(1 for s in sections[:-1] if s.strip())
        total = len(sections) - 1
        results.append(ValidationResult(
            criterion=f"Diagram descriptions in {relative}",
            passed=described == total,
            details=f"{described}/{total} diagrams have preceding descriptions",
            doc_type="architecture",
        ))

    # Check for labeled relationships in diagrams
    for md_file in diagram_files:
        content = md_file.read_text(encoding="utf-8")
        relative = str(md_file)
        mermaid_blocks = re.findall(r"```mermaid\n(.*?)```", content, re.DOTALL)
        for i, block in enumerate(mermaid_blocks):
            has_labels = bool(re.search(r"-->|--|==>|-.->|\|.*\|", block))
            results.append(ValidationResult(
                criterion=f"Relationship labels in diagram {i + 1} of {relative}",
                passed=has_labels,
                details="Relationships are labeled" if has_labels else "No labeled relationships found",
                doc_type="architecture",
            ))

    return results


def validate_onboarding_docs(docs_path: Path) -> list[ValidationResult]:
    """Validate onboarding guide documentation."""
    results = []
    all_md_files = find_markdown_files(docs_path)

    # Find onboarding-related files
    onboarding_files = [
        f for f in all_md_files
        if any(kw in f.stem.lower() for kw in ("onboard", "getting-started", "setup", "quickstart", "guide"))
    ]

    if not onboarding_files:
        results.append(ValidationResult(
            criterion="Onboarding guide files exist",
            passed=False,
            details="No onboarding guide files found",
            doc_type="onboarding",
        ))
        return results

    results.append(ValidationResult(
        criterion="Onboarding guide files exist",
        passed=True,
        details=f"Found {len(onboarding_files)} onboarding file(s)",
        doc_type="onboarding",
    ))

    # Combine content from all onboarding files for section checks
    combined_content = ""
    for f in onboarding_files:
        combined_content += f.read_text(encoding="utf-8") + "\n"

    combined_lower = combined_content.lower()

    # Check required sections
    required_sections = {
        "Prerequisites": ["prerequisite", "requirements", "required tools", "you will need"],
        "Installation": ["install", "setup", "getting started"],
        "Configuration": ["config", "environment variable", "env var", ".env"],
        "Project Structure": ["project structure", "directory", "folder", "layout"],
        "Running the Application": ["run", "start", "build", "execute", "launch"],
        "Common Tasks": ["common task", "workflow", "how to", "development task"],
        "Troubleshooting": ["troubleshoot", "common issue", "problem", "faq", "error"],
    }

    for section, keywords in required_sections.items():
        found = any(kw in combined_lower for kw in keywords)
        results.append(ValidationResult(
            criterion=f"Onboarding section: {section}",
            passed=found,
            details=f"Section '{section}' found" if found else f"Section '{section}' not found in onboarding docs",
            doc_type="onboarding",
        ))

    # Check for copy-pasteable commands
    has_commands = bool(re.search(r"```(?:bash|sh|shell|console)?\n.*\n```", combined_content, re.DOTALL))
    results.append(ValidationResult(
        criterion="Copy-pasteable commands present",
        passed=has_commands,
        details="Code blocks with commands found" if has_commands else "No command code blocks found",
        doc_type="onboarding",
    ))

    return results


def validate_docs(
    docs_path: Path,
    codebase_path: Path | None = None,
    doc_types: list[str] | None = None,
) -> ValidationReport:
    """Run all validation checks on generated documentation.

    Args:
        docs_path: Path to the generated documentation directory.
        codebase_path: Optional path to the source codebase for cross-referencing.
        doc_types: List of doc types to validate. Defaults to all types.

    Returns:
        A ValidationReport with all check results.
    """
    if doc_types is None:
        doc_types = ["api", "architecture", "onboarding"]

    report = ValidationReport()

    # Check docs directory exists and has files
    if not docs_path.exists():
        report.add(ValidationResult(
            criterion="Documentation directory exists",
            passed=False,
            details=f"Directory not found: {docs_path}",
            doc_type="general",
        ))
        return report

    md_files = find_markdown_files(docs_path)
    if not md_files:
        report.add(ValidationResult(
            criterion="Documentation files exist",
            passed=False,
            details=f"No Markdown files found in {docs_path}",
            doc_type="general",
        ))
        return report

    report.add(ValidationResult(
        criterion="Documentation files exist",
        passed=True,
        details=f"Found {len(md_files)} Markdown file(s)",
        doc_type="general",
    ))

    # Formatting validation on all files
    for md_file in md_files:
        report.results.extend(validate_markdown_formatting(md_file))

    # Type-specific validation
    if "api" in doc_types:
        report.results.extend(validate_api_docs(docs_path, codebase_path))

    if "architecture" in doc_types:
        report.results.extend(validate_architecture_docs(docs_path))

    if "onboarding" in doc_types:
        report.results.extend(validate_onboarding_docs(docs_path))

    return report


def main() -> None:
    """Entry point for the documentation validation script."""
    parser = argparse.ArgumentParser(
        description="Validate generated documentation for completeness, accuracy, and formatting."
    )
    parser.add_argument(
        "docs_path",
        type=Path,
        help="Path to the generated documentation directory",
    )
    parser.add_argument(
        "--codebase",
        type=Path,
        default=None,
        help="Path to the source codebase for cross-reference validation",
    )
    parser.add_argument(
        "--types",
        type=str,
        default="api,architecture,onboarding",
        help="Comma-separated list of doc types to validate (default: api,architecture,onboarding)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )

    args = parser.parse_args()
    doc_types = [t.strip() for t in args.types.split(",")]

    report = validate_docs(args.docs_path, args.codebase, doc_types)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"\nDocumentation Validation Report")
        print(f"{'=' * 50}")
        print(f"Docs path: {args.docs_path}")
        if args.codebase:
            print(f"Codebase:  {args.codebase}")
        print(f"Types:     {', '.join(doc_types)}")
        print(f"{'=' * 50}")
        print(f"Total checks: {report.total}")
        print(f"Passed:       {report.passed}")
        print(f"Failed:       {report.failed}")
        print(f"Pass rate:    {report.pass_rate:.1f}%")
        print(f"{'=' * 50}")

        if report.failed > 0:
            print(f"\nFailed checks:")
            for r in report.results:
                if not r.passed:
                    print(f"  [{r.doc_type}] {r.criterion}")
                    print(f"    → {r.details}")

        print()

    sys.exit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    main()
