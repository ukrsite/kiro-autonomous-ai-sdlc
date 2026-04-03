# Release Notes Templates

Place template files in this directory. Default: `ESDT Release Notes Template.docx`. Use `--template /path/to/other.docx` to choose another template.

The template must include these placeholders (docxtpl/Jinja2):
- `Replace_Date`
- `Replace_Release_Number`
- `Replace_Business_Requirements`
- `Replace_Business_Impacts`
- `Replace_NonAI_Descriptions`
- `Replace_Production_Bugs` (optional — production bugs resolved per release)

If the template is missing, use `--template /path/to/your/template.docx` when running `generate_from_template.py`.
