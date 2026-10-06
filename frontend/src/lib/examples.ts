import type { EncounterCreate } from "@/lib/api/types"

/** Synthetic notes for trying the pipeline — never real patient data. */
export const EXAMPLES: { name: string; body: Omit<EncounterCreate, "encounter_id"> }[] = [
  {
    name: "Appendicitis (proposal example)",
    body: {
      patient_id: "pat_4412",
      department: "Emergency Medicine",
      soap_note:
        "S: 24-year-old with 18 hours of periumbilical pain migrating to the right lower quadrant, anorexia and nausea.\n" +
        "O: T 38.2 C, RLQ tenderness at McBurney's point with guarding. WBC 15.2. CT: inflamed appendix with localized periappendiceal fluid, no free air.\n" +
        "A: Acute appendicitis with localized peritonitis, without perforation or gangrene.\n" +
        "P: Emergency laparoscopic appendectomy. IV ceftriaxone and metronidazole.",
      conditions: [{ text: "acute appendicitis with localized peritonitis" }],
      observations: [{ text: "leukocytosis, WBC 15.2" }],
      service_requests: [{ text: "laparoscopic appendectomy" }],
      medication_requests: [{ text: "IV ceftriaxone and metronidazole" }],
    },
  },
  {
    name: "Chest pain with diabetes (several conditions)",
    body: {
      patient_id: "pat_1180",
      department: "Cardiology",
      soap_note:
        "S: 61-year-old with crushing substernal chest pain for 2 hours radiating to the left arm. Known type 2 diabetes on metformin, poorly controlled.\n" +
        "O: ST elevation in V1-V4, troponin I elevated. A1c 9.4%. BP 162/98.\n" +
        "A: Acute anterior wall ST elevation myocardial infarction. Type 2 diabetes mellitus with hyperglycemia. Essential hypertension.\n" +
        "P: Emergent cardiac catheterization. Aspirin, heparin, atorvastatin. Continue metformin.",
      conditions: [
        { text: "acute ST elevation myocardial infarction of anterior wall" },
        { text: "type 2 diabetes mellitus with hyperglycemia" },
        { text: "essential hypertension" },
      ],
      observations: [{ text: "troponin I elevated" }],
      service_requests: [{ text: "cardiac catheterization" }],
      medication_requests: [{ text: "aspirin" }, { text: "atorvastatin" }],
    },
  },
  {
    name: "Lay wording & abbreviations",
    body: {
      patient_id: "pat_2045",
      department: "Primary Care",
      soap_note:
        "S: Pt c/o burning on urination x3 days and frequency. Hx HTN. Also reports pink eye since yesterday, itchy with discharge.\n" +
        "O: UA positive for nitrites and leukocyte esterase. Bilateral conjunctival injection with purulent discharge.\n" +
        "A: Acute cystitis. Bacterial conjunctivitis, both eyes. HTN, stable.\n" +
        "P: Nitrofurantoin 5 days. Erythromycin ophthalmic ointment.",
      conditions: [{ text: "bladder infection" }, { text: "pink eye both eyes" }, { text: "HTN" }],
      medication_requests: [{ text: "nitrofurantoin" }, { text: "erythromycin ophthalmic ointment" }],
    },
  },
]

export function newEncounterId(): string {
  const d = new Date()
  const stamp = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`
  return `enc_${stamp}_${Math.random().toString(36).slice(2, 8).toUpperCase()}`
}
