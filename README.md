# NavapathXR
An AI-powered ocean prediction platform that leverages ARGO float data to forecast ocean conditions like temperature and salinity. It combines a Flask backend with mock RAG pipelines and Plotly dashboards to provide interactive forecasts, confidence levels, and visual insights for climate and marine research.

## About
Oceanographic data is vast, complex, and often difficult to access. The ARGO program generates extensive datasets from autonomous profiling floats, but exploring this data requires technical skills and familiarity with formats like NetCDF.

**NAVPATHXR** is an AI-powered platform that allows users to query, explore, and visualize ARGO float data using natural language. It bridges the gap between raw data and actionable insights, making oceanographic exploration accessible to researchers, students, and decision-makers.

---

## Features
- **Natural Language Queries:** Ask questions like "Show salinity profiles near the equator in March 2023"  
- **Interactive Dashboards:** Visualize oceanographic parameters over time and space  
- **Profile Comparison:** Compare temperature, salinity, or BGC parameters across regions and months  
- **Float Tracking:** Locate the nearest ARGO floats and explore their trajectories  
- **Data Export:** Export data in CSV, NetCDF, or ASCII formats  
- **Extensible:** Future support for BGC floats, gliders, buoys, and satellite datasets  

---

## Technology Stack
- **Backend:** Python, PostgreSQL, FAISS/Chroma vector database  
- **AI:** Large Language Models (GPT, QWEN, LLaMA) with RAG pipelines  
- **Frontend:** Streamlit / Dash, Plotly, Leaflet, Cesium  
- **Data Format:** NetCDF, CSV, Parquet  

---

## How It Works
1. **Data Ingestion:** ARGO NetCDF files are processed and converted into structured formats.  
2. **Storage:** Metadata and summaries are stored in relational and vector databases.  
3. **Query Processing:** LLMs interpret user queries via Retrieval-Augmented Generation (RAG) and map them to database queries.  
4. **Visualization:** Interactive dashboards display profiles, maps, and comparisons.  
5. **User Interaction:** Chatbot-style interface allows natural language exploration of ocean data.  

---


