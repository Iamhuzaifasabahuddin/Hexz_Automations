import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Publishing Guide System",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .info-box {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #f0f2f6;
        margin: 1rem 0;
    }
    .highlight {
        background-color: #ffffcc;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">📚 Publishing Management System</h1>', unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Select Section:", [
    "📏 Trim Size & Page Limits",
    "💰 Royalty Information",
    "📊 Quick Reference",
    "🔍 Format Checker"
])


if page == "📏 Trim Size & Page Limits":
    st.header("Trim Size & Page Limits")

    tab1, tab2, tab3 = st.tabs(["KDP Limits", "Ingram Limits", "Comparison"])

    with tab1:
        st.subheader("📘 KDP (Kindle Direct Publishing)")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Paperback Trim Size Limits")
            trim_data = {
                "Parameter": ["Minimum Width", "Minimum Height", "Maximum Width", "Maximum Height"],
                "Value": ["4 in", "6 in", "8.5 in", "11.69 in"]
            }
            st.dataframe(pd.DataFrame(trim_data), hide_index=True)

            st.markdown("### Hardcover Trim Sizes (Fixed Options)")
            hardcover_sizes = {
                "Size Option": [
                    "5.5 × 8.5 in",
                    "6 × 9 in",
                    "6.14 × 9.21 in",
                    "7 × 10 in",
                    "8.25 × 11 in"
                ],
                "Metric": [
                    "13.97 × 21.59 cm",
                    "15.24 × 22.86 cm",
                    "15.6 × 23.39 cm",
                    "17.78 × 25.4 cm",
                    "20.95 × 27.94 cm"
                ]
            }
            st.dataframe(pd.DataFrame(hardcover_sizes), hide_index=True)
            st.warning("⚠️ **KDP Hardcover:** Only these 5 specific trim sizes are available!")

        with col2:
            st.markdown("### Page Limits")
            page_data = {
                "Book Type": [
                    "All Books (Minimum)",
                    "Paperback Standard Color (Min)",
                    "Paperback (Maximum)",
                    "Hardcover (Minimum)",
                    "Hardcover (Maximum)"
                ],
                "Pages": [24, 72, 828, 76, 550]
            }
            st.dataframe(pd.DataFrame(page_data), hide_index=True)

        st.info("💡 **Note:** Standard color paperbacks require more pages due to binding requirements.")


    with tab2:
        st.subheader("📗 Ingram Spark")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Standard Page Limits")
            ingram_standard = {
                "Parameter": ["Minimum Pages", "Maximum Pages"],
                "Value": [18, 1200]
            }
            st.dataframe(pd.DataFrame(ingram_standard), hide_index=True)

        with col2:
            st.markdown("### Special Format (11 x 8.5 in)")
            ingram_special = {
                "Parameter": ["Trim Size", "Minimum Pages", "Maximum Pages"],
                "Value": ["11 x 8.5 in", 18, 400]
            }
            st.dataframe(pd.DataFrame(ingram_special), hide_index=True)

        st.warning(
            "⚠️ **Special Format Limitation:** The 11 x 8.5 in format has a lower maximum page count (400 vs 1200).")


    with tab3:
        st.subheader("📊 KDP vs Ingram Comparison")

        comparison_data = {
            "Feature": [
                "Minimum Pages (All)",
                "Maximum Pages (Standard)",
                "Paperback Max Pages",
                "Hardcover Max Pages",
                "Special Formats"
            ],
            "KDP": [
                "24 pages",
                "828 (Paperback)",
                "828",
                "550",
                "Limited"
            ],
            "Ingram": [
                "18 pages",
                "1200 pages",
                "1200",
                "1200",
                "11 x 8.5 in (max 400 pages)"
            ]
        }
        st.dataframe(pd.DataFrame(comparison_data), hide_index=True)

        st.success("✅ **Ingram Advantage:** Higher page count limits for most formats")
        st.info("✅ **KDP Advantage:** Simpler submission process, faster distribution")


