#!/usr/bin/env python3
"""Generate professionally formatted DOCX release notes from JSON data (Simple Table Format).
Format: 3-column table (Issue Key, Title, Status) with business value as paragraph below each row.

Usage:
    python generate_release_notes.py --file release_notes_data.json   # RECOMMENDED
    cat data.json | python generate_release_notes.py
    echo '{"project":"...","version":"...","issues":[...]}' | python generate_release_notes.py

Input: JSON data via stdin
Output: Filename to stdout on success, error message to stderr on failure
Exit codes: 0 = success, 1 = error

Required JSON fields:
    - version: Release version (string)
    - issues: Array of issue objects (non-empty)

Optional (inferred when missing):
    - project: Project name (inferred from first issue fields.project if present)
    - date: Release date

Required issue fields:
    - key: Jira issue key (e.g., "ADPPRG-282639")
    - title: Issue summary/title
    - status: Issue status (e.g., "Done", "Backlog")
    - business_value: Business value summary

Optional fields:
    - date: Release date (ISO format)
    - overview: Summary text
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
except ImportError:
    print("Error: python-docx package not installed", file=sys.stderr)
    print("Install with: pip install python-docx", file=sys.stderr)
    sys.exit(1)


def normalize_data(data):
    """Fill in missing top-level fields from issues when possible."""
    if not data.get('project') and data.get('issues'):
        # Infer project from first issue (Jira get_issue_full has fields.project)
        first = data['issues'][0]
        proj = first.get('fields', {}).get('project')
        if isinstance(proj, dict):
            data['project'] = proj.get('name') or proj.get('key', 'Release Notes')
        elif proj:
            data['project'] = str(proj)
        else:
            data['project'] = 'Release Notes'
    if not data.get('project'):
        data['project'] = 'Release Notes'
    if not data.get('date'):
        data['date'] = ''


def validate_input(data):
    """Validate the input data structure.
    
    Args:
        data: Dictionary containing release notes data
        
    Raises:
        ValueError: If validation fails with descriptive error message
    """
    # Check issues exists first (needed for normalize)
    if 'issues' not in data or not data['issues']:
        raise ValueError("Missing required field: issues")
    # Normalize (infer project when missing from first issue)
    normalize_data(data)
    if not data.get('version'):
        raise ValueError("Missing required field: version")
    
    # Validate issues is an array
    if not isinstance(data['issues'], list):
        raise ValueError("issues must be an array")
    
    # Validate issues is not empty
    if len(data['issues']) == 0:
        raise ValueError("issues array cannot be empty")
    
    # Validate each issue has required fields (title or summary)
    for index, issue in enumerate(data['issues']):
        if 'key' not in issue:
            raise ValueError(f"Issue at index {index}: missing required field: key")
        if not (issue.get('title') or issue.get('summary')):
            raise ValueError(f"Issue at index {index}: missing required field: title (or summary)")
        if 'status' not in issue:
            raise ValueError(f"Issue at index {index}: missing required field: status")
        if 'business_value' not in issue:
            raise ValueError(f"Issue at index {index}: missing required field: business_value")


def sanitize_filename(text):
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


def set_cell_border(cell, **kwargs):
    """Set cell borders.
    
    Args:
        cell: Table cell object
        **kwargs: Border properties (top, bottom, left, right)
    """
    tc = cell._element
    tcPr = tc.get_or_add_tcPr()
    
    # Create borders element
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right'):
        if edge in kwargs:
            edge_element = OxmlElement(f'w:{edge}')
            edge_element.set(qn('w:val'), 'single')
            edge_element.set(qn('w:sz'), '4')  # 1/2 pt
            edge_element.set(qn('w:space'), '0')
            edge_element.set(qn('w:color'), 'CCCCCC')  # Light gray
            tcBorders.append(edge_element)
    
    tcPr.append(tcBorders)


def set_cell_shading(cell, fill_color):
    """Set cell background color.
    
    Args:
        cell: Table cell object
        fill_color: Hex color code (e.g., "D5E8F0")
    """
    tc = cell._element
    tcPr = tc.get_or_add_tcPr()
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), fill_color)
    tcPr.append(shading)


def create_release_notes_docx(data):
    """Generate DOCX document from release notes data.
    
    Args:
        data: Dictionary containing validated release notes data
        
    Returns:
        Path to the generated DOCX file
    """
    # Create document
    doc = Document()
    
    # Set page size to US Letter (8.5" x 11")
    section = doc.sections[0]
    section.page_height = Inches(11)
    section.page_width = Inches(8.5)
    
    # Set 1-inch margins
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    
    # Set default font to Arial
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(12)
    
    # Configure Heading 1 style
    heading1_style = doc.styles['Heading 1']
    heading1_style.font.name = 'Arial'
    heading1_style.font.size = Pt(16)
    heading1_style.font.bold = True
    heading1_style.font.color.rgb = RGBColor(0, 0, 0)
    
    # Configure Heading 2 style
    heading2_style = doc.styles['Heading 2']
    heading2_style.font.name = 'Arial'
    heading2_style.font.size = Pt(14)
    heading2_style.font.bold = True
    heading2_style.font.color.rgb = RGBColor(0, 0, 0)
    
    # Add header with project name
    header = section.header
    header_para = header.paragraphs[0]
    header_para.text = f"{data['project']} - Release Notes"
    header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    header_para.style.font.name = 'Arial'
    header_para.style.font.size = Pt(10)
    
    # Add footer with page numbers
    footer = section.footer
    footer_para = footer.paragraphs[0]
    footer_para.text = "Page "
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Add page number field
    run = footer_para.add_run()
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')
    run._element.append(fldChar1)
    
    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = 'PAGE'
    run._element.append(instrText)
    
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'end')
    run._element.append(fldChar2)
    
    # Add title (Heading 1)
    title = doc.add_heading(f"Release Notes: {data['project']} {data['version']}", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    # Add overview section if present
    if 'overview' in data and data['overview']:
        doc.add_heading("Overview", level=2)
        overview_para = doc.add_paragraph(data['overview'])
        overview_para.style.font.name = 'Arial'
        overview_para.style.font.size = Pt(12)
    
    # Add issues section
    doc.add_heading("Issues", level=2)
    
    # Create issues table: Issue Key | Title | Status (business value as paragraph below each row)
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    
    table.autofit = False
    table.allow_autofit = False
    
    # Header row
    header_cells = table.rows[0].cells
    headers = ['Issue Key', 'Title', 'Status']
    
    for i, header_text in enumerate(headers):
        cell = header_cells[i]
        cell.text = header_text
        paragraph = cell.paragraphs[0]
        paragraph.style.font.name = 'Arial'
        paragraph.style.font.size = Pt(12)
        paragraph.style.font.bold = True
        set_cell_shading(cell, 'D5E8F0')
        set_cell_border(cell, top={}, bottom={}, left={}, right={})
        tc = cell._element
        tcPr = tc.get_or_add_tcPr()
        tcMar = OxmlElement('w:tcMar')
        for margin_name in ['top', 'bottom']:
            margin = OxmlElement(f'w:{margin_name}')
            margin.set(qn('w:w'), '80')
            margin.set(qn('w:type'), 'dxa')
            tcMar.append(margin)
        for margin_name in ['left', 'right']:
            margin = OxmlElement(f'w:{margin_name}')
            margin.set(qn('w:w'), '120')
            margin.set(qn('w:type'), 'dxa')
            tcMar.append(margin)
        tcPr.append(tcMar)
    
    # Data rows: each issue = table row (key, title, status) + paragraph below with business value
    for issue in data['issues']:
        row_cells = table.add_row().cells
        title_val = issue.get('title') or issue.get('summary', '')
        values = [
            issue['key'],
            title_val,
            issue['status']
        ]
        
        for i, value in enumerate(values):
            cell = row_cells[i]
            cell.text = str(value)
            paragraph = cell.paragraphs[0]
            paragraph.style.font.name = 'Arial'
            paragraph.style.font.size = Pt(12)
            set_cell_border(cell, top={}, bottom={}, left={}, right={})
            tc = cell._element
            tcPr = tc.get_or_add_tcPr()
            tcMar = OxmlElement('w:tcMar')
            for margin_name in ['top', 'bottom']:
                margin = OxmlElement(f'w:{margin_name}')
                margin.set(qn('w:w'), '80')
                margin.set(qn('w:type'), 'dxa')
                tcMar.append(margin)
            for margin_name in ['left', 'right']:
                margin = OxmlElement(f'w:{margin_name}')
                margin.set(qn('w:w'), '120')
                margin.set(qn('w:type'), 'dxa')
                tcMar.append(margin)
            tcPr.append(tcMar)
        
        # Business value as paragraph below the row (add row with merged cell)
        desc_row = table.add_row()
        desc_cell = desc_row.cells[0]
        desc_cell.merge(desc_row.cells[2])  # span all 3 columns
        desc_cell.text = str(issue.get('business_value', ''))
        for paragraph in desc_cell.paragraphs:
            paragraph.style.font.name = 'Arial'
            paragraph.style.font.size = Pt(12)
        set_cell_border(desc_cell, top={}, bottom={}, left={}, right={})
        tc = desc_cell._element
        tcPr = tc.get_or_add_tcPr()
        tcMar = OxmlElement('w:tcMar')
        for margin_name in ['top', 'bottom']:
            margin = OxmlElement(f'w:{margin_name}')
            margin.set(qn('w:w'), '80')
            margin.set(qn('w:type'), 'dxa')
            tcMar.append(margin)
        for margin_name in ['left', 'right']:
            margin = OxmlElement(f'w:{margin_name}')
            margin.set(qn('w:w'), '120')
            margin.set(qn('w:type'), 'dxa')
            tcMar.append(margin)
        tcPr.append(tcMar)
    
    # Generate filename
    filename = f"{sanitize_filename(data['project'])}_{sanitize_filename(data['version'])}_Release_Notes.docx"
    
    # Save document
    doc.save(filename)
    
    return filename


def main():
    """Main entry point - reads JSON from stdin or --file and generates DOCX."""
    parser = argparse.ArgumentParser(
        description='Generate DOCX release notes from JSON data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--version', action='version', version='1.0.0')
    parser.add_argument('-f', '--file', help='Read JSON from file instead of stdin')
    args = parser.parse_args()
    
    try:
        # Read JSON from file or stdin
        if args.file:
            with open(args.file, 'r', encoding='utf-8') as f:
                input_data = f.read()
        else:
            input_data = sys.stdin.read()
        
        if not input_data.strip():
            raise ValueError("No input data provided. Use --file release_notes_data.json or pipe JSON: cat file.json | python generate_release_notes.py")
        
        # Parse JSON
        try:
            data = json.loads(input_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON input - {e}")
        
        # Validate input
        validate_input(data)
        
        # Generate document
        filename = create_release_notes_docx(data)
        
        # Output filename to stdout
        print(filename)
        sys.exit(0)
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

