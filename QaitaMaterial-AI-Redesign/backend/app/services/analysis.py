from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# These are exploratory scenarios, NOT regulatory or laboratory approval.
USE_CASES = [
    {"title":"Construction gypsum products (subject to testing)","keywords":"gypsum phosphogypsum construction gypsum cement mineral binder","categories":["phosphogypsum","gypsum"]},
    {"title":"Industrial mineral filler (subject to testing)","keywords":"mineral filler byproduct calcium carbonate gypsum construction","categories":["phosphogypsum","gypsum","mineral"]},
    {"title":"Metal recycling after sorting", "keywords":"scrap metal steel iron aluminum remelting metallurgy", "categories":["metal","scrap"]},
    {"title":"Aggregate processing", "keywords":"slag aggregate road construction mineral slag", "categories":["slag"]},
]

def analyze(material):
    missing=[]
    if not material.chemical_properties.strip(): missing.append("chemical composition and impurities")
    if material.hazard_class.lower() in ("unknown","", "неизвестен"): missing.append("hazard classification")
    if not material.lab_verified: missing.append("verified laboratory results")
    if "фосф" in material.name.lower() or "phosph" in material.name.lower() or "phosph" in material.category.lower():
        missing += ["radiological screening", "applicable regulatory review"]
    query=" ".join([material.name,material.category,material.description,material.chemical_properties])
    corpus=[query]+[x["keywords"] for x in USE_CASES]
    sim=cosine_similarity(TfidfVectorizer(ngram_range=(1,2)).fit_transform(corpus))[0][1:]
    recommendations=[]
    for i,item in enumerate(USE_CASES):
        if material.category.lower() not in item["categories"] and not any(word in material.name.lower() for word in item["categories"]):continue
        recommendations.append({"use_case":item["title"],"matching_score":round(float(sim[i])*100,1),"status":"requires_verification","reason":"Category match and TF-IDF text similarity; engineering validation required."})
    recommendations.sort(key=lambda a:a["matching_score"],reverse=True)
    return {"material_id":material.id,"verification_status":"requires_verification" if missing else "requires_independent_approval","missing_information":missing,"recommendations":recommendations,"warning":"Algorithmic match is not proof of safety or legal eligibility; laboratory and legal reviews are required.","model":"TF-IDF cosine similarity + hard verification gate"}

def economy(p):
    revenue=p.quantity*p.sale_price_per_unit
    processing=p.quantity*p.processing_per_unit
    transport=p.quantity*p.transport_per_unit
    storage=p.quantity*p.storage_per_unit
    net=revenue-processing-transport-storage-p.other_cost
    return {"revenue":revenue,"processing":processing,"transport":transport,"storage":storage,"other":p.other_cost,"net":net,"formula":"Q×P − Q×Processing − Q×Transport − Q×Storage − Other","status":"scenario_estimate"}
