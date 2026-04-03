---
name: skill-builder
description: Create new Kiro skills and improve existing ones. CRITICAL to activate whenever any operation with skills. Use when creating a skill, updating a skill, fixing trigger issues, or scaffolding. Triggers on "create a skill", "make a skill for X", "turn this into a skill", "skill isn't triggering", "improve this skill", or any request to build a new capability as a skill.
compatibility: Works in any workspace. For contributing skills, submit an MR to the kiro-autonomous-ai-sdlc repository.
metadata:
  author: connected-operations
  version: "5.2"
---

# Kiro Skill Builder

Guide for creating and improving Kiro skills within the Connected Operations kiro-autonomous-ai-sdlc repository.

## Quick Start

First, detect which workspace you're in:

- **In the kiro-autonomous-ai-sdlc repo** (look for `skills/`, `agents/`, and `manifest.json` at root) → scaffold directly into the correct `skills/<group>/` directory.
- **In any other workspace** → guide the authoring process normally, but remind the user that the finished skill files need to be contributed to the kiro-autonomous-ai-sdlc repo via MR. Help them structure files locally so they can copy them over cleanly.

Then figure out what the user needs and help them move forward:

1. **New skill** — capture intent → interview → scaffold → draft SKILL.md → test → iterate
2. **Improve existing skill** — load SKILL.md → identify issues → fix → test
3. **Turn conversation into skill** — extract workflow from chat → draft → scaffold
4. **Fix triggering** — analyze description → add trigger phrases → test

---

## Phase 1: Understand What the Skill Should Do

If the conversation already contains a workflow (e.g., "turn this into a skill"), extract from context first — the tools used, the sequence of steps, corrections the user made, input/output formats observed. The user may need to fill gaps, and should confirm before proceeding.

Otherwise, ask:

1. What should this skill help Kiro do?
2. When should it trigger? (what would a user say?)
3. What's the expected output?
4. Does it need external tools (MCP servers, APIs)?
5. Which agent(s) should have it?

Also check if a similar skill already exists under `skills/` — maybe extend it instead of creating a new one.

## Phase 2: Interview and Research

Do not proceed to Phase 3 until you have asked clarifying questions and received answers from the user. This is a hard gate — skipping it leads to generic skills that miss the mark. Present your questions, then wait for the user to respond before scaffolding anything.

Why this matters: skills that reference vague sources (e.g., "the standards in Confluence") instead of specific ones (e.g., "the Cloud Tagging Policy page in the INFRA space") are unreliable in practice. The interview is where you get those specifics.

Proactively ask about:
- **Data sources** — if the skill reads from external systems (Confluence, Jira, APIs), ask which specific spaces, pages, projects, or endpoints to target. Don't assume or generalize.
- **Edge cases** — what happens with empty input, huge files, missing fields?
- **Input/output formats** — what exactly goes in, what comes out? Ask for examples if possible.
- **Success criteria** — how will the user know the skill worked correctly?
- **Dependencies** — does it need MCP servers, specific file types, external APIs?
- **Existing patterns** — are there similar skills in the repo to learn from or reuse?

Come prepared with context. If there are relevant skills already in the repo, read them and reference what they do well. This reduces burden on the user and shows you've done your homework.

After gathering answers, summarize what you understood back to the user and get confirmation before moving to Phase 3.

## Phase 3: Scaffold the Skill

### Choose location

Pick the skill group based on who uses it. This matters because agents reference skills from their group, and it helps contributors find related skills:
- `shared-skills/` — useful across multiple roles
- `developer-skills/` — coding, debugging, code review
- `devops-skills/` — CI/CD, infrastructure, deployments
- `product-owner-skills/` — backlog, releases, business value
- `solution-architect-skills/` — architecture, HLD, standards

### Create the directory

```
skills/<skill-group>/<skill-name>/
├── SKILL.md              # Required — the skill definition
├── evals/                # Recommended — test cases for the skill
│   └── evals.json
├── scripts/              # Optional — automation scripts
└── references/           # Optional — reference docs
```

Use kebab-case for the skill name (e.g., `terraform-validator`).

## Phase 4: Write the SKILL.md

### How skills load (progressive disclosure)

Skills use a three-level loading system. Understanding this helps you decide where to put content:

