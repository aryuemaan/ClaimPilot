# ClaimPilot – submission notes

Copy these sections into the submission deck or PDF. Each section is written to be one slide.

---

## 1. Title

**ClaimPilot: an AI claims desk for motor insurance**
Theme: BFSI · Built with Gemini, Agent Development Kit, Gemma, Cloud Run, Firestore and Cloud Storage
Live demo: `<your Cloud Run URL>` · Video: `<link>` · Code: `<repo link>`

## 2. The problem

- Filing a motor claim in India means forms, document uploads, surveyor visits and days of waiting, usually in English, which many customers aren't comfortable writing in.
- Claims teams spend their time reading photos, bills and policy wordings by hand, and the same rules (depreciation, deductibles, exclusions) are re-applied claim after claim.
- Fraud slips through. Reused photos, inflated or edited invoices and claims filed days after buying a policy are hard to spot at volume. Fraud, waste and abuse are estimated to drain **₹8,000–10,000 crore a year from Indian health insurance claims alone** (BCG and Medi Assist, 2025). Motor insurers face the same patterns.
- **Trust** is the product. Customers want speed and a clear explanation; regulators and insurers want a human accountable for every decision.

## 3. The solution

1. The customer opens a link and **tells the story by voice in their own language** (Telugu, Hindi, English and more), then adds photos and bills. There's no form.
2. **Eight agents** process the claim in about 30 seconds:
   - a privacy guard;
   - an intake agent;
   - coverage, damage and fraud specialists, running in parallel;
   - a deterministic cost estimator;
   - an adjudicator.
3. The adjuster receives a **one-page brief** with:
   - damage boxes on the photos;
   - quoted policy clauses;
   - a rupee-by-rupee estimate;
   - fraud evidence;
   - a reply already drafted in the customer's language.
4. The adjuster **decides with one click**. Overrides need a reason, and everything is audited.
5. The customer gets the outcome **in their language**, and can ask follow-up questions ("why is it less than my bill?").

## 4. Why it fits the BFSI theme

| What the brief asked for | How ClaimPilot answers |
|---|---|
| Mitigate risk and fraud | 8 deterministic fraud checks plus Gemini document forensics. Duplicate-photo detection survives cropping and filters. Invoice tampering is caught (white-out, font change, words vs figures). |
| Simplify complex processes | Policy wording, IRDAI depreciation and deductibles are applied automatically and explained line by line. |
| User-friendly customer interaction | Voice-first, multilingual, mobile web. No app install and no forms. Live progress. |
| Hyper-personalisation | Replies in the customer's language and script. Explanations use their own policy, add-ons (Zero-Dep) and vehicle age. |
| Security and trust | PII masking with rules and Gemma, least-privilege service account, Secret Manager, customer views without fraud data, full audit trail. |
| AI informs; people decide | Human sign-off on every claim, written reasons for overrides, and guardrails in code. |

## 5. Demo stories (all fictional data)

| Story | What it shows | AI result |
|---|---|---|
| **Ravi** (Telugu), rear-ended at a signal | Voice intake, damage boxes, depreciation maths, fast-track | Approve ₹11,124 (bill ₹19,187, less 50% depreciation on plastic parts and ₹1,000 deductible) |
| **Priya** (Hindi), parking scrape plus a broken phone | Zero-Dep add-on, clause-level exclusion of personal belongings | Approve in part, ₹18,422; phone excluded under Excl I.4(d) |
| **Arjun** (English), "too good to be true" | Reused photo from another claim, edited invoice dated before the incident, 4-day-old policy, story vs photo mismatch | Investigate, fraud risk 94/100, refer to SIU |

## 6. Google Cloud and AI used

| Technology | Role |
|---|---|
| **Gemini 3.8 Flash** | Voice transcription and translation, multimodal intake (photos, bills, PDF), damage detection with bounding boxes, coverage reasoning, document forensics, adjudication, customer replies, copilot |
| **Agent Development Kit (ADK)** | Sequential and parallel agent tree, custom deterministic agents, structured outputs, callbacks for file routing and live progress, a tool-using copilot |
| **Gemma 4** | Privacy pass on customer text (a model that can also run on-premises) |
| **Cloud Run** | Hosting the containerised app (UI and API), autoscaling |
| **Firestore** | Claims, policies, claim history, audit |
| **Cloud Storage** | Photos, bills, voice notes, policy PDFs |
| **Secret Manager / IAM** | API key storage, least-privilege service account |
| **Cloud Build** | Container build on deploy |
| **Firebase Hosting** (optional) | Custom domain in front of Cloud Run |
| Vertex AI (switch) | Run on Vertex with service-account auth via one environment variable |

## 7. Impact

- **Customers:** a decision-ready claim in minutes instead of days, in their own language, with every rupee explained.
- **Insurers:**
  - adjusters review instead of re-keying;
  - fast-track for low-risk, low-value claims;
  - fraud is held *before* payout, with evidence an SIU can act on;
  - consistent application of depreciation and exclusions.
- **Regulators and trust:**
  - every AI output, human decision and override reason is stored;
  - customers are never told they are suspected of fraud; they're told what will be verified.
- The Insights page tracks the AI review time, the adjuster–AI agreement rate and the amount held for investigation. These are the metrics a pilot would be judged on.

## 8. Feasibility and scale

- It runs today as one container on Cloud Run with serverless storage. There are no servers to manage.
- Production path:
  - a Pub/Sub queue for the pipeline;
  - Vertex AI Agent Engine for agents and sessions;
  - vector search for duplicate photos across millions of claims;
  - IAP and Firebase Auth for access;
  - an India region for data residency.
- It extends to **health** (hospital bills, tariff codes), **property** and **crop** insurance by swapping the policy wording, catalogue and fraud tools. The agent tree and UIs stay the same.

## 9. User guide (short)

| User | Steps |
|---|---|
| Customer | Open `/claim` → choose a policy (demo policyholders listed) → record or type the story → add photos and bills → submit → follow live progress and ask questions on the claim page. |
| Adjuster | Open `/console` → pick a claim → review the brief, coverage, estimate and fraud tabs → ask the copilot if needed → approve, request info, refer to SIU or reject. |
| Admin / demo | Console sidebar → **Load the 3 sample claims** or **Reset demo data**. |

## 10. Roadmap

1. Workshop network integration for cashless authorisation, with live repair status.
2. Video walk-around capture with Gemini (360° damage view).
3. Shared industry duplicate-claim checks (the Insurance Information Bureau-style registry).
4. Health-claim pack: discharge-summary reading, tariff mapping, pre-authorisation.
5. Offline and low-bandwidth mode: on-device Gemma for capture-time quality checks.

---

*Source for the fraud figure: BCG and Medi Assist, "Rebuilding Trust: Combating Fraud, Waste and Abuse in India's Health Insurance Ecosystem", 2025.*
