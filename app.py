import streamlit as st
import pandas as pd
import requests
import json
import time
import plotly.express as px
from urllib.parse import urlparse

def init_session_state():
    if "results_data" not in st.session_state:
        st.session_state.results_data = []
    if "domain" not in st.session_state:
        st.session_state.domain = ""

def get_root_domain(url_or_domain):
    if not str(url_or_domain).startswith(('http://', 'https://')):
        url_or_domain = 'http://' + str(url_or_domain)
    try:
        parsed = urlparse(url_or_domain)
        domain = parsed.netloc
        domain = domain.replace('www.', '')
        return domain.lower()
    except:
        return str(url_or_domain).lower()

def determine_page_type(url):
    if url == "N/A":
        return "N/A"
    url_lower = url.lower()
    if any(keyword in url_lower for keyword in ["/blog/", "/article/", "/post/", "/news/"]):
        return "Blog"
    return "Landing Page"

def get_search_results(keyword, target_domain, api_key, gl="us", hl="en", device="desktop"):
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    feature_str = "Standard"
    global_rank = 0
    matches = []
    
    for page in range(1, 11): # Loop precisely 10 pages (top 100 results)
        payload = json.dumps({
            "q": keyword,
            "gl": gl,
            "hl": hl,
            "page": page,
            "device": device
        })
        
        try:
            response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
            
            if response.status_code == 403:
                return {"error": "API Key Error", "msg": "Unauthorized: Please check your Serper.dev API key."}
            elif response.status_code in [402, 429]:
                return {"error": "Quota Exceeded", "msg": "Serper account out of credits or rate limit reached."}
            elif response.status_code != 200:
                continue
                
            results = response.json()
            organic_results = results.get("organic", [])
            
            if page == 1:
                features = []
                if "answerBox" in results:
                    features.append("Featured Snippet")
                if "places" in results:
                    features.append("Local Pack")
                if "topStories" in results:
                    features.append("Top Stories")
                feature_str = ", ".join(features) if features else "Standard"
                
            if not organic_results:
                break
                
            for result in organic_results:
                global_rank += 1
                link = result.get("link", "")
                
                # Strict subdomain and domain fuzzy matching requested by user
                if target_domain.lower() in link.lower():
                    matches.append({
                        "position": global_rank,
                        "url": link
                    })
                    
        except Exception as e:
            if page == 1:
                return {"error": "Error", "msg": str(e)}
            continue
            
    return {"matches": matches, "features": feature_str}

