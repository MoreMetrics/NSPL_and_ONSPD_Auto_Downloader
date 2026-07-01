"""
app.py

Streamlit app for finding the latest NSPL and ONSPD CSV resources.

Run locally:
    streamlit run app.py

Deploy on Streamlit Community Cloud:
    1. Push this repository to GitHub.
    2. Go to https://share.streamlit.io/
    3. Select the GitHub repository.
    4. Set main file path to app.py.
"""

from __future__ import annotations

import json

import streamlit as st

from nspl_onspd_downloader import (
    PRODUCTS,
    dataset_page_url,
    get_latest_product,
    publisher_name,
)


st.set_page_config(
    page_title="Latest NSPL / ONSPD Downloader",
    page_icon="📮",
    layout="wide",
)

st.title("📮 Latest NSPL / ONSPD Downloader")
st.caption(
    "Search data.gov.uk for the latest NSPL and ONSPD hosted-table CSV resources."
)

st.markdown(
    """
This app uses the **data.gov.uk CKAN API** to find the latest postcode-product CSV links.

It supports:

- **NSPL** — National Statistics Postcode Lookup
- **ONSPD** — ONS Postcode Directory

For large files, especially **ONSPD**, the app provides the direct source CSV link instead of forcing the file through Streamlit.
"""
)

with st.expander("How the search works", expanded=False):
    st.markdown(
        """
The app calls:

```text
https://data.gov.uk/api/action/package_search
```

It uses these API parameters:

```python
q = search query
rows = 100
sort = "metadata_modified desc"
```

It checks these dataset-level keys:

```text
id
name
title
notes
metadata_modified
organization.title
organization.name
```

It checks these resource-level keys:

```text
resources[].name
resources[].description
resources[].format
resources[].url
```

It rejects results that look like:

```text
user guide
centroid
online ons postcode directory
live postcodes
```
"""
    )

product_options = list(PRODUCTS.keys())

selected_products = st.multiselect(
    "Choose product(s) - You can select both NSPL and ONSPD",
    options=product_options,
    default=["NSPL"],
    format_func=lambda key: f"{key} — {PRODUCTS[key]['friendly_name']}",
)

search_button = st.button("Find latest CSV resources", type="primary")

if not selected_products:
    st.warning("Choose at least one product.")

if search_button and selected_products:
    for product_key in selected_products:
        st.divider()

        with st.spinner(f"Searching for {product_key}..."):
            try:
                result = get_latest_product(product_key)
            except Exception as error:
                st.error(f"Could not find {product_key}.")
                st.exception(error)
                continue

        dataset = result["dataset"]
        selected = result["selected"]
        csv_resource = result["csv_resource"]
        candidates = result["candidates"]

        st.subheader(f"{product_key}: {result['friendly_name']}")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Selected date", selected["release_date_text"])

        with col2:
            st.metric("Score", selected["score"])

        with col3:
            st.metric("Date source", selected["date_source"])

        st.markdown("### Selected dataset")

        dataset_url = dataset_page_url(dataset)
        publisher = publisher_name(dataset) or "Unknown"

        st.write(f"**Title:** {dataset.get('title', 'Unknown')}")
        st.write(f"**Publisher:** {publisher}")
        st.write(f"**metadata_modified:** {dataset.get('metadata_modified', 'Unknown')}")
        st.write(f"**Matched query:** `{selected.get('matched_query', 'Unknown')}`")
        st.write(f"**Why selected:** {', '.join(selected.get('reasons', []))}")

        if dataset_url:
            st.link_button("Open data.gov.uk dataset page", dataset_url)

        st.markdown("### CSV resource")

        st.write(f"**Resource name:** {csv_resource.get('name')}")
        st.write(f"**Resource format:** {csv_resource.get('format')}")
        st.code(csv_resource["url"], language="text")

        st.link_button("Download CSV from source", csv_resource["url"])

        st.download_button(
            label="Download selected metadata as JSON",
            data=json.dumps(
                {
                    "product_key": product_key,
                    "dataset": dataset,
                    "csv_resource": csv_resource,
                    "selection": {
                        "score": selected["score"],
                        "release_date_text": selected["release_date_text"],
                        "date_source": selected["date_source"],
                        "matched_query": selected.get("matched_query"),
                        "reasons": selected.get("reasons", []),
                    },
                },
                indent=2,
            ),
            file_name=f"{product_key.lower()}_selected_metadata.json",
            mime="application/json",
        )

        with st.expander("Show candidate datasets"):
            candidate_rows = []

            for candidate in candidates[:20]:
                candidate_dataset = candidate["dataset"]
                candidate_rows.append(
                    {
                        "title": candidate_dataset.get("title"),
                        "publisher": publisher_name(candidate_dataset),
                        "release_date": candidate["release_date_text"],
                        "date_source": candidate["date_source"],
                        "score": candidate["score"],
                        "matched_query": candidate.get("matched_query"),
                        "metadata_modified": candidate_dataset.get("metadata_modified"),
                        "dataset_url": dataset_page_url(candidate_dataset),
                    }
                )

            st.dataframe(candidate_rows, use_container_width=True)

st.divider()

st.markdown(
    """
### Notes

- The app does not store the CSV files anywhere, it provides the direct links instead.
- Streamlit Community Cloud storage is temporary.
- ONSPD can be several GB, so use the direct source link for that file.
"""
)
