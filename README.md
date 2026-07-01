# Auto-Downloader for latest NSPL / ONSPD

This repository contains three ways to get the latest NSPLD and ONSPD datasets

- **NSPL** — National Statistics Postcode Lookup
- **ONSPD** — ONS Postcode Directory

I. Method 1 - Use the cloud based Streamlit app
   Usability - Easiest, Just a couple of clicks 
   Complexity - High - python script contains the code, hosted on github, deployed on streamlit
    
   
Steps:
    
1. Use this streamlit link to the cloud based app: https://nsplonspddownloader.streamlit.app/
2. Select both NSPL and ONSPD datasets
3. Click 'Find Latest CSV Resources'
4. Click both 'Download CSV from source'
5. Check your browser's download folders

Notes:
The app is designed for deployment from GitHub to Streamlit Community Cloud.

## What the app does
The app:
1. Calls the data.gov.uk CKAN search API.
2. Searches for NSPL and/or ONSPD hosted-table datasets.
3. Rejects likely wrong results, such as user guides and centroid datasets.
4. Scores candidate datasets.
5. Selects the newest usable CSV resource.
6. Shows a direct download link for the source CSV.
7. The app gives the direct source link instead of downloading the file through Streamlit.

II. Method 2 - Download and Run the python notebook 
    Usability - Medium - Hardest step is installing a python platform (Jupyter notebook)
    Complexity - Low - Single python notebook contains all the script, low chance of error

Steps:
1. Install Jupyter Notebook using your terminal https://jupyter.org/install#jupyter-notebook
2. download 

## Files in this repository

| File | Purpose |
|---|---|
| `app.py` | Streamlit user interface |
| `nspl_onspd_downloader.py` | Search, scoring and CSV resource selection logic |
| `requirements.txt` | Python packages needed by Streamlit Cloud |
| `.gitignore` | Files/folders Git should ignore |
| `README.md` | This guide |

## How the search works

The app calls:

```text
https://data.gov.uk/api/action/package_search
```

It sends:

```python
params = {
    "q": query,
    "rows": 100,
    "sort": "metadata_modified desc",
}
```

The app uses the following keys from the data.gov.uk / CKAN response.

Dataset-level keys:

```text
id
name
title
notes
metadata_modified
organization.title
organization.name
```

Resource-level keys:

```text
resources[].name
resources[].description
resources[].format
resources[].url
```

The app chooses a resource where:

```text
resources[].format == "CSV"
```

If the `format` field is messy, it also checks whether `CSV` appears in the resource name, description or URL.

## Search queries used

For **NSPL**:

```python
[
    '"National Statistics Postcode Lookup" "Hosted Table"',
    '"National Statistics Postcode Lookup UK"',
    'NSPL "National Statistics Postcode Lookup"',
]
```

For **ONSPD**:

```python
[
    '"ONS Postcode Directory" "Hosted Table"',
    'ONSPD "Hosted Table"',
    '"ONS Postcode Directory" "United Kingdom" "CSV"',
]
```

## What the app rejects

The app rejects candidate datasets containing:

```text
user guide
centroid
online ons postcode directory
live postcodes
```

This reduces the chance of selecting a guide, a centroid-only file, or an unrelated postcode service.

## Run locally

Create and activate a virtual environment if you want:

```bash
python -m venv .venv
```

On Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
streamlit run app.py
```

## Deploy to Streamlit Community Cloud

1. Create a new GitHub repository.
2. Upload these files to the repository.
3. Go to Streamlit Community Cloud.
4. Choose **New app**.
5. Select your GitHub repository.
6. Set the main file path to:

```text
app.py
```

7. Deploy.

## Important note about ONSPD

ONSPD can be very large. It may be several GB depending on the release.

For that reason, this app provides a **direct download link** from the source rather than trying to load the whole CSV into Streamlit memory.

## References

- data.gov.uk API documentation: https://guidance.data.gov.uk/get_data/api_documentation/
- CKAN API guide: https://docs.ckan.org/en/latest/api/
- CKAN Python/CLI project: https://github.com/ckan/ckanapi
- CKAN resource utilities: https://github.com/reubano/ckanutils
- ONS postcode products: https://www.ons.gov.uk/methodology/geography/geographicalproducts/postcodeproducts
- Rolling NSPL dataset: https://www.data.gov.uk/dataset/7ec10db7-c8f4-4a40-8d82-8921935b4865/national-statistics-postcode-lookup-uk
- Example ONSPD hosted table: https://www.data.gov.uk/dataset/65a2ee49-d331-41c9-b09f-c7defc68b965/ons-postcode-directory-may-2026-for-the-united-kingdom-hosted-table
