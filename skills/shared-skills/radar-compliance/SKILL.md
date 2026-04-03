---
name: radar-compliance
description: Extract technologies from ITSAC file and compare with Radar file to verify compliance. Use when you need to validate technology choices against the technology radar.
metadata:
  author: connected-operations
  version: "1.0"
---

# Radar Compliance Check

Extract technologies listed in the ITSAC file and compare them with technologies from the Radar file to identify compliance status.

**Requires**: Ability to read Markdown (.md) files
**Requires**: Ability to read Microsoft Word (.doc/.docx) files

**Inputs**:
- `itsac_file` - Path to ITSAC Markdown file (.md)
- `radar_file` - Path to Technology Radar Word document (.doc or .docx)

**Output**: Generates a compliance report showing which technologies are compliant, non-compliant, or not found in the radar

## Workflow

### 1. Prompt user for input files

Ask the user to provide:
- Path to the ITSAC Markdown file
- Path to the Technology Radar Word document

Validate that both files exist and have the correct extensions.

### 2. Extract technologies from ITSAC file

1. Read the ITSAC Markdown file
2. Parse and extract all technology names mentioned
3. Create a list of unique technologies found
4. Note the context/section where each technology appears

### 3. Extract technologies from Radar file

1. Read the Technology Radar Word document
2. Extract all technology names with their radar status/ring (Adopt, Trial, Assess, Hold)
3. Create a structured list of technologies with their radar status

### 4. Compare and analyze compliance

For each technology found in ITSAC:
1. Check if it exists in the Radar file
2. Categorize compliance:
   - **Compliant**: Technologies in "Adopt" or "Trial" rings
   - **Caution**: Technologies in "Assess" ring
   - **Non-Compliant**: Technologies in "Hold" ring
   - **Unknown**: Technologies not found in Radar

### 5. Generate compliance report

Create `radar_compliance_report.md` with:
- Summary statistics (total, compliant, non-compliant, unknown)
- Detailed table: Technology Name, ITSAC Context, Radar Status, Compliance Status
- Recommendations for non-compliant or unknown technologies
