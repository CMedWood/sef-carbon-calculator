
import streamlit as st
import pandas as pd
from io import StringIO
import base64
from pathlib import Path

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="SEF Carbon (Scope 1 & 2) – Australia", layout="centered")

# ------------------ STYLES ------------------
st.markdown("""
    <style>
        /* Header bar styling */
        .sef-header {
            background: linear-gradient(90deg, #0ea5e9 0%, #10b981 100%);
            color: white;
            border-radius: 12px;
            padding: 14px 18px;
            margin-bottom: 20px;
        }
        .sef-header h1 {
            font-size: 1.6rem;
            margin: 0;
            color: white;
        }
        .sef-header p {
            margin: 4px 0 0 0;
            font-size: 0.9rem;
            opacity: 0.95;
        }
    </style>
""", unsafe_allow_html=True)

# ------------------ HEADER WITH LARGE LOGO ------------------
def show_svg(svg_file: str, height: int = 120):
    """Display an SVG logo in Streamlit."""
    svg_path = Path(svg_file)
    if svg_path.exists():
        svg_bytes = svg_path.read_bytes()
        b64 = base64.b64encode(svg_bytes).decode()
        st.markdown(
            f'<img src="data:image/svg+xml;base64,{b64}" style="height:{height}px; margin-top:4px;">',
            unsafe_allow_html=True
        )
    else:
        st.warning(f"Logo file not found at {svg_file}")

# Layout: logo left, title right, banner background
col1, col2 = st.columns([1, 6])
with col1:
    show_svg("assets/Sustainable Equine Program.svg", height=120)
with col2:
    st.markdown("""
        <div class="sef-header">
            <h1>Sustainable Equine Futures · Carbon Calculator</h1>
            <p>Developed by Vets for Climate Action · Using NGA 2024/25 emission factors by state</p>
        </div>
    """, unsafe_allow_html=True)

# ------------------ MAIN INTRO ------------------
st.markdown("""
This simple calculator estimates **Scope 1** (fuel + optional anaesthetic gases) and **Scope 2** (grid electricity) emissions for Australian veterinary clinics.

- Emission factors are loaded from `nga_factors_2024.csv`. **Replace placeholder values** with the latest NGA factors before use.
- Units expected:
  - Electricity: **kWh**
  - Petrol/Diesel: **litres**
  - LPG: **litres**
  - Natural Gas: **MJ**
  - Anaesthetic agents: **grams**
""")

# ------------------ Sidebar (About) ------------------
with st.sidebar:
    st.header("About")
    st.write("Version: 0.2 (fresh starter, large logo)")
    st.write("Update emission factors annually when DCCEEW publishes new NGA tables.")
    st.write("Tip: Use the **Download results** button to keep a CSV record.")

# ------------------ Load factors ------------------
@st.cache_data
def load_factors(uploaded=None):
    if uploaded is not None:
        return pd.read_csv(uploaded)
    return pd.read_csv("nga_factors_2024.csv")

st.subheader("Load Emission Factors")
use_custom = st.toggle("Upload a custom factors CSV (optional)", value=False)
if use_custom:
    up = st.file_uploader("Upload your `nga_factors_2024.csv`", type=["csv"])
    if up:
        factors = load_factors(up)
    else:
        st.info("Using bundled `nga_factors_2024.csv` until a file is uploaded.")
        factors = load_factors()
else:
    factors = load_factors()

required_cols = ["category","subcategory","unit","factor","state","source","source_year"]
missing = [c for c in required_cols if c not in factors.columns]
if missing:
    st.error(f"`nga_factors_2024.csv` is missing these columns: {missing}. Please fix and reload.")
    st.stop()

def ef(category, subcategory=None, state=None):
    df = factors[factors["category"] == category].copy()
    if subcategory is not None:
        df = df[df["subcategory"] == subcategory]
    if state is not None:
        df = df[df["state"] == state]
    if df.empty:
        raise ValueError(f"No emission factor found for category='{category}', subcategory='{subcategory}', state='{state}'")
    val = df.iloc[0]["factor"]
    try:
        return float(val)
    except Exception as e:
        raise ValueError(f"Factor for {category}/{subcategory}/{state} is not numeric: {val}") from e

# ------------------ Inputs ------------------
st.header("1) Clinic profile")
state = st.selectbox("State/Territory", ["NSW","QLD","VIC","SA","WA","TAS","ACT","NT"])
fte = st.number_input("FTE staff (for intensity)", min_value=0.0, value=10.0, step=0.5)
reporting_year = st.selectbox("Reporting year", ["2024-25","2023-24","Custom"])
clinic_name = st.text_input("Clinic name (optional)", placeholder="e.g., WestVets Brisbane")

