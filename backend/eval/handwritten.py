"""Hand-written evaluation queries — labeled by the author, NOT from an
official source. Each gold entry is a code or code-family prefix; a result
counts as correct if its code starts with any listed prefix. Families are
used where the exact code depends on detail the query doesn't give
(laterality, encounter, severity).

⚠ These labels need review by a clinician or certified coder before the
results are quoted as anything more than indicative.
"""

LABELED_BY = "author — needs clinical review"

# Everyday wording a patient (or a hurried note) might use.
LAY_TERMS: list[tuple[str, list[str]]] = [
    ("heart attack", ["I21"]),
    ("high blood pressure", ["I10"]),
    ("sugar diabetes", ["E11"]),
    ("stroke", ["I63"]),
    ("mini stroke", ["G45"]),
    ("flu", ["J10", "J11"]),
    ("common cold", ["J00"]),
    ("pink eye", ["H10"]),
    ("heartburn", ["R12"]),
    ("acid reflux", ["K21"]),
    ("kidney stones", ["N20"]),
    ("bladder infection", ["N30", "N39.0"]),
    ("low thyroid", ["E03"]),
    ("overactive thyroid", ["E05"]),
    ("broken wrist", ["S62", "S52.5", "S52.6"]),
    ("broken ankle", ["S82.5", "S82.6", "S82.8"]),
    ("chest pain", ["R07"]),
    ("shortness of breath", ["R06.0"]),
    ("stomach ache", ["R10"]),
    ("sore throat", ["J02", "R07.0"]),
    ("ear infection", ["H65", "H66"]),
    ("sinus infection", ["J01", "J32"]),
    ("nosebleed", ["R04.0"]),
    ("hives", ["L50"]),
    ("cold sore", ["B00.1"]),
    ("shingles", ["B02"]),
    ("chickenpox", ["B01"]),
    ("bed sore", ["L89"]),
    ("blood clot in the leg", ["I82.4"]),
    ("blood clot in the lung", ["I26"]),
    ("enlarged prostate", ["N40"]),
    ("fainting", ["R55"]),
    ("dizziness", ["R42"]),
    ("pins and needles", ["R20.2"]),
    ("lazy eye", ["H53.0"]),
    ("whooping cough", ["A37"]),
    ("lockjaw", ["A35"]),
    ("tennis elbow", ["M77.1"]),
    ("yellow skin", ["R17"]),
    ("hay fever", ["J30"]),
]

# Abbreviations common in clinical notes.
ABBREVIATIONS: list[tuple[str, list[str]]] = [
    ("MI", ["I21"]),
    ("HTN", ["I10"]),
    ("T2DM", ["E11"]),
    ("T1DM", ["E10"]),
    ("CHF", ["I50"]),
    ("COPD", ["J44"]),
    ("UTI", ["N39.0"]),
    ("DVT", ["I82.4"]),
    ("PE", ["I26"]),
    ("GERD", ["K21"]),
    ("CAD", ["I25.1"]),
    ("AFib", ["I48"]),
    ("CKD", ["N18"]),
    ("AKI", ["N17"]),
    ("TIA", ["G45"]),
    ("BPH", ["N40"]),
    ("OSA", ["G47.33"]),
    ("URI", ["J06"]),
    ("CAP", ["J18"]),
    ("SOB", ["R06.0"]),
    ("N/V", ["R11"]),
    ("ADHD", ["F90"]),
    ("OCD", ["F42"]),
    ("PTSD", ["F43.1"]),
    ("MDD", ["F32", "F33"]),
    ("RA", ["M05", "M06"]),
    ("OA knee", ["M17"]),
    ("IBS", ["K58"]),
    ("SLE", ["M32"]),
    ("HIV", ["B20"]),
]

# Single-diagnosis sentences in the style of an Assessment line — longer,
# noisier input closer to what Stage 0 extraction will pass to search.
NOTE_SENTENCES: list[tuple[str, list[str]]] = [
    ("Pt c/o burning on urination x3 days, UA positive for nitrites, dx acute cystitis", ["N30.0"]),
    ("Crushing substernal chest pain, troponin elevated, ST elevations in anterior leads", ["I21"]),
    ("Known type 2 diabetic, A1c 9.2, poorly controlled with hyperglycemia", ["E11.65"]),
    ("Fell from ladder, x-ray shows displaced fracture of left distal radius, initial visit", ["S52.5"]),
    ("Wheezing and productive cough, known COPD, acute exacerbation", ["J44.1"]),
    ("Sudden right-sided weakness and facial droop, CT shows ischemic infarct", ["I63"]),
    ("Fever and cough with right lower lobe consolidation on chest x-ray", ["J18"]),
    ("Blood pressure consistently 160/100 on three visits, no end-organ damage", ["I10"]),
    ("Itchy red eyes with purulent discharge bilaterally, bacterial conjunctivitis", ["H10"]),
    ("Severe epigastric pain radiating to back, lipase elevated, gallstones on ultrasound", ["K85.1"]),
    ("32 weeks pregnant, BP 150/100 with new proteinuria", ["O14"]),
    ("Child with barking cough and inspiratory stridor at night, croup", ["J05.0"]),
    ("Painful swollen first MTP joint, elevated uric acid, acute gout flare", ["M10", "M1A"]),
    ("Low hemoglobin, microcytic indices, low ferritin, iron deficiency", ["D50"]),
    ("Palpitations with irregularly irregular rhythm on ECG", ["I48"]),
    ("RLQ pain, fever, McBurney point tenderness, CT confirms acute appendicitis", ["K35"]),
    ("Chronic low back pain without radiation to legs", ["M54.5"]),
    ("Excessive worry most days for 8 months with restlessness, generalized anxiety", ["F41.1"]),
    ("Depressed mood and anhedonia for 3 weeks, first episode, moderate", ["F32.1"]),
    ("Red, warm, swollen right lower leg, cellulitis", ["L03.11"]),
]

SETS = {
    "lay_terms": LAY_TERMS,
    "abbreviations": ABBREVIATIONS,
    "note_sentences": NOTE_SENTENCES,
}
