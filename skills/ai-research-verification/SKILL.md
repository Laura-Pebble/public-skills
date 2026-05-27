---
name: ai-research-verification
description: >
  When the user wants to verify AI-generated research findings before they land in any
  downstream artifact, run the six-check verification protocol against the research
  output and tag every finding with a verification status. Use when the user mentions
  "verify this research", "check these sources", "validate these findings", "research
  verification", "here are the findings", "got research back", or asks to integrate
  AI research into a report, memo, brief, or strategy document. Even when the research
  looks clean, run this skill — fabrication is routine in AI research output, and
  compounding errors across a document chain are the most expensive failure mode to
  catch late.
triggers:
  - "verify this research"
  - "check these sources"
  - "validate these findings"
  - "research verification"
  - "here are the findings"
  - "got research back"
  - "verify AI research"
  - "check AI-generated sources"
version: 1.0.0
last_updated: 2026-05-27
metadata:
  license: ""
  distribution: "operator-only"
---

# SKILL: AI Research Verification

You are verifying inbound AI-generated research before it's used as canonical source in business communications and marketing. Your goal is to prove every load-bearing claim is real, accurate, and properly tagged — and to block fabricated, distorted, or single-thread findings from anchoring anything that gets shared, published, or built upon.

## Purpose

- **What this skill enables**: Verified, status-tagged research findings, with fabricated or distorted claims caught at intake instead of after they propagate.
- **Success criteria**: Every finding is either `[VERIFIED]` (with credibility rating) or `[UNVERIFIED — …]` with a specific reason and recommended action. Zero fabricated or distorted claims pass through to downstream artifacts.
- **Non-goals**: This skill does not produce research; it verifies research already produced. It also does not write the downstream artifact — it gates what is allowed to enter it.

## Inputs & Preconditions

- **Required inputs**:
  - Research output to verify (claims, sources, URLs, quotes).
  - Network access to navigate cited URLs and confirm source existence.
- **Optional inputs**:
  - The downstream context the findings will feed into (report, memo, strategy doc) — useful for judging which claims are load-bearing.
  - The research objective (e.g., market sizing, buyer language, competitive landscape) — verification emphasis adapts by objective type.
- **Preconditions**:
  - **Target surface**: `surface-agnostic`. Runs anywhere the verifier can read the research output, fetch URLs, and write a verification block back to the user.
  - Research has been produced by an AI tool (ChatGPT, Gemini, Perplexity, Claude, ad-hoc web search via an AI agent, etc.). The skill gates what enters downstream artifacts regardless of which tool produced it.
- **Assumptions**:
  - The verifier is running this skill *before* integration, not after.
  - URLs in the research output are accessible to the verifier. Paywalled or auth-walled sources are treated explicitly in Edge Cases.

### Research Objective Affects Verification Emphasis

Verification rigor adapts to what the research was asked to produce. Three common objective types:

1. **Direct-quote / language capture** — actual phrases, vocabulary, terms of art used in source material (interviews, transcripts, public statements). Verification emphasis: source existence, attribution accuracy, register match. Quantitative corroboration is rarely applicable.
2. **Behavioral / process research** — how a population behaves, what channels they use, the path through some decision process. Verification emphasis: methodology transparency (who was surveyed, when), corroboration across at least one independent source for any quantitative behavioral claim.
3. **Generalization / transferability claims** — whether a finding from one segment, geography, or case applies to another. Verification emphasis: claim accuracy (does the source actually support the generalization, or is it being stretched?), single-source flagging.

Quantitative claims (market sizes, growth rates, adoption percentages) demand the strongest corroboration. Direct quotes demand the strongest source-existence check. The six-check protocol covers both; emphasis shifts based on objective type.

## Tools & Permissions

- **Allowed tools**: Web fetch / browser to navigate cited URLs; Read/Write for capturing the verification block; web search for independent corroboration and fabrication checks.
- **Disallowed tools**: None specific to this skill.
- **Required permissions**: Network egress for source URLs.
- **Safety notes**: Do not pass any finding tagged `[UNVERIFIED — …]` through to a downstream artifact under any circumstances. Blocked findings surface to the operator before proceeding.

## Procedure

### Step 1: Source Existence

**Does the cited source actually exist, and does it say what the research tool claims?**

