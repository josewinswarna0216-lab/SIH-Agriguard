TREATMENTS = {
    "Apple___Apple_scab": "Apply fungicide (captan or myclobutanil); remove fallen leaves to reduce spore spread.",
    "Apple___Black_rot": "Prune infected branches; apply copper-based fungicide during dormancy.",
    "Apple___Cedar_apple_rust": "Apply fungicide (myclobutanil) in early spring; remove nearby cedar trees if possible.",
    "Apple___healthy": "No treatment needed.",
    "Blueberry___healthy": "No treatment needed.",
    "Cherry_(including_sour)___Powdery_mildew": "Apply sulfur-based fungicide; improve air circulation via pruning.",
    "Cherry_(including_sour)___healthy": "No treatment needed.",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "Apply foliar fungicide; rotate crops to reduce residue-borne spores.",
    "Corn_(maize)___Common_rust_": "Apply fungicide (azoxystrobin); use rust-resistant hybrids next season.",
    "Corn_(maize)___Northern_Leaf_Blight": "Apply fungicide at early symptom onset; rotate with non-host crops.",
    "Corn_(maize)___healthy": "No treatment needed.",
    "Grape___Black_rot": "Apply mancozeb or myclobutanil; remove mummified berries.",
    "Grape___Esca_(Black_Measles)": "No curative treatment; remove and destroy infected wood, avoid pruning in wet weather.",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": "Apply copper-based fungicide; improve canopy airflow.",
    "Grape___healthy": "No treatment needed.",
    "Orange___Haunglongbing_(Citrus_greening)": "No cure; remove and destroy infected trees, control psyllid insect vectors.",
    "Peach___Bacterial_spot": "Apply copper-based bactericide; avoid overhead irrigation.",
    "Peach___healthy": "No treatment needed.",
    "Pepper,_bell___Bacterial_spot": "Apply copper-based bactericide; use disease-free seed.",
    "Pepper,_bell___healthy": "No treatment needed.",
    "Potato___Early_blight": "Apply chlorothalonil or mancozeb fungicide; rotate crops.",
    "Potato___Late_blight": "Apply fungicide immediately (chlorothalonil); destroy infected plants to prevent spread.",
    "Potato___healthy": "No treatment needed.",
    "Raspberry___healthy": "No treatment needed.",
    "Soybean___healthy": "No treatment needed.",
    "Squash___Powdery_mildew": "Apply sulfur or potassium bicarbonate spray; increase plant spacing.",
    "Strawberry___Leaf_scorch": "Apply fungicide (captan); remove infected leaves after harvest.",
    "Strawberry___healthy": "No treatment needed.",
    "Tomato___Bacterial_spot": "Apply copper-based bactericide; avoid working with wet plants.",
    "Tomato___Early_blight": "Apply chlorothalonil or mancozeb; remove lower infected leaves.",
    "Tomato___Late_blight": "Apply fungicide immediately (chlorothalonil); destroy infected plants to prevent spread.",
    "Tomato___Leaf_Mold": "Improve ventilation; apply chlorothalonil fungicide.",
    "Tomato___Septoria_leaf_spot": "Apply fungicide (chlorothalonil); remove infected lower leaves.",
    "Tomato___Spider_mites Two-spotted_spider_mite": "Apply miticide or insecticidal soap; increase humidity to deter mites.",
    "Tomato___Target_Spot": "Apply fungicide (chlorothalonil); improve air circulation.",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "No cure; remove infected plants, control whitefly vectors.",
    "Tomato___Tomato_mosaic_virus": "No cure; remove infected plants, disinfect tools between use.",
    "Tomato___healthy": "No treatment needed.",
}


def get_treatment(label):
    return TREATMENTS.get(label, "No recommendation available.")


