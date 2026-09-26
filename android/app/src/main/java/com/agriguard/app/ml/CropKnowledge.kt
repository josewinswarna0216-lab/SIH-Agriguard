package com.agriguard.app.ml

// On-device crop knowledge for the 34-class multi-crop model.
//
// These tables are deliberately compiled into the APK rather than fetched from
// the server: a farmer with no signal still needs the treatment text, not just
// a class name. Generated from server/treatments.py and
// server/translations_ta_v2.py so the two stay in lockstep -- if you retrain or
// edit a recommendation, regenerate rather than hand-editing one side.
//
// The Tamil strings carry the same caveat as the server's: machine-generated in
// one pass, worth a native agricultural-Tamil speaker's review before real
// deployment.

/** Class list in the exact output order the model was trained with. */
val CLASS_NAMES_V2 = listOf(
    "Banana_Cordana",
    "Banana_Healthy",
    "Banana_Pestalotiopsis",
    "Banana_Sigatoka",
    "Betel_Anthracnose",
    "Betel_Healthy_Green",
    "Betel_Healthy_Red",
    "Betel_Rust",
    "Citrus_Black_spot",
    "Citrus_Canker",
    "Citrus_Greening",
    "Citrus_Healthy",
    "Corn_Blight",
    "Corn_Common_Rust",
    "Corn_Gray_Leaf_Spot",
    "Corn_Healthy",
    "Cotton_Alternaria_Leaf_Spot",
    "Cotton_Bacterial_Blight",
    "Cotton_Fusarium_Wilt",
    "Cotton_Healthy",
    "Cotton_Verticillium_Wilt",
    "Mango_Anthracnose",
    "Mango_Bacterial_Canker",
    "Mango_Cutting_Weevil",
    "Mango_Die_Back",
    "Mango_Gall_Midge",
    "Mango_Healthy",
    "Mango_Powdery_Mildew",
    "Mango_Sooty_Mould",
    "Sugarcane_Healthy",
    "Sugarcane_Mosaic",
    "Sugarcane_RedRot",
    "Sugarcane_Rust",
    "Sugarcane_Yellow",
)

private val LABELS_EN = mapOf(
    "Banana_Cordana" to "Banana — Cordana",
    "Banana_Healthy" to "Banana — Healthy",
    "Banana_Pestalotiopsis" to "Banana — Pestalotiopsis",
    "Banana_Sigatoka" to "Banana — Sigatoka",
    "Betel_Anthracnose" to "Betel — Anthracnose",
    "Betel_Healthy_Green" to "Betel — Healthy Green",
    "Betel_Healthy_Red" to "Betel — Healthy Red",
    "Betel_Rust" to "Betel — Rust",
    "Citrus_Black_spot" to "Citrus — Black spot",
    "Citrus_Canker" to "Citrus — Canker",
    "Citrus_Greening" to "Citrus — Greening",
    "Citrus_Healthy" to "Citrus — Healthy",
    "Corn_Blight" to "Corn — Blight",
    "Corn_Common_Rust" to "Corn — Common Rust",
    "Corn_Gray_Leaf_Spot" to "Corn — Gray Leaf Spot",
    "Corn_Healthy" to "Corn — Healthy",
    "Cotton_Alternaria_Leaf_Spot" to "Cotton — Alternaria Leaf Spot",
    "Cotton_Bacterial_Blight" to "Cotton — Bacterial Blight",
    "Cotton_Fusarium_Wilt" to "Cotton — Fusarium Wilt",
    "Cotton_Healthy" to "Cotton — Healthy",
    "Cotton_Verticillium_Wilt" to "Cotton — Verticillium Wilt",
    "Mango_Anthracnose" to "Mango — Anthracnose",
    "Mango_Bacterial_Canker" to "Mango — Bacterial Canker",
    "Mango_Cutting_Weevil" to "Mango — Cutting Weevil",
    "Mango_Die_Back" to "Mango — Die Back",
    "Mango_Gall_Midge" to "Mango — Gall Midge",
    "Mango_Healthy" to "Mango — Healthy",
    "Mango_Powdery_Mildew" to "Mango — Powdery Mildew",
    "Mango_Sooty_Mould" to "Mango — Sooty Mould",
    "Sugarcane_Healthy" to "Sugarcane — Healthy",
    "Sugarcane_Mosaic" to "Sugarcane — Mosaic",
    "Sugarcane_RedRot" to "Sugarcane — RedRot",
    "Sugarcane_Rust" to "Sugarcane — Rust",
    "Sugarcane_Yellow" to "Sugarcane — Yellow",
)

