# ClaimPilot – architecture

## System overview

```mermaid
flowchart LR
  subgraph Customer["Customer (phone)"]
    A[Voice note · photos · bills]
  end
  subgraph CR["Cloud Run: ClaimPilot container"]
    API[FastAPI + SSE]
    subgraph ADK["Google ADK pipeline"]
      P[privacy_guard<br/>rules + Gemma] --> I[intake_agent<br/>Gemini multimodal]
      I --> PAR
      subgraph PAR[ParallelAgent]
        C[coverage_agent<br/>Gemini + policy PDF]
        D[damage_agent<br/>Gemini vision]
        subgraph FT[fraud_team]
          S[fraud_signals<br/>8 deterministic tools] --> F[fraud_analyst<br/>Gemini]
        end
      end
      PAR --> E[cost_estimator<br/>deterministic]
      E --> J[adjudicator<br/>Gemini]
    end
    CP[claim_copilot<br/>tool-using agent]
  end
  A -->|HTTPS| API
  API --> ADK
  API <--> FS[(Firestore<br/>claims · policies · history)]
  API <--> GCS[(Cloud Storage<br/>photos · bills · PDFs)]
  ADK --> GM[[Gemini API / Vertex AI]]
  P --> GE[[Gemma]]
  API -->|live updates| CON[Adjuster console]
  CON -->|decision| API
  API -->|reply in Telugu / Hindi| Customer
  SM[Secret Manager] -.API key.-> CR
```

## The agents

| # | Agent | Type | Input | Output (validated schema) |
|---|---|---|---|---|
| 1 | `privacy_guard` | Custom ADK `BaseAgent` | Raw statement | Masked statement and findings. Regex covers Aadhaar, PAN, phone, email, card and bank numbers; Gemma covers free-text details. |
| 2 | `intake_agent` | `LlmAgent` (Gemini) | Statement plus all photos and documents | `IntakeResult`: language, English translation, date/time/place, incident type, every bill line as printed, claimed amount, non-vehicle items, missing info. |
| 3a | `coverage_agent` | `LlmAgent` (Gemini) | Policy schedule, policy wording **PDF**, intake facts | `CoverageResult`: per-item covered/excluded/limited with clause reference and verbatim quote, deductible, depreciation rule. |
| 3b | `damage_agent` | `LlmAgent` (Gemini vision) | **Photos only** | `DamageResult`: per photo, view, quality, and plate/vehicle match; per part, catalogue code, `box_2d`, severity, repair/replace and confidence; consistency with the story. |
| 3c | `fraud_signals` | Custom `BaseAgent` | Photos, history, policy, intake | 8 signals: duplicate photo (multi-crop dHash), camera date, policy age, bill arithmetic, bill date, claim history, claim vs IDV, reporting delay. |
| 3d | `fraud_analyst` | `LlmAgent` (Gemini) | Signals plus **documents only** | `FraudResult`: risk score, red flags with evidence, tampering suspicion, recommended checks. |
| 4 | `cost_estimator` | Custom `BaseAgent` | Damaged parts, policy, vehicle age | Line-by-line parts, labour, paint, 18% GST, IRDAI depreciation (Sec I.2), compulsory deductible (Sec I.3), cap at billed amount. |
| 5 | `adjudicator` | `LlmAgent` (Gemini) | All of the above (no files) | `DecisionBrief`: recommendation, payout (forced to equal the estimate), confidence, rationale with sources, next steps, customer message in English and in the customer's language. |
| – | `claim_copilot` | `LlmAgent` with tools | Question | Answer grounded by `get_claim_file(section)` and `search_policy_wording(query)`. The customer version cannot see fraud data. |

