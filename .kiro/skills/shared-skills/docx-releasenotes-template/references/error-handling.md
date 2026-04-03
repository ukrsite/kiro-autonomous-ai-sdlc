# Error Handling Reference

Complete troubleshooting guide for common errors and issues.

## Common Errors

### Missing Required Field

**Error message:**
```
Error: Missing required field: version
```

**Cause:** Required top-level field is missing from JSON input

**Solution:**
- Verify JSON includes `version` and `date` fields
- Check for typos in field names
- Ensure JSON is properly formatted

**Example fix:**
```json
{
  "version": "ID 25.4.2",  // Add this
  "date": "2026-02-20",    // Add this
  "issues": [...]
}
```

### Empty Issues Array

**Error message:**
```
Error: issues array cannot be empty
```

**Cause:** No issues provided in input data

**Solution:**
- Ensure at least one issue is in the `issues` array
- Check if issues were filtered out during processing
- Verify JQL query returned results

### Invalid JSON

**Error message:**
```
Error: Invalid JSON input - Expecting ',' delimiter: line 5 column 10
```

**Cause:** Malformed JSON, often from unescaped quotes

**Solution:**
- Escape double quotes inside strings: `\"` 
- Use JSON validator to identify syntax errors
- Check for trailing commas (not allowed in JSON)

**Example fix:**
```json
// Wrong
{
  "title": "Fix "critical" bug"
}

// Correct
{
  "title": "Fix \"critical\" bug"
}
```

### Missing Issue Field

**Error message:**
```
Error: Issue at index 0: missing required field: key
```

**Cause:** Required issue field is missing

**Solution:**
- Ensure each issue has `key` and `title` fields
- Check field names match expected format
- Verify data extraction from Jira was successful

### Template Not Found

**Error message:**
```
Error: Default template not found at: .kiro/skills/shared-skills/docx-releasenotes-template/assets/templates/ESDT Release Notes Template.docx
```

**Cause:** Template file doesn't exist at expected location

**Solution:**
- Verify template file exists at specified path
- Use `--template` flag to specify custom path
- Check file permissions

**Example:**
```bash
python3 .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_from_template.py --file data.json --template /path/to/template.docx
```

### Custom Template Not Found

**Error message:**
```
Error: Custom template not found: /path/to/template.docx
```

**Cause:** Specified template file doesn't exist

**Solution:**
- Verify file path is correct
- Check file exists and is readable
- Use absolute path or path relative to current directory

### Invalid Template

**Error message:**
```
Error: Template is not a valid DOCX file
```

**Cause:** Template file is corrupted or not a .docx file

**Solution:**
- Verify file is a valid Word document (.docx format)
- Try opening template in Word to check for corruption
- Re-save template as .docx if it's in older format (.doc)

## Python Errors

### Module Not Found

**Error message:**
```
ModuleNotFoundError: No module named 'docxtpl'
```

**Cause:** Required Python package not installed

**Solution:**
```bash
pip install docxtpl
```

### Unhashable Type: List

**Error message:**
```
Error: unhashable type: 'list'
```

**Cause:** The `component` field (or `components`) was stored as a list and used internally where a hashable string key is required. Common when JSON has Jira raw format `"component": [{"name":"Oversite"}, {"name":"Sitetracker"}]` or `"component": ["A","B"]` passed through without normalization.

**Solution:** The script now auto-normalizes component to a comma-separated string. If you still see this error:
- Ensure `component` per issue is either a **string** (e.g., `"Oversite, Sitetracker"`) or an **array of strings** / Jira objects `[{"name":"X"}]`
- Run via pipeline: `process_release_notes.py | generate_from_template.py` to get pre-normalized format
- Update `release_notes_data.json` so each issue has `"component": "ComponentName"` (string) not a raw list as a top-level key

### Permission Denied

**Error message:**
```
PermissionError: [Errno 13] Permission denied: 'Release_Notes.docx'
```