st.header("2) Electricity (Scope 2)")
elec_kwh = st.number_input("Grid electricity used (kWh)", min_value=0.0, step=100.0)
greenpower_pct = st.slider("GreenPower purchased (% of total kWh) – optional", 0, 100, 0)
st.caption("This calculator reports **location-based** Scope 2 using state factors. Market-based can be added later.")

st.header("3) Fuels (Scope 1)")
petrol_L = st.number_input("Petrol (L)", min_value=0.0, step=50.0)
diesel_L = st.number_input("Diesel (L)", min_value=0.0, step=50.0)
lpg_L = st.number_input("LPG (L)", min_value=0.0, step=10.0)
natgas_MJ = st.number_input("Natural gas (MJ)", min_value=0.0, step=100.0)

with st.expander("Advanced: Anaesthetic gases (optional, Scope 1 fugitive)"):
    use_anaes = st.checkbox("Include anaesthetic agents", value=False)
    iso_g = sev_g = des_g = n2o_g = 0.0
    if use_anaes:
        iso_g = st.number_input("Isoflurane (g)", min_value=0.0, step=10.0)
        sev_g = st.number_input("Sevoflurane (g)", min_value=0.0, step=10.0)
        des_g = st.number_input("Desflurane (g)", min_value=0.0, step=10.0)
        n2o_g = st.number_input("Nitrous oxide (g)", min_value=0.0, step=10.0)

# ------------------ Calculations ------------------
try:
    scope2 = elec_kwh * ef("electricity", state=state)
    scope1_fuels = (
        petrol_L * ef("fuel","petrol_L") +
        diesel_L * ef("fuel","diesel_L") +
        lpg_L * ef("fuel","lpg_L") +
        natgas_MJ * ef("fuel","natural_gas_MJ")
    )
    scope1_anaes = 0.0
    if use_anaes:
        scope1_anaes = (
            iso_g * ef("anaes","isoflurane_g") +
            sev_g * ef("anaes","sevoflurane_g") +
            des_g * ef("anaes","desflurane_g") +
            n2o_g * ef("anaes","n2o_g")
        )
    scope1 = scope1_fuels + scope1_anaes
    total = scope1 + scope2
    intensity_per_fte = total / fte if fte > 0 else 0.0
except Exception as e:
    st.error(f"Calculation error: {e}")
    st.stop()

# ------------------ Results ------------------
st.header("4) Results")
res = pd.DataFrame({
    "Metric": ["Scope 1 (fuels)", "Scope 1 (anaesthetic gases)", "Scope 1 (total)", "Scope 2 (electricity)", "Total (kgCO2e)"],
    "Value (kgCO2e)": [scope1_fuels, scope1_anaes, scope1, scope2, total]
})
st.dataframe(res, use_container_width=True)

st.write(f"**Intensity (kgCO2e per FTE):** {intensity_per_fte:,.2f}")
if fte == 0:
    st.caption("Enter FTE > 0 to show intensity.")

# ------------------ Download ------------------
st.subheader("Download your results")
results_dict = {
    "clinic_name": clinic_name,
    "state": state,
    "reporting_year": reporting_year,
    "fte": fte,
    "inputs": {
        "elec_kwh": elec_kwh,
        "greenpower_pct": greenpower_pct,
        "petrol_L": petrol_L,
        "diesel_L": diesel_L,
        "lpg_L": lpg_L,
        "natgas_MJ": natgas_MJ,
        "isoflurane_g": iso_g,
        "sevoflurane_g": sev_g,
        "desflurane_g": des_g,
        "n2o_g": n2o_g
    },
    "results_kgco2e": {
        "scope1_fuels": scope1_fuels,
        "scope1_anaes": scope1_anaes,
        "scope1_total": scope1,
        "scope2_electricity": scope2,
        "total": total,
        "intensity_per_fte": intensity_per_fte
    },
    "factors_note": "Replace placeholder factors in nga_factors_2024.csv with current NGA values before production use."
}
res_csv = pd.DataFrame.from_records(
    [(k, v) for k, v in results_dict["results_kgco2e"].items()],
    columns=["Metric","Value_kgCO2e"]
).to_csv(index=False)

st.download_button("Download results (CSV)", data=res_csv, file_name="sef_results.csv", mime="text/csv")

st.divider()
st.caption("Emission factors: DCCEEW NGA (location-based). This is a starter app; verify factors and units before pilot use.")