- Navigate to the URL or reference provided.
- Confirm the source is real and accessible (not a hallucinated URL).
- Confirm the specific claim appears in the source — not just a related topic on the same site.

This is the highest-impact check. AI research tools fabricate URLs, invent publication names, and attribute real claims to wrong sources. If the source doesn't exist or doesn't say what was claimed, nothing else matters.

**If it fails:** Tag `[UNVERIFIED — SOURCE NOT FOUND]`. Do not integrate. Request new research with explicit instruction to provide verifiable sources.

### Step 2: Claim Accuracy

**Does the source support the specific claim, or has the AI distorted it?**

- Compare the research output claim against what the source actually says.
- Watch for: rounded numbers presented as exact, conditional findings presented as absolute, regional data presented as global, outdated figures presented as current.
- If paraphrased, confirm the paraphrase is faithful to source meaning.

AI tools often inflate, round, or decontextualize. A source saying "up to 40% in some segments" becomes "40% market-wide" in the research output. The distorted version looks more useful, which is exactly why it's dangerous.

**If it fails:** Correct the claim to match the source. Adjust the credibility rating if needed. If the correction changes strategic significance, flag to the operator.

### Step 3: Corroboration

**Is this quantitative claim supported by more than one independent source?**

- For quantitative claims (market sizes, growth rates, adoption percentages, pricing): find at least one additional independent source.
- "Independent" means not derived from the same underlying dataset. Two articles citing the same Gartner report count as one source, not two.

**Single-source exception.** Niche markets, emerging categories, and proprietary data often have single-source findings. This is acceptable when all three conditions are met:

1. Source is rated HIGH credibility (see Step 5).
2. Finding is tagged `[VERIFIED — SINGLE SOURCE]` when carried forward.
3. Downstream artifacts that build on this finding inherit the single-source flag.

The reason for the flag: if the single source later turns out to be wrong, you need to know exactly which downstream claims are affected.

**If it fails (no corroboration, not HIGH credibility):** Tag `[FLAGGED — VALIDATE]`. Flag to operator with a specific validation plan before the finding anchors downstream work.

### Step 4: Methodology Transparency

**Can you determine how this data was collected or derived?**

- For statistics and market data: is methodology disclosed (sample size, geography, date range, method)?
- For surveys: who was surveyed, how many, when?
- For market sizing: TAM/SAM/SOM, bottom-up, top-down, or undisclosed?

Precise-looking numbers from sources that don't explain where those numbers come from are a common failure mode. Vendor reports are especially prone to this — they publish authoritative-looking statistics without disclosing methodology because the goal is marketing, not research.

**If methodology is undisclosed:** The finding can still be used, but:

- Source credibility drops to MODERATE at best (cannot be HIGH without methodology).
- Tag `[VERIFIED — METHODOLOGY UNDISCLOSED]`.
- If load-bearing (affects 2+ downstream sections or decisions), flag to operator.

### Step 5: Source Credibility Rating

Rate every source:

| Rating | Definition |
|---|---|
| HIGH | Primary research, independent methodology, no conflict of interest. Government data, peer-reviewed studies, established industry bodies (Gartner, Forrester with disclosed methodology), trade association research. |
| MODERATE | Clear methodology but potential bias, or reputable secondary source. Vendor reports about own market, well-sourced journalism, analyst firms without disclosed methodology. |
| LOW | Opinion, self-reported without verification, undated, anonymous. Blog posts without data, forum posts, aggregator sites, unsourced claims, vendor marketing materials presented as research. |

**Rules:**

- LOW sources cannot anchor quantitative claims in any artifact. They provide directional color or qualitative context only — a wrong number is worse than no number.
- Vendor research about their own market: MODERATE at best, regardless of methodology quality. The conflict of interest caps credibility.
- MODERATE sources on load-bearing claims: flag with `[VERIFIED — MODERATE SOURCE]` and seek corroboration.

### Step 6: AI Fabrication Indicators

**Are there signs the research tool invented this rather than found it?**

Red flags — any of these means stop and investigate:

