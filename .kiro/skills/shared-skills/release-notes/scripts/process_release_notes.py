#!/usr/bin/env python3
"""Process Jira issues for release notes - component extraction, deduplication, normalization.

Logic:
- Component extraction: join ALL component names from issue['fields']['components'] with ", "
- Version/date extraction: regex from fix_version (e.g. "ID 25.4.2 - Nov 28" → version, date)
- Deduplication: remove from single-component groups when in multi-component groups
- Child issues: supported if passed (customfield_14336 = parent key)

Usage:
    python process_release_notes.py --file data.json | python ../../docx-releasenotes-template/scripts/generate_from_template.py
    cat data.json | python process_release_notes.py | python ../../docx-releasenotes-template/scripts/generate_from_template.py

Input JSON:
    {
      "version": "25.4.2",          // optional - extracted from fix_version if missing
      "date": "2025-06-26",         // optional - extracted from fix_version if missing
      "issues": [...],
      "production_bugs": [          // optional - bugs resolved in production for this release
        {
          "key": "NDPF-999",
          "fields": {"summary": "...", "status": {"name": "Done"}, "components": [...]},
          "business_value": "..."   // optional
        }
      ]
    }
"""

import json
import logging
import re
import sys
from collections import defaultdict

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)


def _try_repair_unescaped_quotes(text: str) -> str:
    """Repair JSON with unescaped quotes inside strings (e.g. "Accept forecasting predictions")."""
    result = []
    i, n = 0, len(text)
    in_string, after_backslash = False, False
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


# Jira field mapping
DISPLAY2INTERNAL = {
    'benefit_hypotesis': 'customfield_36211',
    'acceptance_criteria': 'customfield_12818',
    'description': 'description'
}


def extract_component(issue: dict) -> str:
    """Extract component from issue fields.
    Uses empty string (not 'General') when no components."""
    if 'fields' not in issue or 'components' not in issue['fields']:
        return issue.get('component', '') or ''
    components = ""
    for component in issue['fields']['components']:
        if components != "":
            components += ", "
        components += component['name']
    return components


def get_release_date_and_version(fix_version: str) -> tuple:
    """Extract version and date from fix_version string (e.g. 'ID 25.4.2 - Nov 28')."""
    if not fix_version:
        return None, None
    version_match = re.search(r'\b(\d+)\.(\d+)\.(\d+)\b', fix_version)
    if not version_match:
        return None, None
    major, minor, patch = version_match.groups()
    version = f"{major}.{minor}.{patch}"
    year = 2000 + int(major)
    after_version = fix_version[version_match.end():]
    date_match = re.search(r'([A-Z][a-z]+)\s+(\d{1,2})', after_version)
    if not date_match:
        return version, None
    month, day = date_match.group(1), int(date_match.group(2))
    suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    formatted_date = f"{month} {day}{suffix}, {year}"
    return version, formatted_date


def extract_fix_version(issue: dict) -> str:
    """Extract fix_version from Jira fields."""
    if 'fix_version' in issue:
        return issue['fix_version']
    if 'fields' in issue and issue['fields'].get('fixVersions'):
        try:
            return issue['fields']['fixVersions'][0]['name']
        except (IndexError, KeyError, TypeError):
            pass
    return ""


def _normalize_child_issue(child: dict) -> dict:
    """Normalize child issue - ensure summary and business_impact exist."""
    summary = child.get('summary') or child.get('title') or (child.get('fields', {}).get('summary', ''))
    business_value = child.get('business_value') or child.get('business_impact', '')
    return {
        'key': child['key'],
        'title': summary,
        'summary': summary,
        'business_value': business_value,
        'business_impact': business_value,
        'child_issues': [],  # Children don't have nested children in FastAPI
    }


def _normalize_production_bug(bug: dict) -> dict:
    """Normalize a production bug for output. Accepts raw Jira format or pre-normalized."""
    summary = bug.get('summary') or bug.get('title') or (bug.get('fields', {}) or {}).get('summary', '')
    business_value = bug.get('business_value') or bug.get('business_impact', '')
    status = bug.get('status', 'Unknown')
    if status == 'Unknown' and isinstance(bug.get('fields'), dict) and bug['fields'].get('status'):
        status = bug['fields']['status'].get('name', 'Unknown')
    component = extract_component(bug) if 'fields' in bug else (bug.get('component') or '')
    return {
        'key': bug['key'],
        'title': summary,
        'summary': summary,
        'status': status,
        'business_value': business_value,
        'component': component,
    }


