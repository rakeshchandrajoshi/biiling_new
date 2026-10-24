"""SOLAR RAYS ENERGY SOLUTIONS LLP quotation manager.

Streamlit Community Cloud entry point: app.py
This is the actual application, NOT an installation or repair script.
"""
from __future__ import annotations

import base64
import html
import json
import math
import sqlite3
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import streamlit as st

from pdf_engine import default_boq, default_materials, generate_quote_pdf

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "solar_quotes.db"
LOGO_PATH = ROOT / "LOGO_SOLARNEW.jpg"
COMPANY_NAME = "SOLAR RAYS ENERGY SOLUTIONS LLP"
COMPANY_ADDRESS = "12A/220, VRINDAVAN COLONY Utrahtia Railway Station Lucknow, Lucknow, Uttar Pradesh, 226029"

st.set_page_config(page_title="Solar Rays | Quotation Management", page_icon="☀️", layout="wide")
st.markdown("""
<style>
.block-container {max-width:1400px; padding-top:1.35rem; padding-bottom:2rem;}
.sr-banner {border:1px solid #d8e0ea; border-radius:16px; padding:20px 24px;
            background:linear-gradient(110deg,#fff5d1, #ffffff 55%, #eefbf0); margin-bottom:12px;}
.sr-banner h1 {font-size:1.65rem; margin:0 0 6px 0; color:#142336;}
.sr-banner p {margin:0; color:#48586c; font-size:.95rem;}
.sr-legal {margin:8px 0 12px 0; line-height:1.55; color:#3f5265;}
</style>
""", unsafe_allow_html=True)

DEFAULT_SETTINGS: Dict[str, Any] = {
    "company_name": COMPANY_NAME,
    "tagline": "Clean solar. Smarter savings.",
    "website": "https://solarraysenergy.com/",
    "phone1": "99365 33017",
    "phone2": "90050 93327",
    "email": "",
    "gstin": "09AFUFS6953D1ZA",
    "state_code": "09",
    "state": "Uttar Pradesh",
    "registered_address": COMPANY_ADDRESS,
    "office_address": COMPANY_ADDRESS,
    "bank_account_name": COMPANY_NAME,
    "bank_name": "",
    "bank_account": "",
    "ifsc": "",
    "bank_branch": "",
    "intro_text": (
        "SOLAR RAYS ENERGY SOLUTIONS LLP designs, deploys and maintains high-performance "
        "rooftop solar power systems focused on long-term savings, reliable engineering "
        "and energy independence."
    ),
    "logo_b64": "",
}


def get_conn():
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK(id=1), json_data TEXT NOT NULL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS quotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_ref TEXT UNIQUE NOT NULL,
            quote_date TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            phone TEXT,
            capacity_kw REAL,
            system_type TEXT,
            grand_total REAL,
            status TEXT DEFAULT 'Draft',
            json_data TEXT NOT NULL,
            pdf_blob BLOB NOT NULL,
            created_at TEXT NOT NULL)""")
        conn.execute("INSERT OR IGNORE INTO settings (id, json_data) VALUES (1, ?)",
                     (json.dumps(DEFAULT_SETTINGS),))
        conn.commit()


def load_settings() -> Dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT json_data FROM settings WHERE id=1").fetchone()
    saved = json.loads(row["json_data"]) if row else {}
    result = dict(DEFAULT_SETTINGS)
    result.update(saved)
    result["company_name"] = str(result.get("company_name") or COMPANY_NAME).upper()
    return result


def save_settings(settings: Dict[str, Any]):
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (id, json_data) VALUES (1, ?)",
                     (json.dumps(settings),))
        conn.commit()


def save_quote(snapshot: Dict[str, Any], pdf: bytes):
    project, customer, commercial = snapshot["project"], snapshot["customer"], snapshot["commercial"]
    with get_conn() as conn:
        conn.execute("""INSERT INTO quotations
            (quote_ref, quote_date, customer_name, phone, capacity_kw, system_type,
             grand_total, status, json_data, pdf_blob, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
            snapshot["quote_ref"], snapshot["quote_date"], customer.get("name", ""),
            customer.get("phone", ""), float(project.get("capacity_kw", 0) or 0),
            project.get("system_type", ""), float(commercial.get("grand_total", 0) or 0),
            "Draft", json.dumps(snapshot), sqlite3.Binary(pdf),
            datetime.now().isoformat(timespec="seconds")))
        conn.commit()