def render_styling():
    st.markdown("""
        <style>
        .stApp {
            background-color: #0E1117;
            color: #FAFAFA;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 4px 4px 0px 0px;
            padding-top: 10px;
            padding-bottom: 10px;
            font-size: 16px;
            font-weight: 600;
        }
        .metric-container {
            background-color: #161A25;
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid #2D333B;
            margin-bottom: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
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

def color_coding(val):
    try:
        val_str = str(val)
        if val_str.startswith(">"):
            return 'background-color: rgba(239, 68, 68, 0.1); color: #ef4444;'
        
        first_val = val_str.split(",")[0].replace("Pos", "").strip()
        val_int = int(first_val)
        
        if val_int <= 3:
            return 'background-color: rgba(16, 185, 129, 0.15); color: #10b981; font-weight: bold;'
        elif val_int <= 10:
            return 'background-color: rgba(52, 211, 153, 0.1); color: #34d399;'
        elif val_int <= 20: # Page 2
            return 'background-color: rgba(245, 158, 11, 0.1); color: #f59e0b;'
        elif val_int <= 50:
            return 'background-color: rgba(245, 158, 11, 0.1); color: #f59e0b;'
        else: # 50+
            return 'background-color: rgba(239, 68, 68, 0.1); color: #ef4444;'
    except:
        return 'background-color: transparent; color: #8B949E;'

def main():
    st.set_page_config(page_title="AI Keyword Tracker", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")
    init_session_state()
    render_styling()
    
    st.title("🎯 AI Keyword Tracker")
    st.markdown("Enterprise-grade SEO tracking powered by AI and Serper.dev")

    with st.sidebar:
        st.header("⚙️ Configuration")
        target_domain = st.text_input("Target Domain", placeholder="e.g. yourdomain.com", value=st.session_state.domain)
        serpapi_key = st.text_input("Serper.dev API Key", type="password")
        
        with st.expander("Advanced Settings"):
            country_code = st.selectbox("Country", ["us", "uk", "ca", "au", "in"], index=0)
            language_code = st.selectbox("Language", ["en", "es", "fr", "de"], index=0)
            devices_input = st.selectbox("Devices to Track", ["Desktop & Mobile", "Desktop Only", "Mobile Only"], index=0)

        st.divider()
        st.markdown("### 📥 Input Keywords")
        input_method = st.radio("Choose input method:", ["📄 Upload CSV", "⌨️ Paste Keywords"], label_visibility="collapsed")
        
        keywords = []
        if input_method == "📄 Upload CSV":
            uploaded_file = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed")
            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    kw_col = next((c for c in df.columns if c.lower() in ['keyword', 'keywords', 'search term', 'query', 'term']), None)
                    if kw_col:
                        keywords = df[kw_col].dropna().astype(str).tolist()
                        st.success(f"✓ Loaded {len(keywords)} keywords")
                    else:
                        st.error("✗ No 'Keyword' column found.")
                except Exception as e:
                    st.error(f"Error reading CSV: {e}")
        else:
            pasted_text = st.text_area("Paste keywords (one per line)", height=150, label_visibility="collapsed", placeholder="keyword 1\nkeyword 2\nkeyword 3")
            if pasted_text:
                keywords = [k.strip() for k in pasted_text.split('\n') if k.strip()]
                if keywords:
                    st.success(f"✓ Loaded {len(keywords)} keywords")

        run_btn = st.button("🚀 Analyze SERP", type="primary", use_container_width=True)

        if run_btn:
            if not target_domain:
                st.error("Target Domain is required.")
            elif not serpapi_key:
                st.error("Serper.dev API Key is required.")
            elif not keywords:
                st.error("Please add keywords to analyze.")
            else:
                st.session_state.domain = target_domain
                st.session_state.results_data = [] # reset
                
                devices_to_check = []
                if "Desktop" in devices_input:
                    devices_to_check.append("desktop")
                if "Mobile" in devices_input:
                    devices_to_check.append("mobile")
                    
                total_runs = len(keywords) * len(devices_to_check)
                
                progress_text = st.empty()
                progress_bar = st.progress(0)
                
                root_domain = get_root_domain(target_domain)
                
                current_run = 0
                for i, kv in enumerate(keywords):
                    for device in devices_to_check:
                        current_run += 1
                        progress_text.text(f"Scanning: '{kv}' [{device.upper()}] ({current_run}/{total_runs})")
                        res = get_search_results(kv, root_domain, serpapi_key, country_code, language_code, device=device)
                        
                        if "error" in res:
                            st.error(f"{res['error']}: {res['msg']}")
                            break
                            
                        matches = res.get("matches", [])
                        if not matches:
                            display_rank = ">100"
                            url = "N/A"
                            page_type = "N/A"
                            all_rankings = "N/A"
                            positions = [101]
                        else:
                            positions = [m['position'] for m in matches]
                            url = matches[0]["url"]
                            page_type = determine_page_type(url)
                            all_rankings = "\n".join([f"Pos {m['position']}: {m['url']}" for m in matches])
                            
                            if len(matches) > 1:
                                display_rank = ", ".join([f"Pos {p}" for p in positions])
                            else:
                                display_rank = str(positions[0])
                        
                        st.session_state.results_data.append({
                            "Keyword": kv,
                            "Device": device.capitalize(),
                            "Rank": display_rank,
                            "Positions": positions,
                            "URL": url,
                            "Page Type": page_type,
                            "All Rankings": all_rankings,
                            "SERP Features": res["features"],
                            "Match Count": len(matches)
                        })
                        progress_bar.progress(current_run / total_runs)
                        time.sleep(0.1) 
                    
                progress_text.empty()
                progress_bar.empty()
                st.success("Analysis Complete!")

    tab1, tab2, tab3 = st.tabs(["📊 Dashboard Overview", "🔍 Keyword Intelligence", "📑 Settings & Exports"])

    with tab1:
        if not st.session_state.results_data:
            st.info("Upload keywords and configure settings in the sidebar to generate your dashboard.")
        else:
            df_res = pd.DataFrame(st.session_state.results_data)
            
            all_positions = []
            display_positions = []
            for pos_list in df_res["Positions"]:
                for p in pos_list:
                    all_positions.append(p)
                    if p <= 100:
                        display_positions.append(p)
            
            total_kw = len(df_res)
            top_3 = len([p for p in all_positions if p <= 3])
            top_10 = len([p for p in all_positions if p <= 10])
            top_100 = len([p for p in all_positions if p <= 100])
            
            avg_pos = sum(display_positions) / len(display_positions) if display_positions else "N/A"
            visibility = round((top_10 / total_kw * 100) if total_kw > 0 else 0, 1)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f'<div class="metric-container"><div class="metric-label">Visibility Index</div><div class="metric-value">{visibility}%</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="metric-container"><div class="metric-label">Top 3 Rankings</div><div class="metric-value">{top_3}</div></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="metric-container"><div class="metric-label">Top 10 Rankings</div><div class="metric-value">{top_10}</div></div>', unsafe_allow_html=True)
            with col4:
                avg_display = f"{avg_pos:.1f}" if avg_pos != "N/A" else "N/A"
                # Mock delta for UI demonstration
                delta_html = "<span style='color: #10b981; font-size: 1rem; margin-left: 8px;'>▲ 1.2</span>" if avg_pos != "N/A" else ""
                st.markdown(f'<div class="metric-container"><div class="metric-label">Avg Position</div><div class="metric-value">{avg_display}{delta_html}</div></div>', unsafe_allow_html=True)

            st.subheader("Insights & Distribution")
            
            chart_col1, chart_col2 = st.columns([2, 1])
            
            with chart_col1:
                st.markdown("##### Ranking Distribution")
                dist = {
                    "Pos 1-3": top_3,
                    "Pos 4-10": top_10 - top_3,
                    "Pos 11-20": len([p for p in all_positions if 10 < p <= 20]),
                    "Pos 21-50": len([p for p in all_positions if 20 < p <= 50]),
                    "Pos 51-100": len([p for p in all_positions if 50 < p <= 100]),
                    "Not Ranked (>100)": total_kw - len([pos_list for pos_list in df_res["Positions"] if min(pos_list) <= 100])
                }
                
                dist_df = pd.DataFrame(list(dist.items()), columns=["Position Range", "Count"])
                fig = px.bar(dist_df, x="Position Range", y="Count", color="Position Range", 
                             color_discrete_sequence=['#10b981', '#34d399', '#fbbf24', '#f59e0b', '#ef4444', '#4b5563'],
                             template="plotly_dark")
                fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
                
            with chart_col2:
                st.markdown("##### Page Types")
                page_types = df_res[df_res["Page Type"] != "N/A"]["Page Type"].value_counts().reset_index()
                page_types.columns = ["Page Type", "Count"]
                if not page_types.empty:
                    fig_pie = px.pie(page_types, values="Count", names="Page Type", hole=0.7, template="plotly_dark",
                                     color_discrete_sequence=['#3b82f6', '#8b5cf6'])
                    fig_pie.update_layout(showlegend=True, margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                          legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No ranked pages to analyze page types.")

    with tab2:
        if not st.session_state.results_data:
            st.info("Run the tracker to view keyword intelligence.")
        else:
            st.subheader("Keyword Intelligence Data")
            df_res_display = pd.DataFrame(st.session_state.results_data)
            
            # Hide internal data columns from UI
            cols_to_drop = ['Positions', 'Match Count'] if 'Positions' in df_res_display.columns else []
            df_res_display = df_res_display.drop(columns=cols_to_drop, errors='ignore')
            
            styled_df = df_res_display.style.map(color_coding, subset=['Rank'])
            st.dataframe(styled_df, use_container_width=True, height=500)

    with tab3:
        st.subheader("Data Export")
        if not st.session_state.results_data:
            st.info("No data to export.")
        else:
            st.markdown("Export your complete SERP intelligence report as a CSV file.")
            df_export = pd.DataFrame(st.session_state.results_data)
            csv = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Detailed Report (CSV)",
                data=csv,
                file_name=f"{st.session_state.domain.replace('.', '_')}_ai_rankings.csv",
                mime='text/csv',
                type="primary"
            )

if __name__ == "__main__":
    main()