private val LABELS_TA = mapOf(
    "Banana_Cordana" to "வாழை — கார்டானா இலை புள்ளி நோய்",
    "Banana_Healthy" to "வாழை — ஆரோக்கியமானது",
    "Banana_Pestalotiopsis" to "வாழை — பெஸ்டலோசியோப்சிஸ் இலை நோய்",
    "Banana_Sigatoka" to "வாழை — சிகடோகா இலை புள்ளி நோய்",
    "Betel_Anthracnose" to "வெற்றிலை — ஆந்த்ராக்நோஸ் நோய்",
    "Betel_Healthy_Green" to "வெற்றிலை — ஆரோக்கியமானது (பச்சை)",
    "Betel_Healthy_Red" to "வெற்றிலை — ஆரோக்கியமானது (சிவப்பு)",
    "Betel_Rust" to "வெற்றிலை — துரு நோய்",
    "Citrus_Black_spot" to "சிட்ரஸ் — கருப்பு புள்ளி நோய்",
    "Citrus_Canker" to "சிட்ரஸ் — கேங்கர் நோய்",
    "Citrus_Greening" to "சிட்ரஸ் — பசுமை நோய்",
    "Citrus_Healthy" to "சிட்ரஸ் — ஆரோக்கியமானது",
    "Corn_Blight" to "சோளம் — கருகல் நோய்",
    "Corn_Common_Rust" to "சோளம் — பொதுவான துரு நோய்",
    "Corn_Gray_Leaf_Spot" to "சோளம் — சாம்பல் இலை புள்ளி நோய்",
    "Corn_Healthy" to "சோளம் — ஆரோக்கியமானது",
    "Cotton_Alternaria_Leaf_Spot" to "பருத்தி — ஆல்டர்நேரியா இலை புள்ளி நோய்",
    "Cotton_Bacterial_Blight" to "பருத்தி — பாக்டீரியா கருகல் நோய்",
    "Cotton_Fusarium_Wilt" to "பருத்தி — ஃபூசேரியம் வாடல் நோய்",
    "Cotton_Healthy" to "பருத்தி — ஆரோக்கியமானது",
    "Cotton_Verticillium_Wilt" to "பருத்தி — வெர்டிசீலியம் வாடல் நோய்",
    "Mango_Anthracnose" to "மாம்பழம் — ஆந்த்ராக்நோஸ் நோய்",
    "Mango_Bacterial_Canker" to "மாம்பழம் — பாக்டீரியா கேங்கர் நோய்",
    "Mango_Cutting_Weevil" to "மாம்பழம் — வெட்டு வண்டு பூச்சி தாக்குதல்",
    "Mango_Die_Back" to "மாம்பழம் — நுனி காய்தல் நோய்",
    "Mango_Gall_Midge" to "மாம்பழம் — கால் நுளம்பு பூச்சி தாக்குதல்",
    "Mango_Healthy" to "மாம்பழம் — ஆரோக்கியமானது",
    "Mango_Powdery_Mildew" to "மாம்பழம் — பொடி பூஞ்சை நோய்",
    "Mango_Sooty_Mould" to "மாம்பழம் — கரிப்பூஞ்சை நோய்",
    "Sugarcane_Healthy" to "கரும்பு — ஆரோக்கியமானது",
    "Sugarcane_Mosaic" to "கரும்பு — மொசைக் நோய்",
    "Sugarcane_RedRot" to "கரும்பு — சிவப்பு அழுகல் நோய்",
    "Sugarcane_Rust" to "கரும்பு — துரு நோய்",
    "Sugarcane_Yellow" to "கரும்பு — மஞ்சள் இலை நோய்",
)