# ---- Multi-crop specialist model (Friday advancement) ----
# Kept separate from TREATMENTS above so the original 38-class model/dashboard
# is untouched.
TREATMENTS_V2 = {
    "Banana_Cordana": "Apply mancozeb or copper-based fungicide; remove and destroy infected leaves; improve field drainage.",
    "Banana_Healthy": "No treatment needed.",
    "Banana_Pestalotiopsis": "Apply copper oxychloride fungicide; avoid leaf injury during handling; remove infected debris.",
    "Banana_Sigatoka": "Apply propiconazole or mancozeb on a spray schedule; remove infected leaves; ensure proper spacing for airflow.",
    "Betel_Anthracnose": "Apply carbendazim or copper oxychloride; remove and burn infected leaves; avoid overhead irrigation.",
    "Betel_Healthy_Green": "No treatment needed.",
    "Betel_Healthy_Red": "No treatment needed.",
    "Betel_Rust": "Apply sulfur-based fungicide; improve ventilation in the vine trellis; remove infected leaves promptly.",
    "Citrus_Black_spot": "Apply copper-based fungicide or strobilurins; remove fallen leaves and fruit; prune for airflow.",
    "Citrus_Canker": "Apply copper bactericide sprays; prune and destroy infected twigs; disinfect tools between trees.",
    "Citrus_Greening": "No cure; remove and destroy infected trees, control Asian citrus psyllid vectors.",
    "Citrus_Healthy": "No treatment needed.",
    "Corn_Blight": "Apply fungicide (azoxystrobin or propiconazole) at early symptom onset; rotate with non-host crops.",
    "Corn_Common_Rust": "Apply fungicide (azoxystrobin); use rust-resistant hybrids next season.",
    "Corn_Gray_Leaf_Spot": "Apply foliar fungicide; rotate crops to reduce residue-borne spores; use resistant hybrids.",
    "Corn_Healthy": "No treatment needed.",
    "Cotton_Alternaria_Leaf_Spot": "Apply mancozeb or chlorothalonil fungicide; remove crop debris after harvest.",
    "Cotton_Bacterial_Blight": "Apply copper-based bactericide; use disease-free seed; avoid overhead irrigation.",
    "Cotton_Fusarium_Wilt": "No curative treatment; use resistant varieties, rotate crops, avoid waterlogging.",
    "Cotton_Healthy": "No treatment needed.",
    "Cotton_Verticillium_Wilt": "No curative treatment; rotate with non-host crops, use resistant varieties, avoid excess nitrogen.",
    "Mango_Anthracnose": "Apply copper oxychloride or carbendazim fungicide; prune for airflow; remove infected fruit and debris.",
    "Mango_Bacterial_Canker": "Apply copper-based bactericide; prune and destroy infected twigs; avoid injury during harvest.",
    "Mango_Cutting_Weevil": "Apply a recommended insecticide to shoots; remove and destroy infested twigs.",
    "Mango_Die_Back": "Prune affected branches well below visible symptoms; apply copper fungicide paste to cut ends; improve orchard sanitation.",
    "Mango_Gall_Midge": "Apply systemic insecticide during flushing; remove and destroy galled leaves and shoots.",
    "Mango_Healthy": "No treatment needed.",
    "Mango_Powdery_Mildew": "Apply sulfur or triadimefon fungicide at flowering; improve air circulation.",
    "Mango_Sooty_Mould": "Control sap-sucking insects (aphids/scale) causing honeydew; wash off mould with a mild soap solution.",
    "Sugarcane_Healthy": "No treatment needed.",
    "Sugarcane_Mosaic": "No cure; use virus-free seed cane, remove and destroy infected plants, control aphid vectors.",
    "Sugarcane_RedRot": "No curative treatment; use resistant varieties, avoid waterlogging, remove and burn infected stalks.",
    "Sugarcane_Rust": "Apply propiconazole or mancozeb fungicide; use resistant varieties.",
    "Sugarcane_Yellow": "No cure; use disease-free planting material, control aphid vectors, remove infected clumps.",
}


def get_treatment_v2(label):
    return TREATMENTS_V2.get(label, "No recommendation available.")
