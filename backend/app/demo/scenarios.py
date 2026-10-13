"""The three demo storylines, with dates relative to 'today' so the demo never goes stale.

  genuine  - Ravi (Telugu): rear-ended at a signal. Clean, covered, fast-track.
  partial  - Priya (Hindi): parking scrape, Zero-Dep add-on, phone bill excluded.
  fraud    - Arjun (English): reused photo from another claim, tampered invoice
             dated before the incident, policy bought 4 days earlier.

`offline` blocks are what the scripted offline model answers when no Gemini
credentials are configured. With Gemini connected they are ignored.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta


def _d(x: date) -> str:
    return x.isoformat()


def _bill_date(x: date) -> str:
    return x.strftime("%d-%m-%Y")


def build(today: date) -> dict[str, dict]:
    g_incident = today - timedelta(days=2)
    p_incident = today - timedelta(days=1)
    f_incident = today - timedelta(days=3)
    history_date = today - timedelta(days=212)

    genuine = {
        "key": "genuine",
        "title": "Rear-ended at a signal",
        "blurb": "A clean, covered claim that qualifies for fast-track.",
        "policy": {
            "policy_number": "SGI-PC-25-118204",
            "holder_name": "Ravi Kumar Reddy",
            "first_name": "Ravi",
            "phone": "+91 98490 21734",
            "phone_masked": "+91 ••••• •1734",
            "address_masked": "Kondapur, Hyderabad 5000••",
            "city": "Hyderabad",
            "language": "te",
            "language_name": "Telugu",
            "customer_since": "2021",
            "vehicle": {
                "registration": "TS 09 EK 4471",
                "make_model": "Hyundai i20 Asta 1.2",
                "year": 2021,
                "registration_date": "2021-08-14",
                "segment": "hatchback",
                "cc": 1197,
                "fuel": "Petrol",
                "colour": "Fiery Red",
                "chassis_masked": "MALBB51BLMM••••82",
            },
            "idv": 620000,
            "start_date": _d(today - timedelta(days=327)),
            "end_date": _d(today - timedelta(days=327) + timedelta(days=364)),
            "addons": ["Roadside Assistance"],
            "ncb_pct": 25,
            "premium": 14862,
        },
        "incident": {"date": _d(g_incident), "time": "18:35", "location": "Gachibowli flyover signal, Hyderabad"},
        "statement": (
            "మొన్న సాయంత్రం సుమారు ఆరున్నర గంటలకు గచ్చిబౌలి ఫ్లైఓవర్ సిగ్నల్ దగ్గర నా కారు ఆగి ఉంది. "
            "వెనుక నుంచి వచ్చిన ఒక కారు నా కారును ఢీకొట్టింది. వెనుక బంపర్ పగిలిపోయింది, ఎడమ వైపు టెయిల్ లైట్ కూడా పగిలింది. "
            "ఎవరికీ గాయాలు కాలేదు. ఆ డ్రైవర్ తన నంబర్ 98480 12345 ఇచ్చి వెళ్ళిపోయాడు. "
            "కారును కొండాపూర్‌లోని శ్రీ సాయి మోటార్ వర్క్స్‌కు తీసుకెళ్లాను, వాళ్ళు ఎస్టిమేట్ ఇచ్చారు."
        ),
        "statement_english": (
            "The day before yesterday at around 6:30 in the evening my car was stopped at the Gachibowli flyover signal. "
            "A car coming from behind hit my car. The rear bumper is broken and the left tail light is also broken. "
            "Nobody was injured. The other driver gave me his number [phone ••••2345] and left. "
            "I took the car to Sri Sai Motor Works in Kondapur and they gave an estimate."
        ),
        "photos": [
            {"name": "rear_view.jpg", "render": "rear", "color": (178, 24, 30), "plate": "TS 09 EK 4471", "side": "left", "seed": 4,
             "taken": datetime.combine(g_incident, time(18, 52))},
            {"name": "rear_left_closeup.jpg", "render": "crop", "of": 0, "box": (0.15, 0.45, 0.45, 0.80),
             "taken": datetime.combine(g_incident, time(18, 53))},
        ],
        "bills": [
            {
                "name": "workshop_estimate.jpg",
                "vendor": "Sri Sai Motor Works",
                "address": "Plot 22, Botanical Garden Road, Kondapur\nHyderabad, Telangana 500084",
                "phone": "040-2311 4420",
                "gstin": "36AAKFS0000A1Z2",
                "title": "ESTIMATE",
                "number": f"SSMW/EST/{today.year}/1187",
                "date": _bill_date(g_incident + timedelta(days=1)),
                "customer": "Ravi Kumar Reddy",
                "vehicle": "TS 09 EK 4471",
                "model": "Hyundai i20 Asta 1.2",
                "job_note": "Job: rear-end collision repair",
                "items": [
                    ("Rear bumper - genuine part", "8708", 1, 6350),
                    ("Tail lamp assembly LH", "8512", 1, 3480),
                    ("Removal & refitting labour", "9987", 1, 1850),
                    ("Painting - rear bumper", "9987", 1, 4200),
                    ("Consumables", "9987", 1, 380),
                ],
                "terms": ["Estimate valid for 15 days", "Final bill subject to insurance survey"],
                "accent": (14, 90, 70),
                "stamp_color": (30, 80, 150),
            }
        ],
    }

    partial = {
        "key": "partial",
        "title": "Parking scrape + phone",
        "blurb": "Zero-Dep add-on; the phone bill is excluded.",
        "policy": {
            "policy_number": "SGI-PC-26-163390",
            "holder_name": "Priya Sharma",
            "first_name": "Priya",
            "phone": "+91 99088 45120",
            "phone_masked": "+91 ••••• •5120",
            "address_masked": "Madhapur, Hyderabad 5000••",
            "city": "Hyderabad",
            "language": "hi",
            "language_name": "Hindi",
            "customer_since": "2023",
            "vehicle": {
                "registration": "TS 07 GR 8812",
                "make_model": "Maruti Suzuki Swift ZXi",
                "year": 2023,
                "registration_date": "2023-02-10",
                "segment": "hatchback",
                "cc": 1197,
                "fuel": "Petrol",
                "colour": "Midnight Blue",
                "chassis_masked": "MA3EWB62SPA••••17",
            },
            "idv": 580000,
            "start_date": _d(today - timedelta(days=212)),
            "end_date": _d(today - timedelta(days=212) + timedelta(days=364)),
            "addons": ["Zero Depreciation", "Roadside Assistance"],
            "ncb_pct": 20,
            "premium": 16390,
        },
        "incident": {"date": _d(p_incident), "time": "09:15", "location": "Basement parking, Inorbit Mall, Madhapur"},
        "statement": (
            "कल सुबह करीब सवा नौ बजे इनॉर्बिट मॉल की बेसमेंट पार्किंग में गाड़ी मोड़ते समय बाईं तरफ़ एक खंभे से रगड़ लग गई। "
            "आगे का बायाँ दरवाज़ा और पीछे का बायाँ दरवाज़ा पिचक गए हैं और बायाँ साइड मिरर टूट गया है। "
            "झटके से मेरा मोबाइल फ़ोन भी गिरकर टूट गया, उसका बिल भी लगा दिया है। कृपया दोनों का क्लेम कर दीजिए। "
            "मेरा आधार नंबर 3412 7788 9015 है।"
        ),
        "statement_english": (
            "Yesterday morning at about 9:15, while turning the car in the Inorbit Mall basement parking, the left side scraped "
            "against a pillar. The front left door and the rear left door are dented and the left side mirror is broken. "
            "My mobile phone also fell and broke in the jolt; I have attached its bill too. Please process the claim for both. "
            "My Aadhaar number is [Aadhaar ••••9015]."
        ),
        "photos": [
            {"name": "left_side.jpg", "render": "side", "color": (30, 84, 170), "seed": 5,
             "taken": datetime.combine(p_incident, time(9, 24))},
            {"name": "mirror_closeup.jpg", "render": "crop", "of": 0, "box": (0.15, 0.42, 0.45, 0.72),
             "taken": datetime.combine(p_incident, time(9, 25))},
        ],
        "bills": [
            {
                "name": "body_shop_estimate.jpg",
                "vendor": "Varun Car Care",
                "address": "8-2-14, Hitech City Road, Madhapur\nHyderabad, Telangana 500081",
                "phone": "040-4012 8890",
                "gstin": "36AADFV0000B1Z7",
                "title": "ESTIMATE",
                "number": f"VCC/{today.year}/EST-0442",
                "date": _bill_date(p_incident),
                "customer": "Priya Sharma",
                "vehicle": "TS 07 GR 8812",
                "model": "Maruti Suzuki Swift ZXi",
                "job_note": "Job: LH side scrape, ORVM broken",
                "items": [
                    ("Front door LH - denting & painting", "9987", 1, 6800),
                    ("Rear door LH - denting & painting", "9987", 1, 6200),
                    ("ORVM assembly LH (electric)", "8708", 1, 3950),
                    ("ORVM fitting labour", "9987", 1, 450),
                    ("Consumables", "9987", 1, 400),
                ],
                "terms": ["Parts subject to availability"],
                "accent": (120, 40, 40),
                "stamp_color": (120, 40, 40),
            },
            {
                "name": "phone_repair_bill.jpg",
                "vendor": "iCare Mobile Service",
                "address": "Shop 6, Cyber Towers Road, Madhapur\nHyderabad, Telangana 500081",
                "phone": "040-6644 2210",
                "gstin": "36AAGCI0000C1Z4",
                "title": "TAX INVOICE",
                "number": f"ICM/{today.year}/7781",
                "date": _bill_date(p_incident),
                "customer": "Priya Sharma",
                "vehicle": "-",
                "model": "Smartphone repair",
                "items": [
                    ("Display assembly replacement - smartphone", "8517", 1, 15000),
                    ("Service charge", "9987", 1, 678),
                ],
                "accent": (60, 60, 70),
                "stamp_color": (60, 60, 140),
            },
        ],
    }

    fraud = {
        "key": "fraud",
        "title": "Too good to be true",
        "blurb": "Reused photo, edited invoice, brand-new policy.",
        "policy": {
            "policy_number": "SGI-PC-26-204517",
            "holder_name": "Arjun Mehta",
            "first_name": "Arjun",
            "phone": "+91 90000 77812",
            "phone_masked": "+91 ••••• •7812",
            "address_masked": "Narsingi, Hyderabad 5000••",
            "city": "Hyderabad",
            "language": "en",
            "language_name": "English",
            "customer_since": str(today.year),
            "vehicle": {
                "registration": "TS 08 HY 2290",
                "make_model": "Honda City VX CVT",
                "year": 2019,
                "registration_date": "2019-06-21",
                "segment": "sedan",
                "cc": 1498,
                "fuel": "Petrol",
                "colour": "Lunar Silver",
                "chassis_masked": "MAKGM6530KN••••40",
            },
            "idv": 710000,
            "start_date": _d(f_incident - timedelta(days=4)),
            "end_date": _d(f_incident - timedelta(days=4) + timedelta(days=364)),
            "addons": [],
            "ncb_pct": 0,
            "premium": 18904,
        },
        "incident": {"date": _d(f_incident), "time": "22:15", "location": "ORR service road near Narsingi, Hyderabad"},
        "statement": (
            "On the night of the incident around 10:15 pm I was driving on the ORR service road near Narsingi when a truck in front "
            "braked suddenly and I crashed into it. The whole front of my car is smashed - front bumper, bonnet, both headlights and "
            "the radiator. Nobody was hurt. The garage has already repaired it and given me the final bill of Rs 98,196. "
            "Please settle it quickly, I need the money urgently. You can reach me on 9000077812."
        ),
        "statement_english": None,
        "photos": [
            # both photos are re-saved copies of a photo from someone else's claim 7 months ago
            {"name": "IMG_front_damage.jpg", "render": "reuse", "of_history": True, "variant": {"crop": 0.06, "brightness": 1.08}},
            {"name": "IMG_night.jpg", "render": "reuse", "of_history": True, "variant": {"crop": 0.08, "darken": True}},
        ],
        "history_photo": {"render": "rear", "color": (196, 198, 202), "plate": "TS 10 FB 7782", "side": "right", "seed": 9,
                          "taken": datetime.combine(history_date, time(17, 5))},
        "bills": [
            {
                "name": "final_invoice.jpg",
                "vendor": "Speed Auto Works",
                "address": "Plot 14, Service Road, Narsingi\nHyderabad, Telangana 500089",
                "phone": "040-2955 1180",
                "gstin": "36AAJFS0000D1Z1",
                "title": "TAX INVOICE",
                "number": f"SAW/{today.year}/0917",
                "date": _bill_date(f_incident - timedelta(days=2)),
                "customer": "Arjun Mehta",
                "vehicle": "TS 08 HY 2290",
                "model": "Honda City VX CVT",
                "items": [
                    ("Front bumper (OEM)", "8708", 1, 9800),
                    ("Bonnet", "8708", 1, 15200),
                    ("Headlamp assembly LH", "8512", 1, 11500),
                    ("Headlamp assembly RH", "8512", 1, 11500),
                    ("Radiator", "8708", 1, 10600),
                    ("Denting & fitting labour", "9987", 1, 6400),
                    ("Painting (3 panels)", "9987", 1, 7200),
                ],
                "tamper_total": 98196,
                "accent": (24, 76, 140),
                "stamp_color": (150, 30, 40),
            }
        ],
    }

    # ------------------------------------------------------------------
    # Scripted answers for offline mode (no Gemini credentials)
    # ------------------------------------------------------------------
    genuine["offline"] = {
        "intake": {
            "language": "Telugu", "language_code": "te",
            "statement_english": genuine["statement_english"],
            "incident_date": _d(g_incident), "incident_time": "18:30",
            "incident_location": "Gachibowli flyover signal, Hyderabad",
            "incident_type": "collision",
            "incident_summary": "The insured car was stationary at a traffic signal when another car hit it from behind. The rear bumper and left tail lamp were damaged; no injuries.",
            "vehicle_registration": "TS 09 EK 4471", "vehicle_make_model": "Hyundai i20",
            "third_party_involved": True, "injuries_reported": False, "police_report_mentioned": False,
            "documents": [
                {"file_index": 1, "file_name": "rear_view.jpg", "doc_type": "damage_photo", "summary": "Rear of a red hatchback TS 09 EK 4471 with a cracked, pushed-in bumper and broken left tail lamp."},
                {"file_index": 2, "file_name": "rear_left_closeup.jpg", "doc_type": "damage_photo", "summary": "Close-up of the rear-left corner showing bumper cracks and the broken tail lamp."},
                {"file_index": 3, "file_name": "workshop_estimate.jpg", "doc_type": "repair_estimate", "summary": "Sri Sai Motor Works repair estimate for bumper and tail lamp, total Rs 19,187."},
            ],
            "bills": [{
                "file_index": 3, "vendor": "Sri Sai Motor Works", "bill_number": f"SSMW/EST/{today.year}/1187",
                "bill_date": _d(g_incident + timedelta(days=1)), "kind": "estimate", "for_vehicle": True,
                "line_items": [
                    {"description": "Rear bumper - genuine part", "amount": 6350},
                    {"description": "Tail lamp assembly LH", "amount": 3480},
                    {"description": "Removal & refitting labour", "amount": 1850},
                    {"description": "Painting - rear bumper", "amount": 4200},
                    {"description": "Consumables", "amount": 380},
                ],
                "subtotal": 16260, "tax": 2926.8, "total": 19187,
            }],
            "claimed_amount_inr": 19187, "non_vehicle_items_claimed": [],
            "missing_information": ["Registration number of the vehicle that hit the insured car"],
        },
        "coverage": {
            "policy_active_on_incident_date": True, "verdict": "covered",
            "items": [
                {"item": "Rear bumper replacement", "status": "covered", "reason": "Accidental collision damage to the insured vehicle.", "clause_ref": "Sec I.1", "clause_quote": "(f) by accidental external means"},
                {"item": "Left tail lamp replacement", "status": "covered", "reason": "Damaged in the same collision.", "clause_ref": "Sec I.1", "clause_quote": "(f) by accidental external means"},
                {"item": "Plastic parts (bumper, lamp)", "status": "limited", "reason": "No Zero Depreciation add-on, so 50% depreciation applies to plastic parts.", "clause_ref": "Sec I.2", "clause_quote": "rubber, nylon and plastic parts, tyres and tubes, batteries and air bags - 50%"},
            ],
            "depreciation_applies": True, "compulsory_deductible_inr": 1000,
            "conditions_to_verify": ["Collect the third-party vehicle number for a possible recovery claim"],
            "summary": "Policy was in force on the incident date and a rear-end collision is covered under Section I. Standard depreciation and the Rs 1,000 deductible apply.",
        },
        "damage": {
            "photos": [
                {"file_index": 1, "view": "rear", "quality": "good", "notes": "Plate TS 09 EK 4471 visible and matches the policy."},
                {"file_index": 2, "view": "rear-left close-up", "quality": "good", "notes": "Clear view of bumper cracks and tail lamp."},
            ],
            "damaged_parts": [
                {"part_code": "rear_bumper", "part_name": "Rear bumper", "file_index": 1, "box_2d": [650, 185, 760, 355], "severity": "moderate", "action": "replace", "confidence": 0.93,
                 "observation": "Bumper cracked and pushed inward at the left corner, gap opened under the tailgate."},
                {"part_code": "tail_lamp_left", "part_name": "Tail lamp (left)", "file_index": 1, "box_2d": [490, 205, 595, 318], "severity": "severe", "action": "replace", "confidence": 0.95,
                 "observation": "Lens shattered with a missing section."},
            ],
            "impact_direction": "rear", "consistent_with_statement": True,
            "consistency_notes": "Damage is concentrated on the rear-left, which fits a car being hit from behind while stopped.",
            "possible_pre_existing_damage": [],
            "summary": "Fresh rear-left impact: bumper needs replacement and the left tail lamp is broken.",
        },
        "fraud": {
            "risk_score": 6, "risk_level": "low", "red_flags": [], "document_tampering_suspected": False,
            "recommended_checks": ["Optional: note the third-party vehicle for recovery"],
            "summary": "All automated checks passed: original photos taken at the time of the incident, estimate arithmetic reconciles, policy in force for over 10 months.",
        },
        "decision": {
            "recommendation": "approve", "confidence": 93, "fast_track_eligible": True, "customer_language": "Telugu",
            "headline": "Covered rear-end collision; damage matches the story. Approve after depreciation.",
            "rationale": [
                {"point": "Policy active and collision is covered under Sec I.1.", "source": "coverage", "impact": "supports"},
                {"point": "Photos show fresh rear-left damage consistent with being hit from behind.", "source": "damage", "impact": "supports"},
                {"point": "All 8 fraud checks passed; photos are original and dated at the incident.", "source": "fraud", "impact": "supports"},
                {"point": "50% depreciation on plastic parts reduces the payout (no Zero-Dep add-on).", "source": "estimate", "impact": "neutral"},
            ],
            "next_steps": ["Approve and send cashless authorisation to Sri Sai Motor Works", "Optional: pursue recovery from the third-party driver"],
            "customer_message_english": "Hi Ravi, we've reviewed your claim for the rear bumper and left tail lamp of your Hyundai i20. Your policy covers this accident. Based on your photos and the workshop estimate, the payable amount is {payout}. This is after the standard 50% depreciation on plastic parts (your policy doesn't include the Zero Depreciation add-on) and the Rs 1,000 compulsory deductible. A claims officer will confirm shortly, and you can start the repair once it's approved.",
            "customer_message_local": "నమస్తే రవి గారు, మీ హ్యుందాయ్ i20 వెనుక బంపర్ మరియు ఎడమ టెయిల్ లైట్ క్లెయిమ్‌ను మేము పరిశీలించాము. ఈ ప్రమాదం మీ పాలసీ కింద కవర్ అవుతుంది. మీ ఫోటోలు మరియు వర్క్‌షాప్ ఎస్టిమేట్ ఆధారంగా చెల్లించదగిన మొత్తం {payout}. ప్లాస్టిక్ భాగాలపై సాధారణ 50% డిప్రిసియేషన్ (మీ పాలసీలో జీరో డిప్రిసియేషన్ యాడ్-ఆన్ లేదు) మరియు ₹1,000 తప్పనిసరి డిడక్టిబుల్ తీసివేసిన తర్వాత ఈ మొత్తం లెక్కించబడింది. క్లెయిమ్ అధికారి త్వరలో నిర్ధారిస్తారు; ఆమోదం వచ్చిన తర్వాత మీరు రిపేర్ మొదలుపెట్టవచ్చు.",
        },
    }

    partial["offline"] = {
        "intake": {
            "language": "Hindi", "language_code": "hi",
            "statement_english": partial["statement_english"],
            "incident_date": _d(p_incident), "incident_time": "09:15",
            "incident_location": "Basement parking, Inorbit Mall, Madhapur",
            "incident_type": "collision",
            "incident_summary": "While turning in a basement car park the left side of the car scraped a concrete pillar. Both left doors were dented and the left mirror broke; the claimant also reports a broken phone.",
            "vehicle_registration": "TS 07 GR 8812", "vehicle_make_model": "Maruti Suzuki Swift",
            "third_party_involved": False, "injuries_reported": False, "police_report_mentioned": False,
            "documents": [
                {"file_index": 1, "file_name": "left_side.jpg", "doc_type": "damage_photo", "summary": "Left side of a blue hatchback with a long scrape across both doors and a hanging mirror."},
                {"file_index": 2, "file_name": "mirror_closeup.jpg", "doc_type": "damage_photo", "summary": "Close-up of the broken left mirror and the front door scrape."},
                {"file_index": 3, "file_name": "body_shop_estimate.jpg", "doc_type": "repair_estimate", "summary": "Varun Car Care estimate for both left doors and the mirror, total Rs 21,004."},
                {"file_index": 4, "file_name": "phone_repair_bill.jpg", "doc_type": "repair_bill", "summary": "iCare Mobile Service invoice for a smartphone display replacement, Rs 18,500."},
            ],
            "bills": [
                {"file_index": 3, "vendor": "Varun Car Care", "bill_number": f"VCC/{today.year}/EST-0442", "bill_date": _d(p_incident), "kind": "estimate", "for_vehicle": True,
                 "line_items": [
                     {"description": "Front door LH - denting & painting", "amount": 6800},
                     {"description": "Rear door LH - denting & painting", "amount": 6200},
                     {"description": "ORVM assembly LH (electric)", "amount": 3950},
                     {"description": "ORVM fitting labour", "amount": 450},
                     {"description": "Consumables", "amount": 400},
                 ], "subtotal": 17800, "tax": 3204, "total": 21004},
                {"file_index": 4, "vendor": "iCare Mobile Service", "bill_number": f"ICM/{today.year}/7781", "bill_date": _d(p_incident), "kind": "invoice", "for_vehicle": False,
                 "line_items": [
                     {"description": "Display assembly replacement - smartphone", "amount": 15000},
                     {"description": "Service charge", "amount": 678},
                 ], "subtotal": 15678, "tax": 2822.04, "total": 18500},
            ],
            "claimed_amount_inr": 39504, "non_vehicle_items_claimed": ["Mobile phone (display replacement, Rs 18,500)"],
            "missing_information": [],
        },
        "coverage": {
            "policy_active_on_incident_date": True, "verdict": "partially_covered",
            "items": [
                {"item": "Front and rear left doors - denting and painting", "status": "covered", "reason": "Accidental damage from scraping a pillar.", "clause_ref": "Sec I.1", "clause_quote": "(f) by accidental external means"},
                {"item": "Left mirror (ORVM) replacement", "status": "covered", "reason": "Damaged in the same incident.", "clause_ref": "Sec I.1", "clause_quote": "(f) by accidental external means"},
                {"item": "Depreciation on replaced parts", "status": "covered", "reason": "Zero Depreciation add-on is in force; no depreciation is deducted.", "clause_ref": "Add-on A1", "clause_quote": "claims under Section I are paid without deduction for depreciation on parts replaced"},
                {"item": "Mobile phone display repair (Rs 18,500)", "status": "excluded", "reason": "Personal belongings and mobile phones carried in the car are not covered.", "clause_ref": "Excl I.4(d)", "clause_quote": "loss of or damage to personal belongings, mobile phones, electronic devices"},
            ],
            "depreciation_applies": False, "compulsory_deductible_inr": 1000,
            "conditions_to_verify": [],
            "summary": "Vehicle damage is covered with no depreciation thanks to the Zero-Dep add-on. The phone repair is excluded under Excl I.4(d).",
        },
        "damage": {
            "photos": [
                {"file_index": 1, "view": "left side", "quality": "good", "notes": "Whole left profile visible in a basement car park; pillar in frame."},
                {"file_index": 2, "view": "left mirror close-up", "quality": "good", "notes": "Mirror housing hanging, glass cracked."},
            ],
            "damaged_parts": [
                {"part_code": "door_front_left", "part_name": "Front door (left)", "file_index": 1, "box_2d": [560, 330, 650, 540], "severity": "moderate", "action": "repair", "confidence": 0.9,
                 "observation": "Long horizontal scrape with a shallow dent across the lower half of the door."},
                {"part_code": "door_rear_left", "part_name": "Rear door (left)", "file_index": 1, "box_2d": [565, 535, 650, 665], "severity": "moderate", "action": "repair", "confidence": 0.88,
                 "observation": "Scrape continues onto the rear door with a dent near the handle."},
                {"part_code": "side_mirror_left", "part_name": "Side mirror (left)", "file_index": 2, "box_2d": [310, 410, 600, 595], "severity": "severe", "action": "replace", "confidence": 0.94,
                 "observation": "Mirror housing knocked down and hanging by its wire; glass cracked."},
            ],
            "impact_direction": "left", "consistent_with_statement": True,
            "consistency_notes": "A sideways scrape along both left doors and a broken mirror is what a pillar strike while turning looks like.",
            "possible_pre_existing_damage": [],
            "summary": "Left-side scrape across both doors (repairable) and a broken left mirror (replace).",
        },
        "fraud": {
            "risk_score": 14, "risk_level": "low",
            "red_flags": [{"title": "Non-vehicle item added to a motor claim", "severity": "low", "evidence": "A smartphone repair invoice (Rs 18,500) is attached to an own-damage car claim.", "source": "statement"}],
            "document_tampering_suspected": False,
            "recommended_checks": ["Explain the phone exclusion to the customer"],
            "summary": "No fraud indicators beyond an excluded personal item. Photos are original and bills reconcile.",
        },
        "decision": {
            "recommendation": "approve_partial", "confidence": 91, "fast_track_eligible": True, "customer_language": "Hindi",
            "headline": "Covered parking scrape with Zero-Dep; exclude the Rs 18,500 phone bill.",
            "rationale": [
                {"point": "Door and mirror damage is accidental and covered under Sec I.1.", "source": "coverage", "impact": "supports"},
                {"point": "Zero Depreciation add-on means no depreciation cut.", "source": "policy", "impact": "supports"},
                {"point": "Mobile phone is a personal belonging, excluded by Excl I.4(d).", "source": "coverage", "impact": "against"},
                {"point": "Photos match the story; low fraud risk.", "source": "fraud", "impact": "supports"},
            ],
            "next_steps": ["Approve vehicle repairs with Varun Car Care", "Send the customer the phone exclusion explanation"],
            "customer_message_english": "Hi Priya, we've reviewed your claim. The damage to your Swift's left front door, left rear door and left mirror is covered, and because you have the Zero Depreciation add-on there's no depreciation cut. The estimated payable amount is {payout} after the Rs 1,000 compulsory deductible. Your phone repair isn't covered under the car policy, because personal belongings are excluded (Exclusion I.4(d)). A claims officer will confirm shortly.",
            "customer_message_local": "नमस्ते प्रिया जी, हमने आपका क्लेम देख लिया है। आपकी स्विफ्ट के बाएँ आगे के दरवाज़े, बाएँ पीछे के दरवाज़े और बाएँ साइड मिरर का नुकसान कवर है, और आपके पास ज़ीरो डेप्रिसिएशन ऐड-ऑन है, इसलिए कोई डेप्रिसिएशन नहीं कटेगा। ₹1,000 अनिवार्य डिडक्टिबल के बाद अनुमानित देय राशि {payout} है। आपके मोबाइल फ़ोन की मरम्मत कार पॉलिसी में कवर नहीं होती, क्योंकि निजी सामान इसमें शामिल नहीं है (एक्सक्लूज़न I.4(d))। क्लेम अधिकारी जल्द ही इसकी पुष्टि करेंगे।",
        },
    }

    fraud["offline"] = {
        "intake": {
            "language": "English", "language_code": "en",
            "statement_english": fraud["statement"].replace("9000077812", "[phone ••••7812]"),
            "incident_date": _d(f_incident), "incident_time": "22:15",
            "incident_location": "ORR service road near Narsingi, Hyderabad",
            "incident_type": "collision",
            "incident_summary": "The claimant says the car hit a braking truck at night, damaging the entire front end. The car has already been repaired and a final invoice submitted.",
            "vehicle_registration": "TS 08 HY 2290", "vehicle_make_model": "Honda City",
            "third_party_involved": True, "injuries_reported": False, "police_report_mentioned": False,
            "documents": [
                {"file_index": 1, "file_name": "IMG_front_damage.jpg", "doc_type": "damage_photo", "summary": "Rear view of a silver hatchback with right-side bumper and tail lamp damage; plate reads TS 10 FB 7782."},
                {"file_index": 2, "file_name": "IMG_night.jpg", "doc_type": "damage_photo", "summary": "Dark, blurry close-up of the same rear-right damage."},
                {"file_index": 3, "file_name": "final_invoice.jpg", "doc_type": "repair_bill", "summary": "Speed Auto Works tax invoice for front-end parts and labour, grand total Rs 98,196."},
            ],
            "bills": [{
                "file_index": 3, "vendor": "Speed Auto Works", "bill_number": f"SAW/{today.year}/0917",
                "bill_date": _d(f_incident - timedelta(days=2)), "kind": "invoice", "for_vehicle": True,
                "line_items": [
                    {"description": "Front bumper (OEM)", "amount": 9800},
                    {"description": "Bonnet", "amount": 15200},
                    {"description": "Headlamp assembly LH", "amount": 11500},
                    {"description": "Headlamp assembly RH", "amount": 11500},
                    {"description": "Radiator", "amount": 10600},
                    {"description": "Denting & fitting labour", "amount": 6400},
                    {"description": "Painting (3 panels)", "amount": 7200},
                ],
                "subtotal": 72200, "tax": 12996, "total": 98196,
            }],
            "claimed_amount_inr": 98196, "non_vehicle_items_claimed": [],
            "missing_information": ["Photos of the front of the vehicle", "Truck registration or police report", "Pre-repair survey"],
        },
        "coverage": {
            "policy_active_on_incident_date": True, "verdict": "needs_review",
            "items": [
                {"item": "Front-end collision repairs", "status": "covered", "reason": "Accidental collision is an insured peril, subject to verification.", "clause_ref": "Sec I.1", "clause_quote": "(f) by accidental external means"},
                {"item": "Repairs completed before survey", "status": "limited", "reason": "The car was repaired before the insurer could inspect it.", "clause_ref": "Cond 2", "clause_quote": "No repair shall be undertaken without the written consent of the Company"},
                {"item": "Depreciation", "status": "limited", "reason": "No Zero-Dep add-on; 7-year-old vehicle.", "clause_ref": "Sec I.2", "clause_quote": "5 to 10 years - 40%"},
            ],
            "depreciation_applies": True, "compulsory_deductible_inr": 1000,
            "conditions_to_verify": ["Physical inspection of TS 08 HY 2290", "Original invoice and replaced parts", "Police report or truck details"],
            "summary": "The peril is insured in principle, but repairs were done without the insurer's consent and the incident came 4 days after cover began. Needs verification before any payout.",
        },
        "damage": {
            "photos": [
                {"file_index": 1, "view": "rear-right", "quality": "good", "notes": "Number plate reads TS 10 FB 7782 - not the insured vehicle TS 08 HY 2290. The car is a silver hatchback, not a Honda City sedan."},
                {"file_index": 2, "view": "rear-right close-up", "quality": "dark", "notes": "Very dark and blurred; appears to be the same scene as photo 1."},
            ],
            "damaged_parts": [
                {"part_code": "rear_bumper", "part_name": "Rear bumper", "file_index": 1, "box_2d": [655, 645, 760, 820], "severity": "moderate", "action": "replace", "confidence": 0.86,
                 "observation": "Rear bumper cracked at the right corner."},
                {"part_code": "tail_lamp_right", "part_name": "Tail lamp (right)", "file_index": 1, "box_2d": [480, 680, 590, 800], "severity": "severe", "action": "replace", "confidence": 0.9,
                 "observation": "Right tail lamp shattered."},
            ],
            "impact_direction": "rear", "consistent_with_statement": False,
            "consistency_notes": "The statement describes a frontal crash into a truck (bumper, bonnet, both headlamps, radiator), but the photos only show rear-right damage on a different vehicle. No photo shows the front of the insured car.",
            "possible_pre_existing_damage": [],
            "summary": "Photos show rear-right damage on a silver hatchback with a different number plate; nothing supports the claimed front-end damage.",
        },
        "fraud": {
            "risk_score": 94, "risk_level": "high",
            "red_flags": [
                {"title": "Photo reused from another claim", "severity": "high", "evidence": "Both photos are near-identical copies of a photo submitted in claim CLM-HIST-0412 seven months ago by a different policyholder.", "source": "photo_forensics"},
                {"title": "Photo taken months before the incident", "severity": "high", "evidence": "Camera timestamp predates the reported incident by about seven months.", "source": "photo_forensics"},
                {"title": "Invoice total appears altered", "severity": "high", "evidence": "The grand total sits on a white-out patch in a different typeface; it reads Rs 98,196 while the amount in words and the line-item maths give Rs 85,196.", "source": "document_forensics"},
                {"title": "Invoice dated before the incident", "severity": "high", "evidence": "Final invoice is dated two days before the reported crash.", "source": "billing"},
                {"title": "Claim 4 days after policy purchase", "severity": "high", "evidence": "Cover began 4 days before the incident.", "source": "policy_timing"},
                {"title": "Repeat claimant", "severity": "medium", "evidence": "Two motor claims in the last 12 months on the claimant's record.", "source": "claim_history"},
                {"title": "Pressure and repairs before survey", "severity": "medium", "evidence": "Claimant pushes for urgent settlement and says the car was already repaired, so damage can't be inspected.", "source": "statement"},
            ],
            "document_tampering_suspected": True,
            "recommended_checks": ["Physical inspection of TS 08 HY 2290", "Call Speed Auto Works to verify invoice SAW/0917", "Ask for a police report or truck registration", "Refer to the Special Investigation Unit (SIU)"],
            "summary": "Multiple independent high-severity indicators: reused photos from another claim, an altered invoice dated before the incident, and a claim days after buying cover.",
        },
        "decision": {
            "recommendation": "investigate", "confidence": 95, "fast_track_eligible": False, "customer_language": "English",
            "headline": "Hold: photos reused from another claim and invoice altered and dated before the incident.",
            "rationale": [
                {"point": "Photos match claim CLM-HIST-0412 and show a different car (TS 10 FB 7782).", "source": "fraud", "impact": "against"},
                {"point": "Damage shown is rear-right; the story is a frontal crash.", "source": "damage", "impact": "against"},
                {"point": "Invoice total inflated by Rs 13,000 and dated before the incident.", "source": "fraud", "impact": "against"},
                {"point": "Repairs done without survey, breaching Cond 2.", "source": "coverage", "impact": "against"},
            ],
            "next_steps": ["Refer to SIU", "Arrange a physical survey", "Verify the invoice directly with the workshop", "Do not release payment until verified"],
            "customer_message_english": "Hi Arjun, thank you for reporting your claim. We need to verify a few details before we can go ahead, so a claims officer will contact you within one working day to arrange an inspection of your car. Please keep the replaced parts and the original invoice with you. We'll keep you posted here.",
            "customer_message_local": "Hi Arjun, thank you for reporting your claim. We need to verify a few details before we can go ahead, so a claims officer will contact you within one working day to arrange an inspection of your car. Please keep the replaced parts and the original invoice with you. We'll keep you posted here.",
        },
    }

    return {"genuine": genuine, "partial": partial, "fraud": fraud}


def history_claims(today: date) -> list[dict]:
    """Past (settled) claims used for duplicate-photo checks, claimant history and the insights baseline."""
    rows = [
        # id, holder, vehicle, reg, days_ago, type, claimed, paid, status, days_to_settle
        ("CLM-HIST-0412", "Vikram Rao", "Maruti Swift VXi", "TS 10 FB 7782", 212, "collision", 24800, 15240, "settled", 9),
        ("CLM-HIST-0388", "Arjun Mehta", "Hyundai Verna SX", "TS 08 GA 1123", 150, "collision", 61400, 0, "withdrawn", 14),
        ("CLM-HIST-0301", "Arjun Mehta", "Hyundai Verna SX", "TS 08 GA 1123", 290, "theft", 38000, 0, "rejected", 21),
        ("CLM-HIST-0455", "Lakshmi Narayana", "Tata Nexon XZ+", "TS 11 EH 5520", 95, "flood", 72500, 51800, "settled", 12),
        ("CLM-HIST-0467", "Mohammed Irfan", "Toyota Innova Crysta", "TS 13 UB 0981", 80, "collision", 45200, 38900, "settled", 8),
        ("CLM-HIST-0472", "Sneha Kulkarni", "Kia Seltos HTX", "TS 07 FM 3345", 71, "vandalism", 12800, 9600, "settled", 6),
        ("CLM-HIST-0480", "Rahul Verma", "Maruti Baleno Alpha", "TS 09 FT 7710", 64, "collision", 31900, 22150, "settled", 10),
        ("CLM-HIST-0491", "Anitha Reddy", "Honda Amaze VX", "TS 12 EP 4422", 52, "collision", 18700, 13900, "settled", 7),
        ("CLM-HIST-0503", "Karthik Iyer", "Mahindra XUV700 AX5", "TS 08 GE 9087", 40, "collision", 88300, 70100, "settled", 15),
        ("CLM-HIST-0511", "Farah Khan", "Hyundai Creta SX", "TS 09 GB 6612", 33, "fire", 15600, 0, "rejected", 11),
        ("CLM-HIST-0519", "Venkatesh Babu", "Tata Punch Creative", "TS 15 EY 2209", 21, "collision", 9800, 7450, "settled", 6),
        ("CLM-HIST-0526", "Deepa Menon", "Maruti Dzire ZXi", "TS 10 EK 3381", 12, "collision", 26400, 19800, "settled", 8),
    ]
    out = []
    for cid, holder, vehicle, reg, days_ago, typ, claimed, paid, status, settle in rows:
        inc = today - timedelta(days=days_ago)
        first, *rest = holder.split()
        out.append({
            "id": cid,
            "holder_name": holder,
            "claimant_masked": f"{first} {rest[-1][0]}." if rest else first,
            "vehicle": vehicle,
            "registration": reg,
            "incident_date": inc.isoformat(),
            "reported_date": (inc + timedelta(days=1)).isoformat(),
            "type": typ,
            "amount_claimed": claimed,
            "amount_paid": paid,
            "status": status,
            "days_to_settle": settle,
            "photos": [],
        })
    return out
