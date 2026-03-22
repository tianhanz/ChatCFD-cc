---
name: gemini-review
description: "Review a file using Gemini-2.5-Pro via the OpenAI-compatible API. Sends the file content to the model and prints a structured review with improvement suggestions. Use when the user asks for a Gemini review, external model review, or second opinion on any file — code, documentation, CFD configs, or skill definitions. Accepts an optional file path argument; defaults to README-fork.md."
---

# Gemini Review

Use Gemini-2.5-Pro to review a file and provide improvement suggestions.

The argument provided is: $ARGUMENTS

## Step 1 — Determine the target file

1. If `$ARGUMENTS` specifies a file path, use that.
2. Otherwise default to `README-fork.md` in the repo root.
3. Verify the file exists. If not, report the error and stop.

## Step 2 — Call the API

Send the file contents to Gemini-2.5-Pro via the **OpenAI-compatible chat completions** endpoint.

**IMPORTANT**: This uses the standard OpenAI `messages` format, NOT the
predictions API format used by `/gpt-review`. Do not confuse the two.

- **Base URL**: Read from `OPENAI_BASE_URL` or `ANTHROPIC_BASE_URL` environment variable.
- **API key**: Read from `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` environment variable.
- **Model**: `Vendor2/Gemini-2.5-Pro`
- **Endpoint**: `POST {base_url}/v1/chat/completions`

### Request format (OpenAI chat completions)

```json
{
    "model": "Vendor2/Gemini-2.5-Pro",
    "messages": [
        {"role": "system", "content": "<system prompt>"},
        {"role": "user", "content": "<file contents>"}
    ],
    "max_tokens": 16384,
    "temperature": 0.3
}
```

### Response format

```json
{
    "choices": [{"message": {"content": "<review text>"}}],
    "usage": {"prompt_tokens": ..., "completion_tokens": ...}
}
```

The system prompt:

```
You are a senior CFD engineer and computational scientist reviewing a file from ChatCFD-cc, an LLM-driven agent for end-to-end CFD automation built on OpenFOAM and ANSYS Fluent.

Your review must be rigorous on physics and numerical methods. Specifically:

1. PHYSICS ACCURACY: Are physical models, equations, and assumptions correct? Check units, dimensions, sign conventions, coordinate systems. Verify that turbulence model recommendations (y+, wall treatment) are consistent with established CFD literature (Versteeg & Malalasekera, Ferziger & Peric, Pope).

2. NUMERICAL METHODS: Are discretization schemes, convergence criteria, mesh quality thresholds, and solver settings physically justified? Are the threshold values (non-orthogonality, skewness, aspect ratio, etc.) consistent with OpenFOAM source code defaults and ANSYS Fluent documentation?

3. COMPLETENESS: Are edge cases handled? Missing metrics? Missing solver types? Are the recommendations actionable and specific (not just "improve mesh quality")?

4. CODE QUALITY: For Python scripts — are regex patterns robust against format variations? Are float parsing edge cases handled (scientific notation, negative values)? Are there untested code paths?

5. CROSS-SOLVER CONSISTENCY: If the file covers both OpenFOAM and Fluent, verify that metric conversions and threshold mappings between solvers are mathematically correct (e.g., Orthogonal Quality = cos(non-orthogonality angle)).

Structure your response as:
- Physics & Numerics Accuracy (errors, questionable values, missing caveats)
- Completeness & Coverage (gaps in metrics, solver types, or edge cases)
- Code Robustness (parsing issues, error handling, untested paths)
- Specific Corrections (line-level fixes with justification)
```

If the script is missing or fails, construct the API call directly using
the request format above. Common mistake: using the predictions API format
(`input.prompt`) instead of the chat completions format (`messages`) — these
are two different GPUGeek endpoints.

## Step 3 — Present the results

Show the full review output to the user. If the API call fails (missing key, network error, model unavailable), report the error clearly and suggest checking the environment variables.
