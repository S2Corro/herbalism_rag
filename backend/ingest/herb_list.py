"""Herbalism RAG — Canonical Herb List.

Single source of truth for all herb names used across the ingestion
pipeline.  Every ingester imports from here rather than maintaining its
own hardcoded list.

``HERB_NAMES`` contains display names suitable for PubMed, NCCIH, and
ClinicalTrials.gov queries.  ``HERB_SLUGS`` contains URL-safe slugs
used by the MSK scraper (and any future scrapers that need slug-form
herb identifiers).
"""

from __future__ import annotations

# Display names (used by PubMed, NCCIH, ClinicalTrials.gov)
HERB_NAMES: list[str] = [
    "Ashwagandha", "Turmeric", "Ginger", "Echinacea", "Ginkgo",
    "Garlic", "Valerian", "St. John's Wort", "Chamomile", "Ginseng",
    "Green Tea", "Milk Thistle", "Saw Palmetto", "Black Cohosh",
    "Evening Primrose", "Feverfew", "Kava", "Licorice Root",
    "Flaxseed", "Aloe Vera", "Rhodiola", "Elderberry", "Astragalus",
    "Holy Basil", "Maca", "Boswellia", "Cat's Claw", "Dong Quai",
    "Passionflower", "Hawthorn", "Butterbur", "Berberine",
    "Tribulus", "Shatavari", "Bacopa", "Cordyceps", "Reishi",
    "Lion's Mane", "Chaga", "Turkey Tail", "Schisandra",
    "Andrographis", "Moringa", "Neem", "Oregano Oil", "Slippery Elm",
    "Marshmallow Root", "Dandelion", "Nettle", "Plantain",
]

# URL-safe slugs for MSK scraper
HERB_SLUGS: list[str] = [
    "ashwagandha", "turmeric", "ginger", "echinacea", "ginkgo-biloba",
    "garlic", "valerian", "st-johns-wort", "chamomile", "ginseng",
    "green-tea", "milk-thistle", "saw-palmetto", "black-cohosh",
    "evening-primrose", "feverfew", "kava", "licorice-root",
    "flaxseed", "aloe-vera", "rhodiola", "elderberry", "astragalus",
    "holy-basil", "maca", "boswellia", "cats-claw", "dong-quai",
    "passionflower", "hawthorn", "butterbur", "berberine",
    "tribulus", "shatavari", "bacopa", "cordyceps", "reishi",
    "lions-mane", "chaga", "turkey-tail", "schisandra",
    "andrographis", "moringa", "neem", "oregano-oil", "slippery-elm",
    "marshmallow-root", "dandelion", "nettle", "plantain",
]
