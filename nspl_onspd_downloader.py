"""
nspl_onspd_downloader.py

Backend helper functions for the Streamlit app.

This module searches data.gov.uk for the latest NSPL and ONSPD CSV resources.

Products:
    NSPL  = National Statistics Postcode Lookup
    ONSPD = ONS Postcode Directory

Beginner explanation:
    Think of data.gov.uk as a library catalogue.

    This file does the library work:
    1. Search the catalogue.
    2. Find the right dataset record.
    3. Check the download buttons/resources.
    4. Pick the CSV resource.
    5. Return the link to Streamlit.

References:
    data.gov.uk API documentation:
        https://guidance.data.gov.uk/get_data/api_documentation/

    CKAN API guide:
        https://docs.ckan.org/en/latest/api/

    CKAN Python/CLI project:
        https://github.com/ckan/ckanapi

    CKAN resource utilities:
        https://github.com/reubano/ckanutils

    ONS postcode products:
        https://www.ons.gov.uk/methodology/geography/geographicalproducts/postcodeproducts

    Rolling NSPL dataset:
        https://www.data.gov.uk/dataset/7ec10db7-c8f4-4a40-8d82-8921935b4865/national-statistics-postcode-lookup-uk

    Example ONSPD hosted table:
        https://www.data.gov.uk/dataset/65a2ee49-d331-41c9-b09f-c7defc68b965/ons-postcode-directory-may-2026-for-the-united-kingdom-hosted-table
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests


# =============================================================================
# 1. Settings
# =============================================================================

# data.gov.uk uses CKAN.
# CKAN calls datasets "packages", so the search endpoint is called package_search.
DATA_GOV_PACKAGE_SEARCH_URL = "https://data.gov.uk/api/action/package_search"

# Product settings.
# Each product has several search queries because data.gov.uk titles can vary.
PRODUCTS: Dict[str, Dict[str, Any]] = {
    "NSPL": {
        "friendly_name": "National Statistics Postcode Lookup",
        "queries": [
            '"National Statistics Postcode Lookup" "Hosted Table"',
            '"National Statistics Postcode Lookup UK"',
            'NSPL "National Statistics Postcode Lookup"',
        ],
        "canonical_phrases": [
            "national statistics postcode lookup",
            "nspl",
        ],
        "strong_title_phrase": "national statistics postcode lookup",
        "allowed_publishers": [
            "office for national statistics",
            "london borough of camden",
        ],
        "reject_phrases": [
            "user guide",
            "centroid",
            "online ons postcode directory",
            "live postcodes",
        ],
        # The rolling Camden NSPL record may not have a month/year in the title,
        # so we allow metadata_modified to act as the date.
        "allow_metadata_date_fallback": True,
    },
    "ONSPD": {
        "friendly_name": "ONS Postcode Directory",
        "queries": [
            '"ONS Postcode Directory" "Hosted Table"',
            'ONSPD "Hosted Table"',
            '"ONS Postcode Directory" "United Kingdom" "CSV"',
        ],
        "canonical_phrases": [
            "ons postcode directory",
            "onspd",
        ],
        "strong_title_phrase": "ons postcode directory",
        "allowed_publishers": [
            "office for national statistics",
        ],
        "reject_phrases": [
            "user guide",
            "centroid",
            "online ons postcode directory",
            "live postcodes",
        ],
        # For ONSPD, official releases usually contain a month/year in the title.
        "allow_metadata_date_fallback": False,
    },
}


MONTH_NAME_TO_NUMBER = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


# =============================================================================
# 2. Date helper functions
# =============================================================================

def parse_month_year_from_text(text: str) -> Optional[Tuple[int, int, int]]:
    """
    Find a date like "(May 2026)" in a dataset title.

    Returns:
        (year, month, day)

    Why day = 1?
        The title usually only gives month and year, not a day.
        Using day 1 gives us a sortable date.
    """
    pattern = (
        r"\("
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+"
        r"(\d{4})"
        r"\)"
    )

    match = re.search(pattern, text, flags=re.IGNORECASE)

    if match is None:
        return None

    month_name = match.group(1).lower()
    year = int(match.group(2))
    month = MONTH_NAME_TO_NUMBER[month_name]

    return year, month, 1


def parse_metadata_modified(value: str) -> Optional[Tuple[int, int, int]]:
    """
    Parse the data.gov.uk metadata_modified date.

    Example CKAN value:
        2026-06-22T12:34:56.123456
    """
    if not value:
        return None

    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.year, dt.month, dt.day
    except ValueError:
        return None


def date_tuple_to_text(date_tuple: Optional[Tuple[int, int, int]]) -> str:
    """
    Turn a date tuple into readable text.
    """
    if date_tuple is None:
        return "Unknown"

    year, month, day = date_tuple
    return f"{year:04d}-{month:02d}-{day:02d}"


# =============================================================================
# 3. data.gov.uk search helper functions
# =============================================================================

def call_package_search(query: str, rows: int = 100) -> List[Dict[str, Any]]:
    """
    Call the data.gov.uk package_search API.

    API route:
        https://data.gov.uk/api/action/package_search

    Parameters used:
        q     = search text
        rows  = number of results to return
        sort  = ask data.gov.uk to put recently modified records first
    """
    params = {
        "q": query,
        "rows": rows,
        "sort": "metadata_modified desc",
    }

    response = requests.get(
        DATA_GOV_PACKAGE_SEARCH_URL,
        params=params,
        timeout=60,
    )
    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        raise RuntimeError(f"data.gov.uk API returned success=false: {data}")

    return data["result"]["results"]


def dataset_text_blob(dataset: Dict[str, Any]) -> str:
    """
    Combine useful CKAN fields into one lowercase text blob.

    Dataset-level keys used:
        id
        name
        title
        notes
        metadata_modified
        organization.title
        organization.name

    Resource-level keys used:
        resources[].name
        resources[].description
        resources[].format
        resources[].url
    """
    pieces = [
        str(dataset.get("id", "")),
        str(dataset.get("name", "")),
        str(dataset.get("title", "")),
        str(dataset.get("notes", "")),
        str(dataset.get("metadata_modified", "")),
    ]

    organisation = dataset.get("organization") or {}
    pieces.append(str(organisation.get("title", "")))
    pieces.append(str(organisation.get("name", "")))

    for resource in dataset.get("resources", []):
        pieces.append(str(resource.get("name", "")))
        pieces.append(str(resource.get("description", "")))
        pieces.append(str(resource.get("format", "")))
        pieces.append(str(resource.get("url", "")))

    return " ".join(pieces).lower()


def publisher_name(dataset: Dict[str, Any]) -> str:
    """
    Get publisher name from CKAN organization metadata.
    """
    organisation = dataset.get("organization") or {}
    return str(organisation.get("title") or organisation.get("name") or "").lower()


def has_csv_resource(dataset: Dict[str, Any]) -> bool:
    """
    Check if a dataset has a CSV resource.
    """
    for resource in dataset.get("resources", []):
        resource_format = str(resource.get("format", "")).upper().strip()
        resource_url = resource.get("url")

        if resource_format == "CSV" and resource_url:
            return True

    # Backup if the format field is messy.
    for resource in dataset.get("resources", []):
        text = " ".join(
            [
                str(resource.get("name", "")),
                str(resource.get("description", "")),
                str(resource.get("url", "")),
            ]
        ).lower()

        if "csv" in text and resource.get("url"):
            return True

    return False


def choose_csv_resource(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return the best CSV resource from the dataset.
    """
    resources = dataset.get("resources", [])

    # First choice: exact CSV format.
    for resource in resources:
        resource_format = str(resource.get("format", "")).upper().strip()
        resource_url = resource.get("url")

        if resource_format == "CSV" and resource_url:
            return resource

    # Backup: CSV mentioned in name, description, or URL.
    for resource in resources:
        text = " ".join(
            [
                str(resource.get("name", "")),
                str(resource.get("description", "")),
                str(resource.get("url", "")),
            ]
        ).lower()

        if "csv" in text and resource.get("url"):
            return resource

    raise RuntimeError(f"No CSV resource found for dataset: {dataset.get('title')}")


