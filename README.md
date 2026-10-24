# SOLAR RAYS ENERGY SOLUTIONS LLP — Quotation Web App

A **complete, ready-to-deploy Streamlit application** that creates branded, three-page PDF quotations for solar power projects. **Run `app.py`**. There are **no update, installer or repair scripts** in this repository.

## Deploy on Streamlit Community Cloud (new GitHub repository)

1. Download `SolarRays_GitHub_Ready.zip` and **extract it on your computer**.
2. Sign into GitHub and choose **New repository** (for example `solarrays-quotation`).
3. Create the repository on the **`main`** branch.
4. Select **Add file → Upload files**. Upload all the extracted files (`app.py`, `pdf_engine.py`, `LOGO_SOLARNEW.jpg`, `requirements.txt`, `README.md` and `.gitignore` if visible). **Do not upload the ZIP by itself**; GitHub does not automatically extract ZIP files into executable source files.
5. Open https://share.streamlit.io/ and select **Create app → Deploy a public app from GitHub** (wording may vary).
6. Select your new GitHub repository and set:
   - **Branch:** `main`
   - **Main file path:** `app.py`
7. Click **Deploy**. Streamlit automatically installs the dependencies from `requirements.txt`.

The new repository must show `app.py` and `pdf_engine.py` at the top level. **Never rename `apply_solar_rays_update.py` or any installer to `app.py`.**

### Alternative: deploy from a new folder in an existing GitHub repository

Upload all the extracted files into one folder, e.g. `solar-rays-app/`. The Streamlit **Main file path** must then be `solar-rays-app/app.py` (with the same branch). Keep `pdf_engine.py` and `LOGO_SOLARNEW.jpg` in that same folder.

## Running on your computer

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Python 3.10 or newer is recommended. Open the local address shown by Streamlit (typically http://localhost:8501).

## Included files

| File | Role |
| --- | --- |
| `app.py` | **Actual Streamlit web application** — the entry point |
| `pdf_engine.py` | Branded quotation PDF creator |
| `LOGO_SOLARNEW.jpg` | Your supplied Solar Rays company logo |
| `requirements.txt` | Python packages automatically installed on deploy |
| `README.md` | Setup instructions |
| `.gitignore` | Excludes local DB and Python cache files |

## Company details preconfigured

**SOLAR RAYS ENERGY SOLUTIONS LLP**  
12A/220, VRINDAVAN COLONY Utrahtia Railway Station Lucknow, Lucknow, Uttar Pradesh, 226029  
**GSTIN:** 09AFUFS6953D1ZA  
**State Code:** 09  
**State:** Uttar Pradesh

The name appears in uppercase in the web header and generated PDF. These defaults can be changed under **Company Settings**. The supplied logo is displayed on the webpage and every page of new PDFs. You may also upload a different logo.

## Quotation workflow

1. Enter the customer, system type and capacity.
2. Choose a solar module manufacturer. When selecting **Other**, type the make; the app requires it before creating the PDF.
3. Optionally enter an **Other** inverter make or a custom mounting structure make.
4. The **BOQ** and **Detailed Material Specification** are populated automatically.
5. Open **Manually enter makes and design specifications** to replace *As per approved design*, *Standard approved make*, *As per system*, etc. with exact makes or specifications. Click **Apply manual specifications** so the changes appear in the tables and PDF. Any table cell can also be edited directly.
6. Enter commercial details, GST, subsidies, terms and quotation reference.
7. Click **Build Quotation PDF**, download it, and optionally **Save to History**.

The PDF contains a cover/project summary, commercial quotation with BOQ and pricing, and detailed materials with registered company details. A new quotation will always use the most recently saved company settings; previously saved PDFs do not change automatically.

## Important limitation on Streamlit Community Cloud

This prototype stores saved quotation history and company-setting changes in a local SQLite file. On a cloud redeployment, app reboot or sleeping instance, **local files may disappear or reset**. PDFs should be downloaded and archived separately. For permanent production records, connect a managed PostgreSQL database or Supabase and add authentication. Do not store confidential or sensitive customer details in a public app without access controls.

No real passwords, customer data, SQLite database, workflow keep-alive scripts, or update installers are included in this ZIP.
