---
name: gpt-review
description: "Review a file using GPT-5.2 via the GPUGeek predictions API. Sends the file content to the model and prints a structured review with improvement suggestions. Use when the user asks for a GPT review, external model review, or second opinion on any file — code, documentation, CFD configs, or skill definitions. Accepts an optional file path argument; defaults to README-fork.md."
---

# GPT Review

Use GPT-5.2 to review a file and provide improvement suggestions.

The argument provided is: $ARGUMENTS

## Step 1 — Determine the target file

1. If `$ARGUMENTS` specifies a file path, use that.
2. Otherwise default to `README-fork.md` in the repo root.
3. Verify the file exists. If not, report the error and stop.

## Step 2 — Call the API

Send the file contents to GPT-5.2 via the GPUGeek **predictions** endpoint.

**IMPORTANT**: This endpoint uses a **different format** from the OpenAI chat
completions API. Do NOT use `messages` array. Use `input.prompt` instead.

- **API key**: Read from `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` environment variable.
- **Model**: `Vendor2/GPT-5.2`
- **Endpoint**: `POST https://api.gpugeek.com/predictions`

### Request format (predictions API)

```json
{
    "model": "Vendor2/GPT-5.2",
    "input": {
        "prompt": "<system prompt>\n\n<user message with file contents>",
        "max_tokens": 16384,
        "temperature": 0.3
    }
}
```

### Response format

```json
{
    "output": "<review text>",
    "metrics": {"input_token_count": ..., "output_token_count": ...}
}
```

The system prompt to prepend (concatenated with file contents into `input.prompt`):

```
You are a senior CFD engineer and computational scientist reviewing a file from ChatCFD-cc, an LLM-driven agent for end-to-end CFD automation built on OpenFOAM and ANSYS Fluent.

Your review should challenge assumptions and suggest creative alternatives. Specifically:

1. PHYSICS FROM FIRST PRINCIPLES: Are threshold values derived from physical reasoning, or just copied from tutorials? For each numerical threshold, ask: why this number? What physical phenomenon sets it? For example, the non-orthogonality limit of 70 degrees in OpenFOAM comes from the accuracy degradation of the least-squares gradient scheme — is this explained?

2. ALTERNATIVE APPROACHES: Could the same goal be achieved differently? For mesh quality checking — are there metrics not covered that matter for specific flow regimes (e.g., cell Peclet number for convection-dominated flows, CFL-based criteria for transient simulations)?

3. CROSS-VALIDATION: Do the OpenFOAM and Fluent thresholds tell a consistent story? The same physical mesh evaluated in both tools should get the same pass/fail verdict. Check that the threshold mappings ensure this.

4. PRACTICAL GAPS: What real-world scenarios would break this? Polyhedral meshes? Overset meshes? AMR (adaptive mesh refinement)? Parallel decomposed cases? Are these mentioned or silently unsupported?

5. PEDAGOGY: If this is documentation — does it explain the "why" behind each criterion, or just list numbers? A CFD beginner should understand not just "skewness < 0.85" but WHY skewness matters (interpolation accuracy at face centers).

Structure your response as:
- Physics Deep-Dive (are thresholds physically justified?)
- Missing Scenarios (what workflows would fail?)
- Creative Alternatives (better approaches or metrics)
- Specific Corrections (line-level fixes with justification)
```

If the script is missing or fails, construct the API call directly using
the request format above. Common mistake: using `messages` array instead of
`input.prompt` — this returns `400 Bad Request`.

## Step 3 — Present the results

Show the full review output to the user. If the API call fails (missing key, network error, model unavailable), report the error clearly and suggest checking the environment variables.
