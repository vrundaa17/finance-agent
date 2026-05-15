import streamlit as st
import document_faq as nlp
import assistant as rag

# Page Setup "Title + Layout"
st.set_page_config(page_title="Automated FAQ Generator", layout="wide")

# Helper Analytics function
def display_faq_metrics(faq, row=None, product_fields=None,):
    st.subheader("FAQ Metrics")
    num_faqs = len(faq)
    coverage = None
    if row is not None and product_fields is not None:
        coverage = sum([1 for field in product_fields if str(row[field]) in [f['answer'] for f in faq]]) / len(product_fields) * 100
    
    avg_q_len = sum(len(f['question'].split()) for f in faq) / num_faqs
    unique_q = len(set(f['question'] for f in faq)) / num_faqs * 100
    
    st.markdown(f"- **Number of FAQs generated:** {num_faqs}")
    if coverage is not None:
        st.markdown(f"- **Coverage of product fields:** {coverage:.1f}%")
    st.markdown(f"- **Average question length (words):** {avg_q_len:.1f}")
    st.markdown(f"- **Uniqueness of questions:** {unique_q:.1f}%")
    
# Title
st.title("📄 Document Assistant")

st.write("Upload a document and either:\n")

# File 
uploaded_file = st.file_uploader(
    "Upload PDF Files",
    type=["pdf"]
)

if uploaded_file is not None:

    # Saving temp file
    temp_path = f"temp_{uploaded_file.name}"

    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success("File uploaded successfully!")


    if "rag_chain" not in st.session_state:

        with st.spinner("Building RAG system..."):
            st.session_state.rag_chain = rag.create_rag_chain(temp_path)
        st.success("RAG system ready!")



    st.subheader("Ask Questions")
    user_question = st.text_input("Enter your question")

    if st.button("Ask"):
        if user_question.strip() != "":
            with st.spinner("Searching document..."):
                result = rag.ask_question(st.session_state.rag_chain,user_question)

            st.markdown("### Answer")
            st.write(result["answer"])
            st.markdown("### Sources")

            for s in result["sources"]:
                st.write(s)

   