### ADK features used
- `SequentialAgent`, `ParallelAgent` and a nested `SequentialAgent`, mixing `LlmAgent` with custom `BaseAgent` subclasses.
- `output_schema` (pydantic) and `output_key`, so agents hand structured state to each other.
- Instruction providers (callables) that inject session state as JSON.
- `before_model_callback` for per-agent **file routing**: the damage agent sees only photos, coverage gets only the policy PDF, the fraud analyst gets only documents, and the adjudicator gets no files. This cuts tokens and latency and reduces cross-contamination.
- `before_agent_callback` to stream live progress into Firestore, and from there over SSE to both UIs.
- `Gemini` model class with HTTP retry options (408/429/5xx) and `ThinkingConfig(thinking_level=LOW)` for speed.
- Function tools with automatic schema generation for the copilot.

## Guardrails in code (not in prompts)

These rules are enforced in `pipeline._apply_guards()`:
- The payout equals the deterministic estimate for approve/approve_partial, and 0 otherwise.
- High fraud risk with an approve recommendation is forced to `investigate`.
- Fast-track requires low risk, a payout under ₹50,000 and confidence of 85% or more.

These rules are enforced in the decision API:
- An override (a different action, or an amount more than 1% away from the AI's) requires a written reason.
- Request-info and reject decisions require a note for the customer.
- Every step is appended to an audit log.

## Data model (Firestore)

| Collection | Contents |
|---|---|
| `claims/{id}` | Claimant, vehicle, statement, files (with GCS keys), `trace` (per-agent status, ms, summary), `ai` (all agent outputs), `final_decision`, `timeline` (customer-facing), `audit`, `chat`. |
| `policies/{number}` | Schedule, vehicle, add-ons, IDV, policy PDF key, wording text, claims in the last 12 months. |
| `past_claims/{id}` | Historical claims with photo hash lists, used for duplicate detection and the baseline. |
| `samples/{key}` | Demo kits. |
| `meta/seed` | Date the demo data was generated. |

## Security and privacy

- Personal identifiers are masked before any downstream agent sees the statement. Masked findings are listed in the console.
- The service runs as a dedicated service account with `datastore.user`, `aiplatform.user` and bucket-scoped `storage.objectAdmin` only.
- The API key lives in Secret Manager and is mounted as an environment variable at runtime.
- Customer views (`/public`, the customer copilot) never include fraud signals, scores or internal notes.
- Files are served through the API, not public bucket URLs.
- In production:
  - put the console behind Identity-Aware Proxy or Firebase Auth with adjuster roles;
  - use OTP login for customers;
  - add CMEK on the bucket;
  - keep data in an India region (asia-south1) with Vertex AI regional endpoints.

## Scaling to production

| Today (prototype) | Production path |
|---|---|
| Pipeline runs as a background task in the Cloud Run instance (`--no-cpu-throttling`) | Pub/Sub or Cloud Tasks queue triggers a worker service, with retries and dead-lettering. |
| In-memory ADK sessions | `VertexAiSessionService` / Agent Engine for durable sessions and tracing. |
| SSE by polling Firestore | Firestore real-time listeners in the client. |
| Catalogue prices in code | Insurer's parts and labour master in BigQuery, refreshed by region and brand. |
| Duplicate search over all past photos | Vertex AI Vector Search over image embeddings, plus pHash prefilter, for millions of claims. |
| Demo login | Firebase Auth (OTP) for customers, IAP plus roles for adjusters, and a maker-checker flow above an approval limit. |
| Manual prompt tuning | ADK evaluation sets built from adjuster decisions (the agreement rate is already logged). |

**Cost and latency.** A claim is 5 Gemini calls plus 1 Gemma call. The 3 specialist calls run in parallel, so latency is roughly intake + the slowest specialist + adjudicator. Each agent receives only its own files, which keeps token use proportional to the evidence. Check current per-token prices on the Gemini pricing page to cost it for your volume.

## Extending to other lines of business

The pipeline shape stays the same. You swap:
- the coverage wording;
- the catalogue (a hospital tariff for health, repair rates for property);
- the fraud tools (provider blacklists, duplicate bills across insurers).

The ADK agent tree, file routing, guardrails, console and customer app are reused as they are.