**Cause:** Output file is open in another application or lacks write permissions

**Solution:**
- Close the file if it's open in Word or another application
- Check directory write permissions
- Use different output path with `--output` flag

### File Already Exists

**Error message:**
```
FileExistsError: Output file already exists
```

**Cause:** Output file exists and script won't overwrite

**Solution:**
- Delete or rename existing file
- Use `--output` flag to specify different filename
- Move existing file to backup location

## Data Issues

### Missing Business Value

**Symptom:** Some issues show empty business value in output

**Cause:** `business_value` field is empty or missing

**Solution:**
- Ensure business value is extracted from Jira
- Use fallback to summary field if description is empty
- Generate business value using AI if needed

### Component Grouping Issues

**Symptom:** Issues not grouped correctly by component

**Cause:** Component field format doesn't match expectations

**Solution:**
- Use comma-separated format for multiple components: "Oversite, Sitetracker"
- Ensure component names are consistent (case-sensitive)
- Check for extra spaces in component names

### Child Issues Not Appearing

**Symptom:** Child issues don't show in output

**Cause:** `child_issues` array is empty or malformed

**Solution:**
- Verify child issues are included in JSON
- Check child issue format matches parent issue format
- Ensure child issues have required fields (`key`, `title`)

## Pipeline Issues

### Stdin Blocking

**Symptom:** Script hangs waiting for input

**Cause:** Script expects stdin input but none provided

**Solution:**
- Use `--file` flag instead of piping: `--file data.json`
- If piping, ensure previous command outputs valid JSON
- Check pipeline for errors: `command1 | command2` (if command1 fails, command2 hangs)

### Pipeline Failure

**Symptom:** Pipeline produces no output or errors

**Cause:** First command in pipeline fails

**Solution:**
- Test each command separately
- Check first command output: `python3 process_release_notes.py --file data.json`
- Verify JSON is valid before piping

**Example debugging:**
```bash
# Test process_release_notes.py separately
python3 .kiro/skills/shared-skills/release-notes/scripts/process_release_notes.py --file release_notes_data.json > processed.json

# Check output
cat processed.json

# Then test generate_from_template.py
python3 .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_from_template.py --file processed.json
```

## Output Issues

### File Not Created

**Symptom:** Script completes but no file is created

**Cause:** Script failed silently or output path is incorrect

**Solution:**
- Check script exit code: `echo $?` (0 = success, non-zero = error)
- Look for error messages in stderr
- Verify current directory is correct
- Check disk space

### Incorrect Formatting

**Symptom:** Output document formatting doesn't match template

**Cause:** RichText formatting not applied correctly

**Solution:**
- Verify template uses correct placeholder names
- Check template styles are defined
- Ensure RichText objects are used in script

### Missing Sections

**Symptom:** Some sections are empty in output

**Cause:** No data for that section or placeholder not replaced

**Solution:**
- Verify input data includes all required fields
- Check template placeholders match script expectations
- Ensure component grouping is working correctly

## Debugging Tips

1. **Enable verbose output:**
   ```bash
   python3 -v .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_from_template.py --file data.json
   ```

2. **Validate JSON:**
   ```bash
   python3 -m json.tool release_notes_data.json
   ```

3. **Check file permissions:**
   ```bash
   ls -la .kiro/skills/shared-skills/docx-releasenotes-template/assets/templates/
   ```

4. **Test with minimal data:**
   ```json
   {
     "version": "Test",
     "date": "2026-01-01",
     "issues": [
       {
         "key": "TEST-1",
         "title": "Test Issue"
       }
     ]
   }
   ```

5. **Check Python version:**
   ```bash
   python3 --version  # Should be 3.7+
   ```

## Getting Help

If you encounter an error not covered here:

1. Check the error message carefully
2. Verify input data format matches expected format
3. Test with minimal example data
4. Check file paths and permissions
5. Review script output for additional context