elif page == "💰 Royalty Information":
    st.header("Royalty Distribution & Payment Schedule")

    tab1, tab2, tab3 = st.tabs(["Payment Timeline", "Royalty Rates", "Calculator"])

    with tab1:
        st.subheader("📅 Payment Timeline")

        st.markdown("### Monthly Payment Schedule")
        st.write("Royalties are paid approximately **60 days** after the end of the month in which sales occurred.")


        timeline_data = {
            "Month of Sale": ["January", "February", "March", "April", "May", "June"],
            "Payment Month": ["March", "April", "May", "June", "July", "August"],
            "Days Delay": ["~60 days", "~60 days", "~60 days", "~60 days", "~60 days", "~60 days"]
        }
        st.dataframe(pd.DataFrame(timeline_data), hide_index=True)

        st.markdown("---")


        st.markdown("### 🔍 Payment Date Calculator")
        sale_month = st.selectbox(
            "Select Month of Sale:",
            ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"]
        )

        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        sale_index = months.index(sale_month)
        payment_index = (sale_index + 2) % 12
        payment_month = months[payment_index]

        st.success(f"📌 Sales in **{sale_month}** will be paid in **{payment_month}** (approximately 60 days later)")

    with tab2:
        st.subheader("💵 Royalty Rate Information")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### KDP Royalty Options")
            kdp_royalty = {
                "Option": ["35% Royalty", "70% Royalty"],
                "Rate": ["35%", "70%"],
                "Requirements": [
                    "All prices, all markets",
                    "Price: $2.99-$9.99, specific markets"
                ]
            }
            st.dataframe(pd.DataFrame(kdp_royalty), hide_index=True)

            st.info(
                "**70% Royalty Requirements:**\n- Price between $2.99 and $9.99\n- Available in specific markets\n- Delivery costs deducted")

        with col2:
            st.markdown("### Ingram Spark Royalty")
            st.write("Royalty = List Price - Print Cost - Distribution Cut")
            st.write("")
            st.write("**Typical margins:** 40-60% depending on:")
            st.write("- Print costs")
            st.write("- Distribution channel")
            st.write("- Book specifications")

    with tab3:
        st.subheader("🧮 Simple Royalty Calculator")

        platform = st.radio("Select Platform:", ["KDP eBook", "KDP Paperback", "Ingram Spark"])

        if platform == "KDP eBook":
            price = st.number_input("List Price ($):", min_value=0.99, max_value=200.0, value=9.99, step=0.01)
            royalty_option = st.radio("Royalty Option:", ["35%", "70%"])

            if royalty_option == "35%":
                royalty = price * 0.35
            else:
                if 2.99 <= price <= 9.99:
                    delivery_cost = st.number_input("Delivery Cost ($):", min_value=0.0, value=0.15, step=0.01)
                    royalty = (price * 0.70) - delivery_cost
                else:
                    st.warning("⚠️ 70% royalty only available for prices $2.99-$9.99")
                    royalty = price * 0.35

            st.success(f"💰 Estimated Royalty per Sale: **${royalty:.2f}**")

        elif platform == "KDP Paperback":
            price = st.number_input("List Price ($):", min_value=0.01, value=14.99, step=0.01)
            print_cost = st.number_input("Printing Cost ($):", min_value=0.01, value=4.00, step=0.01)

            royalty = (price - print_cost) * 0.60
            st.success(f"💰 Estimated Royalty per Sale: **${royalty:.2f}**")
            st.info("KDP Paperback royalty is 60% of (List Price - Print Cost)")

        else:
            price = st.number_input("List Price ($):", min_value=0.01, value=19.99, step=0.01)
            print_cost = st.number_input("Printing Cost ($):", min_value=0.01, value=5.00, step=0.01)
            discount = st.slider("Wholesale Discount (%):", min_value=30, max_value=55, value=40)

            wholesale_price = price * (1 - discount / 100)
            royalty = wholesale_price - print_cost

            st.success(f"💰 Estimated Royalty per Sale: **${royalty:.2f}**")
            st.info(f"Calculation: (${price:.2f} × {100 - discount}%) - ${print_cost:.2f} = ${royalty:.2f}")


