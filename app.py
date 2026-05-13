import streamlit as st
import pandas as pd
import requests
import json
import time
import plotly.express as px
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Location options — DataForSEO accepts exact location_name strings
# ---------------------------------------------------------------------------
LOCATIONS = {
    "United States":                  "United States",
    "United Kingdom":                 "United Kingdom",
    "Canada":                         "Canada",
    "Australia":                      "Australia",
    "India":                          "India",
    "Pakistan":                       "Pakistan",
    "New York, US":                   "New York,New York,United States",
    "Los Angeles, US":                "Los Angeles,California,United States",
    "Chicago, US":                    "Chicago,Illinois,United States",
    "Houston, US":                    "Houston,Texas,United States",
}

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def init_session_state():
    if "domain" not in st.session_state:
        st.session_state.domain = ""
    if "results_data" not in st.session_state:
        st.session_state.results_data = []
    elif st.session_state.results_data and "Rank" not in st.session_state.results_data[0]:
        st.session_state.results_data = []

# ---------------------------------------------------------------------------
# Domain helpers
# ---------------------------------------------------------------------------
def get_root_domain(url_or_domain):
    s = str(url_or_domain).strip()
    if not s.startswith(("http://", "https://")):
        s = "http://" + s
    try:
        netloc = urlparse(s).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return str(url_or_domain).lower()

def domain_matches(link, target_domain):
    result_domain = get_root_domain(link)
    return result_domain == target_domain or result_domain.endswith("." + target_domain)

def determine_page_type(url):
    if not url or url == "N/A":
        return "N/A"
    u = url.lower()
    if any(kw in u for kw in ["/blog", "/article", "/post", "/news", "blog/", "article/", "post/"]):
        return "Blog"
    return "Landing Page"

# ---------------------------------------------------------------------------
# DataForSEO Live API call
# ---------------------------------------------------------------------------
def get_search_results(keyword, target_domain, login, password, location, language, device):
    """
    Queries DataForSEO Live SERP API.

    Returns rank_absolute — the true visual position on Google including ads,
    featured snippets, and all other SERP features. One API call covers the
    full top-100, no pagination needed.
    """
    headers = {"Content-Type": "application/json"}
    payload = json.dumps([{
        "keyword":       keyword,
        "location_name": location,
        "language_name": language,
        "device":        device,
        "os":            "windows",
        "depth":         100,
    }])

    for attempt in range(2):
        try:
            response = requests.post(
                "https://api.dataforseo.com/v3/serp/google/organic/live/regular",
                headers=headers,
                data=payload,
                auth=(login, password),
                timeout=30,
            )

            if response.status_code == 401:
                return {"error": "Auth Error", "msg": "Invalid DataForSEO login or password."}
            if response.status_code == 402:
                return {"error": "Insufficient Credits", "msg": "Top up your DataForSEO balance."}
            if response.status_code != 200:
                if attempt == 0:
                    time.sleep(3.0)
                    continue
                return {"error": "API Error", "msg": f"HTTP {response.status_code}"}

            data  = response.json()
            tasks = data.get("tasks", [])
            if not tasks:
                return {"rank": "Not in Top 100", "url": "N/A"}

            task   = tasks[0]
            status = task.get("status_code", 0)
            if status == 40101:
                return {"error": "Auth Error", "msg": task.get("status_message", "Auth failed.")}
            if status not in [20000, 20100]:
                if attempt == 0:
                    time.sleep(3.0)
                    continue
                return {"rank": "Not in Top 100", "url": "N/A"}

            result = task.get("result", [])
            if not result:
                return {"rank": "Not in Top 100", "url": "N/A"}

            items = result[0].get("items", []) or []
            for item in items:
                if item.get("type") != "organic":
                    continue
                url = item.get("url", "")
                if domain_matches(url, target_domain):
                    return {
                        "rank": item.get("rank_absolute"),
                        "url":  url,
                    }

            return {"rank": "Not in Top 100", "url": "N/A"}

        except Exception as e:
            if attempt == 0:
                time.sleep(3.0)
                continue
            return {"error": "Error", "msg": str(e)}

    return {"rank": "Not in Top 100", "url": "N/A"}

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
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
        if "Not in" in v or v in ["N/A", "Error"]:
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

# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------
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
    st.markdown("Real-time Google rank tracking powered by **DataForSEO**")

    with st.sidebar:
        st.header("⚙️ Configuration")
        target_domain = st.text_input(
            "Target Domain",
            placeholder="e.g. agtech.folio3.com",
            value=st.session_state.domain,
            help="Enter the exact domain or subdomain to track.",
        )

        dfs_login    = st.text_input("DataForSEO Login (email)", placeholder="you@example.com")
        dfs_password = st.text_input("DataForSEO Password", type="password")

        with st.expander("Advanced Settings"):
            location_label = st.selectbox("Location", list(LOCATIONS.keys()), index=0)
            language       = st.selectbox("Language", ["English", "Spanish", "French", "German"], index=0)
            device         = st.selectbox("Device",   ["desktop", "mobile"], index=0)

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
            if not target_domain:
                st.error("Target Domain is required.")
            elif not dfs_login or not dfs_password:
                st.error("DataForSEO login and password are required.")
            elif not keywords:
                st.error("Please add keywords to analyze.")
            else:
                st.session_state.domain       = target_domain
                st.session_state.results_data = []

                root_domain   = get_root_domain(target_domain)
                location_name = LOCATIONS[location_label]
                progress_text = st.empty()
                progress_bar  = st.progress(0)

                for i, kv in enumerate(keywords):
                    progress_text.text(f"Scanning: '{kv}'  ({i + 1}/{len(keywords)})")
                    res = get_search_results(kv, root_domain, dfs_login, dfs_password,
                                            location_name, language, device)

                    if "error" in res:
                        if res["error"] in ("Auth Error", "Insufficient Credits"):
                            st.error(f"{res['error']}: {res['msg']}")
                            break
                        st.warning(f"⚠️ Skipped '{kv}': {res['msg']}")
                        st.session_state.results_data.append({
                            "Keyword":   kv,
                            "Rank":      "Error",
                            "URL":       "N/A",
                            "Page Type": "N/A",
                            "Position":  102,
                        })
                        progress_bar.progress((i + 1) / len(keywords))
                        continue

                    rank     = res.get("rank", "Not in Top 100")
                    url      = res.get("url",  "N/A")
                    rank_str = str(rank)

                    if rank_str.isdigit():
                        display_rank = rank_str
                        position     = int(rank_str)
                        page_type    = determine_page_type(url)
                    else:
                        display_rank = "Not in Top 100"
                        position     = 101
                        page_type    = "N/A"

                    st.session_state.results_data.append({
                        "Keyword":   kv,
                        "Rank":      display_rank,
                        "URL":       url,
                        "Page Type": page_type,
                        "Position":  position,
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

            total_kw   = len(df_res)
            top_3      = sum(1 for p in all_pos if p <= 3)
            top_10     = sum(1 for p in all_pos if p <= 10)
            top_100    = sum(1 for p in all_pos if p <= 100)
            avg_pos    = sum(ranked) / len(ranked) if ranked else None
            visibility = round(top_10 / total_kw * 100, 1) if total_kw else 0

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f'<div class="metric-container"><div class="metric-label">Visibility Index</div><div class="metric-value">{visibility}%</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="metric-container"><div class="metric-label">Top 3 Rankings</div><div class="metric-value">{top_3}</div></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="metric-container"><div class="metric-label">Top 10 Rankings</div><div class="metric-value">{top_10}</div></div>', unsafe_allow_html=True)
            with col4:
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
                    "Not Ranked": total_kw - top_100,
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
            st.download_button(
                label="📥 Download Report (CSV)",
                data=csv,
                file_name=f"{st.session_state.domain.replace('.', '_')}_rankings.csv",
                mime="text/csv",
                type="primary",
            )

if __name__ == "__main__":
    main()