private val TREATMENTS_EN = mapOf(
    "Banana_Cordana" to "Apply mancozeb or copper-based fungicide; remove and destroy infected leaves; improve field drainage.",
    "Banana_Healthy" to "No treatment needed.",
    "Banana_Pestalotiopsis" to "Apply copper oxychloride fungicide; avoid leaf injury during handling; remove infected debris.",
    "Banana_Sigatoka" to "Apply propiconazole or mancozeb on a spray schedule; remove infected leaves; ensure proper spacing for airflow.",
    "Betel_Anthracnose" to "Apply carbendazim or copper oxychloride; remove and burn infected leaves; avoid overhead irrigation.",
    "Betel_Healthy_Green" to "No treatment needed.",
    "Betel_Healthy_Red" to "No treatment needed.",
    "Betel_Rust" to "Apply sulfur-based fungicide; improve ventilation in the vine trellis; remove infected leaves promptly.",
    "Citrus_Black_spot" to "Apply copper-based fungicide or strobilurins; remove fallen leaves and fruit; prune for airflow.",
    "Citrus_Canker" to "Apply copper bactericide sprays; prune and destroy infected twigs; disinfect tools between trees.",
    "Citrus_Greening" to "No cure; remove and destroy infected trees, control Asian citrus psyllid vectors.",
    "Citrus_Healthy" to "No treatment needed.",
    "Corn_Blight" to "Apply fungicide (azoxystrobin or propiconazole) at early symptom onset; rotate with non-host crops.",
    "Corn_Common_Rust" to "Apply fungicide (azoxystrobin); use rust-resistant hybrids next season.",
    "Corn_Gray_Leaf_Spot" to "Apply foliar fungicide; rotate crops to reduce residue-borne spores; use resistant hybrids.",
    "Corn_Healthy" to "No treatment needed.",
    "Cotton_Alternaria_Leaf_Spot" to "Apply mancozeb or chlorothalonil fungicide; remove crop debris after harvest.",
    "Cotton_Bacterial_Blight" to "Apply copper-based bactericide; use disease-free seed; avoid overhead irrigation.",
    "Cotton_Fusarium_Wilt" to "No curative treatment; use resistant varieties, rotate crops, avoid waterlogging.",
    "Cotton_Healthy" to "No treatment needed.",
    "Cotton_Verticillium_Wilt" to "No curative treatment; rotate with non-host crops, use resistant varieties, avoid excess nitrogen.",
    "Mango_Anthracnose" to "Apply copper oxychloride or carbendazim fungicide; prune for airflow; remove infected fruit and debris.",
    "Mango_Bacterial_Canker" to "Apply copper-based bactericide; prune and destroy infected twigs; avoid injury during harvest.",
    "Mango_Cutting_Weevil" to "Apply a recommended insecticide to shoots; remove and destroy infested twigs.",
    "Mango_Die_Back" to "Prune affected branches well below visible symptoms; apply copper fungicide paste to cut ends; improve orchard sanitation.",
    "Mango_Gall_Midge" to "Apply systemic insecticide during flushing; remove and destroy galled leaves and shoots.",
    "Mango_Healthy" to "No treatment needed.",
    "Mango_Powdery_Mildew" to "Apply sulfur or triadimefon fungicide at flowering; improve air circulation.",
    "Mango_Sooty_Mould" to "Control sap-sucking insects (aphids/scale) causing honeydew; wash off mould with a mild soap solution.",
    "Sugarcane_Healthy" to "No treatment needed.",
    "Sugarcane_Mosaic" to "No cure; use virus-free seed cane, remove and destroy infected plants, control aphid vectors.",
    "Sugarcane_RedRot" to "No curative treatment; use resistant varieties, avoid waterlogging, remove and burn infected stalks.",
    "Sugarcane_Rust" to "Apply propiconazole or mancozeb fungicide; use resistant varieties.",
    "Sugarcane_Yellow" to "No cure; use disease-free planting material, control aphid vectors, remove infected clumps.",
)

