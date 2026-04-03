---
name: ppt-to-markdown
description: Convert PowerPoint files (.pptx) to markdown format, extracting text and images. Use when you need to analyze PowerPoint content or prepare it for further processing.
compatibility: Requires Python with python-pptx library installed.
metadata:
  author: connected-operations
  version: "1.0"
---

# Convert PowerPoint to Markdown

Extract text content and images from PowerPoint presentations and convert them to markdown format for analysis.

**Requires**: Python with `python-pptx` library
**Requires**: Access to the PowerPoint file path

## Workflow

### 1. Prompt user for PowerPoint file

- `file_path` - path to the .pptx file to convert

Validate the file exists and has .pptx extension. If not found, ask user to provide correct path.

### 2. Run the conversion script

Execute the Python script:

```bash
python scripts/convert_ppt.py "<file_path>" --no-describe
```

The script will:
- Extract all text content from slides (titles, bullet points, text boxes)
- Extract tables and convert to markdown table format
- Extract and save all images to an `images/` subdirectory
- Generate markdown file with same name as PowerPoint
- Preserve structure (headings, lists, tables, images)

### 3. Add image descriptions

After conversion, analyze extracted images and add descriptions to the markdown file.

### 4. Return results

Return the markdown file path so it can be used by other skills for analysis.

## Installation Requirements

```bash
pip install python-pptx
```
