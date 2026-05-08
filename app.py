import streamlit as st
import pandas as pd
import requests
import json
import time
import plotly.express as px
from urllib.parse import urlparse

def init_session_state():
    if "domain" not in st.session_state:
        st.session_state.domain = ""
    # Clear stale results from older schema versions
    existing = st.session_state.get("results_data", [])
    if existing and "Rank" not in existing[0]:
        st.session_state.results_data = []
    elif "results_data" not in st.session_state:
        st.session_state.results_data = []

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

def get_search_results(keyword, target_domain, api_key, gl="us", hl="en", device="desktop"):
    """
    Scans top 100 Google results (10 pages x 10) via Serper.dev.

    Uses a cumulative rank_counter — increments once per organic result
    received across all pages. This is the most reliable position method
    because Serper.dev's own `position` field resets to 1-10 on each page
    and adding a location parameter changes which Google datacenter is hit,
    producing different (less consistent) results.

    1 second between pages keeps requests within Serper.dev rate limits.
    Without this pause, later pages fail silently and ranks look too low.
    """
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    rank_counter = 0

    for page in range(1, 11):
        payload = json.dumps({
            "q": keyword,
            "gl": gl,
            "hl": hl,
            "page": page,
            "num": 10,
            "device": device,
        })

        try:
            response = requests.post(
                "https://google.serper.dev/search",
                headers=headers,
                data=payload,
                timeout=15,
            )

            if response.status_code == 403:
                return {"error": "API Key Error", "msg": "Unauthorized — check your Serper.dev API key."}
            if response.status_code in [402, 429]:
                return {"error": "Rate Limited", "msg": "Serper.dev rate limit hit. Reduce keywords or upgrade plan."}
            if response.status_code != 200:
                break

            organic = response.json().get("organic", [])
            if not organic:
                break

            for result in organic:
                rank_counter += 1
                link = result.get("link", "")
                if domain_matches(link, target_domain):
                    return {"rank": rank_counter, "url": link}

        except Exception as e:
            if page == 1:
                return {"error": "Error", "msg": str(e)}
            break

        if page < 10:
            time.sleep(1.0)

    return {"rank": "Not in Top 100", "url": "N/A"}

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
        if "Not in" in v or v == "N/A":
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
    st.markdown("Real-time Google rank tracking")

    with st.sidebar:
        st.header("⚙️ Configuration")
        target_domain = st.text_input(
            "Target Domain",
            placeholder="e.g. domain.com",
            value=st.session_state.domain,
            help="Enter the exact domain or subdomain — e.g. agtech.folio3.com, not folio3.com",
        )
        serper_key = st.text_input("Serper.dev API Key", type="password")

        with st.expander("Advanced Settings"):
            country_code  = st.selectbox("Country",  ["us", "uk", "ca", "au", "in", "pk"], index=0)
            language_code = st.selectbox("Language", ["en", "es", "fr", "de"],              index=0)
            device_type   = st.selectbox("Device",   ["desktop", "mobile"],                 index=0)

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
            elif not serper_key:
                st.error("Serper.dev API Key is required.")
            elif not keywords:
                st.error("Please add keywords to analyze.")
            else:
                st.session_state.domain = target_domain
                st.session_state.results_data = []

                root_domain   = get_root_domain(target_domain)
                progress_text = st.empty()
                progress_bar  = st.progress(0)

                for i, kv in enumerate(keywords):
                    progress_text.text(f"Scanning: '{kv}'  ({i + 1}/{len(keywords)})")
                    res = get_search_results(kv, root_domain, serper_key, country_code, language_code, device_type)

                    if "error" in res:
                        st.error(f"{res['error']}: {res['msg']}")
                        break

                    rank = res.get("rank", "Not in Top 100")
                    url  = res.get("url", "N/A")
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

                    if i < len(keywords) - 1:
                        time.sleep(1.0)

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
            st.subheader("Keyword Intelligence Data")
            df_display = pd.DataFrame(st.session_state.results_data).drop(columns=["Position"], errors="ignore")
            style_cols = [c for c in ["Rank"] if c in df_display.columns]
            styled = df_display.style.map(rank_color, subset=style_cols)
            st.dataframe(styled, use_container_width=True, height=500)

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
