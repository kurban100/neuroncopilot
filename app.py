import os
import streamlit as st
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage, Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from src.graph.knowledge_graph import KnowledgeGraph

# ============ CONFIGURE MODELS ============
Settings.llm = Ollama(model="qwen2.5:0.5b", request_timeout=360.0)
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

# ============ TEACHING BEHAVIORS ============

def classify_query(user_input):
    """Classify user query into teaching behavior type"""
    user_lower = user_input.lower()
    
    if "quiz me" in user_lower or "test me" in user_lower:
        return "quiz"
    elif "explain this code" in user_lower or "what does this code" in user_lower:
        return "code_explanation"
    elif "?" in user_input and len(user_input.split()) <= 5 and not user_input.lower().startswith("what"):
        return "clarification"
    else:
        return "guided_prompt"

TEACHING_PROMPTS = {
    "guided_prompt": """You are a Socratic tutor. Instead of directly answering, ask a thought-provoking question 
    that helps the student discover the answer themselves. Guide them to think deeper about: {query}
    
    Ask ONE guiding question that encourages critical thinking.""",
    
    "clarification": """The student asked a brief question: {query}
    
    Ask ONE clarifying question to understand exactly what aspect they want to learn about. 
    Keep it focused and helpful.""",
    
    "quiz": """Create a multiple-choice quiz question about: {query}
    
    Format:
    Question: [Clear question]
    A) [Option]
    B) [Option]
    C) [Option]
    D) [Option]
    
    Correct Answer: [Letter]
    Explanation: [Why this is correct]""",
    
    "code_explanation": """Provide a line-by-line explanation of this code concept: {query}
    
    For each key line or block:
    1. Show the code element
    2. Explain what it does
    3. Explain WHY it's important
    
    Use clear annotations and avoid jargon."""
}

def apply_teaching_behavior(query, behavior_type, base_response):
    """Apply teaching behavior wrapper around base response"""
    
    if behavior_type == "guided_prompt":
        prompt = f"""Based on this information: {base_response}
        
        Instead of giving the answer directly, ask the student a Socratic question that helps them discover it.
        Make it thought-provoking but not too difficult."""
        
    elif behavior_type == "clarification":
        prompt = f"""The student asked: "{query}"
        
        Ask ONE specific clarifying question to better understand what aspect they want to learn about.
        Options to clarify: concept vs implementation, theoretical vs practical, basic vs advanced."""
        
    elif behavior_type == "quiz":
        prompt = f"""Based on this content: {base_response}
        
        Create a multiple-choice question that tests understanding of the key concept.
        Include 4 options (A-D) and provide the correct answer with explanation."""
        
    elif behavior_type == "code_explanation":
        prompt = f"""Content: {base_response}
        
        Provide step-by-step code explanation with:
        - What each part does
        - Why it's structured this way
        - Common mistakes to avoid"""
    
    return Settings.llm.complete(prompt).text

# ============ LOAD INDEX ============

@st.cache_resource
def load_query_engine():
    persist_dir = r"D:\Neuron_Copilot_Demo\storage"
    
    if not os.path.exists(persist_dir):
        st.error(f"❌ Storage not found at {persist_dir}!")
        st.stop()
    
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    index = load_index_from_storage(storage_context)
    return index.as_query_engine(llm=Settings.llm)

@st.cache_resource
def get_knowledge_graph():
    return KnowledgeGraph()

query_engine = load_query_engine()
kg = get_knowledge_graph()

# ============ STREAMLIT UI ============

st.set_page_config(page_title="NeuronCopilot", layout="wide")

st.title("🧠 NeuronCopilot AgenEducation")
st.write("**Learner-Centric AI Pedagogy with Four Teaching Behaviors**")

# ========== SIDEBAR: LEARNING PATH WITH LOGIN ==========

st.sidebar.title("📚 Your Learning Path")

# Initialize session state
if 'student_id' not in st.session_state:
    st.session_state.student_id = None
if 'show_login' not in st.session_state:
    st.session_state.show_login = False

# Login/Logout buttons
login_col1, login_col2 = st.sidebar.columns(2)
with login_col1:
    if st.button("🔐 Login", key="login_btn"):
        st.session_state.show_login = True

with login_col2:
    if st.session_state.student_id:
        if st.button("🚪 Logout", key="logout_btn"):
            st.session_state.student_id = None
            st.rerun()

