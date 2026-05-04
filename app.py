import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import time

def get_search_results(keyword, target_domain, api_key):
    for start in [0, 10, 20, 30, 40]:
        params = {
            "engine": "google",
            "q": keyword,
            "location": "United States",
            "gl": "us",
            "hl": "en",
            "device": "desktop",
            "start": start,
            "api_key": api_key
        }
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if "error" in results:
                error_msg = results.get("error", "")
                if "Invalid API key" in error_msg:
                    return "API Key Error", "Please provide a valid SerpApi Key."
                elif "out of bounds" in error_msg.lower() or "credits" in error_msg.lower():
                    return "Quota Exceeded", "SerpApi account out of credits or rate limit reached."
                elif "rate limit" in error_msg.lower():
                    return "Rate Limit", "Too many requests to SerpApi. Please slow down."
                else:
                    return "API Error", error_msg
                
            organic_results = results.get("organic_results", [])
            
            for result in organic_results:
                link = result.get("link", "")
                if target_domain.lower() in link.lower():
                    return result.get("position", "N/A"), link
                    
        except Exception as e:
            return "Error", str(e)
            
    return "Not in Top 50", "N/A"

def main():
    st.set_page_config(page_title="Keyword Rank Tracker", page_icon="📊", layout="wide")
    
    st.title("📊 Keyword Rank Tracker")
    st.markdown("Track your website's keyword rankings in the US region using SerpApi.")

    # Sidebar for Settings
    with st.sidebar:
        st.header("⚙️ Settings")
        target_domain = st.text_input("Target Domain", placeholder="mysite.com", help="Domain to track (e.g., mysite.com)")
        serpapi_key = st.text_input("SerpApi Key", type="password", help="Your SerpApi private key")
        
        st.divider()
        
        st.markdown("### 📝 Instructions")
        st.markdown(
            "1. **Configure**: Set your Target Domain and API Key above.
"
            "2. **Upload**: Provide a CSV file containing your keywords.
"
            "3. **Launch**: Click the **Run Tracker** button."
        )

    # Main Area - Upload
    st.subheader("1. Upload Keywords")
    uploaded_file = st.file_uploader("Upload CSV containing keywords", type=["csv"])
    
    keywords = []
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            kw_col = next((c for c in df.columns if c.lower() in ['keyword', 'keywords', 'search term', 'query', 'term']), None)
            
            if kw_col:
                keywords = df[kw_col].dropna().astype(str).tolist()
                st.success(f"Loaded {len(keywords)} keywords from the '{kw_col}' column.")
            else:
                st.error("Could not find a 'Keyword' column in the uploaded CSV.")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")

    # Metrics Placeholder
    metrics_container = st.container()

    # Execution
    st.subheader("2. Run Tracker")
    if st.button("▶ Run Tracker", type="primary"):
        if not target_domain:
            st.sidebar.error("Please provide a Target Domain.")
        elif not serpapi_key:
            st.sidebar.error("Please provide a SerpApi Key.")
        elif not keywords:
            st.warning("Please upload a valid CSV with keywords.")
        else:
            results_data = []
            
            with st.spinner("Fetching ranking data..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, keyword in enumerate(keywords):
                    status_text.text(f"Fetching: '{keyword}' ({i+1}/{len(keywords)})")
                    
                    rank, url = get_search_results(keyword, target_domain, serpapi_key)
                    
                    results_data.append({
                        "Keyword": keyword,
                        "Current Rank": rank,
                        "URL": url
                    })
                    
                    progress_bar.progress((i + 1) / len(keywords))
                    time.sleep(0.2) 
                    
                status_text.empty()
                progress_bar.empty()
            
            st.success("Successfully fetched all keyword rankings!")
            
            # Generate DataFrame
            results_df = pd.DataFrame(results_data)
            
            # Calculate Metrics
            total_keywords = len(results_df)
            numeric_ranks = pd.to_numeric(results_df["Current Rank"], errors='coerce').dropna()
            top_3 = len(numeric_ranks[numeric_ranks <= 3]) if not numeric_ranks.empty else 0
            avg_pos = round(numeric_ranks.mean(), 1) if not numeric_ranks.empty else "N/A"
            
            # Display Metrics Container
            with metrics_container:
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Keywords", total_keywords)
                col2.metric("Top 3 Rankings", top_3)
                col3.metric("Average Position", avg_pos)
            
            # Output Table
            st.subheader("3. Results")
            st.dataframe(results_df, use_container_width=True)
            
            csv_data = results_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv_data,
                file_name=f"{target_domain.replace('.', '_')}_rankings.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
