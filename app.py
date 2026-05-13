import streamlit as st
import pandas as pd
import json
import plotly.express as px
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2 import service_account

COUNTRY_CODES = {
    "us": "usa",
    "uk": "gbr",
    "ca": "can",
    "au": "aus",
    "in": "ind",
    "pk": "pak",
}

def init_session_state():
    if "domain" not in st.session_state:
        st.session_state.domain = ""
    if "results_data" not in st.session_state:
        st.session_state.results_data = []
    elif st.session_state.results_data and "Rank" not in st.session_state.results_data[0]:
        st.session_state.results_data = []

def determine_page_type(url):
    if not url or url == "N/A":
        return "N/A"
    u = url.lower()
    if any(kw in u for kw in ["/blog", "/article", "/post", "/news", "blog/", "article/", "post/"]):
        return "Blog"
    return "Landing Page"

def build_gsc_service(credentials_info):
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
    )
    return build("searchconsole", "v1", credentials=credentials)

def get_keyword_ranking(service, site_url, keyword, start_date, end_date, country_code=None, device=None):
    filters = [{"dimension": "query", "operator": "equals", "expression": keyword}]
    if country_code:
        filters.append({"dimension": "country", "operator": "equals", "expression": country_code})
    if device and device != "all":
        filters.append({"dimension": "device", "operator": "equals", "expression": device.upper()})

    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query", "page"],
        "dimensionFilterGroups": [{"filters": filters}],
        "rowLimit": 10,
        "dataState": "final",
    }

    try:
        response = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
        rows = response.get("rows", [])
        if not rows:
            return {"rank": "No Data", "url": "N/A", "clicks": 0, "impressions": 0, "ctr": 0.0}
        best = min(rows, key=lambda r: r.get("position", 999))
        return {
            "rank": round(best.get("position", 0)),
            "url": best["keys"][1] if len(best["keys"]) > 1 else "N/A",
            "clicks": int(best.get("clicks", 0)),
            "impressions": int(best.get("impressions", 0)),
            "ctr": round(best.get("ctr", 0) * 100, 1),
        }
    except Exception as e:
        return {"error": str(e)}

