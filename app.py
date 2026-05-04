import streamlit as st
import pandas as pd
import requests
import time
import json

def get_search_results(keyword, target_domain, api_key, gl="us", hl="en"):
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    # Loop to check the first 3 pages
    for page in range(1, 4):
        payload = json.dumps({
            "q": keyword,
            "gl": gl,
            "hl": hl,
            "num": 100,
            "page": page
        })
        
        try:
            response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
            
            if response.status_code == 403:
                return "API Key Error", "Unauthorized: Please check your Serper.dev API key."
            elif response.status_code in [402, 429]:
                return "Quota Exceeded", "Serper account out of credits or rate limit reached."
            elif response.status_code != 200:
                return "API Error", f"HTTP {response.status_code}"
                
            results = response.json()
            organic_results = results.get("organic", [])
            
            for result in organic_results:
                link = result.get("link", "")
                
                # Check if target domain is inside the found URL (fuzzy matching for subdomains)
                if target_domain.lower() in link.lower():
                    return result.get("position", "N/A"), link
                    
            # If no organic results are returned or less than 100 hit, we can safely exit the loop early
            if len(organic_results) < 100:
                break
                
        except Exception as e:
            return "Error", str(e)
            
    return "Not in Top 300", "N/A"

def init_session_state():
    if "results_data" not in st.session_state:
        st.session_state.results_data = []

def main():
    st.set_page_config(page_title="SERP Pulse Dashboard", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")
    init_session_state()
    
    # Custom CSS for SaaS look
    st.markdown("""
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .metric-card {
            background-color: #1E1E1E;
            border-radius: 8px;
            padding: 20px;
            border: 1px solid #333;
        }
        .css-1544g2n {
            padding: 1rem 1rem 1.5rem;
        }
        h1, h2, h3 {
            font-family: 'Inter', sans-serif;
            font-weight: 800;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("⚡ SERP Pulse")
    st.markdown("Advanced Search Engine Ranking Analysis using Serper.dev")

    # --- Sidebar Configuration ---
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        with st.expander("🔑 API & Domain", expanded=True):
            target_domain = st.text_input("Target Domain", placeholder="mysite.com", help="Domain to track (e.g., mysite.com)")
            serpapi_key = st.text_input("Serper.dev API Key", type="password", help="Your Serper.dev private key")
            
        with st.expander("🌍 Search Parameters", expanded=False):
            country_code = st.selectbox("Country (gl)", ["us", "uk", "ca", "au", "in"], index=0)
            language_code = st.selectbox("Language (hl)", ["en", "es", "fr", "de"], index=0)
            
        st.divider()
        st.markdown("### 📝 Instructions")
        st.markdown(
            "1. **Configure API**: Set your Target Domain and Serper.dev Key.\n"
            "2. **Search Settings**: Adjust location and details if needed.\n"
            "3. **Upload**: Use the Tracker panel to upload keyword CSV.\n"
            "4. **Analyze**: View results and visual metrics."
        )

    # --- Main Dashboard Tabs ---
    tab_track, tab_dashboard = st.tabs(["🔍 Rank Tracker", "📊 Analytics Dashboard"])

    with tab_track:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("1. Upload Keywords")
            st.markdown("CSV must contain a column named **Keyword**.")
            uploaded_file = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed")
            
            keywords = []
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

        with col2:
            st.subheader("2. Execution")
            st.markdown(f"**Target Domain:** {target_domain or 'Not set'} | **Keywords:** {len(keywords)}")
            
            run_btn = st.button("🚀 Start Rank Tracking", type="primary", use_container_width=True)
            
            if run_btn:
                if not target_domain:
                    st.error("Please configure the Target Domain in the sidebar.")
                elif not serpapi_key:
                    st.error("Please provide your Serper.dev Key in the sidebar.")
                elif not keywords:
                    st.warning("Please upload a CSV containing keywords first.")
                else:
                    st.session_state.results_data = [] # Reset data
                    
                    with st.status("Analyzing SERP Data...", expanded=True) as status:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for i, keyword in enumerate(keywords):
                            status_text.text(f"Fetching: '{keyword}' ({i+1}/{len(keywords)})")
                            
                            rank, url = get_search_results(keyword, target_domain, serpapi_key, country_code, language_code)
                            
                            st.session_state.results_data.append({
                                "Keyword": keyword,
                                "Rank": rank,
                                "URL": url
                            })
                            
                            progress_bar.progress((i + 1) / len(keywords))
                            time.sleep(0.2) 
                            
                        status.update(label="Analysis Complete!", state="complete", expanded=False)
                    st.success("Successfully fetched ranking data. Check the Analytics Dashboard!")

    with tab_dashboard:
        if not st.session_state.results_data:
            st.info("No data available yet. Please run the tracker first.")
        else:
            results_df = pd.DataFrame(st.session_state.results_data)
            
            # Clean ranks for metrics calculation
            numeric_ranks = pd.to_numeric(results_df["Rank"], errors='coerce').dropna()
            
            total_keywords = len(results_df)
            top_3 = len(numeric_ranks[numeric_ranks <= 3]) if not numeric_ranks.empty else 0
            avg_pos = round(numeric_ranks.mean(), 1) if not numeric_ranks.empty else "N/A"
            
            # Metrics Row (Total Keywords, Top 3, Average Rank)
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Keywords", total_keywords)
            m2.metric("Top 3", top_3)
            m3.metric("Average Rank", avg_pos)
            
            st.divider()
            
            # Layout for Charts and Data
            chart_col, data_col = st.columns([1, 2])
            
            with chart_col:
                st.subheader("Visibility Summary")
                
                top_10 = len(numeric_ranks[numeric_ranks <= 10]) if not numeric_ranks.empty else 0
                unranked = total_keywords - len(numeric_ranks)
                
                # Prepare data for a simple bar chart
                dist = {
                    "Top 3": top_3,
                    "Pos 4-10": top_10 - top_3,
                    "Pos 11-300": len(numeric_ranks[numeric_ranks > 10]),
                    "Unranked": unranked
                }
                dist_df = pd.DataFrame(list(dist.items()), columns=["Range", "Count"])
                dist_df.set_index("Range", inplace=True)
                st.bar_chart(dist_df, color="#3b82f6")
                
            with data_col:
                st.subheader("Ranking Data")
                
                # Filters
                search_term = st.text_input("🔍 Filter keywords...", "")
                if search_term:
                    display_df = results_df[results_df["Keyword"].str.contains(search_term, case=False)]
                else:
                    display_df = results_df
                    
                st.dataframe(display_df, use_container_width=True, height=350)
                
                # Action Buttons
                csv_data = results_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Export Full Report as CSV",
                    data=csv_data,
                    file_name=f"{target_domain.replace('.', '_')}_rank_report.csv",
                    mime="text/csv",
                    type="primary"
                )

if __name__ == "__main__":
    main()
