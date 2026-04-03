# Template Reference

Guide for using and creating Word document templates.

## Default Template

**Location:**
```
.kiro/skills/shared-skills/docx-releasenotes-template/assets/templates/ESDT Release Notes Template.docx
```

**Usage:**
```bash
# Uses default template automatically
python3 .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_from_template.py --file data.json
```

## Custom Templates

### Using Custom Templates

**Method 1: Command line argument**
```bash
python3 .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_from_template.py --file data.json --template /path/to/custom_template.docx
```

**Method 2: JSON field**
```json
{
  "version": "1.0.0",
  "date": "2026-02-20",
  "template_path": "/path/to/custom_template.docx",
  "issues": [...]
}
```

### Required Placeholders

Custom templates must include these placeholders:

| Placeholder | Type | Description |
|------------|------|-------------|
| `Replace_Date` | Text | Release date |
| `Replace_Release_Number` | Text | Release version |
| `Replace_Business_Requirements` | RichText | Business requirements section |
| `Replace_Business_Impacts` | RichText List | Business impacts section |
| `Replace_NonAI_Descriptions` | RichText List | Descriptions section |
| `Replace_Production_Bugs` | RichText | Production bugs resolved in this release (optional) |

## RichText Formatting

The script uses `RichText` and `RichTextParagraph` objects from docxtpl to preserve Word formatting.

### Business Requirements Section

- **Type**: Single RichTextParagraph
- **Style**: ListBullet with italic text
- **Format**: `[NDSD-12345], KEY: Title`

Example:
```
[NDSD-12345], ADPPRG-282639: PMS 18.3.1 Upgrade
ADPPRG-282638: Network Configuration Update
```

### Business Impacts Section

- **Type**: List of RichTextParagraph objects (one per component)
- **Component name**: Heading3 style
- **Issues**: ListBullet style with italic text
- **Business value**: Normal style
- **Child issues**: Normal style with bullet points (•)

Example structure:
```
PMS (Heading3)
• ADPPRG-282639: PMS 18.3.1 Upgrade (ListBullet, italic)

This upgrade reduces operational costs by 15%... (Normal)

  • ADPPRG-282640: Database Migration (Normal with bullet)
  
  Enables faster queries... (Normal)
```

### Descriptions Section

- **Type**: List of RichTextParagraph objects (one per component)
- **Component name**: Heading3 style
- **Issues**: ListBullet style with italic text
- **Status**: Included in brackets after title

Example:
```
PMS (Heading3)
• ADPPRG-282639: PMS 18.3.1 Upgrade [Backlog] (ListBullet, italic)
```

## Creating Custom Templates

1. **Start with a Word document** (.docx format)

2. **Add placeholder text** using Jinja2 syntax:
   ```
   {{ Replace_Date }}
   {{ Replace_Release_Number }}
   {{ Replace_Business_Requirements }}
   {% for impact in Replace_Business_Impacts %}
   {{ impact }}
   {% endfor %}
   {% for desc in Replace_NonAI_Descriptions %}
   {{ desc }}
   {% endfor %}
   {{ Replace_Production_Bugs }}
   ```

3. **Apply Word styles** to placeholder text:
   - Use built-in styles (Heading1, Heading2, Heading3, Normal, ListBullet)
   - Format text (bold, italic, underline) as desired
   - Set paragraph spacing and indentation

4. **Test the template**:
   ```bash
   python3 .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_from_template.py --file test_data.json --template your_template.docx
   ```

## Template Troubleshooting

### Placeholder not replaced

**Symptom**: Placeholder text appears in output document

**Solution**: 
- Verify placeholder name matches exactly (case-sensitive)
- Check for extra spaces or characters
- Ensure placeholder is plain text (not in a text box or shape)

### Formatting lost

**Symptom**: Output document loses formatting from template

**Solution**:
- Use RichText placeholders for formatted content
- Apply styles to placeholder text in template
- Avoid manual formatting (use styles instead)

### List formatting incorrect

**Symptom**: Bullets or numbering don't appear correctly

**Solution**:
- Apply ListBullet or ListNumber style to placeholder
- Ensure list style is defined in template
- Check paragraph indentation settings

## Template Best Practices

1. **Use built-in styles** - Don't rely on manual formatting
2. **Keep placeholders simple** - Avoid complex Jinja2 logic in template
3. **Test with sample data** - Verify all sections render correctly
4. **Document custom placeholders** - If adding new placeholders, document them
5. **Version control templates** - Track template changes alongside code

## Example Template Structure

```
[Company Logo]

Release Notes
Version: {{ Replace_Release_Number }}
Date: {{ Replace_Date }}

1. Business Requirements
{{ Replace_Business_Requirements }}

2. Business Impacts
{% for impact in Replace_Business_Impacts %}
{{ impact }}
{% endfor %}

3. Descriptions
{% for desc in Replace_NonAI_Descriptions %}
{{ desc }}
{% endfor %}

4. Production Bugs Resolved
{{ Replace_Production_Bugs }}

[Footer with page numbers]
```
