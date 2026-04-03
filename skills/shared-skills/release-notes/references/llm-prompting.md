# LLM Prompting for Business Value

## Three-Part Message Structure

```python
messages = [
    {"role": "assistant", "content": assistant_role},
    {"role": "user", "content": context},
    {"role": "user", "content": user_query}
]
```

Use assistant role as "assistant" message, not "system".

## Implementation Pattern

1. Offer A/B/C: (A) All custom: Description, Benefit Hypothesis, Acceptance Criteria; (B) description only; (C) specify which field(s)
2. Build context from *selected* Jira fields
3. Build assistant role: `f"You are an assistant that understands {selected_fields} of a Jira ticket"`
4. Build user query: 80–120 words, 4–6 sentences, avoid short 1–2 sentence summaries
5. Anti-repetition: append first 65 chars of previous response to avoid repetitive openings
6. max_tokens=250, temperature=0.5
7. Return empty string if all fields empty; "TBD" if no information at all

## Field Mapping

```python
display2internal_field_map = {
    'benefit_hypotesis': 'customfield_36211',
    'acceptance_criteria': 'customfield_12818',
    'description': 'description'
}
```