1. **Metadata** (name + description) — always in context, ~100 words. This is what triggers the skill.
2. **SKILL.md body** — loaded when the skill triggers, ideally under 500 lines. This is the main instruction set.
3. **Bundled resources** (references/, scripts/) — loaded on demand, unlimited size. The SKILL.md should tell the model when and why to read these.

This means: keep SKILL.md focused on the workflow. Move large reference material, lookup tables, or detailed specs into `references/` with clear pointers from SKILL.md about when to consult them. For large reference files (>300 lines), include a table of contents.

### Template

```markdown
---
name: <skill-name>
description: <What it does. Use when X, Y, or Z. Triggers on "phrase 1" or "phrase 2".>
compatibility: <Prerequisites like "Requires Confluence MCP server", or omit if none>
metadata:
  author: connected-operations
  version: "1.0"
---

# <Skill Title>

<One paragraph explaining what the skill does and why it's useful.>

**Requires**: <List each prerequisite>

## Workflow

### 1. <First Step>

<What to do, what inputs are needed>

### 2. <Second Step>

<What to do>

### 3. <Third Step>

<What to do>
```

### Writing the description (most important field)

The description is the primary trigger mechanism — it determines whether the skill gets activated. Make it "pushy": lean toward triggering too often rather than too rarely. Users can always ignore a skill that activates unnecessarily, but they can't use a skill that never triggers.

Instead of:
> "Validates Terraform modules against cloud standards."

Write:
> "Validate Terraform modules against cloud standards. Use when checking IaC compliance, reviewing terraform plans, or validating infrastructure code. Make sure to use this skill whenever the user mentions terraform, infrastructure validation, cloud compliance, or IaC review, even if they don't explicitly ask for 'validation'."

The pattern: **what it does** + **when to use it** + **trigger phrases** + **push for edge cases**.

### Writing principles

- **Explain the why.** Instead of rigid "ALWAYS do X" rules, explain the reasoning. Today's LLMs are smart — when they understand *why* something matters, they handle edge cases better than when following blind rules. If you find yourself writing ALWAYS or NEVER in all caps, reframe it as reasoning.
- **Generalize, don't overfit.** Skills get used across many different prompts. Write instructions that work broadly, not just for the examples you tested with. If there's a stubborn issue, try different approaches rather than adding narrow workarounds.
- **Keep it lean.** Remove instructions that aren't pulling their weight. Read through the skill with fresh eyes — if something feels redundant or the model would do it naturally, cut it.
- **Use imperative form.** "Extract the data" not "The data is extracted."
- **Include examples.** Show input/output pairs when the format matters. This is more effective than lengthy descriptions.

## Phase 5: Test the Skill

Every new skill should include an `evals/` directory with test cases. This helps contributors verify their skill works before pushing, and gives reviewers something to check against.

### 5.1 Create test cases

Create `evals/evals.json` inside the skill directory:

```json
{
  "skill_name": "<skill-name>",
  "tests": [
    {
      "prompt": "A realistic thing a user would say to trigger this skill",
      "expected": "What a good result looks like",
      "result": "untested",
      "notes": ""
    },
    {
      "prompt": "An edge case or variation",
      "expected": "Expected outcome",
      "result": "untested",
      "notes": ""
    }
  ]
}
```

Set `result` to `"pass"`, `"fail"`, or `"untested"` after running each test.

Aim for 2-3 test cases:
1. A straightforward, realistic case (with detail — file paths, context, specifics)
2. An edge case or variation
3. A casual/abbreviated phrasing

Make test prompts realistic. Bad: `"Format this data"`. Good: `"ok so I have this xlsx file in my downloads called 'Q4 sales final v2.xlsx' and I need to add a profit margin column. Revenue is in column C and costs in column D"`. Real users provide context, typos, and backstory.

### 5.2 Run and record

For each test prompt, try it with the skill active:
- Does the skill trigger when it should?
- Does the output match expectations?
- Are there confusing or missing steps?

Update `result` to "pass" or "fail" and add `notes` for anything that needs fixing. Iterate until all tests pass.

## Phase 6: Wire Up to Agents

If the skill should appear in a specific agent's context, add it to their `resources` in `agents/<agent>.json`. This is required for agent-specific skills, optional for shared skills that users invoke directly via `#` in chat.

```json
"resources": [
  "file://.kiro/skills/<skill-name>/SKILL.md",
  "file://~/.kiro/skills/<skill-name>/SKILL.md"
]
```

Both paths needed — first for local dev, second for distributed users.

## Phase 7: Optimize the Description