# =============================================================================
# 4. Scoring and selecting candidate datasets
# =============================================================================

def score_dataset(
    dataset: Dict[str, Any],
    product_key: str,
    settings: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Score one dataset.

    The app keeps the newest high-scoring candidate.

    A candidate must:
        - look like the right product
        - not be a user guide or centroid file
        - have a CSV resource
        - come from an expected publisher
    """
    title = str(dataset.get("title", ""))
    title_lower = title.lower()
    blob = dataset_text_blob(dataset)
    publisher = publisher_name(dataset)

    # Reject unwanted records.
    for phrase in settings["reject_phrases"]:
        if phrase in blob:
            return None

    # Must contain one of the product identifiers.
    if not any(phrase in blob for phrase in settings["canonical_phrases"]):
        return None

    # Must have a CSV resource.
    if not has_csv_resource(dataset):
        return None

    # If publisher metadata is present, require an expected publisher.
    if publisher:
        if not any(allowed in publisher for allowed in settings["allowed_publishers"]):
            return None

    # Find release/update date.
    release_date = parse_month_year_from_text(title)
    date_source = "title_month_year"

    if release_date is None and settings["allow_metadata_date_fallback"]:
        release_date = parse_metadata_modified(str(dataset.get("metadata_modified", "")))
        date_source = "metadata_modified"

    if release_date is None:
        return None

    score = 0
    reasons: List[str] = []

    if settings["strong_title_phrase"] in title_lower:
        score += 50
        reasons.append("canonical product phrase in title")

    if "hosted table" in title_lower:
        score += 30
        reasons.append("hosted table in title")

    if "office for national statistics" in publisher:
        score += 25
        reasons.append("publisher is Office for National Statistics")

    if product_key == "NSPL" and "london borough of camden" in publisher:
        score += 10
        reasons.append("rolling NSPL record from Camden/data.gov.uk")

    if has_csv_resource(dataset):
        score += 20
        reasons.append("has CSV resource")

    if date_source == "title_month_year":
        score += 10
        reasons.append("release date found in title")
    else:
        reasons.append("date taken from metadata_modified")

    return {
        "score": score,
        "release_date": release_date,
        "release_date_text": date_tuple_to_text(release_date),
        "date_source": date_source,
        "dataset": dataset,
        "reasons": reasons,
    }


def find_candidates_for_product(product_key: str) -> List[Dict[str, Any]]:
    """
    Return scored candidate datasets for one product.

    The result is sorted by:
        1. newest release/update date
        2. highest score
    """
    if product_key not in PRODUCTS:
        raise ValueError(f"Unknown product {product_key}. Choose from: {list(PRODUCTS)}")

    settings = PRODUCTS[product_key]
    candidates_by_id: Dict[str, Dict[str, Any]] = {}

    for query in settings["queries"]:
        results = call_package_search(query, rows=100)

        for dataset in results:
            dataset_id = str(dataset.get("id", ""))

            if not dataset_id:
                continue

            scored = score_dataset(dataset, product_key, settings)

            if scored is None:
                continue

            existing = candidates_by_id.get(dataset_id)

            if existing is None or scored["score"] > existing["score"]:
                scored["matched_query"] = query
                candidates_by_id[dataset_id] = scored

    candidates = list(candidates_by_id.values())

    candidates.sort(
        key=lambda row: (
            row["release_date"],
            row["score"],
        ),
        reverse=True,
    )

    return candidates


def get_latest_product(product_key: str) -> Dict[str, Any]:
    """
    Return the selected latest product plus its CSV resource.
    """
    candidates = find_candidates_for_product(product_key)

    if not candidates:
        raise RuntimeError(
            f"No usable CSV dataset found for {product_key}. "
            f"Try relaxing filters or checking data.gov.uk manually."
        )

    selected = candidates[0]
    dataset = selected["dataset"]
    csv_resource = choose_csv_resource(dataset)

    return {
        "product_key": product_key,
        "friendly_name": PRODUCTS[product_key]["friendly_name"],
        "selected": selected,
        "dataset": dataset,
        "csv_resource": csv_resource,
        "candidates": candidates,
    }


def dataset_page_url(dataset: Dict[str, Any]) -> str:
    """
    Build a readable data.gov.uk page URL when possible.
    """
    dataset_id = str(dataset.get("id", ""))
    dataset_name = str(dataset.get("name", ""))

    if dataset_id and dataset_name:
        return f"https://www.data.gov.uk/dataset/{dataset_id}/{dataset_name}"

    if dataset_id:
        return f"https://www.data.gov.uk/dataset/{dataset_id}"

    return ""
