import streamlit as st
import pandas as pd
import requests
import json
import time
import plotly.express as px
import tldextract
from urllib.parse import urlparse

# --- INITIALIZATION ---
def init_session_state():
    if "results_data" not in st.session_state:
        st.session_state.results_data = []
    if "domain" not in st.session_state:
        st.session_state.domain = ""

# --- SEO LOGIC ---
def get_clean_root(url_or_domain):
    """Accurately extracts the root domain (e.g., folio3.com) using tldextract."""
    ext = tldextract.extract(url_or_domain)
    return f"{ext.domain}.{ext.suffix}".lower()

def determine_page_type(url):
    if url == "N/A": return "N/A"
    url_lower = url.lower()
    if any(k in url_lower for k in ["/blog/", "/article/", "/post/", "/news/"]):
        return "Blog"
    return "Landing Page"

def get_search_results(keyword, target_input, api_key, gl="us", hl="en", device="desktop"):
    """Fetches real-time rankings and handles multiple listings per domain."""
    target_root = get_clean_root(target_input)
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    
    payload = json.dumps({
        "q": keyword, "gl": gl, "hl": hl, "num": 100, 
        "autocorrect": False, "device": device
    })
    
    try:
        response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
        if response.status_code != 200: return {"error": "API Error"}
            
        data = response.json()
        organic = data.get("organic", [])
        found_matches = [] 

        for result in organic:
            link = result.get("link", "")
            pos = result.get("position")
            if get_clean_root(link) == target_root:
                found_matches.append((link, pos))

        if not found_matches:
            return {"rank": "Not in Top 100", "url": "N/A", "all_ranks": "N/A"}

        # Sort matches so the best rank is first
        found_matches.sort(key=lambda x: x[1])
        return {
            "rank": str(found_matches[0][1]),
            "url": found_matches[0][0],
            "all_ranks": ", ".join([f"Pos {p}" for u, p in found_matches])
        }
    except: return {"error": "System Error"}

# --- THEME-ADAPTIVE STYLING ---
def render_styling():
    """Uses Streamlit CSS variables to support Light and Dark themes automatically."""
    st.markdown("""
        <style>
        .metric-container {
            background-color: var(--secondary-bg-color);
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            margin-bottom: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .metric-value {
            font-size: 2.2rem;
            font-weight: 800;
            color: var(--text-color);
        }
        .metric-label {
            font-size: 0.85rem;
            color: var(--text-color);
            opacity: 0.7;
            text-transform: uppercase;
            font-weight: 600;
        }
        /* Style adjustments for cleaner table view */
        [data-testid="stDataFrame"] {
            border: 1px solid var(--border-color);
            border-radius: 8px;
        }
        </style>
    """, unsafe_allow_html=True)

def color_coding(val):
    if val == "Not in Top 100": 
        return 'background-color: rgba(239, 68, 68, 0.15); color: #ef4444;'
    try:
        v = int(str(val))
        if v <= 3: return 'background-color: rgba(16, 185, 129, 0.2); color: #10b981; font-weight: bold;'
        if v <= 10: return 'background-color: rgba(52, 211, 153, 0.15); color: #34d399;'
        return 'color: #f59e0b;' 
    except: return ''

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="AI Keyword Tracker", page_icon="🎯", layout="wide")
    init_session_state()
    render_styling()
    
    st.title("🎯 AI Keyword Tracker")

    with st.sidebar:
        st.header("⚙️ Configuration")
        target_domain = st.text_input("Target Domain", value=st.session_state.domain, placeholder="e.g. folio3.com")
        serpapi_key = st.text_input("Serper.dev API Key", type="password")
        
        st.divider()
        input_method = st.radio("Input Keywords", ["📄 CSV", "⌨️ Paste"])
        keywords = []
        
        if input_method == "📄 CSV":
            file = st.file_uploader("Upload CSV", type=["csv"])
            if file:
                df = pd.read_csv(file)
                col = next((c for c in df.columns if 'keyword' in c.lower()), None)
                if col: keywords = df[col].dropna().tolist()
        else:
            text = st.text_area("One keyword per line")
            keywords = [k.strip() for k in text.split('\n') if k.strip()]

        if st.button("🚀 Analyze SERP", type="primary", use_container_width=True):
            if target_domain and serpapi_key and keywords:
                st.session_state.domain = target_domain
                st.session_state.results_data = []
                p_bar = st.progress(0)
                
                for i, kw in enumerate(keywords):
                    res = get_search_results(kw, target_domain, serpapi_key)
                    st.session_state.results_data.append({
                        "Keyword": kw,
                        "Best Rank": res.get("rank"), # Uniform naming to fix KeyError
                        "URL": res.get("url"),
                        "Page Type": determine_page_type(res.get("url")),
                        "All Listings": res.get("all_ranks")
                    })
                    p_bar.progress((i + 1) / len(keywords))
                st.success("Complete!")

    tab1, tab2, tab3 = st.tabs(["📊 Dashboard Overview", "🔍 Keyword Intelligence", "📥 Export"])

    with tab1:
        if st.session_state.results_data:
            df = pd.DataFrame(st.session_state.results_data)
            # Ensuring numeric conversion for metrics
            valid = [int(r) for r in df["Best Rank"] if str(r).isdigit()]
            
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(f'<div class="metric-container"><div class="metric-label">Top 10</div><div class="metric-value">{len([r for r in valid if r <= 10])}</div></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="metric-container"><div class="metric-label">Avg Rank</div><div class="metric-value">{(sum(valid)/len(valid)) if valid else 0 :.1f}</div></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="metric-container"><div class="metric-label">Visibility</div><div class="metric-value">{len(valid)} / {len(df)}</div></div>', unsafe_allow_html=True)
            
            fig = px.histogram(df[df["Best Rank"].apply(lambda x: str(x).isdigit())], 
                               x="Best Rank", template="none", title="Rank Distribution")
            st.plotly_chart(fig, use_container_width=True, theme="streamlit")

    with tab2:
        if st.session_state.results_data:
            df_display = pd.DataFrame(st.session_state.results_data)
            # Fix: Using .map() instead of .applymap() to avoid AttributeError
            st.dataframe(df_display.style.map(color_coding, subset=['Best Rank']), 
                         use_container_width=True, height=600)

    with tab3:
        if st.session_state.results_data:
            csv = pd.DataFrame(st.session_state.results_data).to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Report", csv, "seo_report.csv", "text/csv")

if __name__ == "__main__":
    main()