After the skill works correctly, it's worth testing whether the description triggers reliably across different phrasings. This is optional but recommended for skills that will be widely used.

### 7.1 Write trigger test queries

Create 10-15 test queries — a mix of should-trigger and should-not-trigger:

**Should-trigger (6-8 queries):**
- Different phrasings of the same intent (formal, casual, abbreviated)
- Cases where the user doesn't name the skill explicitly but clearly needs it
- Uncommon use cases the skill handles

**Should-not-trigger (4-6 queries):**
- Near-misses that share keywords but need something different
- Adjacent domains where a naive keyword match would trigger but shouldn't
- Ambiguous phrasing where another tool is more appropriate

Avoid obviously irrelevant negatives — "write a fibonacci function" as a negative for a PDF skill tests nothing. The best negatives are genuinely tricky.

### 7.2 Test manually

For each query, check: does the skill trigger? Record results. If should-trigger queries aren't triggering, make the description pushier. If should-not-trigger queries are triggering, narrow the scope or add clarifying context.

### 7.3 Update the description

Apply what you learned. Show the user before/after and explain what changed and why.

## Phase 8: Contribute

Once you're happy with the skill:

**If you're in the kiro-autonomous-ai-sdlc repo:**
1. Commit all files to a feature branch
2. Create a Merge Request to main
3. Skill becomes available to users on next contextcore sync after merge

**If you're in another workspace:**
1. Ensure your skill files follow the expected directory structure (`skills/<group>/<skill-name>/SKILL.md`, plus `evals/`, `scripts/`, `references/` as needed)
2. Clone or open the kiro-autonomous-ai-sdlc repo, copy the files into the correct location
3. Wire up to agents if needed (Phase 6)
4. Commit to a feature branch and create a Merge Request to main

---

## Improving an Existing Skill

When updating a skill that already exists:

1. Read the current SKILL.md and understand its workflow
2. If `evals/evals.json` exists, run the test cases to see what's passing/failing
3. Make your changes
4. Re-run tests and update results
5. Bump the `version` in frontmatter metadata

### Improvement principles

- **Generalize from feedback.** You're iterating on a few examples, but the skill will be used across many prompts. Don't add narrow fixes that only help the test cases — look for the underlying pattern and address that.
- **Keep the prompt lean.** Remove things that aren't pulling their weight. Read the skill with fresh eyes — if the model would do something naturally without being told, cut the instruction.
- **Look for repeated work.** If every test run independently creates the same helper script or takes the same multi-step approach, that's a signal to bundle it. Write it once in `scripts/` and reference it from the skill.

### When to bump the version

- Fix a typo or clarify wording → small bump (1.0 → 1.1)
- Add a new workflow step or change behavior → bigger bump (1.0 → 2.0)
- Complete rewrite or breaking changes → start fresh at next whole number

---

## Fixing Trigger Issues

If a skill isn't triggering when it should, the problem is usually the `description` field.

### Good description patterns

```
# Action + Context + Trigger phrases + Push
"Validate Terraform modules against cloud standards. Use when checking 
IaC compliance or reviewing terraform plans. Make sure to use this skill 
whenever the user mentions terraform, infrastructure validation, or IaC 
review, even if they don't explicitly ask for 'validation'."

# Capability list + When to use + Push
"Extract data from PDFs and convert to structured formats. Use when 
working with PDF documents or extracting tables. Triggers on 'parse 
this PDF' or 'get data from document'. Use this skill for any PDF-related 
task, even simple ones."
```

### Bad description patterns

```
# Too vague
"Helps with infrastructure tasks."

# Too narrow
"Runs terraform validate on .tf files in the current directory."

# No trigger phrases
"Terraform validation skill."
```

### Testing triggers

Try variations of how users might ask:
- Formal: "Please validate my Terraform configuration"
- Casual: "check my tf files"
- Indirect: "is this infrastructure code correct?"

If the skill doesn't trigger, add those phrases to the description.

---

## Reference: Repo Conventions

- Frontmatter: `name`, `description`, `metadata.author`, `metadata.version`
- Optional: `compatibility` field with "Requires" prefix
- Workflow steps: numbered H3 headings (`### 1. Step Name`)
- Parameters: backtick formatting (`parameter_name`)
- Commands: fenced code blocks
- Skills organized by role under `skills/`
- Agent resources use dual paths (`.kiro/` + `~/.kiro/`)
