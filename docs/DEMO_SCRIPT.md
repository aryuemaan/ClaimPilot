# ClaimPilot – demo playbook

This file has three parts: what to prepare, the 3-minute submission video, and the live demo for the finale.

---

## A. Before you record or present

**The day before**
- [ ] Run `python -m app.doctor` (locally) or open `<url>/api/health` (Cloud Run).
  - Locally, every model should show `ok`.
  - On Cloud Run, `mode` should say `"live"`.
- [ ] Put real damage photos in `sample-data/photos/` (README section 8), then redeploy. This step is optional but makes a big difference.
- [ ] Do one full rehearsal of each story and note how long the agents take on your quota (usually 20–40 seconds).
- [ ] On your phone, open the Cloud Run URL once and **allow microphone access** for the site.

**30 minutes before**
- [ ] Console → **Demo controls → Reset demo data**. This gives fresh dates and an empty queue.
- [ ] Laptop: open `/console` in one tab and `/console/insights` in another. Zoom the browser to 110% so the audience can read it.
- [ ] Phone: open `/claim`, screen brightness up, Do Not Disturb on.
- [ ] Optional: click **Load the 3 sample claims** in a second browser profile ahead of time. That way you have finished briefs ready if the network is slow.

**Backup plan.** If Gemini quota or the network fails mid-demo, restart with `FORCE_OFFLINE=true`. Every screen keeps working with the scripted model, and the yellow bar says so honestly.

---

## B. The 3-minute video

Record the screen at 1080p. Show the phone with a mirroring tool (scrcpy, QuickTime or Phone Link), or use Chrome DevTools' device mode for the customer app. Talk calmly; 150 words a minute is about right.

| Time | Screen | Say |
|---|---|---|
| 0:00 – 0:15 | Landing page, road diagram | "In India a car-insurance claim still means forms, surveys and days of waiting, and insurers lose crores to fraud every year. ClaimPilot is an AI claims desk on Google Cloud that turns a voice note and a few photos into a decision-ready brief in under a minute, while a person still makes the call." |
| 0:15 – 0:45 | Phone: pick Ravi → record in Telugu → transcript appears → sample photos → submit | "Ravi was rear-ended at a signal. He doesn't fill in a form. He just tells us what happened in Telugu. Gemini transcribes and translates it. He adds two photos and the workshop estimate, and submits." |
| 0:45 – 1:10 | Customer progress screen, then console agent trace filling in | "Behind this, eight agents built with Google's Agent Development Kit go to work. A privacy guard uses rules and Gemma to mask his Aadhaar and phone numbers. An intake agent reads everything. Then three specialists run in parallel: coverage reads the policy PDF, damage inspects the photos, and fraud runs eight hard checks plus document forensics." |
| 1:10 – 1:45 | Claim brief: damage boxes → Coverage tab (clause quote) → Estimate tab | "The adjuster gets one page. Gemini has boxed the damaged bumper and tail lamp. Coverage quotes the exact clause. The money is computed in code, not by the model: parts, labour, GST, the 50% IRDAI depreciation on plastic parts and the ₹1,000 deductible. ₹11,124, fast-track eligible, with a reply already drafted in Telugu." |
| 1:45 – 1:55 | Click Approve → stamp → phone shows approval in Telugu | "One click. Ravi gets the answer in his language, minutes after the accident." |
| 1:55 – 2:35 | Open Arjun's claim → Fraud tab → side-by-side photo → invoice | "Now a claim that looks fine at first glance. The fraud agent finds that the photo is a cropped copy of one from another customer's claim seven months ago. The camera date predates the accident. Gemini spots that the invoice total sits on a white-out patch in a different font, while the amount in words still says ₹85,196. The bill is dated before the crash, and the policy is four days old. ClaimPilot recommends the investigation unit and never accuses the customer. His message just says an officer will call." |
| 2:35 – 2:50 | Ask ClaimPilot drawer: "What should I verify before approving?" | "Adjusters can question the file. The copilot uses tools to read the claim and the policy wording, and cites its sources." |
| 2:50 – 3:00 | Insights page | "Gemini, ADK, Gemma, Cloud Run, Firestore and Cloud Storage: claims settled in minutes, fraud caught before payout, and a human signing off on every decision. That's ClaimPilot." |

**Recording tips**
- Record each segment separately and cut out the waiting while the agents run. Leave 2–3 seconds of the live trace in so judges see it's real.
- In the Arjun segment, hover over the duplicate-photo comparison and the invoice image. Point the cursor at the white-out patch.
- Upload to YouTube as "Unlisted" or to Google Drive with "Anyone with the link can view".

---

## C. Live demo at the finale (5–7 minutes)

**Setup:** the laptop shows the console on the projector; you hold the phone, or a teammate does.

1. **Hook (20 s).** Ask the jury: *"Who here has filed a car insurance claim? How long did it take?"* Then show the landing page road diagram for one sentence.
2. **Ravi, live (2 min).**
   - Teammate on the phone: open Ravi, record the story **live in Telugu** (or Hindi or English if nobody speaks Telugu, since language is auto-detected), add the sample photos and submit.
   - You on the laptop: the queue updates. Open the claim and narrate the agent trace as it fills in.
   - Walk through the damage boxes, the coverage clause and the estimate.
   - Click Approve. The stamp lands and the phone shows the Telugu approval. Hold the phone up.
3. **Arjun (2 min).** Open the pre-loaded claim (or submit it live if time allows). Go to the Fraud tab and show the side-by-side photo, the invoice forensics and the timing. Click **Refer to SIU** and add a note.
4. **Override and audit (30 s).** On Priya's claim, change the payout and try to approve. The console requires a reason. Show the Audit tab: every AI output and human decision is recorded.
5. **Close (30 s).** Show the Insights page, then the architecture (`docs/ARCHITECTURE.md` diagram or one slide).

### Likely jury questions

- **"What stops the model hallucinating a payout?"**
  The LLM only identifies parts and severity. Rupees come from a deterministic estimator with the IRDAI schedule. A guard in code forces the recommended payout to equal that estimate, and high fraud risk always routes to investigation.
- **"How do you know the duplicate-photo detection works?"**
  It compares perceptual hashes across shifted crops, so cropping, re-compressing or brightening a photo doesn't hide it. In our tests, true re-uses score above 0.87 similarity and unrelated photos below 0.73. The threshold is 0.86.
- **"Isn't sending customer data to an LLM a privacy risk?"**
  Structured identifiers are masked by rules before analysis. Gemma (which can run locally) catches free-text personal details. Files stay in a private bucket, and in production Vertex AI keeps the data in the customer's Google Cloud project.
- **"How does this scale?"**
  Cloud Run autoscales stateless containers, and Firestore and Cloud Storage are serverless. In production a Pub/Sub or Cloud Tasks queue would feed the pipeline, and agents can move to Vertex AI Agent Engine. See `ARCHITECTURE.md`.
- **"What about health or property claims?"**
  The pipeline shape is the same. You swap the coverage wording, the parts catalogue (for example, hospital tariff codes) and the fraud checks.
- **"Accuracy?"**
  Every AI recommendation is compared with the adjuster's final decision. The Insights page shows the agreement rate, which becomes the evaluation dataset for tuning prompts and thresholds.