elif page == "📊 Quick Reference":
    st.header("Quick Reference Guide")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📏 Popular Trim Sizes")
        popular_sizes = {
            "Format": [
                "Mass Market",
                "Digest",
                "Trade Paperback",
                "US Trade",
                "Large Print",
                "Square"
            ],
            "Dimensions": [
                "4.25 × 6.87 in",
                "5.5 × 8.5 in",
                "5 × 8 in",
                "6 × 9 in",
                "7 × 10 in",
                "8.5 × 8.5 in"
            ],
            "Best For": [
                "Fiction novels",
                "Manuals, workbooks",
                "Fiction, poetry",
                "Most non-fiction",
                "Accessibility",
                "Photography, art"
            ]
        }
        st.dataframe(pd.DataFrame(popular_sizes), width="stretch", hide_index=True)

        st.markdown("### 📕 KDP Hardcover Sizes (Only)")
        kdp_hardcover = {
            "Inches": [
                "5.5 × 8.5",
                "6 × 9",
                "6.14 × 9.21",
                "7 × 10",
                "8.25 × 11"
            ],
            "Centimeters": [
                "13.97 × 21.59",
                "15.24 × 22.86",
                "15.6 × 23.39",
                "17.78 × 25.4",
                "20.95 × 27.94"
            ]
        }
        st.dataframe(pd.DataFrame(kdp_hardcover), width="stretch", hide_index=True)
        st.caption("⚠️ KDP hardcover limited to these 5 sizes only")

    with col2:
        st.markdown("### 💡 Key Reminders")
        st.info("""
        **Distribution Timeline:**
        - Sales in Month X → Payment in Month X+2
        - Example: January sales → March payment

        **KDP Requirements:**
        - Min pages: 24 (all) / 72 (color)
        - Max pages: 828 (paperback) / 550 (hardcover)

        **Ingram Advantages:**
        - Higher page limits (1200 standard)
        - More trim size options
        - Wider distribution network

        **Royalty Optimization:**
        - KDP eBook: Price $2.99-$9.99 for 70%
        - Paperback: Keep print costs low
        - Ingram: Balance discount vs. royalty
        """)

    st.markdown("---")

    st.markdown("### 📋 Pre-Publication Checklist")

    checklist_items = [
        "Verify trim size meets platform requirements",
        "Check page count is within limits",
        "Calculate printing costs",
        "Set competitive pricing for target royalty",
        "Review interior formatting for chosen trim size",
        "Prepare cover with correct dimensions and bleed",
        "Double-check ISBN assignment",
        "Review distribution settings",
        "Set up royalty payment method"
    ]

    for item in checklist_items:
        st.checkbox(item, key=item)