# Show login form if needed
if st.session_state.show_login:
    student_id = st.sidebar.text_input("Enter Student ID:", key="student_id_input", placeholder="e.g., student_001")
    if st.sidebar.button("Confirm", key="confirm_btn"):
        if student_id.strip():
            st.session_state.student_id = student_id
            st.session_state.show_login = False
            st.rerun()

# Display recommendations based on login status
st.sidebar.markdown("---")

if st.session_state.student_id:
    # ✓ METHOD 2: PERSONALIZED (Student logged in)
    st.sidebar.markdown(f"### 👤 Welcome!")
    st.sidebar.markdown(f"**Student ID:** {st.session_state.student_id}")
    st.sidebar.markdown("### 📖 Your Recommended Next:")
    
try:
    recommendations = kg.get_next_recommendations(st.session_state.student_id)
    if recommendations:
        for rec in recommendations[:3]:
            difficulty_stars = "⭐" * rec['difficulty']
            st.sidebar.markdown(
                f"- 🔹 **{rec['name']}** {difficulty_stars}\n"
                f"  *(Ready: {rec['prerequisites_met']} prereqs met)*"
            )
    else:
        st.sidebar.markdown("*No more recommendations available!* 🎉")
except Exception as e:
    st.sidebar.error(f"Error: {str(e)}")  # ← SHOW THE ERROR!
    print(f"DEBUG ERROR: {e}")  # ← Print to terminal too
    print(f"DEBUG ERROR: {e}")  # Also print to terminal
else:
    # ❌ METHOD 1: CONCEPT-BASED (No login)
    st.sidebar.markdown("### 📖 Explore Concepts:")
    st.sidebar.caption("Login to see personalized recommendations")
    
    concept_to_explore = st.sidebar.selectbox(
        "Select a concept:",
        ["Gradient Descent", "Cost Functions", "Linear Regression", "Neural Networks", "Backpropagation"],
        key="concept_select"
    )
    
    try:
        related = kg.get_next_concepts(concept_to_explore)
        if related:
            st.sidebar.markdown(f"**{concept_to_explore}** connects to:")
            for concept in related:
                st.sidebar.markdown(f"- 🔗 {concept}")
        else:
            st.sidebar.markdown("*No connected concepts*")
    except Exception as e:
        st.sidebar.warning(f"Error loading connections")

# Learning progress
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Progress")
if st.session_state.student_id:
    st.sidebar.progress(0.65)
    st.sidebar.caption("Mastered: 3/11 concepts")
else:
    st.sidebar.caption("*Login to track progress*")

# ========== SIDEBAR: TEACHING BEHAVIORS ==========
st.sidebar.markdown("---")
st.sidebar.title("🎓 Teaching Behaviors")
st.sidebar.markdown("""
- 💭 **Guided Prompts**: Socratic questions
- 🎯 **Clarifications**: Scope narrowing  
- 📝 **Quizzes**: Knowledge checks
- 💻 **Code Explanations**: Step-by-step
""")

# Manual override (optional)
st.sidebar.markdown("---")
override = st.sidebar.checkbox("Manual behavior selection", key="manual_override")
if override:
    behavior_type = st.sidebar.selectbox(
        "Select teaching behavior:",
        ["guided_prompt", "clarification", "quiz", "code_explanation"],
        key="behavior_select"
    )
else:
    behavior_type = None

# ========== MAIN CONTENT ==========

# Query input
query = st.text_input("Ask about your course materials:", placeholder="e.g., What is gradient descent?")

if st.button("Ask", type="primary"):
    if query:
        # Classify query
        detected_behavior = classify_query(query) if not override else behavior_type
        
        # Show detected behavior
        behavior_names = {
            "guided_prompt": "💭 Guided Prompt (Socratic)",
            "clarification": "🎯 Clarification Needed",
            "quiz": "📝 Quiz Mode",
            "code_explanation": "💻 Code Explanation"
        }
        st.info(f"**Teaching Behavior:** {behavior_names[detected_behavior]}")
        
        with st.spinner("Thinking..."):
            # Get base response from RAG
            base_response = query_engine.query(query)
            
            # Apply teaching behavior
            final_response = apply_teaching_behavior(
                query, 
                detected_behavior, 
                str(base_response)
            )
            
            # Display
            st.write("**Answer:**")
            st.write(final_response)
            
            # Show raw response in expander
            with st.expander("Show base knowledge (for debugging)"):
                st.write(base_response)
    else:
        st.warning("Please enter a question!")