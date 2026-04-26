---
name: create-anythingllm-skill
description: Creates AnythingLLM custom agent skill bundles that follow official plugin.json and handler.js requirements. Use when user asks to build, scaffold, or update AnythingLLM agent skills, tools, or plugin-based custom skills.
---

# Create AnythingLLM Skill

Build AnythingLLM custom agent skills. Do not build Cursor skills unless user explicitly asks for Cursor skill authoring.

## Goal

Produce an AnythingLLM-compatible custom skill bundle with correct structure and runtime behavior.

Required output:

- `<hubId>/plugin.json`
- `<hubId>/handler.js`
- `<hubId>/README.md`

Optional output:

- helper modules in the same `<hubId>/` folder
- `package.json` only if dependencies are needed

## Hard Requirements (AnythingLLM)

1. Skill runs in NodeJS and must be written in JavaScript.
2. `handler.js` must export `module.exports.runtime = { handler: async function (...) { ... } }`.
3. `handler` must return a string in all success and error paths.
4. `handler` should use `try/catch`.
5. `plugin.json` must define:
   - `active` (boolean)
   - `hubId` (must match folder name)
   - `name` (human readable)
   - `description`
   - `version`
   - `entrypoint.file` (usually `handler.js`)
   - `entrypoint.params` with parameter descriptions and types (`string|number|boolean`) when inputs are required
6. Include 1-3 `examples` in `plugin.json` to improve tool selection.
7. Include `README.md` with setup and usage notes.

## Discovery Questions

Collect missing inputs before writing files:

- Skill purpose and external API/service target
- `hubId` and display name
- Input parameters and types
- Output contract expected by the agent
- Auth method (env vars, headers, tokens)
- Runtime constraints (timeouts, retries, rate limits)

If user is missing details, ask compact questions in one turn.

## Implementation Workflow

1. Confirm target path for AnythingLLM plugin storage or repo location.
2. Create `<hubId>/plugin.json` with valid schema fields.
3. Create `<hubId>/handler.js`:
   - validate inputs
   - run external call or local logic
   - return stringified JSON or plain string
   - log via `this.introspect` and `this.logger` when useful
4. Create `<hubId>/README.md`:
   - what the skill does
   - required configuration
   - example invocations
5. If dependencies are needed, add local `package.json` in the same folder and document install steps.
6. Validate all return paths are strings and folder name equals `hubId`.

## Output Contract

When done, provide:

- Created/updated file list
- Brief behavior summary
- Minimal verification checklist:
  - `hubId` matches folder
  - `entrypoint` params align with handler input
  - all handler returns are strings
  - examples match expected call shape

## Guardrails

- Never output Cursor `SKILL.md` templates when user asked for AnythingLLM custom skill code.
- Never omit `plugin.json` or `handler.js`.
- Never return non-string objects from `handler`.
- Never reference files outside plugin folder for runtime imports.
- Never hardcode secrets; use config/env and document required variables.

## Minimal Templates

`plugin.json` baseline:

```json
{
  "active": true,
  "hubId": "replace-with-hubid",
  "name": "Replace With Skill Name",
  "description": "What this skill does.",
  "version": "1.0.0",
  "entrypoint": {
    "file": "handler.js",
    "params": {
      "input": {
        "description": "Primary input value",
        "type": "string"
      }
    }
  },
  "examples": [
    {
      "prompt": "Example user ask",
      "call": "{\"input\":\"example\"}"
    }
  ]
}
```

`handler.js` baseline:

```javascript
module.exports.runtime = {
  handler: async function ({ input }) {
    const callerId = `${this.config.name}-v${this.config.version}`;
    try {
      this.introspect(`${callerId} invoked`);
      if (!input || typeof input !== "string") {
        return "Invalid input: expected non-empty string.";
      }

      const result = { ok: true, input };
      return JSON.stringify(result);
    } catch (e) {
      this.logger(`${callerId} failed`, e.message);
      return `Skill failed: ${e.message}`;
    }
  }
};
```

## Official References

- [https://docs.anythingllm.com/agent/custom/developer-guide](https://docs.anythingllm.com/agent/custom/developer-guide)
- [https://docs.useanything.com/agent/custom/plugin-json](https://docs.useanything.com/agent/custom/plugin-json)
- [https://docs.useanything.com/agent/custom/handler-js](https://docs.useanything.com/agent/custom/handler-js)
- [https://docs.anythingllm.com/agent/setup](https://docs.anythingllm.com/agent/setup)
