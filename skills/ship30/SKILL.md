# Ship 30 for 30 Skill

## Purpose

This skill generates a ~1,250-word essay in the Ship 30 for 30 digital writing style,
grounded in Lenny's Podcast transcript evidence.

## When Activated

The router activates this skill when the user's intent is classified as `SHIP30`.

Trigger phrases include:
- "write an essay about..."
- "ship 30 style essay"
- "turn this into a ship 30 essay"
- "write a digital essay"
- "create a newsletter post"
- "write a thread about this conversation"

## Inputs

- Current conversation context (recent messages)
- Retrieved transcript chunks relevant to the essay topic
- The Ship 30 principles (see `principles.md`)
- The essay template (see `template.md`)

## Outputs

A single Markdown string containing:
- A strong hook headline
- Clear sections with H2 subheadings
- Short paragraphs (1-3 sentences)
- Selective **bold** emphasis
- Transcript-grounded claims with source attribution
- A concrete takeaway/conclusion
- Approximate length: 1,100–1,350 words

## Grounding Rules

1. Every major claim MUST be attributable to retrieved transcript evidence.
2. Do NOT fabricate quotes. If you cannot find evidence, say so.
3. Distinguish between what was said in transcripts vs. editorial inference.
4. Use "According to [Guest] on Lenny's Podcast..." for direct attributions.

## Non-Goals

- Do not write clickbait with no substance.
- Do not exceed 1,500 words.
- Do not use generic platitudes unsupported by transcript evidence.