private val TREATMENTS_TA = mapOf(
    "Banana_Cordana" to "mancozeb அல்லது காப்பர் பூஞ்சைக்கொல்லி தெளிக்கவும்; பாதிக்கப்பட்ட இலைகளை அகற்றி அழிக்கவும்; வயல் வடிகால் வசதியை மேம்படுத்தவும்.",
    "Banana_Healthy" to "சிகிச்சை தேவையில்லை.",
    "Banana_Pestalotiopsis" to "காப்பர் ஆக்ஸிகுளோரைடு பூஞ்சைக்கொல்லி தெளிக்கவும்; கையாளும்போது இலைகளுக்கு காயம் ஏற்படாமல் பார்த்துக்கொள்ளவும்; பாதிக்கப்பட்ட கழிவுகளை அகற்றவும்.",
    "Banana_Sigatoka" to "propiconazole அல்லது mancozeb ஐ குறிப்பிட்ட காலஇடைவெளியில் தெளிக்கவும்; பாதிக்கப்பட்ட இலைகளை அகற்றவும்; காற்றோட்டத்திற்கு போதுமான இடைவெளி விடவும்.",
    "Betel_Anthracnose" to "carbendazim அல்லது காப்பர் ஆக்ஸிகுளோரைடு தெளிக்கவும்; பாதிக்கப்பட்ட இலைகளை அகற்றி எரிக்கவும்; மேலிருந்து நீர் பாய்ச்சுவதை தவிர்க்கவும்.",
    "Betel_Healthy_Green" to "சிகிச்சை தேவையில்லை.",
    "Betel_Healthy_Red" to "சிகிச்சை தேவையில்லை.",
    "Betel_Rust" to "சல்பர் பூஞ்சைக்கொல்லி தெளிக்கவும்; பந்தல் அமைப்பில் காற்றோட்டத்தை மேம்படுத்தவும்; பாதிக்கப்பட்ட இலைகளை உடனடியாக அகற்றவும்.",
    "Citrus_Black_spot" to "காப்பர் பூஞ்சைக்கொல்லி அல்லது strobilurin தெளிக்கவும்; விழுந்த இலைகள் மற்றும் பழங்களை அகற்றவும்; காற்றோட்டத்திற்காக கிளை கத்தரிக்கவும்.",
    "Citrus_Canker" to "காப்பர் பாக்டீரியா நாசினி தெளிக்கவும்; பாதிக்கப்பட்ட கிளைகளை கத்தரித்து அழிக்கவும்; மரங்களுக்கு இடையே கருவிகளை கிருமி நீக்கம் செய்யவும்.",
    "Citrus_Greening" to "குணப்படுத்த முடியாத நோய்; பாதிக்கப்பட்ட மரங்களை அகற்றி அழிக்கவும், சிட்ரஸ் சில்லிட் பூச்சிகளை கட்டுப்படுத்தவும்.",
    "Citrus_Healthy" to "சிகிச்சை தேவையில்லை.",
    "Corn_Blight" to "அறிகுறி தென்பட்டவுடன் பூஞ்சைக்கொல்லி (azoxystrobin அல்லது propiconazole) தெளிக்கவும்; பயிர் சுழற்சி செய்யவும்.",
    "Corn_Common_Rust" to "azoxystrobin பூஞ்சைக்கொல்லி தெளிக்கவும்; அடுத்த பருவத்தில் துரு எதிர்ப்பு வகை விதைகளை பயன்படுத்தவும்.",
    "Corn_Gray_Leaf_Spot" to "இலை பூஞ்சைக்கொல்லி தெளிக்கவும்; பயிர் சுழற்சி செய்யவும்; எதிர்ப்பு வகை விதைகளை பயன்படுத்தவும்.",
    "Corn_Healthy" to "சிகிச்சை தேவையில்லை.",
    "Cotton_Alternaria_Leaf_Spot" to "mancozeb அல்லது chlorothalonil பூஞ்சைக்கொல்லி தெளிக்கவும்; அறுவடைக்குப் பின் பயிர் கழிவுகளை அகற்றவும்.",
    "Cotton_Bacterial_Blight" to "காப்பர் பாக்டீரியா நாசினி பயன்படுத்தவும்; நோய் இல்லாத விதைகளை பயன்படுத்தவும்; மேலிருந்து நீர் பாய்ச்சுவதை தவிர்க்கவும்.",
    "Cotton_Fusarium_Wilt" to "குணப்படுத்த முடியாத நோய்; எதிர்ப்பு வகைகளை பயன்படுத்தவும், பயிர் சுழற்சி செய்யவும், நீர் தேங்குவதை தவிர்க்கவும்.",
    "Cotton_Healthy" to "சிகிச்சை தேவையில்லை.",
    "Cotton_Verticillium_Wilt" to "குணப்படுத்த முடியாத நோய்; வேறு பயிர்களுடன் சுழற்சி செய்யவும், எதிர்ப்பு வகைகளை பயன்படுத்தவும், அதிக நைட்ரஜனை தவிர்க்கவும்.",
    "Mango_Anthracnose" to "காப்பர் ஆக்ஸிகுளோரைடு அல்லது carbendazim பூஞ்சைக்கொல்லி தெளிக்கவும்; காற்றோட்டத்திற்காக கிளை கத்தரிக்கவும்; பாதிக்கப்பட்ட பழங்கள் மற்றும் கழிவுகளை அகற்றவும்.",
    "Mango_Bacterial_Canker" to "காப்பர் பாக்டீரியா நாசினி பயன்படுத்தவும்; பாதிக்கப்பட்ட கிளைகளை கத்தரித்து அழிக்கவும்; அறுவடையின் போது காயம் ஏற்படாமல் பார்த்துக்கொள்ளவும்.",
    "Mango_Cutting_Weevil" to "தளிர்களில் பரிந்துரைக்கப்பட்ட பூச்சிக்கொல்லியை தெளிக்கவும்; பாதிக்கப்பட்ட கிளைகளை அகற்றி அழிக்கவும்.",
    "Mango_Die_Back" to "பாதிக்கப்பட்ட கிளைகளை அறிகுறிக்கு கீழே நன்றாக கத்தரிக்கவும்; வெட்டிய பகுதிகளில் காப்பர் பூஞ்சைக்கொல்லி பசை தடவவும்; தோட்ட சுகாதாரத்தை மேம்படுத்தவும்.",
    "Mango_Gall_Midge" to "தளிர் விடும் காலத்தில் சிஸ்டமிக் பூச்சிக்கொல்லியை தெளிக்கவும்; கட்டி ஏற்பட்ட இலைகள் மற்றும் தளிர்களை அகற்றி அழிக்கவும்.",
    "Mango_Healthy" to "சிகிச்சை தேவையில்லை.",
    "Mango_Powdery_Mildew" to "பூக்கும் காலத்தில் சல்பர் அல்லது triadimefon பூஞ்சைக்கொல்லி தெளிக்கவும்; காற்றோட்டத்தை மேம்படுத்தவும்.",
    "Mango_Sooty_Mould" to "தேன்பனி உருவாக்கும் சாறு உறிஞ்சும் பூச்சிகளை (அஃபிட்ஸ்/அளவீட்டு பூச்சி) கட்டுப்படுத்தவும்; லேசான சோப் கரைசலால் பூஞ்சையை கழுவவும்.",
    "Sugarcane_Healthy" to "சிகிச்சை தேவையில்லை.",
    "Sugarcane_Mosaic" to "குணப்படுத்த முடியாத நோய்; வைரஸ் இல்லாத விதை கரும்பை பயன்படுத்தவும், பாதிக்கப்பட்ட செடிகளை அகற்றி அழிக்கவும், அஃபிட் பூச்சிகளை கட்டுப்படுத்தவும்.",
    "Sugarcane_RedRot" to "குணப்படுத்த முடியாத நோய்; எதிர்ப்பு வகைகளை பயன்படுத்தவும், நீர் தேங்குவதை தவிர்க்கவும், பாதிக்கப்பட்ட தண்டுகளை அகற்றி எரிக்கவும்.",
    "Sugarcane_Rust" to "propiconazole அல்லது mancozeb பூஞ்சைக்கொல்லி தெளிக்கவும்; எதிர்ப்பு வகைகளை பயன்படுத்தவும்.",
    "Sugarcane_Yellow" to "குணப்படுத்த முடியாத நோய்; நோய் இல்லாத நடவு பொருட்களை பயன்படுத்தவும், அஃபிட் பூச்சிகளை கட்டுப்படுத்தவும், பாதிக்கப்பட்ட புதர்களை அகற்றவும்.",
)

