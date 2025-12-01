import pandas as pd
import streamlit as st

st.title("KDP Sales Extractor")

uploaded_file = st.file_uploader("Upload your KDP Excel file (.xlsx)", type=["xlsx"])


@st.cache_data(ttl=3600)
def process_sheet(df, sheet_name):
    with st.expander(f"📄 Sheet: {sheet_name}", expanded=False):
        if "Royalty Date" not in df.columns:
            st.error(f"'Royalty Date' column not found in {sheet_name}. Skipping this sheet.")
            return

        df["Royalty Date"] = pd.to_datetime(df["Royalty Date"], errors="coerce")
        df["Year"] = df["Royalty Date"].dt.year
        df["Month-Year"] = df["Royalty Date"].dt.strftime("%b-%Y")

        # Show preview
        df_show = df.copy()
        df_show["Royalty Date"] = df_show["Royalty Date"].dt.strftime("%B-%Y")
        df_show.index = range(1, len(df_show) + 1)
        st.subheader("Preview")
        st.dataframe(df_show)

        # --- YEARLY SUMMARY ---
        if "Royalty" in df.columns:
            royalty_summary = df.groupby(["Year", "Title"], as_index=False)["Royalty"].sum()
        else:
            st.error(f"'Royalty' column not found in {sheet_name}.")
            royalty_summary = pd.DataFrame(columns=["Year", "Title", "Royalty"])

        possible_units = ["Units Sold", "Units", "Units_Sold"]
        units_col = next((col for col in possible_units if col in df.columns), None)
        if units_col:
            units_summary = df.groupby(["Year", "Title"], as_index=False)[units_col].sum()
        else:
            st.error(f"No units column found in {sheet_name}.")
            units_summary = pd.DataFrame(columns=["Year", "Title", "Units Sold"])

        if not royalty_summary.empty and not units_summary.empty:
            merged_summary = pd.merge(royalty_summary, units_summary, on=["Year", "Title"])
            merged_summary["Royalty"] = merged_summary["Royalty"].map("${:,.2f}".format)
            merged_summary.index = range(1, len(merged_summary) + 1)
            st.subheader("Yearly Summary")
            st.dataframe(merged_summary)

        # --- MONTHLY SUMMARY ---
        if not df.empty and units_col:
            monthly_summary = df.groupby(["Year", "Month-Year", "Title"], as_index=False).agg({
                "Royalty": "sum",
                units_col: "sum"
            })
            monthly_summary["Royalty"] = monthly_summary["Royalty"].map("${:,.2f}".format)
            monthly_summary.index = range(1, len(monthly_summary) + 1)
            st.subheader("Monthly Summary")
            st.dataframe(monthly_summary)


if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = ["eBook Royalty", "Paperback Royalty", "Hardcover Royalty", "Combined Sales"]

        for sheet in sheet_names:
            df = pd.read_excel(uploaded_file, sheet_name=sheet)
            process_sheet(df, sheet)

        st.success("All sheets processed successfully!")

    except Exception as e:
        st.error(f"Error reading file: {e}")
