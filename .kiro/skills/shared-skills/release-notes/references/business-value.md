# Extract Business Value from Jira Issues

Extract business value summaries from Jira issues for release notes.

**Requires**: docker engine to run jira mcp server
**Requires**: Jira mcp authenticated with Personal Access Token (PAT)

**Inputs**:
- List of Jira issue keys (e.g., ADPPRG-282639)
- Fields to analyze: offer A/B/C — (A) All custom: Description, Benefit Hypothesis, Acceptance Criteria; (B) description only; (C) specify which field(s)

**Output**: Business value summaries for each issue (and each child issue when present)

---

## 1. When to Generate Business Impact

- **Trigger:** For each issue (and each child) that has no child issues.
- **Input:** Issue with Jira fields populated (Description, Benefit hypothesis, Acceptance criteria).
- **Output:** A single paragraph of **80–120 words** summarizing business impact.

---

## 2. Three-Part Prompt Structure

The prompt has three parts. Use this structure exactly:

| Part     | Role      | Content |
|----------|-----------|---------|
| **Role** | Assistant | Domain: what Jira field types the assistant understands. |
| **Context** | User   | Raw text from the selected Jira fields. |
| **Query** | User     | Task description and constraints. |

**Example structure:**
```
Role:    "You are an assistant that understands Description, Benefit hypothesis, Acceptance criteria of a Jira ticket"
Context: "Description: ...\n\nBenefit hypothesis: ...\n\nAcceptance criteria: ..."
Query:   "Given the following ..., write a single clear paragraph of max 120 words..."
```

---

## 3. Rules for the Role

1. **Be explicit about field names** — Use human-readable names from the field mapping (e.g. "Benefit hypothesis", "Acceptance criteria", "Description").
2. **Keep it domain-specific** — State that the assistant understands Jira ticket content.
3. **Use actual field names** — Only include fields that have non-null content.

**Format:** `"You are an assistant that understands {field1}, {field2}, {field3} of a Jira ticket"`

**Field name mapping** (use these display names in the role and query):

| Jira field key         | Display in prompt    |
|------------------------|----------------------|
| `description`          | Description          |
| `benefit_hypotesis`    | Benefit hypothesis   |
| `acceptance_criteria`  | Acceptance criteria  |
| `release_note`         | Release note         |
| `limitation_text`      | Limitation text      |

---

## 4. Rules for the Context

1. **Include only non-null fields** — Build context only from fields that have content.
2. **Format each field clearly** — Use: `Field Name: <content>\n\n` so the model can distinguish fields.
3. **Use human-readable field names** — See table above (e.g. `benefit_hypotesis` → `Benefit hypothesis`).
4. **Preserve original text** — Do not truncate or modify the Jira content; pass it as-is.
5. **If Description is empty** — Include Summary in context to infer business value.

**Build context:**
```python
DISPLAY2INTERNAL = {
    'benefit_hypotesis': 'customfield_36211',
    'acceptance_criteria': 'customfield_12818',
    'description': 'description'
}
FIELD_DISPLAY = {
    'benefit_hypotesis': 'Benefit hypothesis',
    'acceptance_criteria': 'Acceptance criteria',
    'description': 'Description'
}
context = ""
for field in fields:
    val = issue['fields'].get(DISPLAY2INTERNAL.get(field, field))
    if val:
        display = FIELD_DISPLAY.get(field, field.replace("_", " ").capitalize())
        context += display + ": " + str(val) + "\n\n"
```

---

## 5. Rules for the Query (Task)

1. **State the task clearly** — Ask for a single paragraph summarizing business impact.
2. **Define length** — **MANDATORY: 80–120 words.** Shorter output is WRONG.
3. **Define focus areas** — How the work improves processes, reduces costs, removes blockers.
4. **Require multiple sentences** — Output MUST be 4–6 sentences. Two sentences is WRONG.
5. **Handle vague data** — If Acceptance Criteria are vague, infer from Benefit Hypothesis. If no usable information, return `TBD`.
6. **Language and style** — Straightforward, business-friendly. No jargon unless in source. No "Assumptions" section in output.
7. **Avoid repetition** — For the next issue, append: `"To avoid repetition of the previous response, avoid the style of the following text on the beginning of the result: " + first_65_chars_of_previous_response`

---

## 6. Reference Prompt (Use This Exactly)

**Role:**
```
"You are an assistant that understands Description, Benefit hypothesis, Acceptance criteria of a Jira ticket"
```
(Adjust field names to match the fields you included in context.)

**Query:**
```
Given the following Description, Benefit hypothesis, Acceptance criteria, write a single clear paragraph of 80-120 words, summarizing the business impact they imply for the organization, focusing on how they will improve processes, reduce costs, or remove blockers. Use 4-6 sentences. Do NOT write a short 1-2 sentence summary. If the Acceptance Criteria are vague or undefined, infer likely business impacts based on the Benefit Hypothesis while stating assumptions made, but do not simply return TBD. Use straightforward, business-friendly language. If really there is no information at all, return TBD. Do not include assumptions.
```

**Anti-repetition** (for 2nd+ issue):
```
To avoid repetition of the previous response, avoid the style of the following text on the beginning of the result: [first 65 characters of previous response]
```

---

## 7. Length Requirement — CRITICAL

| Output length        | Status |
|----------------------|--------|
| 1–2 sentences (~20–40 words) | **WRONG** — too short |
| 3 sentences (~50–70 words)   | **WRONG** — expand further |
| 4–6 sentences (~80–120 words)| **CORRECT** |
| > 120 words                  | Trim to fit |

**WRONG examples** (too short):
> Provides consistent remote supervision capabilities for North American customers without requiring complete tool replacement, enabling market expansion.

> Enabler for Oversite implementation for North American customers using the NA01 instance.