/**
 * Crop -> indices of that crop's classes, derived from the class names the same
 * way the server does it. Once the farmer tells us which crop they're standing
 * in front of, the other crops' classes can never win -- see [OnDeviceClassifier].
 */
val CROP_CLASS_INDICES: Map<String, List<Int>> =
    CLASS_NAMES_V2.withIndex()
        .groupBy({ it.value.substringBefore('_') }, { it.index })

val SUPPORTED_CROPS: List<String> = CROP_CLASS_INDICES.keys.toList()

fun labelFor(className: String, lang: String): String =
    if (lang == "ta") LABELS_TA[className] ?: className else LABELS_EN[className] ?: className

fun treatmentFor(className: String, lang: String): String =
    if (lang == "ta") {
        TREATMENTS_TA[className] ?: "\u0baa\u0bb0\u0bbf\u0ba8\u0bcd\u0ba4\u0bc1\u0bb0\u0bc8 \u0b95\u0bbf\u0b9f\u0bc8\u0b95\u0bcd\u0b95\u0bb5\u0bbf\u0bb2\u0bcd\u0bb2\u0bc8."
    } else {
        TREATMENTS_EN[className] ?: "No recommendation available."
    }

/** A class is "healthy" when its name says so -- same rule the server uses. */
fun isHealthy(className: String): Boolean = className.contains("Healthy", ignoreCase = true)
