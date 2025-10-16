import streamlit as st
import pandas as pd
import base64
from pathlib import Path
import plotly.express as px

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="SEF Carbon (Scope 1 & 2) – Australia", layout="centered")

# ------------------ STYLES ------------------
st.markdown(
    """
    <style>
        .sef-header {
            background: linear-gradient(90deg, #0ea5e9 0%, #10b981 100%);
            color: white;
            border-radius: 12px;
            padding: 14px 18px;
            margin-bottom: 20px;
        }
        .sef-header h1 { font-size: 1.6rem; margin: 0; color: white; }
        .sef-header p  { margin: 4px 0 0 0; font-size: 0.9rem; opacity: 0.95; }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------ HEADER WITH LARGE LOGO ------------------
def show_svg(svg_file: str, height: int = 120):
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

col1, col2 = st.columns([1, 6])
with col1:
    show_svg("assets/Sustainable Equine Program.svg", height=120)
with col2:
    st.markdown(
        """
        <div class="sef-header">
            <h1>Sustainable Equine Futures · Carbon Calculator</h1>
            <p>Developed by Vets for Climate Action · Using NGA 2024/25 emission factors by state</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# ------------------ INTRO ------------------
st.markdown(
    "This calculator estimates **Scope 1** and **Scope 2** emissions for Australian veterinary clinics. "
    "Replace placeholder factors in `nga_factors_2024.csv` with current NGA values before use."
)

# ------------------ LOAD FACTORS ------------------
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

# ------------------ INPUTS ------------------
st.header("1) Clinic profile")
state = st.selectbox("State/Territory", ["NSW","QLD","VIC","SA","WA","TAS","ACT","NT"])
fte = st.number_input("FTE staff (for intensity)", min_value=0.0, value=10.0, step=0.5)
reporting_year = st.selectbox("Reporting year", ["2024-25","2023-24","Custom"])
clinic_name = st.text_input("Clinic name (optional)", placeholder="e.g., WestVets Brisbane")

st.header("2) Grid Electricity (Scope 2)")
elec_kwh = st.number_input("Grid electricity used (kWh)", min_value=0.0, step=100.0)

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

# ------------------ CALCULATIONS ------------------
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

# ------------------ RESULTS ------------------
st.header("4) Results")
res = pd.DataFrame({
    "Metric": ["Scope 1 (fuels)", "Scope 1 (anaesthetic gases)", "Scope 1 (total)", "Scope 2 (electricity)", "Total (kgCO2e)"],
    "Value (kgCO2e)": [scope1_fuels, scope1_anaes, scope1, scope2, total]
})
st.dataframe(res, use_container_width=True)
st.write(f"**Intensity (kgCO2e per FTE):** {intensity_per_fte:,.2f}")
if fte == 0:
    st.caption("Enter FTE > 0 to show intensity.")

# ------------------ VISUALS ------------------
st.subheader("Visual Summary")

# PIE: % breakdown of Grid electricity, Anaesthetic agents, and Fuel
pie_df = pd.DataFrame({
    "Category": ["Grid electricity", "Anaesthetic agents", "Fuel"],
    "Emissions (kg CO2e)": [scope2, scope1_anaes, scope1_fuels],
})
pie = px.pie(
    pie_df,
    names="Category",
    values="Emissions (kg CO2e)",
    title="Emissions breakdown (%)",
    hole=0.35
)
# Show % labels on the pie and the absolute values in hover
pie.update_traces(textinfo="percent+label", hovertemplate="%{label}: %{value:,.2f} kg CO₂e")
st.plotly_chart(pie, use_container_width=True)

# BAR: keep your existing by-category bar (optional tweak to align labels)
by_cat = pie_df.rename(columns={"Category": "Metric", "Emissions (kg CO2e)": "Value (kgCO2e)"})
bar = px.bar(
    by_cat,
    x="Metric",
    y="Value (kgCO2e)",
    title="Emissions by Category",
    text_auto=".2s"
)
bar.update_layout(xaxis_title="", yaxis_title="kg CO₂e")
st.plotly_chart(bar, use_container_width=True)

# ------------------ DOWNLOAD ------------------
st.subheader("Download your results")
res_csv = res.to_csv(index=False)
st.download_button("Download results (CSV)", data=res_csv, file_name="sef_results.csv", mime="text/csv")

st.divider()
st.caption("Emission factors: DCCEEW NGA (location-based). Verify factors and units before pilot use.")