- Suspiciously round numbers (exactly 50%, exactly $10B).
- Statistics that perfectly confirm the hypothesis being researched.
- Claims attributed to well-known sources that don't appear on those sources' actual websites.
- URLs that 404 or redirect to unrelated content.
- Multiple "sources" using identical phrasing (suggests the AI generated the claim and then fabricated multiple "citations" to support it).
- Data points that appear nowhere else on the internet when searched independently.

**If fabrication suspected:** Tag `[UNVERIFIED — FABRICATION SUSPECTED]`. Do not integrate. Request fresh research with this constraint: "Provide only claims you can trace to a specific, named, accessible source. Do not synthesize or estimate."

## Verification Status Tags

Apply during verification. These travel with the finding into any downstream artifact.

| Tag | Meaning |
|---|---|
| `[VERIFIED]` | Source exists, claim accurate, corroborated, credibility rated HIGH or MODERATE |
| `[VERIFIED — SINGLE SOURCE]` | Passed all checks, one source only, HIGH credibility (single-source exception applies) |
| `[VERIFIED — MODERATE SOURCE]` | Passed all checks, MODERATE credibility — note the caveat downstream |
| `[VERIFIED — METHODOLOGY UNDISCLOSED]` | Claim checks out, methodology opaque — note the caveat downstream |
| `[FLAGGED — VALIDATE]` | Single source without HIGH credibility; needs operator decision before use |
| `[UNVERIFIED — SOURCE NOT FOUND]` | Cannot locate cited source — do not integrate |
| `[UNVERIFIED — CLAIM MISMATCH]` | Source exists but doesn't support the claim — correct or discard |
| `[UNVERIFIED — FABRICATION SUSPECTED]` | Red flags for AI-generated data — do not integrate |

## Output Format

After running verification on a research batch, present results before proceeding:

```
RESEARCH VERIFICATION — [Date]
Source tool: [Which AI tool produced the research]
Objective: [What the research was asked to produce]
Findings checked: [count]

VERIFIED: [count]
- [Finding summary] → [tag] — [source, credibility rating]

FLAGGED: [count]
- [Finding summary] → [tag] — [issue, what needs attention]

BLOCKED: [count]
- [Finding summary] → [tag] — [reason, recommended action]

Recommendation: [Proceed with integration | Operator decision needed on flagged findings | Do not proceed — blocked findings]
```

If all findings verify clean, state that and proceed. If any are BLOCKED, stop and surface to the operator before continuing — blocked findings mean the research tool produced unreliable output, and the operator needs to decide how to proceed.

## Gotchas

- **AI tools cite real publications and fabricate the article.** The publication name (Harvard Business Review, McKinsey Quarterly) is real; the specific article title or DOI is not. Step 1 catches this only if you actually navigate to the URL — never accept a citation just because the publisher is reputable.
- **"Up to" silently becomes "is."** A source saying "up to 40% in some segments" routinely returns from the research tool as "40% of the market." This is the single most common Step 2 failure mode. Read the source's qualifier language word-for-word.
- **Analyst press releases ≠ analyst reports.** AI tools cite the press release URL because the report itself is paywalled. The press release contains marketing language with the precise number stripped of methodology. Treat as MODERATE credibility at best until the underlying report is accessed.
- **Two articles citing the same study count as one source.** Reuters and Bloomberg both quoting the same Forrester finding is one source, not two. Step 3 corroboration must trace to independent underlying datasets, not independent retellings.
- **Suspiciously round numbers often pass Step 1.** A fabricated "$10B market" claim can be supported by a real-looking URL that goes to a real consulting firm's blog post that does not actually contain $10B. Step 1 (source exists) and Step 2 (source supports claim) are separate checks for a reason.
- **Single-source HIGH credibility is acceptable; single-source MODERATE is not.** The single-source exception in Step 3 has three preconditions and they all must hold. Operators often remember the exception and forget the preconditions.
- **Vendor research about the vendor's own market is capped at MODERATE.** Even if methodology is disclosed and the sample is large. The conflict of interest is the binding constraint, not the methodology quality.
- **Direct quotes are verified differently from statistics.** Skip Step 3 corroboration for direct quotes — emphasize Step 1 source existence and register match. A fabricated quote is a Step 1 failure, not a Step 3 failure.

## Edge Cases & Failure Modes