def render_styling():
    st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-list"] { gap: 24px; }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            background-color: transparent;
            border-radius: 4px 4px 0px 0px;
            padding: 10px;
            font-size: 16px;
            font-weight: 600;
        }
        .metric-container {
            background-color: #161A25;
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid #2D333B;
            margin-bottom: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 2.2rem;
            font-weight: 800;
            color: #FFFFFF;
            margin-top: 0.5rem;
        }
        .metric-label {
            font-size: 0.85rem;
            color: #8B949E;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)

def rank_color(val):
    try:
        v = str(val)
        if v in ["No Data", "N/A", "Error"]:
            return "background-color: rgba(239,68,68,0.1); color: #ef4444;"
        n = int(v.strip())
        if n <= 3:
            return "background-color: rgba(16,185,129,0.15); color: #10b981; font-weight: bold;"
        elif n <= 10:
            return "background-color: rgba(52,211,153,0.1); color: #34d399;"
        elif n <= 30:
            return "background-color: rgba(245,158,11,0.1); color: #f59e0b;"
        elif n <= 100:
            return "background-color: rgba(245,158,11,0.05); color: #d97706;"
        else:
            return "background-color: rgba(239,68,68,0.1); color: #ef4444;"
    except Exception:
        return "background-color: transparent; color: #8B949E;"

def main():
    st.set_page_config(
        page_title="AI Keyword Tracker",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_session_state()
    render_styling()

    st.title("🎯 AI Keyword Tracker")
    st.markdown("Rank tracking powered by **Google Search Console** — 100% accurate Google data")

    with st.sidebar:
        st.header("⚙️ Configuration")

        site_url = st.text_input(
            "GSC Property URL",
            placeholder="https://agtech.folio3.com/",
            value=st.session_state.domain,
            help="Must match exactly as it appears in Google Search Console, including trailing slash.",
        )

        st.markdown("**Service Account Credentials**")
        creds_file = st.file_uploader("Upload service account JSON", type=["json"])
        credentials_info = None
        if creds_file:
            try:
                credentials_info = json.load(creds_file)
                st.success("✓ Credentials loaded")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")

        with st.expander("Advanced Settings"):
            country_option  = st.selectbox("Country",     ["us", "uk", "ca", "au", "in", "pk"],            index=0)
            date_range      = st.selectbox("Date Range",  ["Last 7 days", "Last 28 days", "Last 3 months"], index=1)
            device_option   = st.selectbox("Device",      ["all", "desktop", "mobile", "tablet"],           index=0)

        st.divider()
        st.markdown("### 📥 Input Keywords")
        input_method = st.radio(
            "Choose input method:",
            ["📄 Upload CSV", "⌨️ Paste Keywords"],
            label_visibility="collapsed",
        )

        keywords = []
        if input_method == "📄 Upload CSV":
            uploaded_file = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed")
            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    kw_col = next(
                        (c for c in df.columns if c.lower() in ["keyword", "keywords", "search term", "query", "term"]),
                        None,
                    )
                    if kw_col:
                        keywords = df[kw_col].dropna().astype(str).str.strip().tolist()
                        st.success(f"✓ Loaded {len(keywords)} keywords")
                    else:
                        st.error("✗ No 'Keyword' column found.")
                except Exception as e:
                    st.error(f"Error reading CSV: {e}")
        else:
            pasted = st.text_area(
                "Paste keywords (one per line)",
                height=150,
                label_visibility="collapsed",
                placeholder="keyword 1\nkeyword 2\nkeyword 3",
            )
            if pasted:
                keywords = [k.strip() for k in pasted.split("\n") if k.strip()]
                if keywords:
                    st.success(f"✓ Loaded {len(keywords)} keywords")

        run_btn = st.button("🚀 Analyze SERP", type="primary", use_container_width=True)

        if run_btn:
            if not site_url:
                st.error("GSC Property URL is required.")
            elif not credentials_info:
                st.error("Service account credentials are required.")
            elif not keywords:
                st.error("Please add keywords to analyze.")
            else:
                st.session_state.domain = site_url
                st.session_state.results_data = []

                end_date = (datetime.today() - timedelta(days=3)).strftime("%Y-%m-%d")
                days_map = {"Last 7 days": 10, "Last 28 days": 31, "Last 3 months": 93}
                start_date = (datetime.today() - timedelta(days=days_map[date_range])).strftime("%Y-%m-%d")

                country_code = COUNTRY_CODES.get(country_option)

                try:
                    gsc_service = build_gsc_service(credentials_info)
                except Exception as e:
                    st.error(f"Authentication failed: {e}")
                    st.stop()

                progress_text = st.empty()
                progress_bar  = st.progress(0)

                for i, kv in enumerate(keywords):
                    progress_text.text(f"Scanning: '{kv}'  ({i + 1}/{len(keywords)})")
                    res = get_keyword_ranking(gsc_service, site_url, kv, start_date, end_date, country_code, device_option)

                    if "error" in res:
                        st.warning(f"⚠️ Error for '{kv}': {res['error']}")
                        st.session_state.results_data.append({
                            "Keyword": kv, "Rank": "Error", "URL": "N/A",
                            "Page Type": "N/A", "Clicks": 0, "Impressions": 0, "CTR (%)": 0.0,
                            "Position": 102,
                        })
                        progress_bar.progress((i + 1) / len(keywords))
                        continue

                    rank = res["rank"]
                    url  = res["url"]

                    if isinstance(rank, int):
                        display_rank = str(rank)
                        position     = rank
                        page_type    = determine_page_type(url)
                    else:
                        display_rank = "No Data"
                        position     = 101
                        page_type    = "N/A"

                    st.session_state.results_data.append({
                        "Keyword":      kv,
                        "Rank":         display_rank,
                        "URL":          url,
                        "Page Type":    page_type,
                        "Clicks":       res["clicks"],
                        "Impressions":  res["impressions"],
                        "CTR (%)":      res["ctr"],
                        "Position":     position,
                    })
                    progress_bar.progress((i + 1) / len(keywords))

                progress_text.empty()
                progress_bar.empty()
                st.success("Analysis Complete!")

    tab1, tab2, tab3 = st.tabs(["📊 Dashboard Overview", "🔍 Keyword Intelligence", "📑 Settings & Exports"])

    with tab1:
        if not st.session_state.results_data:
            st.info("Configure settings in the sidebar and click Analyze SERP to see your dashboard.")
        else:
            df_res  = pd.DataFrame(st.session_state.results_data)
            all_pos = df_res["Position"].tolist()
            ranked  = [p for p in all_pos if p <= 100]

            total_kw        = len(df_res)
            top_3           = sum(1 for p in all_pos if p <= 3)
            top_10          = sum(1 for p in all_pos if p <= 10)
            top_100         = sum(1 for p in all_pos if p <= 100)
            avg_pos         = sum(ranked) / len(ranked) if ranked else None
            visibility      = round(top_10 / total_kw * 100, 1) if total_kw else 0
            total_clicks    = int(df_res["Clicks"].sum())
            total_impressions = int(df_res["Impressions"].sum())

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f'<div class="metric-container"><div class="metric-label">Visibility Index</div><div class="metric-value">{visibility}%</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="metric-container"><div class="metric-label">Top 3 Rankings</div><div class="metric-value">{top_3}</div></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="metric-container"><div class="metric-label">Total Clicks</div><div class="metric-value">{total_clicks:,}</div></div>', unsafe_allow_html=True)
            with col4:
                st.markdown(f'<div class="metric-container"><div class="metric-label">Total Impressions</div><div class="metric-value">{total_impressions:,}</div></div>', unsafe_allow_html=True)

            col5, col6 = st.columns(2)
            with col5:
                st.markdown(f'<div class="metric-container"><div class="metric-label">Top 10 Rankings</div><div class="metric-value">{top_10}</div></div>', unsafe_allow_html=True)
            with col6:
                avg_display = f"{avg_pos:.1f}" if avg_pos is not None else "N/A"
                st.markdown(f'<div class="metric-container"><div class="metric-label">Avg Position</div><div class="metric-value">{avg_display}</div></div>', unsafe_allow_html=True)

            st.subheader("Insights & Distribution")
            c1, c2 = st.columns([2, 1])

            with c1:
                st.markdown("##### Ranking Distribution")
                dist = {
                    "Pos 1-3":    top_3,
                    "Pos 4-10":   top_10 - top_3,
                    "Pos 11-30":  sum(1 for p in all_pos if 10 < p <= 30),
                    "Pos 31-100": sum(1 for p in all_pos if 30 < p <= 100),
                    "No Data":    total_kw - top_100,
                }
                fig = px.bar(
                    pd.DataFrame(list(dist.items()), columns=["Range", "Count"]),
                    x="Range", y="Count", color="Range",
                    color_discrete_sequence=["#10b981", "#34d399", "#fbbf24", "#f59e0b", "#4b5563"],
                    template="plotly_dark",
                )
                fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=30, b=0),
                                  plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                st.markdown("##### Page Types")
                pt = df_res[df_res["Page Type"] != "N/A"]["Page Type"].value_counts().reset_index()
                pt.columns = ["Page Type", "Count"]
                if not pt.empty:
                    fig_pie = px.pie(pt, values="Count", names="Page Type", hole=0.7,
                                    template="plotly_dark",
                                    color_discrete_sequence=["#3b82f6", "#8b5cf6"])
                    fig_pie.update_layout(
                        showlegend=True, margin=dict(l=0, r=0, t=30, b=0),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No ranked pages to show.")

    with tab2:
        if not st.session_state.results_data:
            st.info("Run the tracker to view keyword intelligence.")
        else:
            df_display = pd.DataFrame(st.session_state.results_data).drop(columns=["Position"], errors="ignore")
            total_rows = len(df_display)
            st.subheader(f"Keyword Intelligence Data ({total_rows} keywords)")
            style_cols = [c for c in ["Rank"] if c in df_display.columns]
            styled = df_display.style.map(rank_color, subset=style_cols)
            tbl_height = min(total_rows * 35 + 38, 1200)
            st.dataframe(styled, use_container_width=True, height=tbl_height)

    with tab3:
        st.subheader("Data Export")
        if not st.session_state.results_data:
            st.info("No data to export yet.")
        else:
            df_export = pd.DataFrame(st.session_state.results_data).drop(columns=["Position"], errors="ignore")
            csv = df_export.to_csv(index=False).encode("utf-8")
            safe_name = st.session_state.domain.replace("https://", "").replace("/", "_").replace(".", "_")
            st.download_button(
                label="📥 Download Report (CSV)",
                data=csv,
                file_name=f"{safe_name}_rankings.csv",
                mime="text/csv",
                type="primary",
            )

if __name__ == "__main__":
    main()
