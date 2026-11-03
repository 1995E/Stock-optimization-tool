import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import io

st.set_page_config(
    page_title="Material Analysis Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to inject an ultra-clean modern corporate layout style
st.markdown("""
    <style>
        .main { 
            background-color: #f4f6f9; 
        }
        .metric-card {
            background-color: #ffffff;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            border-top: 4px solid #1a365d;
            text-align: center;
            margin-bottom: 15px;
        }
        .metric-card h6 {
            color: #718096;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }
        .metric-card h3 {
            color: #1a365d;
            font-size: 1.8rem;
            font-weight: 700;
            margin: 0;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Material Overview & Stock Analysis")
st.markdown("Retrieve structured insights, classify inventory status, and assess material for scrapping or to be transferred.")

# 1. FILE UPLOADERS IN SIDEBAR
with st.sidebar:
    st.header("📂 Data Source Configuration")
    uploaded_materials = st.file_uploader("Material Overview per Plant (Excel)", type=["xlsx"])
    uploaded_prices = st.file_uploader("Material Overview per Price (Excel)", type=["xlsx"])
    st.markdown("--- ")

if uploaded_materials is not None and uploaded_prices is not None:
    # Read DataFrames
    removed_materials_df = pd.read_excel(uploaded_materials)
    unit_price_df = pd.read_excel(uploaded_prices)

    # 2. PROCESSING INFORMATION
    filtered_unit_prices = unit_price_df[unit_price_df['Valuation Type'] == 'BLOC-17']
    material_prices = filtered_unit_prices.groupby('Material n°')['Item Price'].mean()
    removed_materials_df['Unit price'] = removed_materials_df['Material n°'].map(material_prices)

    requested_columns = [
        'Material n°', 'Material description', 'Material discipline',
        'Plant code', 'Plant', 'storage bin', 'FASD', 'Blocking status',
        'MRP Type', 'Stock qty', 'Blocked Stock Qty', 'Safety', 'Min',
        'Max', 'Unit price'
    ]
    existing_columns = [col for col in requested_columns if col in removed_materials_df.columns]
    df = removed_materials_df[existing_columns].copy()

    # DYNAMIC PLANT SELECTOR IN SIDEBAR
    with st.sidebar:
        available_plants = sorted(df['Plant'].dropna().unique())
        plant = st.selectbox(
            "Select Plant of Interest:",
            available_plants,
            index=0 if 'PAZFLOR' not in available_plants else available_plants.index('PAZFLOR')
        )

    # Perform calculations based on selection
    Total_removed_materials = df['Material n°'].nunique()
    pd_v1_df = df[df['MRP Type'].isin(['PD', 'V1'])].copy()
    pd_v1_unique_materials = pd_v1_df.drop_duplicates(subset=['Material n°'])

    stock_greater_zero = pd_v1_df[pd_v1_df['Stock qty'] > 0]
    stock_greater_zero_unique = pd_v1_df[pd_v1_df['Stock qty'] > 0].drop_duplicates(subset=['Material n°']).copy()

    Interested_plant = stock_greater_zero[stock_greater_zero['Plant'] == plant].copy()
    Interested_plant_unique = Interested_plant.drop_duplicates(subset=['Material n°']).copy()

    Total_stock_value = (stock_greater_zero['Stock qty'] * stock_greater_zero['Unit price']).sum()
    Interested_plant_stock_value = (Interested_plant['Stock qty'] * Interested_plant['Unit price']).sum()

    # Categorization logic
    other_active_materials = stock_greater_zero[
        (stock_greater_zero['Plant'] != plant) &
        (stock_greater_zero['FASD'].str.upper() != 'DEAD')
    ]['Material n°'].unique()

    def categorize_material(row):
        mat_no = row['Material n°']
        if mat_no in other_active_materials:
            return 'TO BE TRANSFERRED'
        else:
            return 'TO BE SCRAPPED'

    if not Interested_plant.empty:
        Interested_plant['Category'] = Interested_plant.apply(categorize_material, axis=1)
    else:
        Interested_plant['Category'] = pd.Series(dtype='object')

    # 3. HIGHLY VISUAL KPI METRICS SECTION
    st.markdown("### Key Performance Indicators")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        st.markdown(f'<div class="metric-card"><h6>Total Removed Materials</h6><h3>{Total_removed_materials:,}</h3></div>', unsafe_allow_html=True)
    with kpi2:
        st.markdown(f'<div class="metric-card"><h6>Unique Stock Materials (PD/V1)</h6><h3>{len(pd_v1_unique_materials):,}</h3></div>', unsafe_allow_html=True)
    with kpi3:
        st.markdown(f'<div class="metric-card"><h6>Total Stock Value (USD)</h6><h3>${Total_stock_value:,.2f}</h3></div>', unsafe_allow_html=True)
    with kpi4:
        st.markdown(f'<div class="metric-card"><h6>{plant} Stock Value (USD)</h6><h3>${Interested_plant_stock_value:,.2f}</h3></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. INTERACTIVE CHARTS (HEATMAP & PIE)
    st.markdown("### Distribution and Visual Categorization Insights")

    if not Interested_plant.empty:
        col_left, col_right = st.columns(2)

        with col_left:
            cross_tab = pd.crosstab(Interested_plant['FASD'], Interested_plant['Category'])
            # Modern heatmap using Plotly express
            fig_heat = px.imshow(
                cross_tab,
                text_auto=True,
                aspect="auto",
                color_continuous_scale="Blues",
                labels=dict(x="Category", y="FASD Status", color="Material Quantity"),
                title="Distribution per FASD Status"
            )
            fig_heat.update_layout(
                margin=dict(l=40, r=40, t=60, b=40),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_heat, use_container_width=True)

        with col_right:
            category_counts = Interested_plant['Category'].value_counts().reset_index()
            category_counts.columns = ['Category', 'Count']

            # Interactive and Clean Donut Chart
            fig_pie = px.pie(
                category_counts,
                values='Count',
                names='Category',
                hole=0.45,
                color_discrete_sequence=["#3182ce", "#319795"],
                title="General Classification Distribution"
            )
            fig_pie.update_traces(textinfo='percent+label', pull=[0.05] * len(category_counts))
            fig_pie.update_layout(
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
                margin=dict(l=40, r=40, t=60, b=40),
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.warning(f"No stock records found for plant: {plant}")

    # 5. MULTI-VIEW MATERIALS ANALYSIS (WITH REVOLUTIONARY SANKEY REPRESENTATION)
    st.markdown("### Material Filtering & Stock Value Funnel Analysis")
    
    # Toggle for selecting different layouts including the alternative Sankey style
    layout_choice = st.radio(
        "Select the layout:", 
        ["Standard Funnel Layout", "Modern Horizontal Progress Layout", "Sankey Flow Diagram (Interactive)"], 
        horizontal=True
    )

    stage1_count = df['Material n°'].nunique()
    stage1_value = (df[df['Stock qty'] > 0].eval('`Stock qty` * `Unit price`')).sum()
    if pd.isna(stage1_value) or stage1_value == 0:
        stage1_value = Total_stock_value

    stage2_count = len(pd_v1_unique_materials)
    stage2_value = (pd_v1_df[pd_v1_df['Stock qty'] > 0].eval('`Stock qty` * `Unit price`')).sum()

    stage3_count = len(stock_greater_zero_unique)
    stage3_value = Total_stock_value

    transferred_df = Interested_plant[Interested_plant['Category'] == 'TO BE TRANSFERRED']
    stage_transferred_count = transferred_df['Material n°'].nunique()
    transferred_stock_value = (transferred_df.eval('`Stock qty` * `Unit price`')).sum()

    stage4_count = len(Interested_plant_unique) - stage_transferred_count
    stage4_value = Interested_plant_stock_value - transferred_stock_value

    stages = [
        "Total Removed Materials",
        "Total Stock Materials",
        "Total Stock Materials with Quantity > 0",
        f"Stock Materials in ({plant})",
        f"Materials to be Transferred (from {plant})"
    ]
    counts = [stage1_count, stage2_count, stage3_count, stage4_count, stage_transferred_count]
    values = [stage1_value, stage2_value, stage3_value, stage4_value, transferred_stock_value]
    text_labels = [f"{c} Materials<br>${v:,.2f}" for c, v in zip(counts, values)]

    if layout_choice == "Standard Funnel Layout":
        fig_funnel = go.Figure(go.Funnel(
            y=stages,
            x=counts,
            textinfo="text",
            text=text_labels,
            hoverinfo="y+text",
            marker=dict(color=["#1A365D", "#2B6CB0", "#3182CE", "#4299E1", "#63B3ED"]),
            connector=dict(line=dict(color="#CBD5E0", width=1.5))
        ))
        fig_funnel.update_layout(
            title_text="Standard Funnel Flow",
            title_x=0.5,
            funnelmode="stack",
            showlegend=False,
            height=450,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_funnel, use_container_width=True)
    elif layout_choice == "Modern Horizontal Progress Layout":
        # Alternative Modern Horizontal Progression Bar chart style
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=stages[::-1],
            x=counts[::-1],
            orientation='h',
            text=[text_labels[i].replace("<br>", " - ") for i in range(len(text_labels))][::-1],
            textposition='auto',
            marker=dict(
                color=["#63B3ED", "#4299E1", "#3182CE", "#2B6CB0", "#1A365D"],
                line=dict(color='rgba(255, 255, 255, 1)', width=1)
            )
        ))
        fig_bar.update_layout(
            title_text="Progressive Pipeline Distribution",
            title_x=0.5,
            xaxis_title="Material Volume / Item Count",
            yaxis_title="Stages",
            height=450,
            margin=dict(l=150, r=40, t=60, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        # Highly modern interactive Sankey Flow design
        fig_sankey = go.Figure(data=[go.Sankey(
            node = dict(
              pad = 20,
              thickness = 25,
              line = dict(color = "gray", width = 0.5),
              label = ["Initial Pool", "PD/V1 Classified", "Excluded Category", "Active Stock (Other Plants)", f"{plant} Inventory", "To Be Scrapped", "To Be Transferred"],
              color = ["#1A365D", "#2B6CB0", "#E53E3E", "#4299E1", "#319795", "#E53E3E", "#3182CE"]
            ),
            link = dict(
              source = [0, 0, 1, 1, 4, 4], 
              target = [1, 2, 3, 4, 5, 6],
              value = [
                  stage2_count,
                  max(1, stage1_count - stage2_count),
                  max(1, stage2_count - stage3_count),
                  stage3_count,
                  stage4_count,
                  stage_transferred_count
              ]
            )
        )])
        fig_sankey.update_layout(
            title_text="Sankey Inventory Lifecycle & Transition Flow",
            title_x=0.5,
            height=480,
            font_size=12,
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_sankey, use_container_width=True)

    # 6. EXPORT ACTION IN SIDEBAR
    with st.sidebar:
        st.markdown("--- ")
        st.header("📦 Download the Results")
        if not Interested_plant.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                Interested_plant.to_excel(writer, index=False, sheet_name=f'{plant}_Materials')
            buffer.seek(0)

            st.download_button(
                label=f"📥 {plant} Materials for Scrap (Excel)",
                data=buffer,
                file_name=f"{plant}_interested_materials.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No data available to export.")
else:
    st.info("Please upload both Excel files in the sidebar to activate the dashboard.")