- **Missing or empty research input**: Stop. Ask the operator for the research output. Do not attempt to verify summaries paraphrased into chat — verify the actual research artifact with its citations intact.
- **All findings BLOCKED**: The research tool produced unreliable output. Stop. Surface the entire batch to the operator. Do not attempt to salvage individual findings — pattern-level fabrication often means the whole batch is suspect.
- **Single source on load-bearing claim with HIGH credibility**: Acceptable per the single-source exception. Tag `[VERIFIED — SINGLE SOURCE]` and ensure the flag propagates downstream so a future correction can be traced.
- **Source exists but is paywalled and inaccessible**: Treat as `[UNVERIFIED — SOURCE NOT FOUND]` for purposes of this skill. The verifier cannot verify what they cannot read. Request the operator obtain access or substitute an accessible source.
- **Direct-quote finding where corroboration does not apply**: Skip Step 3 corroboration; emphasize Step 1 source existence and Step 2 attribution accuracy. Note the objective type on the verification output so downstream readers understand why corroboration was waived.
- **Research delivered as a paraphrased summary without citations**: Stop. Ask the operator to re-request the research with citations included. Verification without citations is impossible; do not approximate.
- **Network access denied / cannot fetch URLs**: Stop. Verification requires fetching the actual sources. Tell the operator and either request the URLs be fetched on the verifier's behalf, or defer verification until network access is available.
- **Ambiguous research scope (verifier cannot tell which claims are load-bearing)**: Ask the operator one targeted question — "Which of these findings will anchor downstream decisions?" — before applying the heavier corroboration and methodology checks.

## Examples

### Example 1: Mixed batch from initial AI research

**Input.** A research batch of four findings on buyer behavior in mid-market software:

1. Claim: "62% of mid-market software buyers shortlist vendors via peer review sites before vendor websites." Source: TrustRadius 2025 Buyer Behavior Report (URL provided).
2. Claim: "The mid-market AI tooling market is exactly $14B in 2025." Source: A consulting blog post (URL provided, no methodology disclosed).
3. Claim: "Buyers spend up to 40% of evaluation time on peer review platforms." Source: A G2 blog post, restated in the research output as "Buyers spend 40% of evaluation time on peer review platforms."
4. Quote: "We don't shortlist anything we can't see ROI on in 90 days." Source: Anonymized buyer interview from a vendor case study.

**Steps.** Run the six-check protocol per finding:

- Finding 1: Step 1 confirms the report exists and contains the 62% figure. Step 2 confirms the claim is faithful. Step 3 finds a corroborating Forrester finding from the same year. Step 4 confirms methodology (n=400, North America, Q1 2025). Step 5 rates TrustRadius MODERATE (vendor-adjacent platform reporting on their own segment) and Forrester HIGH. Step 6 clean. → `[VERIFIED]`, MODERATE primary + HIGH corroboration.
- Finding 2: Step 1 confirms the blog post exists. Step 2 fails — the blog post says "approximately $12-15B" with no specific methodology. The research output rounded to "exactly $14B." Step 4 fails — no methodology. → `[UNVERIFIED — CLAIM MISMATCH]`, request correction.
- Finding 3: Step 1 confirms the G2 post exists. Step 2 fails — the source says "up to 40%" and the research output dropped "up to." → `[UNVERIFIED — CLAIM MISMATCH]`, correct to source language.
- Finding 4: Step 1 confirms the case study exists and the quote appears verbatim. Direct-quote objective, so Steps 3 and 4 do not apply. Step 5 rates the case study MODERATE (vendor-published, but direct quote attribution). Step 6 clean. → `[VERIFIED — MODERATE SOURCE]`.

**Expected output.**

```
RESEARCH VERIFICATION — 2026-05-27
Source tool: ChatGPT
Objective: Buyer behavior in mid-market software (Findings 1-3) + direct buyer quote (Finding 4)
Findings checked: 4

VERIFIED: 2
- Peer-review-first shortlisting (62%) → [VERIFIED] — TrustRadius 2025 Buyer Behavior Report (MODERATE) corroborated by Forrester (HIGH)
- Buyer ROI quote ("90 days") → [VERIFIED — MODERATE SOURCE] — vendor case study, direct quote

FLAGGED: 0

BLOCKED: 2
- "$14B market in 2025" → [UNVERIFIED — CLAIM MISMATCH] — source says "$12-15B", no methodology disclosed; request research correction with exact source language and methodology citation
- "40% of evaluation time on peer reviews" → [UNVERIFIED — CLAIM MISMATCH] — source says "up to 40%"; correct to source qualifier or discard

Recommendation: Do not proceed — blocked findings. Send #2 and #3 back to the research tool with the explicit instruction: "Restate each finding using source's exact qualifier language. Disclose methodology or mark UNDISCLOSED."
```

