import streamlit as st
import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_URL = os.getenv('API_URL', 'http://localhost:8000')

st.set_page_config(
    page_title="SHL Assessment Recommender",
    page_icon="📊",
    layout="wide"
)

st.title("SHL Assessment Recommendation System")
st.markdown("Enter a job description or query to get relevant SHL assessment recommendations.")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    api_url_input = st.text_input("API URL", value=API_URL)
    if api_url_input:
        API_URL = api_url_input

# Main input area
query = st.text_area(
    "Enter your job description or query:",
    height=200,
    placeholder="""Example: I am hiring for Java developers who can collaborate effectively with business teams. 
    Looking for assessments that can be completed in 40 minutes."""
)

col1, col2 = st.columns([1, 5])
with col1:
    submit_button = st.button("Get Recommendations", type="primary", use_container_width=True)
with col2:
    st.markdown("")

if submit_button or query:
    if not query.strip():
        st.error("Please enter a query")
    else:
        with st.spinner("Finding relevant assessments..."):
            try:
                response = requests.post(
                    f"{API_URL}/recommend",
                    json={"query": query},
                    timeout=60
                )
                response.raise_for_status()
                data = response.json()
                
                assessments = data['recommended_assessments']
                
                if assessments:
                    st.success(f"Found {len(assessments)} recommendations")
                    
                    # Display summary statistics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        # Exclude 0/null durations from average calculation
                        durations = [a['duration'] for a in assessments if a.get('duration', 0) and a['duration'] > 0]
                        if durations:
                            avg_duration = sum(durations) / len(durations)
                            st.metric("Average Duration", f"{avg_duration:.0f} mins")
                        else:
                            st.metric("Average Duration", "N/A")
                    with col2:
                        remote_count = sum(1 for a in assessments if a['remote_support'] == 'Yes')
                        st.metric("Remote Supported", f"{remote_count}/{len(assessments)}")
                    with col3:
                        adaptive_count = sum(1 for a in assessments if a['adaptive_support'] == 'Yes')
                        st.metric("Adaptive Tests", f"{adaptive_count}/{len(assessments)}", help="Adaptive tests use IRT (Item Response Theory) to adjust difficulty based on responses. Most technical skill assessments are not adaptive.")
                    
                    # Display as table
                    st.subheader("Recommended Assessments")
                    df = pd.DataFrame([
                        {
                            'Rank': i + 1,
                            'Name': a['name'],
                            'Duration (mins)': a['duration'],
                            'Test Type': ', '.join(a['test_type']) if a['test_type'] else 'Unknown',
                            'Remote Support': a['remote_support'],
                            'Adaptive': a['adaptive_support'],
                            'URL': a['url']
                        }
                        for i, a in enumerate(assessments)
                    ])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # Display detailed cards
                    st.subheader("Detailed Information")
                    for i, assessment in enumerate(assessments, 1):
                        with st.expander(f"{i}. {assessment['name']}", expanded=(i == 1)):
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                st.write(f"**URL:** [{assessment['url']}]({assessment['url']})")
                                # Clean description - fix ellipsis encoding issue
                                description = assessment.get('description', '') or ''
                                # Replace common encoding issues with proper ellipsis
                                description = description.replace('â€¦', '…').replace('â€"', '—').replace('â€™', "'")
                                st.write(f"**Description:** {description}")
                            with col2:
                                duration_display = f"{assessment['duration']} minutes" if assessment.get('duration', 0) and assessment['duration'] > 0 else "Not specified"
                                st.write(f"**Duration:** {duration_display}")
                                st.write(f"**Test Type:** {', '.join(assessment['test_type']) if assessment['test_type'] else 'Unknown'}")
                                st.write(f"**Remote Support:** {assessment['remote_support']}")
                                st.write(f"**Adaptive Support:** {assessment['adaptive_support']}")
                else:
                    st.warning("No assessments found")
                    
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to API. Make sure the API is running.")
                st.info(f"Expected API URL: {API_URL}")
                st.code("uvicorn src.api:app --reload", language="bash")
            except requests.exceptions.Timeout:
                st.error("Request timed out. The API may be processing a large query.")
            except requests.exceptions.HTTPError as e:
                st.error(f"API Error: {e}")
                if e.response.status_code == 500:
                    st.info("The API may need the vector database initialized. Run: python src/embeddings.py")
            except Exception as e:
                st.error(f"Error: {e}")

# Footer
st.markdown("---")
st.markdown("**SHL Assessment Recommendation System** - Built for AI Research Intern Assessment")


