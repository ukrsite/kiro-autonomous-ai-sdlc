#!/usr/bin/env python3
"""Generate release notes DOCX from template and JSON data.

This script generates professionally formatted Word documents from a template
and JSON input data. It uses a template (default: ESDT Release Notes Template) and replaces
placeholders with RichText formatted content.

Usage:
    python generate_from_template.py < data.json
    cat data.json | python generate_from_template.py
    echo '{"version":"...","date":"...","issues":[...]}' | python generate_from_template.py

Input: JSON data via stdin
Output: Filename to stdout on success, error message to stderr on failure
Exit codes: 0 = success, 1 = error

Required JSON fields:
    - version: Release version (string)
    - date: Release date (string)
    - issues: Array of issue objects (non-empty) OR
    - processed_issues: Dictionary with 'all' and 'by_component' keys (Jira processor format)

Required issue fields (for 'issues' array):
    - key: Jira issue key (e.g., "ADPPRG-282639")
    - title: Issue summary/title (or 'summary' field)

    Optional issue fields:
    - status: Issue status (e.g., "Done", "Backlog")
    - business_value: Business value summary (can be empty string, or 'business_impact' field)
    - component: Component name (optional, empty string when none)
    - ndsd_ticket: NDSD ticket reference (e.g., "NDSD-12345")
    - child_issues: Array of child issue objects with same structure
    - fix_version: Fix version from Jira

Alternative input format (from Jira processor):
    - processed_issues: Dictionary with keys:
        - 'all': List of all issues
        - 'by_component': Dictionary mapping component names to issue lists
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional


def _try_repair_unescaped_quotes(text: str) -> str:
    """Attempt to repair JSON with unescaped quotes inside string values.
    Common when Jira content contains phrases like "Accept forecasting predictions".
    """
    result = []
    i = 0
    in_string = False
    after_backslash = False
    n = len(text)
    while i < n:
        c = text[i]
        if after_backslash:
            result.append(c)
            after_backslash = False
        elif c == '\\' and in_string:
            result.append(c)
            after_backslash = True
        elif c == '"':
            if not in_string:
                result.append(c)
                in_string = True
            else:
                # In string: this " could be end of string or unescaped quote
                # Look ahead: if followed by : or , or } or ] or newline -> end of string
                j = i + 1
                while j < n and text[j] in ' \t\r\n':
                    j += 1
                if j < n and text[j] in (':', ',', ']', '}', '\r', '\n'):
                    result.append(c)
                    in_string = False
                else:
                    result.append('\\')
                    result.append(c)
        else:
            result.append(c)
        i += 1
    return ''.join(result)

# Configure logging
logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO
)

try:
    from docxtpl import DocxTemplate, RichText, RichTextParagraph
except ImportError:
    print("Error: docxtpl package not installed", file=sys.stderr)
    print("Install with: pip install docxtpl", file=sys.stderr)
    sys.exit(1)


def validate_input(data: Dict) -> None:
    """Validate the input data structure.
    
    Supports two input formats:
    1. Simple format: {version, date, issues: [...]}
    2. Jira processor format: {version, date, processed_issues: {all: [...], by_component: {...}}}
    
    Args:
        data: Dictionary containing release notes data
        
    Raises:
        ValueError: If validation fails with descriptive error message
    """
    # Normalize common field name variants before validation
    if 'release_info' in data and isinstance(data['release_info'], dict):
        ri = data['release_info']
        if 'version' not in data and ri.get('version'):
            data['version'] = ri['version']
        if 'date' not in data and ri.get('date'):
            data['date'] = ri['date']
        if 'project' not in data and ri.get('project'):
            data['project'] = ri['project']
    if 'release_version' in data and 'version' not in data:
        data['version'] = data['release_version']
    if 'release_date' in data and 'date' not in data:
        data['date'] = data['release_date']
    for issue in data.get('issues', []) + data.get('processed_issues', {}).get('all', []):
        if 'summary' in issue and 'title' not in issue:
            issue['title'] = issue['summary']
        if 'title' in issue and 'summary' not in issue:
            issue['summary'] = issue['title']
        if 'issue_key' in issue and 'key' not in issue:
            issue['key'] = issue['issue_key']
        # Normalize component to string (handles list or Jira list-of-dicts; avoids "unhashable type: list")
        comp_raw = issue.get('component') or issue.get('components') or (issue.get('fields') or {}).get('components')
        if comp_raw is not None:
            issue['component'] = _normalize_component_to_string(comp_raw)

    # Check required top-level fields
    required_fields = ['version', 'date']
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValueError(
                f"Missing required field: {field}. Use top-level 'version' and 'date', "
                "or release_info.version/date, or release_version/release_date."
            )
    
    # Check for either 'issues' or 'processed_issues'
    if 'processed_issues' in data:
        # Jira processor format
        if not isinstance(data['processed_issues'], dict):
            raise ValueError("processed_issues must be a dictionary")
        
        if 'all' not in data['processed_issues']:
            raise ValueError("processed_issues must contain 'all' key")
        
        if not isinstance(data['processed_issues']['all'], list):
            raise ValueError("processed_issues['all'] must be a list")
        
        if len(data['processed_issues']['all']) == 0:
            raise ValueError("processed_issues['all'] cannot be empty")
        
        # Validate issues in 'all' array
        issues_to_validate = data['processed_issues']['all']
        
    elif 'issues' in data:
        # Simple format
        if not isinstance(data['issues'], list):
            raise ValueError("issues must be an array")
        
        if len(data['issues']) == 0:
            raise ValueError("issues array cannot be empty")
        
        issues_to_validate = data['issues']
    else:
        raise ValueError("Missing required field: either 'issues' or 'processed_issues'")
    
    # Validate each issue has required fields (title or summary)
    for index, issue in enumerate(issues_to_validate):
        if 'key' not in issue or issue['key'] is None:
            raise ValueError(f"Issue at index {index}: missing required field: key")
        if not (issue.get('title') or issue.get('summary')):
            raise ValueError(f"Issue at index {index}: missing required field: title (or summary)")
        
        # business_value can be empty string but should exist
        if 'business_value' not in issue:
            # Set default empty string if missing
            issue['business_value'] = ''


def sanitize_filename(text: str) -> str:
    """Sanitize a string for use in filenames.
    
    Args:
        text: String to sanitize
        
    Returns:
        Sanitized string safe for filenames
    """
    # Replace invalid filename characters with underscore
    text = re.sub(r'[<>:"/\\|?*]', '_', text)
    # Replace spaces with underscore
    text = re.sub(r'\s+', '_', text)
    # Replace multiple underscores with single underscore
    text = re.sub(r'_+', '_', text)
    # Remove leading/trailing underscores
    text = text.strip('_')
    return text


def _normalize_component_to_string(component) -> str:
    """Convert component field to a hashable string key. Handles Jira list-of-dicts format."""
    if component is None:
        return ''
    if isinstance(component, str):
        return component.strip()
    if isinstance(component, list):
        parts = []
        for c in component:
            if isinstance(c, dict) and 'name' in c:
                parts.append(str(c['name']).strip())
            elif isinstance(c, str):
                parts.append(c.strip())
            else:
                parts.append(str(c))
        return ", ".join(p for p in parts if p)
    return str(component)


def group_issues_by_component(issues: List[Dict]) -> Dict[str, List[Dict]]:
    """Group issues by component field.
    
    Args:
        issues: List of issue dictionaries
        
    Returns:
        Dictionary mapping component names (strings) to lists of issues
    """
    grouped: Dict[str, List[Dict]] = {}
    for issue in issues:
        # Check component, components, or fields.components (Jira raw format)
        component_raw = (
            issue.get('component') or
            issue.get('components') or
            (issue.get('fields') or {}).get('components') or
            ''
        )
        component = _normalize_component_to_string(component_raw)

        if component not in grouped:
            grouped[component] = []
        grouped[component].append(issue)
    return grouped


def deduplicate_component_groups(by_component: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """Remove duplicate issues from single-component groups.
    
    Deduplication logic:
    - If an issue has components "A, B" and also appears in single-component group "A",
      remove it from the "A" group (keep in "A, B" multi-component group)
    - Remove empty component groups after deduplication
    
    Example:
        Issue NDPF-709 has components "Oversite, Sitetracker"
        Issue appears in both "Oversite" (single) and "Oversite, Sitetracker" (multi)
        → Remove NDPF-709 from "Oversite", KEEP in "Oversite, Sitetracker"
        Result: 1.3.3 Oversite, Sitetracker | 1.3.6 Sitetracker (separate groups)
    
    Args:
        by_component: Dictionary mapping component names to issue lists
        
    Returns:
        Deduplicated dictionary with empty groups removed
    """
    import logging
    
    # Create a copy to avoid modifying during iteration
    result = {comp: issues[:] for comp, issues in by_component.items()}
    
    # Iterate over all component groups
    for components in list(result.keys()):
        components_list = components.split(", ")
        
        # Compare with other component groups
        for other_components in list(result.keys()):
            other_components_list = other_components.split(", ")
            
            # Skip if same group
            if components == other_components:
                continue
            
            # Skip if current group has MORE components than other
            # (we only remove from smaller/single-component groups)
            if len(components_list) > len(other_components_list):
                continue
            
            # Check if all components in current (smaller) group are in other (larger) group
            # Example: "Oversite" is subset of "Oversite, Sitetracker"
            if all(component in other_components_list for component in components_list):
                # Build maps of issue keys to child issue keys
                components_items_w_childs = {
                    parent['key']: [ci['key'] for ci in parent.get('child_issues', [])] if parent.get('child_issues') else []
                    for parent in result[components]
                }
                
                other_components_items_w_childs = {
                    parent['key']: [ci['key'] for ci in parent.get('child_issues', [])] if parent.get('child_issues') else []
                    for parent in result[other_components]
                }
                
                # Check each issue in the smaller component group
                # REMOVE from smaller group (components) when duplicate in larger (other_components)
                for item_key, item_childs in components_items_w_childs.items():
                    # If issue exists as parent in the larger component group, remove from SMALLER group
                    if item_key in other_components_items_w_childs.keys():
                        logging.info(f"Found duplicate [{components}]:{item_key} in [{other_components}] parents")
                        logging.info(f"Removing {item_key} from [{components}]")
                        result[components] = [
                            pi for pi in result[components] if pi['key'] != item_key
                        ]
                    
                    # Check if issue exists as child in the larger component group
                    for other_item, other_childs in other_components_items_w_childs.items():
                        if other_childs and item_key in other_childs:
                            logging.info(f"Found duplicate [{components}]:{item_key} in [{other_components}]:{other_item} childs")
                            logging.info(f"Removing {item_key} from [{components}]")
                            result[components] = [
                                pi for pi in result[components] if pi['key'] != item_key
                            ]
    
    # Remove empty component groups
    initial_count = len(result)
    result = {comp: issues for comp, issues in result.items() if issues}
    removed_count = initial_count - len(result)
    
    if removed_count > 0:
        logging.info(f"Removed {removed_count} empty component groups after deduplication")
    
    return result


def normalize_issue_fields(issue: Dict) -> Dict:
    """Normalize issue field names to match expected format.
    
    Handles variations in field names:
    - 'title' or 'summary' → 'summary'
    - 'business_value' or 'business_impact' → prefer business_value (generated paragraph) when both exist
    
    Args:
        issue: Issue dictionary with potentially varying field names
        
    Returns:
        Normalized issue dictionary
    """
    normalized = issue.copy()
    
    # Normalize summary field
    if 'summary' not in normalized and 'title' in normalized:
        normalized['summary'] = normalized['title']
    elif 'title' not in normalized and 'summary' in normalized:
        normalized['title'] = normalized['summary']
    
    # Use business_value (generated 80-120 word paragraph) for DOCX; prefer over business_impact when both exist
    bv = (normalized.get('business_value') or '').strip()
    bi = (normalized.get('business_impact') or '').strip()
    normalized['business_impact'] = bv if bv else bi
    normalized['business_value'] = normalized['business_impact']
    
    # Normalize child issues recursively
    if 'child_issues' in normalized and normalized['child_issues']:
        normalized['child_issues'] = [
            normalize_issue_fields(child) for child in normalized['child_issues']
        ]
    
    return normalized


def build_production_bugs_section(production_bugs: List[Dict]) -> RichTextParagraph:
    """Build Production Bugs Resolved section. Format: KEY: Title [Status], optional business_value below.
    
    Args:
        production_bugs: List of bug dicts with key, title/summary, status, optional business_value
        
    Returns:
        RichTextParagraph with formatted production bugs
    """
    paragraph = RichTextParagraph()
    for bug in production_bugs or []:
        bug = normalize_issue_fields(bug)
        summary = bug.get('summary') or bug.get('title') or ''
        status = bug.get('status') or 'Unknown'
        new_text = RichText()
        new_text.add(f"{bug['key']}: {summary} [{status}]", italic=True)
        paragraph.add(new_text, parastyle="ListBullet")
        bv = (bug.get('business_value') or bug.get('business_impact') or '').strip()
        if bv:
            bv_text = RichText()
            bv_text.add(f"\n{bv}\n")
            paragraph.add(bv_text, parastyle="Normal")
    return paragraph


def build_business_requirements(all_issues: List[Dict]) -> RichTextParagraph:
    """Build business requirements section using RichText formatting.
    
    Business requirements section formatting.
    Each issue is formatted as italic text with ListBullet style.
    
    Args:
        all_issues: List of all issues from processed_issues['all']
        
    Returns:
        RichTextParagraph with formatted business requirements
    """
    business_paragraph = RichTextParagraph()
    
    for issue in all_issues:
        issue = normalize_issue_fields(issue)
        new_text = RichText()
        
        # Format: [NDSD_TICKET], KEY: Summary (if ndsd_ticket exists)
        # Format: KEY: Summary (if no ndsd_ticket)
        if issue.get('ndsd_ticket'):
            new_text.add(
                f"[{issue['ndsd_ticket']}], {issue['key']}: {issue['summary']}", 
                italic=True
            )
        else:
            new_text.add(
                f"{issue['key']}: {issue['summary']}", 
                italic=True
            )
        
        business_paragraph.add(new_text, parastyle="ListBullet")
    
    return business_paragraph


def build_paragraphs(by_component_issues: Dict[str, List[Dict]], issue_field: str) -> List[RichTextParagraph]:
    """Build component-grouped paragraphs using RichText formatting.
    
    Component-grouped paragraphs formatting.
    Creates one paragraph per component with Heading3 style, followed by
    issues with ListBullet style and child issues with Normal style.
    
    Args:
        by_component_issues: Dictionary mapping component names to issue lists
        issue_field: Field name to extract ('business_impact' or 'description')
        
    Returns:
        List of RichTextParagraph objects, one per component
    """
    paragraphs = []
    
    # Iterate in dict order (no sort)
    for component in by_component_issues:
        paragraph = RichTextParagraph()
        
        # Add component name as Heading3
        paragraph.add(component, parastyle="Heading3")
        
        for issue in by_component_issues[component]:
            issue = normalize_issue_fields(issue)
            issue_text = RichText()
            
            # Format main issue
            if issue.get('ndsd_ticket'):
                main_issue = f"[{issue['ndsd_ticket']}], {issue['key']}: {issue['summary']}\n"
            else:
                main_issue = f"{issue['key']}: {issue['summary']}\n"
            
            issue_text.add(main_issue, italic=True, style="ListBullet")
            
            # Handle child issues
            if issue.get('child_issues') and len(issue['child_issues']) > 0:
                for child_issue in issue['child_issues']:
                    child_issue = normalize_issue_fields(child_issue)
                    
                    # Add child issue title
                    child_issue_title = f"\n• {child_issue['key']}: {child_issue['summary']}\n"
                    issue_text.add(child_issue_title, italic=True, style="Normal")
                    
                    # Add child issue field content if not empty
                    if child_issue.get(issue_field) and child_issue[issue_field] != "":
                        field_text = f"\n{child_issue[issue_field]}\n"
                        issue_text.add(field_text, style="Normal")
            else:
                # Add parent issue field content if not empty
                if issue.get(issue_field) and issue[issue_field] != "":
                    field_text = f"\n{issue[issue_field]}\n"
                    issue_text.add(field_text)
            
            paragraph.add(issue_text, parastyle="ListBullet")
        
        paragraphs.append(paragraph)
    
    return paragraphs


def get_default_template_path() -> Path:
    """Get the path to the default template.
    
    Returns:
        Path to the template .docx (default: ESDT Release Notes Template.docx)
        
    Raises:
        FileNotFoundError: If template doesn't exist
    """
    # Get script directory
    script_dir = Path(__file__).parent
    
    # Template is in top-level assets/templates/ subdirectory
    template_path = script_dir.parent / "assets" / "templates" / "ESDT Release Notes Template.docx"
    
    if not template_path.exists():
        raise FileNotFoundError(
            f"Default template not found at: {template_path}\n"
            f"Use --template /path/to/your/template.docx or add the default template to assets/templates/"
        )
    
    return template_path


def generate_document(data: Dict, template_path: Optional[Path] = None, output_path: Optional[Path] = None) -> str:
    """Generate DOCX document from template and data.
    
    Supports two input formats:
    1. Simple format: {version, date, issues: [...]}
    2. Jira processor format: {version, date, processed_issues: {all: [...], by_component: {...}}}
    
    Args:
        data: Dictionary containing validated release notes data
        template_path: Optional path to custom template (uses default if None)
        output_path: Optional path for output file (default: Release_Notes_{version}.docx in cwd)
        
    Returns:
        Path to the generated DOCX file
        
    Raises:
        FileNotFoundError: If template doesn't exist
        Exception: If document generation fails
    """
    # Get template path (default or custom)
    if template_path is None:
        template_path = get_default_template_path()
    else:
        template_path = Path(template_path)
        if not template_path.exists():
            raise FileNotFoundError(f"Custom template not found: {template_path}")
    
    # Load template
    doc = DocxTemplate(template_path)
    
    # Handle both input formats
    if 'processed_issues' in data:
        # Jira processor format: use 'all' and 'by_component' directly
        all_issues = data['processed_issues']['all']
        by_component_raw = data['processed_issues'].get('by_component', {})
        
        if not by_component_raw:
            by_component_issues = group_issues_by_component(all_issues)
            by_component_issues = deduplicate_component_groups(by_component_issues)
        else:
            # Normalize keys to strings (handles list keys that cause "unhashable type: list")
            by_component_issues = {
                _normalize_component_to_string(k): v
                for k, v in by_component_raw.items()
            }
            by_component_issues = deduplicate_component_groups(by_component_issues)
    else:
        # Simple format: use 'issues' array, group and deduplicate
        all_issues = data['issues']
        by_component_issues = group_issues_by_component(all_issues)
        by_component_issues = deduplicate_component_groups(by_component_issues)
    
    # Build content sections using RichText formatting
    business_requirements = build_business_requirements(all_issues)
    business_impacts = build_paragraphs(by_component_issues, 'business_impact')
    descriptions = build_paragraphs(by_component_issues, 'description')
    production_bugs_section = build_production_bugs_section(
        data.get('production_bugs', [])
    )
    
    # Prepare context for template
    # The template expects RichText objects that preserve Word formatting
    context = {
        'Replace_Date': data['date'],
        'Replace_Release_Number': data['version'],
        'Replace_Business_Requirements': business_requirements,
        'Replace_Business_Impacts': business_impacts,
        'Replace_NonAI_Descriptions': descriptions,
        'Replace_Production_Bugs': production_bugs_section,
    }
    
    # Render template with context
    try:
        doc.render(context)
    except TypeError as e:
        if "not iterable" in str(e):
            # Provide helpful error message
            raise Exception(
                f"Template rendering failed. The template structure may not match the expected format. "
                f"Expected RichText objects for formatting. Original error: {e}"
            )
        else:
            raise
    except Exception as e:
        raise Exception(f"Template rendering failed: {e}")
    
    # Output path: explicit or default in cwd (template name as prefix, e.g. ESDT_Release_Notes_Template_25.4.2.docx)
    if output_path is not None:
        filename = str(Path(output_path).resolve())
    else:
        prefix = sanitize_filename(template_path.stem)
        filename = f"{prefix}_{sanitize_filename(data['version'])}.docx"
    
    # Save document
    doc.save(filename)
    
    return filename


def main():
    """Main entry point - reads JSON from stdin and generates DOCX."""
    parser = argparse.ArgumentParser(
        description='Generate DOCX release notes from template and JSON data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--version', action='version', version='1.0.0')
    parser.add_argument(
        '--file',
        type=str,
        metavar='PATH',
        help='Read JSON from file instead of stdin (avoids blocking)'
    )
    parser.add_argument(
        '--template',
        type=str,
        help='Path to custom template (optional, uses default template by default)'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        metavar='PATH',
        help='Output file path (default: Release_Notes_{version}.docx in current directory)'
    )
    args = parser.parse_args()
    
    try:
        # Read JSON from file or stdin
        if args.file:
            with open(args.file, 'r', encoding='utf-8') as f:
                input_data = f.read()
        else:
            input_data = sys.stdin.read()
        
        if not input_data.strip():
            raise ValueError("No input data provided")
        
        # Parse JSON (attempt repair if unescaped quotes detected)
        try:
            data = json.loads(input_data)
        except json.JSONDecodeError as e:
            if 'Expecting' in e.msg and ('delimiter' in e.msg or 'value' in e.msg):
                repaired = _try_repair_unescaped_quotes(input_data)
                try:
                    data = json.loads(repaired)
                except json.JSONDecodeError:
                    pos = e.pos or 0
                    start = max(0, pos - 60)
                    end = min(len(input_data), pos + 60)
                    snippet = repr(input_data[start:end])
                    msg = (
                        f"Invalid JSON at line {e.lineno} col {e.colno}: {e.msg}. "
                        f"Common cause: unescaped double quotes in business_value or title. "
                        f"Context: ...{snippet}..."
                    )
                    raise ValueError(msg)
            else:
                raise
        
        # Validate input
        validate_input(data)
        
        # Generate document
        template_path = Path(args.template) if args.template else None
        output_path = Path(args.output) if args.output else None
        filename = generate_document(data, template_path, output_path)
        
        # Output filename to stdout
        print(filename)
        sys.exit(0)
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