### Example 2: Fabrication-suspected single finding

**Input.** A single inbound claim: "Exactly 50% of B2B SaaS buyers cite vendor LinkedIn presence as a top-three trust signal." Source: a URL that 404s, attributed to a "2025 LinkedIn B2B Trust Index."

**Steps.** Step 1 fails — URL 404s. Step 6 triggers on three indicators: suspiciously round number (exactly 50%), no LinkedIn product called "B2B Trust Index" appears in independent search, claim aligns suspiciously well with what a buyer-discovery hypothesis would want.

**Expected output.**

```
RESEARCH VERIFICATION — 2026-05-27
Source tool: Perplexity
Objective: Buyer trust signals
Findings checked: 1

VERIFIED: 0
FLAGGED: 0
BLOCKED: 1
- "50% cite LinkedIn presence as top-three trust signal" → [UNVERIFIED — FABRICATION SUSPECTED] — cited URL 404s; no "LinkedIn B2B Trust Index" appears in independent search; suspiciously round number aligned with hypothesis. Request fresh research with constraint: "Provide only claims you can trace to a specific, named, accessible source. Do not synthesize or estimate."

Recommendation: Do not proceed — blocked finding. Re-run the query against a different tool with the no-synthesis constraint above, or fall back to manual sourcing.
```

## Verification

Before declaring a research batch verified, run these concrete checks:

1. Open every cited URL in the research output. Confirm each loads (no 404, no redirect to unrelated content) and contains the specific claim attributed to it. Findings whose URLs fail this check are tagged `[UNVERIFIED — SOURCE NOT FOUND]`.
2. For every quantitative claim, count the number of independent sources. "Independent" excludes articles that cite the same underlying dataset. The count is either ≥2 (corroborated) or 1 (single-source; check the HIGH-credibility exception applies).
3. Search at least two of the supposedly fabrication-suspect findings (round numbers, hypothesis-perfect statistics) on the open web via an independent query. Findings that appear nowhere outside the research output get `[UNVERIFIED — FABRICATION SUSPECTED]`.
4. Re-read the verification block you are about to return. Confirm every finding has exactly one verification tag from the table in **Verification Status Tags**, and that the VERIFIED / FLAGGED / BLOCKED counts sum to the total findings checked.

If any check fails or returns ambiguous results, do not present the verification block — fix the gap first or escalate to the operator.

## Deliverables

- **Files created/modified**: None by default. This skill produces a verification block returned in chat. If the operator chooses to capture it, paste the block into the relevant downstream document, project log, or PR description.
- **Output format**: The block shown in **Output Format** above — plain markdown.
- **Naming conventions**: N/A (no files produced).
- **Output location**: Presented inline in the conversation.
- **What to return to the user**: The verification block plus the explicit recommendation line — one of: "Proceed with integration", "Operator decision needed on flagged findings", or "Do not proceed — blocked findings".

## Quality Bar Checklist

Before returning the verification block:

- [ ] Every finding carries exactly one verification status tag from the table above.
- [ ] No finding tagged `[UNVERIFIED — …]` has been integrated into a downstream artifact.
- [ ] Every quantitative load-bearing claim has either corroboration or an explicit `[VERIFIED — SINGLE SOURCE]` flag.
- [ ] Every source has a credibility rating (HIGH / MODERATE / LOW).
- [ ] LOW-credibility sources are not anchoring any quantitative claim.
- [ ] VERIFIED + FLAGGED + BLOCKED counts sum to total findings checked.
- [ ] Recommendation line states one of: "Proceed with integration", "Operator decision needed on flagged findings", or "Do not proceed — blocked findings".

## Related Skills

This skill is standalone — it has no upstream or downstream skill dependencies. It can be paired with any content-production, strategy, or research workflow that consumes AI-generated research as input.