def quote_history() -> pd.DataFrame:
    with get_conn() as conn:
        rows = conn.execute("""SELECT id, quote_ref, quote_date, customer_name, phone,
            capacity_kw, system_type, grand_total, status, created_at
            FROM quotations ORDER BY id DESC""").fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def get_quote_pdf(quote_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT quote_ref, pdf_blob FROM quotations WHERE id=?", (quote_id,)).fetchone()
    return (row["quote_ref"], bytes(row["pdf_blob"])) if row else (None, None)


def update_status(quote_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE quotations SET status=? WHERE id=?", (status, quote_id))
        conn.commit()


def delete_quote(quote_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM quotations WHERE id=?", (quote_id,))
        conn.commit()


def fy_label(d: date) -> str:
    yr = d.year if d.month >= 4 else d.year - 1
    return f"{yr}-{(yr + 1) % 100:02d}"


def next_quote_ref(d: date, system_type: str) -> str:
    prefix = f"SRES/{fy_label(d)}/{ {'On-Grid':'ON','Hybrid':'HYB','Off-Grid':'OFF'}.get(system_type,'SOL') }/"
    with get_conn() as conn:
        rows = conn.execute("SELECT quote_ref FROM quotations WHERE quote_ref LIKE ?", (prefix + "%",)).fetchall()
    seqs = []
    for r in rows:
        try:
            seqs.append(int(str(r["quote_ref"]).rsplit("/", 1)[-1]))
        except (ValueError, IndexError):
            continue
    return prefix + f"{(max(seqs) + 1) if seqs else 1:04d}"


def df_records(frame: pd.DataFrame):
    return frame.fillna("").to_dict(orient="records")


def fmt_money(amount: Any) -> str:
    return f"₹{float(amount):,.0f}"


def logo_preview(settings):
    if settings.get("logo_b64"):
        try:
            return BytesIO(base64.b64decode(settings["logo_b64"], validate=True))
        except (ValueError, base64.binascii.Error):
            pass
    return str(LOGO_PATH) if LOGO_PATH.exists() else None


def show_manual_entry_form():
    """Offer explicit inputs for each generic BOQ/material make, quantity or description.

    The same underlying dataframe is consumed by the PDF generator, so custom
    values cannot be lost between the web form and the quotation PDF.
    """
    phrases = ("as per approved design", "standard approved make", "as per site design",
               "as per system", "as per module layout", "as per approved electrical design")
    candidates = []
    for table_key, title in (("boq_df", "BOQ"), ("material_df", "Materials")):
        frame = st.session_state[table_key]
        for idx, row in frame.iterrows():
            name = str(row.get("Component", row.get("Description", f"Row {idx + 1}")))
            for col in ("Make", "Quantity", "Description"):
                if col in frame.columns and any(p in str(row.get(col, "")).lower() for p in phrases):
                    candidates.append((table_key, title, idx, name, col, str(row[col])))
    if not candidates:
        st.caption("All predefined generic specifications have been replaced. You can still edit any BOQ or material cell below.")
        return

    with st.expander("✍️ Manually enter makes and design specifications", expanded=False):
        st.caption("Use these fields for 'As per approved design', 'Standard approved make', "
                   "generic quantities and other placeholders. Click Apply, then generate the PDF.")
        with st.form("manual_specifications"):
            updates = []
            for table_key, title, idx, name, col, value in candidates:
                field_key = f"spec_{table_key}_{idx}_{col}"
                proposed = st.text_input(f"{title} · {name[:54]} · {col}",
                                         value=value, key=field_key)
                updates.append((table_key, idx, col, value, proposed))
            if st.form_submit_button("Apply manual specifications", type="primary"):
                modified = 0
                for table_key, idx, col, old, proposed in updates:
                    replacement = proposed.strip()
                    if replacement and replacement != old:
                        st.session_state[table_key].at[idx, col] = replacement
                        modified += 1
                if modified:
                    st.session_state.editor_version += 1
                    st.rerun()
                else:
                    st.info("No entries were changed. You can also edit the tables directly.")


init_db()
settings = load_settings()

head_logo, head_text = st.columns([1, 7], vertical_alignment="center")
with head_logo:
    preview = logo_preview(settings)
    if preview is not None:
        st.image(preview, width=140)
with head_text:
    st.markdown(
        "<div class='sr-banner'>"
        f"<h1>{html.escape(settings['company_name'].upper())}</h1>"
        "<p>Solar Quotation Management · Design, price and download professional solar proposals</p>"
        "</div>", unsafe_allow_html=True)
st.markdown(
    f"**Registered Address:** {settings.get('registered_address') or COMPANY_ADDRESS}  \n"
    f"**GSTIN:** {settings.get('gstin', '')}  |  "
    f"**State Code:** {settings.get('state_code', '09')}  |  "
    f"**State:** {settings.get('state', 'Uttar Pradesh')}")

new_tab, history_tab, settings_tab = st.tabs(
    ["➕ New Quotation", "📚 Quotation History", "⚙️ Company Settings"])

with new_tab:
    st.subheader("Customer & Project Details")
    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        customer_name = st.text_input("Customer name *", placeholder="Customer / organization name")
        customer_address = st.text_area("Installation / billing address", height=84)
    with c2:
        customer_phone = st.text_input("Mobile number")
        customer_email = st.text_input("Email")
        customer_gstin = st.text_input("Customer GSTIN (optional)")
    with c3:
        quote_date = st.date_input("Quotation date", value=date.today())
        system_type = st.selectbox("System type", ["On-Grid", "Hybrid", "Off-Grid"])
        capacity_kw = st.number_input("Plant capacity (kW)", min_value=0.5, max_value=1000.0,
                                      value=5.0, step=0.5)

    st.divider()
    st.subheader("Technical Configuration")
    p1, p2, p3, p4 = st.columns(4)
    module_selection = p1.selectbox("Solar module make", [
        "Waaree", "Adani Solar", "Vikram Solar", "RenewSys", "Tata Power Solar", "Other"])
    if module_selection == "Other":
        panel_brand = p1.text_input("Enter solar module make *", placeholder="Manufacturer name").strip()
    else:
        panel_brand = module_selection
    panel_wattage = p2.number_input("Module wattage (Wp)", min_value=300, max_value=800,
                                    value=580, step=5)
    phase = p3.selectbox("Phase", ["Single Phase", "Three Phase"])
    inverter_selection = p4.selectbox("Inverter make", [
        "Luminous", "Solis", "Sungrow", "Growatt", "GoodWe", "Fronius", "Other"])
    if inverter_selection == "Other":
        inverter_brand = p4.text_input("Enter inverter make *").strip()
    else:
        inverter_brand = inverter_selection

    q1, q2, q3 = st.columns(3)
    inverter_capacity_kw = q1.number_input("Inverter capacity (kW)", min_value=0.5,
                                           max_value=1000.0, value=float(capacity_kw), step=0.5)
    structure_choice = q2.selectbox("Mounting structure", [
        "GI / HDG", "Pre-GI", "Aluminium", "As per site design", "Other"])
    if structure_choice in ("Other", "As per site design"):
        structure_detail = q2.text_input("Enter mounting structure make / specification (optional)")
        structure_make = structure_detail.strip() or structure_choice
    else:
        structure_make = structure_choice
    net_metering = q3.selectbox("Net-metering scope", [
        "Included / assisted", "Customer scope", "Not applicable"])

    panels = int(math.ceil(float(capacity_kw) * 1000 / int(panel_wattage)))
    st.info(f"Suggested quantity: **{panels} modules** × {panel_wattage} Wp = "
            f"**{panels * panel_wattage / 1000:.2f} kWp** installed DC capacity")

    project = {
        "system_type": system_type, "capacity_kw": capacity_kw, "phase": phase,
        "panel_brand": panel_brand, "panel_wattage": panel_wattage, "panel_count": panels,
        "inverter_brand": inverter_brand, "inverter_capacity_kw": inverter_capacity_kw,
        "structure_make": structure_make,
    }
    signature = json.dumps(project, sort_keys=True)
    if st.session_state.get("project_signature") != signature:
        st.session_state.project_signature = signature
        st.session_state.boq_df = pd.DataFrame(default_boq(project))
        st.session_state.material_df = pd.DataFrame(default_materials(project))
        st.session_state.editor_version = st.session_state.get("editor_version", 0) + 1
        for key in list(st.session_state.keys()):
            if key.startswith("spec_"):
                del st.session_state[key]

    st.divider()
    st.subheader("Bill of Quantities")
    st.caption("Every description, make, quantity and unit can be edited. Values shown in these "
               "tables are the ones printed on the generated PDF.")
    show_manual_entry_form()
    st.session_state.boq_df = st.data_editor(
        st.session_state.boq_df, num_rows="dynamic", use_container_width=True,
        key=f"boq_editor_{st.session_state.editor_version}")
    with st.expander("Detailed Material Specification", expanded=False):
        st.session_state.material_df = st.data_editor(
            st.session_state.material_df, num_rows="dynamic", use_container_width=True,
            key=f"material_editor_{st.session_state.editor_version}")

    st.divider()
    st.subheader("Commercials")
    a1, a2, a3, a4 = st.columns(4)
    pricing_mode = a1.selectbox("Pricing mode", ["Lump sum", "Rate per kW"])
    if pricing_mode == "Rate per kW":
        rate_per_kw = a2.number_input("Rate per kW (₹)", min_value=0.0,
                                      value=50000.0, step=1000.0)
        basic_amount = float(capacity_kw) * float(rate_per_kw)
        a2.caption(f"Basic amount: {fmt_money(basic_amount)}")
    else:
        rate_per_kw = 0.0
        basic_amount = a2.number_input("Basic amount (₹)", min_value=0.0,
                                       value=250000.0, step=5000.0)
    discount = a3.number_input("Discount (₹)", min_value=0.0, value=0.0, step=1000.0)
    gst_rate = a4.number_input("GST (%)", min_value=0.0, max_value=28.0,
                               value=5.0, step=0.5)
    b1, b2, b3 = st.columns(3)
    other_charges = b1.number_input("Other charges (₹)", min_value=0.0, value=0.0, step=500.0)
    central_subsidy = b2.number_input("Central subsidy - indicative (₹)", min_value=0.0,
                                      value=0.0, step=1000.0)
    state_subsidy = b3.number_input("State subsidy - indicative (₹)", min_value=0.0,
                                    value=0.0, step=1000.0)
    taxable_value = max(float(basic_amount) - float(discount), 0.0)
    gst_amount = taxable_value * float(gst_rate) / 100
    grand_total = taxable_value + gst_amount + float(other_charges)
    total_subsidy = float(central_subsidy) + float(state_subsidy)
    effective_price = max(grand_total - total_subsidy, 0.0)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Taxable value", fmt_money(taxable_value))
    m2.metric("GST", fmt_money(gst_amount))
    m3.metric("Grand total", fmt_money(grand_total))
    m4.metric("Effective cost", fmt_money(effective_price))
    subsidy_note = st.text_area("Subsidy note", value=(
        "Subsidy is indicative and subject to eligibility, applicable rules and portal approval."), height=70)

    st.divider()
    st.subheader("Terms & Conditions")
    t1, t2 = st.columns(2)
    validity = t1.number_input("Quotation validity (days)", min_value=1, max_value=90, value=10)
    payment_terms = t1.text_input("Payment terms", value="100% advance, or as mutually agreed in purchase order.")
    delivery = t2.text_input("Delivery / commissioning timeline", value=(
        "Within 1–2 weeks from order and advance, subject to site readiness."))
    warranty = t2.text_input("Warranty", value="As per OEM warranty and final order terms.")
    material_note = st.text_area("Material note", value=(
        "Final makes, models and quantities are subject to site survey, availability, "
        "approved design and the mutually accepted purchase order."), height=75)
    quote_ref = st.text_input("Quotation reference", value=next_quote_ref(quote_date, system_type))

    make_pdf = st.button("📄 Build Quotation PDF", type="primary")
    if make_pdf:
        if not customer_name.strip():
            st.error("Please enter the customer name.")
        elif not quote_ref.strip():
            st.error("Please enter a quotation reference.")
        elif module_selection == "Other" and not panel_brand:
            st.error("Please enter the solar module make when 'Other' is selected.")
        elif inverter_selection == "Other" and not inverter_brand:
            st.error("Please enter the inverter make when 'Other' is selected.")
        else:
            snapshot = {
                "quote_ref": quote_ref.strip(),
                "quote_date": quote_date.strftime("%d/%m/%Y"),
                "settings": dict(settings),
                "customer": {"name": customer_name.strip(), "address": customer_address.strip(),
                             "phone": customer_phone.strip(), "email": customer_email.strip(),
                             "gstin": customer_gstin.strip()},
                "project": project,
                "boq": df_records(st.session_state.boq_df),
                "materials": df_records(st.session_state.material_df),
                "commercial": {
                    "pricing_mode": pricing_mode, "rate_per_kw": rate_per_kw,
                    "basic_amount": basic_amount, "discount": discount,
                    "taxable_value": taxable_value, "gst_rate": gst_rate,
                    "gst_amount": gst_amount, "other_charges": other_charges,
                    "grand_total": grand_total, "central_subsidy": central_subsidy,
                    "state_subsidy": state_subsidy, "total_subsidy": total_subsidy,
                    "effective_price": effective_price, "subsidy_note": subsidy_note,
                },
                "terms": {"validity_days": validity, "payment_terms": payment_terms,
                          "delivery_timeline": delivery, "warranty": warranty,
                          "net_metering": net_metering, "material_note": material_note},
            }
            try:
                pdf = generate_quote_pdf(snapshot)
                st.session_state.generated_quote = {"snapshot": snapshot, "pdf": pdf}
                st.success("Quotation PDF generated successfully.")
            except Exception as exc:
                st.error("Unable to generate the PDF. See technical details below.")
                st.exception(exc)

    generated = st.session_state.get("generated_quote")
    if generated:
        snapshot, pdf = generated["snapshot"], generated["pdf"]
        st.divider()
        st.subheader("Generated Quotation")
        x1, x2, x3 = st.columns([1, 1, 2])
        filename = snapshot["quote_ref"].replace("/", "-") + ".pdf"
        x1.download_button("⬇️ Download PDF", pdf, file_name=filename,
                           mime="application/pdf", use_container_width=True)
        if x2.button("💾 Save to History", use_container_width=True):
            try:
                save_quote(snapshot, pdf)
                st.success("Quotation saved.")
            except sqlite3.IntegrityError:
                st.error("This quotation number already exists. Change the reference and regenerate.")
        x3.caption("History uses local SQLite. On Streamlit Community Cloud this storage may "
                   "reset on redeployment or reboot; use persistent storage for production.")

with history_tab:
    st.subheader("Saved Quotations")
    hist = quote_history()
    if hist.empty:
        st.info("No saved quotations yet.")
    else:
        search = st.text_input("Search customer / quotation / phone")
        filtered = hist.copy()
        if search.strip():
            needle = search.strip()
            match = False
            for field in ("quote_ref", "customer_name", "phone"):
                match = match | filtered[field].astype(str).str.contains(needle, case=False, regex=False, na=False)
            filtered = filtered[match]
        show = filtered[["id", "quote_ref", "quote_date", "customer_name", "phone",
                         "capacity_kw", "system_type", "grand_total", "status"]].copy()
        show["grand_total"] = show["grand_total"].map(fmt_money)
        st.dataframe(show, use_container_width=True, hide_index=True)
        if not filtered.empty:
            selection = st.selectbox("Select a quotation", filtered["id"].tolist(),
                format_func=lambda qid: f"#{qid} · {filtered.loc[filtered['id']==qid, 'quote_ref'].iloc[0]}")
            selected = filtered.loc[filtered["id"] == selection].iloc[0]
            x1, x2, x3, x4 = st.columns(4)
            reference, saved_pdf = get_quote_pdf(int(selection))
            if saved_pdf:
                x1.download_button("⬇️ Download", saved_pdf,
                                   file_name=reference.replace("/", "-") + ".pdf",
                                   mime="application/pdf", use_container_width=True)
            statuses = ["Draft", "Sent", "Accepted", "Rejected", "Expired"]
            selected_status = x2.selectbox("Status", statuses,
                index=statuses.index(selected["status"]) if selected["status"] in statuses else 0)
            if x3.button("Update Status"):
                update_status(int(selection), selected_status)
                st.success("Status updated.")
                st.rerun()
            if x4.button("Delete Quotation"):
                delete_quote(int(selection))
                st.warning("Quotation deleted.")
                st.rerun()

with settings_tab:
    st.subheader("Company Settings")
    st.caption("Prefilled with the company details supplied. Changes saved here appear on "
               "newly generated PDFs. Existing saved PDFs do not change.")
    with st.form("company_settings_form"):
        s1, s2 = st.columns(2)
        company_name = s1.text_input("Registered company name", value=settings.get("company_name", COMPANY_NAME))
        tagline = s1.text_input("Tagline", value=settings.get("tagline", ""))
        website = s1.text_input("Website", value=settings.get("website", ""))
        email = s1.text_input("Email", value=settings.get("email", ""))
        phone1 = s1.text_input("Phone 1", value=settings.get("phone1", ""))
        phone2 = s1.text_input("Phone 2", value=settings.get("phone2", ""))
        gstin = s2.text_input("GSTIN", value=settings.get("gstin", ""))
        state_code = s2.text_input("State Code", value=settings.get("state_code", "09"))
        state = s2.text_input("State", value=settings.get("state", "Uttar Pradesh"))
        address = s2.text_area("Registered / office address", value=settings.get("registered_address", COMPANY_ADDRESS), height=94)
        st.markdown("#### Bank Details")
        b1, b2 = st.columns(2)
        account_name = b1.text_input("Bank account name", value=settings.get("bank_account_name", COMPANY_NAME))
        bank_name = b1.text_input("Bank name", value=settings.get("bank_name", ""))
        bank_account = b2.text_input("Account number", value=settings.get("bank_account", ""))
        ifsc = b2.text_input("IFSC", value=settings.get("ifsc", ""))
        bank_branch = b2.text_input("Branch", value=settings.get("bank_branch", ""))
        intro_text = st.text_area("Company introduction for PDF", value=settings.get("intro_text", ""), height=94)
        st.markdown("#### Logo")
        preview = logo_preview(settings)
        if preview is not None:
            st.image(preview, width=150)
        uploaded_logo = st.file_uploader("Upload a different company logo (PNG/JPG, optional)",
                                         type=["png", "jpg", "jpeg"])
        retain_custom = st.checkbox("Keep previously uploaded logo", value=True)
        submitted = st.form_submit_button("Save Company Settings", type="primary")
        if submitted:
            logo_b64 = settings.get("logo_b64", "") if retain_custom else ""
            if uploaded_logo is not None:
                logo_b64 = base64.b64encode(uploaded_logo.getvalue()).decode("ascii")
            updated = {
                "company_name": company_name.strip().upper() or COMPANY_NAME,
                "tagline": tagline.strip(), "website": website.strip(),
                "email": email.strip(), "phone1": phone1.strip(), "phone2": phone2.strip(),
                "gstin": gstin.strip(), "state_code": state_code.strip(), "state": state.strip(),
                "registered_address": address.strip(), "office_address": address.strip(),
                "bank_account_name": account_name.strip(), "bank_name": bank_name.strip(),
                "bank_account": bank_account.strip(), "ifsc": ifsc.strip(),
                "bank_branch": bank_branch.strip(), "intro_text": intro_text.strip(),
                "logo_b64": logo_b64,
            }
            save_settings(updated)
            st.success("Company settings saved.")
            st.rerun()
    st.info("Deployment note: SQLite files on Streamlit Community Cloud are not durable "
            "across all restarts. Use PostgreSQL or Supabase for permanent multi-user history.")