**CORRECT example** (NDPF-709, ~90 words):
> Enables the legacy MANA ST NA01 instance (hybrid solution with Global ST package) to integrate with ECO for Oversite functionality using standard APIs via ID integration architecture (AWS ML). This integration is critical for North American customers using the NA01 instance, providing them access to Oversite capabilities for remote supervision and automated acceptance workflows. The solution ensures feature parity across different ST deployment models and supports consistent user experience regardless of instance type.

**CORRECT example** (NDPF-844, ~75 words):
> Synchronizing the new VI Use Cases to make them available in Over Site and ST will streamline access to critical data and ensure consistency across platforms. This integration will improve operational efficiency by reducing manual efforts, minimizing errors, and enabling faster decision-making. By aligning these systems, the organization can enhance collaboration, improve workflow automation, and reduce potential delays, ultimately driving cost savings and better resource utilization.

---

## 8. Antipatterns to Avoid

| Antipattern                         | Correct approach                                      |
|------------------------------------|-------------------------------------------------------|
| 1–2 sentence output                | Use 4–6 sentences, 80–120 words                       |
| Using technical field IDs in role  | Use human-readable names (e.g. "Benefit hypothesis")  |
| Including null/empty fields        | Include only fields with non-null content             |
| Asking for bullet points or lists  | Ask for a single paragraph                            |
| Allowing short summaries           | Enforce 80–120 words, 4–6 sentences                   |
| Ignoring missing data              | Explicitly handle "no information" → return `TBD`     |
| Including assumptions in output    | Instruct the model not to add "Assumptions" section   |
| Generic assistant role             | Make the role specific to Jira ticket content         |

---

## 9. Field Selection — Offer A/B/C Options

**Offer user:**
- **A)** Use all three fields (recommended — provides most comprehensive business value)
- **B)** Use only specific field — `description`
- **C)** Use only specific field(s) — please specify which one(s)

| Field key            | Jira custom field     | Extract with                          | Display name          |
|----------------------|-----------------------|---------------------------------------|-----------------------|
| `benefit_hypotesis`  | customfield_36211     | `issue['fields']['customfield_36211']` | Benefit hypothesis    |
| `acceptance_criteria`| customfield_12818     | `issue['fields']['customfield_12818']` | Acceptance criteria   |
| `description`        | description           | `issue['fields']['description']`       | Description           |

**A** → `fields = ['benefit_hypotesis', 'acceptance_criteria', 'description']`  
**B** → `fields = ['description']`  
**C** → Parse user's specification (e.g. "Benefit hypothesis and Description") → build context from selected fields only.

**Fallback:** Fewer fields → shorter output (not recommended for full 80–120 words).

---

## 10. Fallback Behavior

1. **No fields selected** — Return empty string.
2. **All selected fields are empty** — Return `TBD`.
3. **LLM returns unusable output** — Fall back to `TBD`.

---

## 11. Workflow Summary

1. Use `get_issue_full` to retrieve issue details.
2. **Offer A/B/C:** (A) All custom: Description, Benefit Hypothesis, Acceptance Criteria; (B) description only; (C) specify which field(s).
3. **Extract selected fields** using DISPLAY2INTERNAL (see §9).
4. Build context with human-readable field names, only non-null *selected* fields.
5. Build Role with field names that have content.
6. Use the Reference Query above (adjust field names in query to match selection; 80–120 words, 4–6 sentences).
7. Add anti-repetition text for 2nd+ issue.
8. Return `business_value` in structured output.

---

## 12. MANDATORY: Field Verification Before Generating

**Before writing business_value for each issue, extract these fields from `get_issue_full`:**

**Required (use as context for generation):**

| Field                 | Jira path                      | Use for  |
|-----------------------|--------------------------------|----------|
| Benefit hypothesis    | `issue['fields']['customfield_36211']` | Input    |
| Acceptance criteria   | `issue['fields']['customfield_12818']` | Input    |
| Description           | `issue['fields']['description']`       | Input    |

**Optional (Jira may have these — use as extra context when generating, but do NOT copy to output):**
| Field                 | Note |
|-----------------------|------|
| business_impact       | Jira custom field — raw content. Use as input context only. |
| business_value_custom | Jira custom field — raw content. Use as input context only. |

**Verification checklist:**
- [ ] I offered A/B/C options (A: all three; B: description only; C: specify which)
- [ ] I read the *selected* fields — include full text in context
- [ ] If any field is null/empty, I still use the others; if ALL empty, return "TBD"
- [ ] My output will be 80–120 words, 4–6 sentences

**If you produce a short 1–2 sentence business_value, you may have skipped fields.** Re-read the issue, ensure you used all *selected* fields (default: all three), and generate again with full context.

**Jira MCP `get_issue_full` returns:** The full issue object. Access fields via `result['fields']['customfield_36211']`, `result['fields']['customfield_12818']`, `result['fields']['description']`.

---

## 13. Output: Use ONLY `business_value` — Do Not Copy Jira Fields

**Jira may have fields like:** `business_impact`, `business_value_custom`, or similar — these are Jira's own custom fields (raw/manual content).

**For release_notes_data.json, each issue must have:**
- `business_value` — **only** your generated 80–120 word paragraph

**Do NOT add to the output:**
- `business_impact` (from Jira)
- `business_value_custom` (from Jira)
- Any other Jira field that sounds similar

**Input vs output:**
- **Input** (from get_issue_full): Use `customfield_36211`, `customfield_12818`, `description` to generate. You may also use Jira's `business_impact` or `business_value_custom` as additional context when generating, if they have content.
- **Output** (to release_notes_data.json): Write only `business_value` = your generated paragraph. Overwrite or ignore Jira's business_impact/business_value_custom in the output.
