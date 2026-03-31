---
id: RES-001
title: "Herbalism RAG — Data Sources Research"
type: explanation
status: COMPLETE
owner: architect
agents: [all]
created: 2026-03-31
version: 1.0.0
---

> **BLUF:** Four credible, free data sources identified for ingestion. PubMed (API) is the primary source. MSK About Herbs (scraping) is the highest-quality clinical monograph source. USDA Duke DB (CSV) adds phytochemical depth. WHO monographs (curated JSON) add official regulatory coverage.

# RES-001: Data Sources Research

## 1. Research Question
Which publicly accessible data sources provide credible, citable herbalism and botanical medicine data suitable for RAG ingestion?

## 2. Criteria
- Credibility: peer-reviewed, clinical, or official regulatory source
- Accessibility: free, public, no subscription required
- Citability: each document has a stable URL users can click
- Coverage: herbs, compounds, safety, interactions, evidence grades

## 3. Sources Evaluated and Selected

### 3.1 PubMed / NCBI E-utilities — PRIMARY
- **URL:** https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
- **Type:** Peer-reviewed biomedical research
- **Access:** Free REST API, no key required up to 3 req/s
- **Coverage:** Clinical trials, pharmacology, phytochemistry, safety data
- **Citation format:** PMID + https://pubmed.ncbi.nlm.nih.gov/{PMID}/
- **Ingestion plan:** ESearch by herb name + condition keywords, EFetch abstracts, chunk + store
- **Status:** SELECTED — primary source

### 3.2 Memorial Sloan Kettering About Herbs — HIGH PRIORITY
- **URL:** https://www.mskcc.org/cancer-care/diagnosis-treatment/symptom-management/integrative-medicine/herbs/search
- **Type:** Clinical monographs written by oncology pharmacists
- **Access:** Free, public, web scraping
- **Coverage:** 200+ herbs with evidence grades, drug interactions, safety for cancer patients
- **Citation format:** Direct MSK URL per herb
- **Ingestion plan:** Scrape herb index, extract monograph content, chunk + store
- **Status:** SELECTED — highest quality clinical monograph source

### 3.3 USDA Dr. Duke's Phytochemical Database
- **URL:** https://phytochem.nal.usda.gov/
- **Type:** Phytochemical and ethnobotanical database
- **Access:** No API; bulk CSV available via Ag Data Commons
- **Coverage:** Chemical constituents per plant, biological activities, ethnobotanical uses
- **Citation format:** Plant name + USDA Duke DB attribution
- **Ingestion plan:** Download CSV bulk export, transform rows to text, chunk + store
- **Status:** SELECTED — adds phytochemical depth unavailable in PubMed abstracts

### 3.4 WHO Monographs on Selected Medicinal Plants
- **URL:** https://www.who.int/publications/i/item/9789241545174
- **Type:** Official WHO regulatory guidance
- **Access:** Free PDFs (volumes 1-4), 28 herbs covered
- **Coverage:** Defined therapeutic uses, traditional uses, contraindications, dosing
- **Citation format:** WHO Monographs Vol. X, Year
- **Ingestion plan:** Manual curation of key sections into data/seeds/who_monographs.json (committed to repo)
- **Status:** SELECTED — official regulatory weight; top 20 most-queried herbs curated

## 4. Sources Evaluated but NOT Selected

### Examine.com
- No public API (404), scraping ToS unclear
- Status: REJECTED

### Natural Medicines Database (formerly Natural Standard)
- Subscription required (~$200+/year)
- Status: REJECTED — out of budget for v1

### HerbMed
- Subscription required for full access
- Status: REJECTED

### OpenFDA
- No dedicated botanical database; adverse event data only, not therapeutic monographs
- Status: REJECTED — wrong data type

## 5. Coverage by Source

| Herb | PubMed | MSK | Duke | WHO |
|:-----|:-------|:----|:-----|:----|
| Ashwagandha | High | Yes | Yes | Yes |
| Berberine | High | Yes | Yes | No |
| Holy Basil | Medium | Yes | Yes | No |
| Rhodiola | Medium | Yes | Yes | No |
| Lion's Mane | Growing | Yes | Yes | No |
| Turmeric | High | Yes | Yes | Yes |
| Valerian | High | Yes | Yes | Yes |
| Reishi | Medium | Yes | Yes | No |
| Ginger | High | Yes | Yes | Yes |
| Echinacea | High | Yes | Yes | Yes |

## 6. Recommendation

Ingest in this order:
1. WHO seed JSON (fastest, already curated, committed to repo)
2. MSK About Herbs (highest clinical value, web scrape)
3. PubMed (broadest coverage, API-based targeted search per herb)
4. USDA Duke (phytochemical depth, CSV bulk load)

## 7. Sources

- PubMed E-utilities docs: https://www.ncbi.nlm.nih.gov/books/NBK25497/
- MSK About Herbs: https://www.mskcc.org/cancer-care/diagnosis-treatment/symptom-management/integrative-medicine/herbs/search
- USDA Duke DB: https://phytochem.nal.usda.gov/
- WHO Monographs: https://www.who.int/publications/i/item/9789241545174

## 8. Change Log

| Date | Version | Change | Author |
|:-----|:--------|:-------|:-------|
| 2026-03-31 | 1.0.0 | Initial research complete | Architect Agent |
