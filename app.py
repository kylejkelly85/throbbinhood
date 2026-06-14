import streamlit as st
import os

st.set_page_config(page_title="Throbbinhood Storage Test", layout="wide")
st.title("🚀 Throbbinhood Streamlit Dashboard")

# Create a local folder called 'input' inside your app workspace
SAVE_DIR = "input"
os.makedirs(SAVE_DIR, exist_ok=True)

uploaded_file = st.file_uploader("Upload a file to test local storage save", type=["pdf", "txt"])

if uploaded_file:
    # Build the path where it will land
    file_path = os.path.join(SAVE_DIR, uploaded_file.name)
    
    # Corrected method: getbuffer() has no underscore
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    st.success(f"✅ Saved permanently! File is sitting at: `{file_path}`")
    
    # List the directory to visually confirm the file exists on the disk
    st.write("📁 **Current files in storage directory:**")
    st.code(os.listdir(SAVE_DIR))
