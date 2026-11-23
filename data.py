"""Knowledge base: diseases, their symptom profiles, and basic advice.

"core" symptoms are the ones usually present; "secondary" ones appear less often.
This is a small educational dataset, NOT a medical reference.
"""

DISEASES = {
    "Common Cold": {
        "core": ["runny_nose", "sneezing", "sore_throat", "cough"],
        "secondary": ["headache", "fatigue", "body_ache", "fever"],
        "description": "A mild viral infection of the nose and throat that usually clears up in a week.",
        "precautions": ["Rest and drink plenty of fluids", "Gargle with warm salt water", "Wash hands often", "Use a humidifier or steam"],
        "specialist": "General Physician",
    },
    "Influenza (Flu)": {
        "core": ["high_fever", "body_ache", "chills", "fatigue", "cough"],
        "secondary": ["headache", "sore_throat", "runny_nose", "loss_of_appetite"],
        "description": "A contagious respiratory illness caused by influenza viruses, with sudden fever and body aches.",
        "precautions": ["Rest and stay hydrated", "Stay home to avoid spreading it", "Take fever reducers as advised by a doctor", "Get an annual flu vaccine"],
        "specialist": "General Physician",
    },
    "COVID-19": {
        "core": ["fever", "dry_cough", "loss_of_smell", "fatigue"],
        "secondary": ["shortness_of_breath", "sore_throat", "body_ache", "headache", "diarrhea"],
        "description": "A respiratory illness caused by the SARS-CoV-2 virus. Loss of smell or taste is a typical sign.",
        "precautions": ["Isolate and wear a mask", "Take a COVID test", "Monitor oxygen level and breathing", "Seek urgent care if breathing becomes difficult"],
        "specialist": "General Physician / Pulmonologist",
    },
    "Dengue": {
        "core": ["high_fever", "severe_headache", "eye_pain_behind", "joint_pain", "skin_rash"],
        "secondary": ["nausea", "vomiting", "fatigue", "body_ache", "abdominal_pain"],
        "description": "A mosquito-borne viral disease. High fever with pain behind the eyes and joint pain is typical.",
        "precautions": ["Drink lots of fluids", "Get a platelet count / blood test", "Avoid aspirin and ibuprofen", "Use mosquito nets and remove stagnant water"],
        "specialist": "General Physician / Infectious Disease",
    },
    "Malaria": {
        "core": ["high_fever", "chills", "sweating", "headache"],
        "secondary": ["nausea", "vomiting", "body_ache", "fatigue", "jaundice"],
        "description": "A mosquito-borne parasitic disease causing cycles of chills, high fever and sweating.",
        "precautions": ["Get a blood smear / rapid malaria test", "Complete the full anti-malarial course", "Use mosquito nets and repellent", "Seek care quickly - it can become severe"],
        "specialist": "Infectious Disease Specialist",
    },
    "Typhoid": {
        "core": ["high_fever", "abdominal_pain", "weakness", "loss_of_appetite"],
        "secondary": ["headache", "diarrhea", "nausea", "skin_rash", "fatigue"],
        "description": "A bacterial infection (Salmonella Typhi) spread by contaminated food and water, with prolonged fever.",
        "precautions": ["Drink only boiled or safe water", "Get blood culture / Widal test", "Complete the antibiotic course", "Maintain hand hygiene and food safety"],
        "specialist": "General Physician / Gastroenterologist",
    },
    "Gastroenteritis": {
        "core": ["diarrhea", "vomiting", "nausea", "abdominal_pain"],
        "secondary": ["fever", "loss_of_appetite", "weakness", "dizziness"],
        "description": "Inflammation of the stomach and intestines, usually from a virus or bacteria in food or water.",
        "precautions": ["Take oral rehydration solution (ORS)", "Eat light food (rice, banana, toast)", "Avoid oily and spicy food", "See a doctor if there is blood in stool or severe dehydration"],
        "specialist": "Gastroenterologist",
    },
    "Migraine": {
        "core": ["severe_headache", "sensitivity_to_light", "nausea"],
        "secondary": ["vomiting", "dizziness", "blurred_vision", "fatigue"],
        "description": "A neurological condition causing intense, often one-sided headaches with light sensitivity and nausea.",
        "precautions": ["Rest in a dark, quiet room", "Keep a trigger diary (food, sleep, stress)", "Stay hydrated and keep regular sleep", "Consult a doctor for preventive treatment"],
        "specialist": "Neurologist",
    },
    "Type 2 Diabetes": {
        "core": ["frequent_urination", "excessive_thirst", "fatigue", "blurred_vision"],
        "secondary": ["weight_loss", "itching", "loss_of_appetite", "weakness"],
        "description": "A long-term condition where the body cannot use insulin properly, leading to high blood sugar.",
        "precautions": ["Get fasting blood sugar and HbA1c tests", "Follow a low-sugar, balanced diet", "Exercise regularly", "Take medicines and monitor sugar as prescribed"],
        "specialist": "Endocrinologist",
    },
    "Hypertension": {
        "core": ["headache", "dizziness", "chest_pain"],
        "secondary": ["blurred_vision", "shortness_of_breath", "fatigue", "nausea"],
        "description": "Persistently high blood pressure, which raises the risk of heart disease and stroke.",
        "precautions": ["Measure blood pressure regularly", "Reduce salt intake", "Exercise and manage stress", "Take prescribed medicines; seek emergency care for severe chest pain"],
        "specialist": "Cardiologist",
    },
    "Asthma": {
        "core": ["wheezing", "shortness_of_breath", "dry_cough", "chest_pain"],
        "secondary": ["fatigue", "sneezing"],
        "description": "A chronic condition where the airways narrow and swell, causing wheezing and breathlessness.",
        "precautions": ["Keep a reliever inhaler nearby", "Avoid dust, smoke and known triggers", "Follow your asthma action plan", "Seek emergency help for severe breathlessness"],
        "specialist": "Pulmonologist",
    },
    "Pneumonia": {
        "core": ["high_fever", "cough", "shortness_of_breath", "chest_pain", "chills"],
        "secondary": ["fatigue", "sweating", "nausea", "loss_of_appetite"],
        "description": "An infection that inflames the air sacs in the lungs, causing cough, fever and breathing difficulty.",
        "precautions": ["Get a chest X-ray", "Take antibiotics only as prescribed", "Rest and drink fluids", "Seek urgent care if breathing is hard"],
        "specialist": "Pulmonologist",
    },
    "Urinary Tract Infection": {
        "core": ["burning_urination", "frequent_urination", "abdominal_pain"],
        "secondary": ["fever", "dark_urine", "nausea", "fatigue"],
        "description": "A bacterial infection of the urinary system, most commonly the bladder.",
        "precautions": ["Drink plenty of water", "Get a urine test", "Complete the antibiotic course", "Maintain good personal hygiene"],
        "specialist": "Urologist / General Physician",
    },
    "Hepatitis A": {
        "core": ["jaundice", "dark_urine", "fatigue", "nausea", "abdominal_pain"],
        "secondary": ["loss_of_appetite", "fever", "vomiting", "itching"],
        "description": "A viral liver infection spread through contaminated food or water, causing yellowing of skin and eyes.",
        "precautions": ["Rest and eat light, low-fat food", "Avoid alcohol and unnecessary medicines", "Drink only safe water", "Get a liver function test and the hepatitis A vaccine"],
        "specialist": "Gastroenterologist / Hepatologist",
    },
    "Allergic Rhinitis": {
        "core": ["sneezing", "runny_nose", "itching"],
        "secondary": ["headache", "cough", "sore_throat", "fatigue"],
        "description": "An allergic reaction to dust, pollen or pets, causing sneezing, runny nose and itchy eyes or nose.",
        "precautions": ["Avoid known allergens and dust", "Keep windows closed in high-pollen seasons", "Use antihistamines as advised", "Wash bedding regularly"],
        "specialist": "ENT Specialist / Allergist",
    },
    "Chickenpox": {
        "core": ["skin_rash", "itching", "fever"],
        "secondary": ["fatigue", "headache", "loss_of_appetite", "body_ache"],
        "description": "A contagious viral infection causing an itchy blister-like rash and mild fever.",
        "precautions": ["Isolate until all blisters crust over", "Do not scratch; keep nails short", "Use calamine lotion for itching", "Vaccination prevents it"],
        "specialist": "General Physician / Dermatologist",
    },
    "GERD (Acid Reflux)": {
        "core": ["heartburn", "chest_pain", "nausea"],
        "secondary": ["cough", "sore_throat", "abdominal_pain", "vomiting"],
        "description": "Stomach acid flowing back into the food pipe, causing a burning sensation in the chest.",
        "precautions": ["Eat smaller meals; avoid lying down right after eating", "Avoid spicy, oily food, coffee and smoking", "Raise the head of your bed", "Get chest pain checked to rule out heart problems"],
        "specialist": "Gastroenterologist",
    },
    "Tuberculosis": {
        "core": ["cough", "weight_loss", "sweating", "fatigue", "fever"],
        "secondary": ["chest_pain", "loss_of_appetite", "chills", "shortness_of_breath"],
        "description": "A bacterial infection mainly of the lungs; a cough lasting more than 2-3 weeks with weight loss is a warning sign.",
        "precautions": ["Get sputum test and chest X-ray", "Complete the full 6-month treatment", "Cover mouth when coughing", "Ensure good ventilation"],
        "specialist": "Pulmonologist / TB Specialist",
    },
    "Meningitis": {
        "core": ["high_fever", "stiff_neck", "severe_headache", "sensitivity_to_light"],
        "secondary": ["vomiting", "nausea", "skin_rash", "dizziness"],
        "description": "Inflammation of the membranes around the brain and spinal cord. This is a medical emergency.",
        "precautions": ["Go to the emergency department immediately", "Do not wait for symptoms to improve", "Vaccination can prevent some types"],
        "specialist": "Emergency / Neurologist",
    },
}

# Build the full, sorted symptom list from the disease profiles
SYMPTOMS = sorted({s for d in DISEASES.values() for s in d["core"] + d["secondary"]})


def label(symptom: str) -> str:
    """'eye_pain_behind' -> 'Eye Pain Behind'"""
    return symptom.replace("_", " ").title()