def normalize_issue(issue: dict, component: str) -> dict:
    """Build processed issue with normalized fields."""
    summary = issue.get('summary') or issue.get('title') or (issue.get('fields', {}).get('summary', ''))
    business_value = issue.get('business_value') or issue.get('business_impact', '')
    ndsd_ticket = issue.get('ndsd_ticket')
    if ndsd_ticket is None and 'fields' in issue:
        ndsd_ticket = issue['fields'].get('customfield_18752')
    fix_version = extract_fix_version(issue)
    status = issue.get('status', 'Unknown')
    if status == 'Unknown' and 'fields' in issue and issue['fields'].get('status'):
        status = issue['fields']['status'].get('name', 'Unknown')
    # Normalize child issues - each needs key, summary, business_impact
    child_issues = [_normalize_child_issue(c) for c in issue.get('child_issues', [])]
    return {
        'key': issue['key'],
        'title': summary,
        'summary': summary,
        'status': status,
        'business_value': business_value,
        'business_impact': business_value,
        'component': component,
        'child_issues': child_issues,
        'ndsd_ticket': ndsd_ticket,
        'fix_version': fix_version,
    }


def deduplicate_component_groups(by_component: dict) -> dict:
    """Deduplication: remove from single-component groups when in multi-component.
    Remove from single-component groups when issue also in multi-component group.
    """
    for components in list(by_component.keys()):
        comp_list = components.split(", ")
        for other in list(by_component.keys()):
            other_list = other.split(", ")
            if components == other or len(comp_list) > len(other_list):
                continue
            if not all(c in other_list for c in comp_list):
                continue
            items_w_childs = {
                p['key']: [c['key'] for c in p.get('child_issues', [])]
                for p in by_component[components]
            }
            other_items_w_childs = {
                p['key']: [c['key'] for c in p.get('child_issues', [])]
                for p in by_component[other]
            }
            for item_key in items_w_childs:
                if item_key in other_items_w_childs:
                    logging.info(f"Removing {item_key} from [{components}] (keep in [{other}])")
                    by_component[components] = [pi for pi in by_component[components] if pi['key'] != item_key]
                for _, other_childs in other_items_w_childs.items():
                    if other_childs and item_key in other_childs:
                        logging.info(f"Removing {item_key} from [{components}] (child in [{other}])")
                        by_component[components] = [pi for pi in by_component[components] if pi['key'] != item_key]
    return {c: issues for c, issues in by_component.items() if issues}


def process_issues(data) -> dict:
    """Process issues - extract components, normalize, deduplicate.
    Accepts: dict with 'issues' key, or bare list of issues.
    Accepts version/date from: version, date, release_version, release_date, release, release_info."""
    if isinstance(data, list):
        data = {'issues': data, 'version': '', 'date': ''}
    if not isinstance(data, dict):
        raise ValueError("Input must be a JSON object or array of issues")
    # Normalize version/date from common field names
    if not data.get('version') and data.get('release_version'):
        data['version'] = data['release_version']
    if not data.get('date') and data.get('release_date'):
        data['date'] = data['release_date']
    if 'release_info' in data and isinstance(data['release_info'], dict):
        ri = data['release_info']
        if not data.get('version') and ri.get('version'):
            data['version'] = ri['version']
        if not data.get('date') and ri.get('date'):
            data['date'] = ri['date']
    if (not data.get('version') or not data.get('date')) and data.get('release'):
        v, d = get_release_date_and_version(str(data['release']))
        if not data.get('version') and v:
            data['version'] = v
        if not data.get('date') and d:
            data['date'] = d
    issues = data.get('issues', [])
    version = data.get('version', '')
    date = data.get('date', '')
    if not issues:
        raise ValueError("issues array cannot be empty")
    processed = {'all': [], 'by_component': defaultdict(list)}
    for issue in issues:
        component = extract_component(issue)
        normalized = normalize_issue(issue, component)
        processed['all'].append(normalized)
        processed['by_component'][component].append(normalized)
    processed['by_component'] = deduplicate_component_groups(dict(processed['by_component']))
    if not version or not date:
        fv = extract_fix_version(issues[0])
        v, d = get_release_date_and_version(fv)
        version = version or v or ''
        date = date or d or ''
    result = {'version': version, 'date': date, 'processed_issues': processed}
    # Pass through production_bugs if present (normalized)
    production_bugs_raw = data.get('production_bugs', [])
    if production_bugs_raw:
        result['production_bugs'] = [_normalize_production_bug(b) for b in production_bugs_raw]
    return result


def main():
    import argparse as _argparse
    parser = _argparse.ArgumentParser(description='Process Jira issues for release notes')
    parser.add_argument('-f', '--file', help='Read JSON from file instead of stdin')
    args = parser.parse_args()
    try:
        if args.file:
            with open(args.file, 'r', encoding='utf-8') as f:
                raw = f.read()
        else:
            raw = sys.stdin.read()
        if not raw.strip():
            raise ValueError("No input. Use --file release_notes_data.json or: cat file.json | python process_release_notes.py")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            if 'delimiter' in e.msg or 'value' in e.msg:
                repaired = _try_repair_unescaped_quotes(raw)
                try:
                    data = json.loads(repaired)
                except json.JSONDecodeError:
                    logging.error(f"Invalid JSON (unescaped quotes in description/business_value?): {e}")
                    sys.exit(1)
            else:
                logging.error(f"Invalid JSON: {e}")
                sys.exit(1)
        result = process_issues(data)
        print(json.dumps(result, indent=2, default=str))
    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)


if __name__ == '__main__':
    main()