else:
    st.header("🔍 Format Compatibility Checker")

    st.write("Enter your book specifications to check compatibility with KDP and Ingram:")

    col1, col2, col3 = st.columns(3)

    with col1:
        book_type = st.selectbox("Book Type:", ["Paperback", "Hardcover", "Paperback (Standard Color)"])

    with col2:
        if book_type == "Hardcover":

            hardcover_size = st.selectbox(
                "KDP Hardcover Size:",
                ["5.5 × 8.5 in", "6 × 9 in", "6.14 × 9.21 in", "7 × 10 in", "8.25 × 11 in"]
            )

            if hardcover_size != "Custom":
                # Parse the selected size
                size_parts = hardcover_size.replace(" in", "").split(" × ")
                trim_width = float(size_parts[0])
                trim_height = float(size_parts[1])
                st.info(f"Using KDP standard: {hardcover_size}")
            else:
                trim_width = st.number_input("Trim Width (inches):", min_value=4.0, max_value=12.0, value=6.0,
                                             step=0.01)
        else:
            trim_width = st.number_input("Trim Width (inches):", min_value=4.0, max_value=12.0, value=6.0, step=0.1)

    with col3:
        if book_type == "Hardcover" and hardcover_size != "Custom":

            st.metric("Trim Height (inches)", f"{trim_height}")
        else:
            trim_height = st.number_input("Trim Height (inches):", min_value=4.0, max_value=12.0, value=9.0, step=0.1)

    page_count = st.number_input("Page Count:", min_value=1, max_value=1500, value=200, step=1)

    if st.button("Check Compatibility", type="primary"):
        st.markdown("---")
        st.subheader("Results:")

        col1, col2 = st.columns(2)


        with col1:
            st.markdown("### 📘 KDP Compatibility")

            kdp_compatible = True
            issues = []

            # Define KDP hardcover allowed sizes
            kdp_hardcover_sizes = [
                (5.5, 8.5),
                (6.0, 9.0),
                (6.14, 9.21),
                (7.0, 10.0),
                (8.25, 11.0)
            ]


            if book_type == "Hardcover":

                size_match = False
                for allowed_width, allowed_height in kdp_hardcover_sizes:
                    if (abs(trim_width - allowed_width) < 0.05 and abs(trim_height - allowed_height) < 0.05):
                        size_match = True
                        break

                if not size_match:
                    kdp_compatible = False
                    issues.append(f"❌ Hardcover size {trim_width} × {trim_height} in not in KDP's allowed list")
                    issues.append("   Allowed sizes: 5.5×8.5, 6×9, 6.14×9.21, 7×10, 8.25×11")
            else:

                if trim_width < 4 or trim_width > 8.5:
                    kdp_compatible = False
                    issues.append(f"❌ Width {trim_width} in is outside KDP range (4-8.5 in)")

                if trim_height < 6 or trim_height > 11.69:
                    kdp_compatible = False
                    issues.append(f"❌ Height {trim_height} in is outside KDP range (6-11.69 in)")


            if book_type == "Paperback (Standard Color)":
                if page_count < 72:
                    kdp_compatible = False
                    issues.append(f"❌ Color paperback needs ≥72 pages (you have {page_count})")
                elif page_count > 828:
                    kdp_compatible = False
                    issues.append(f"❌ Exceeds paperback max of 828 pages")
            elif book_type == "Paperback":
                if page_count < 24:
                    kdp_compatible = False
                    issues.append(f"❌ Needs ≥24 pages (you have {page_count})")
                elif page_count > 828:
                    kdp_compatible = False
                    issues.append(f"❌ Exceeds paperback max of 828 pages")
            else:
                if page_count < 76:
                    kdp_compatible = False
                    issues.append(f"❌ Hardcover needs ≥75 pages (you have {page_count})")
                elif page_count > 550:
                    kdp_compatible = False
                    issues.append(f"❌ Exceeds hardcover max of 550 pages")

            if kdp_compatible:
                st.success("✅ **COMPATIBLE WITH KDP**")
                st.balloons()
            else:
                st.error("❌ **NOT COMPATIBLE WITH KDP**")
                for issue in issues:
                    st.write(issue)


        with col2:
            st.markdown("### 📗 Ingram Spark Compatibility")

            ingram_compatible = True
            ingram_issues = []

            is_special_format = (trim_width == 11 and trim_height == 8.5) or (trim_width == 8.5 and trim_height == 11)

            if is_special_format:
                if page_count < 18:
                    ingram_compatible = False
                    ingram_issues.append(f"❌ Needs ≥18 pages (you have {page_count})")
                elif page_count > 400:
                    ingram_compatible = False
                    ingram_issues.append(f"❌ Special format (11×8.5) limited to 400 pages")
                else:
                    st.info("ℹ️ This is a special format (11 × 8.5 in)")
            else:
                if page_count < 18:
                    ingram_compatible = False
                    ingram_issues.append(f"❌ Needs ≥18 pages (you have {page_count})")
                elif page_count > 1200:
                    ingram_compatible = False
                    ingram_issues.append(f"❌ Exceeds max of 1200 pages")

            if ingram_compatible:
                st.success("✅ **COMPATIBLE WITH INGRAM**")
            else:
                st.error("❌ **NOT COMPATIBLE WITH INGRAM**")
                for issue in ingram_issues:
                    st.write(issue)


        st.markdown("---")
        if kdp_compatible and ingram_compatible:
            st.success("🎉 Your book specifications are compatible with both KDP and Ingram Spark!")
        elif kdp_compatible:
            st.warning("⚠️ Compatible with KDP only. Consider adjusting specifications for Ingram.")
        elif ingram_compatible:
            st.warning("⚠️ Compatible with Ingram only. Consider adjusting specifications for KDP.")
        else:
            st.error("❌ Not compatible with either platform. Please adjust your specifications.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p>📚 Publishing Management System v1.0</p>
    <p>For questions or updates, consult platform documentation</p>
</div>
""", unsafe_allow_html=True)