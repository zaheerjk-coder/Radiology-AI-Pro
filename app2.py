import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.colors import HexColor
import tempfile
from gemini_api import GEMINI_API_KEY
import json

# Configure API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Page config
st.set_page_config(page_title="RadiologyAI Pro", page_icon="🏥", layout="wide")

# Compact CSS
st.markdown("""
<style>
.main{background:linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%)}
.main-header{font-size:2.5rem;font-weight:700;color:#1e3a8a;text-align:center;padding:1.5rem;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.card{background:white;padding:1.5rem;border-radius:15px;box-shadow:0 4px 6px rgba(0,0,0,0.1);margin:1rem 0;transition:transform 0.3s}
.card:hover{transform:translateY(-5px);box-shadow:0 10px 20px rgba(0,0,0,0.15)}
.stats-box{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:1.5rem;border-radius:15px;text-align:center}
.disclaimer{background:#fef3c7;border-left:4px solid #f59e0b;padding:1rem;border-radius:10px;margin:1rem 0}
.report-box{background:#fff;padding:2rem;border-radius:15px;border-left:5px solid #667eea;box-shadow:0 4px 6px rgba(0,0,0,0.1)}
.stButton>button{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;font-weight:600;border-radius:10px;transition:all 0.3s}
.stButton>button:hover{transform:scale(1.05)}
.metric{text-align:center;padding:1rem;background:white;border-radius:10px;margin:0.5rem}
.comparison{display:flex;gap:1rem;align-items:center}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'history' not in st.session_state:
    st.session_state.history = []
if 'comparison_mode' not in st.session_state:
    st.session_state.comparison_mode = False

# Utility functions
def process_image(file):
    try:
        return Image.open(file)
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None

def generate_report(image, prompt, include_confidence=False):
    try:
        with st.spinner("🔄 Analyzing..."):
            if include_confidence:
                prompt += "\n\nIMPORTANT: Include a confidence score (0-100%) for each finding."
            response = model.generate_content([prompt, image])
            return response.text
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None

def create_pdf(report_text, image, report_type, patient_info=None):
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        doc = SimpleDocTemplate(temp_file.name, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=22, 
                                     textColor=HexColor('#1e3a8a'), alignment=TA_CENTER, fontName='Helvetica-Bold')
        
        story.append(Paragraph("🏥 RADIOLOGY ANALYSIS REPORT", title_style))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"<b>Type:</b> {report_type} | <b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        
        if patient_info:
            story.append(Spacer(1, 0.2*inch))
            for k, v in patient_info.items():
                story.append(Paragraph(f"<b>{k}:</b> {v}", styles['Normal']))
        
        if image:
            img_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            image.save(img_temp.name, format='PNG')
            story.append(Spacer(1, 0.2*inch))
            story.append(RLImage(img_temp.name, width=4*inch, height=3*inch))
        
        story.append(Spacer(1, 0.3*inch))
        for line in report_text.split('\n'):
            if line.strip():
                story.append(Paragraph(line, styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
        disclaimer = ParagraphStyle('Disclaimer', parent=styles['Normal'], fontSize=9, 
                                   textColor=HexColor('#dc2626'), borderWidth=1, borderPadding=8)
        story.append(Paragraph("⚠️ AI-generated. Requires professional validation.", disclaimer))
        
        doc.build(story)
        with open(temp_file.name, 'rb') as f:
            return f.read()
    except Exception as e:
        st.error(f"❌ PDF Error: {str(e)}")
        return None

def save_to_history(report_type, image, report_text):
    st.session_state.history.append({
        'timestamp': datetime.now(),
        'type': report_type,
        'image': image,
        'report': report_text
    })
    if len(st.session_state.history) > 10:
        st.session_state.history.pop(0)

# Sidebar
st.sidebar.title("🏥 MedInsight AI")
st.sidebar.markdown("### RadiologyAI Pro")
st.sidebar.markdown("---")

page = st.sidebar.radio("Navigation", 
    ["🏠 Home", "🔍 Image Classification", "🩻 X-ray", "🔬 CT Scan", "🧠 MRI", "🔊 Ultrasound", "📊 History", "🔄 Compare"],
    label_visibility="collapsed")

# Feature configurations
FEATURES = {
    "🔍 Image Classification": {
        "title": "🔍 Medical Image Classification",
        "desc": "Automatic image type detection with confidence scoring",
        "prompt": """Classify this medical image: X-ray, CT, MRI, or Ultrasound. 
        Provide: 1) Classification 2) Confidence % 3) Key features 4) Image quality assessment""",
    },
    "🩻 X-ray": {
        "title": "🩻 X-ray Analysis",
        "desc": "Comprehensive X-ray diagnostic reporting",
        "prompt": """Expert radiologist analysis. Provide structured report:
        1. Image Quality & Positioning 2. Anatomical Findings 3. Abnormalities (if any) 
        4. Impression 5. Recommendations. Include confidence scores.""",
    },
    "🔬 CT Scan": {
        "title": "🔬 CT Scan Analysis",
        "desc": "Detailed CT scan clinical interpretation",
        "prompt": """CT imaging specialist analysis:
        1. Technical details 2. Anatomical region 3. Density analysis 4. Measurements 
        5. Clinical impression 6. Follow-up recommendations. Include confidence scores.""",
    },
    "🧠 MRI": {
        "title": "🧠 MRI Scan Analysis",
        "desc": "Advanced MRI interpretation with sequence analysis",
        "prompt": """MRI specialist report:
        1. Sequence type 2. Anatomical region 3. Signal characteristics 4. Findings 
        5. Differential diagnosis 6. Clinical correlation 7. Follow-up. Include confidence scores.""",
    },
    "🔊 Ultrasound": {
        "title": "🔊 Ultrasound Analysis",
        "desc": "Ultrasound imaging diagnostic summary",
        "prompt": """Sonography expert analysis:
        1. Examination type 2. Image quality 3. Echogenicity patterns 4. Measurements 
        5. Doppler findings 6. Impression 7. Recommendations. Include confidence scores.""",
    }
}

# HOME PAGE
if "Home" in page:
    st.markdown('<h1 class="main-header">RadiologyAI Pro</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center;color:#667eea;font-size:1.2rem;font-weight:600">AI-Powered Medical Imaging Analysis</p>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    stats = [("5", "Modalities"), ("AI", "Powered"), ("PDF", "Export"), ("24/7", "Available")]
    for col, (num, label) in zip([col1, col2, col3, col4], stats):
        with col:
            st.markdown(f'<div class="stats-box"><div style="font-size:2rem;font-weight:700">{num}</div><div>{label}</div></div>', unsafe_allow_html=True)
    
    st.markdown("### 🎯 Features")
    col1, col2 = st.columns(2)
    features_list = [
        ("🔍", "Image Classification", "Auto-detect image type with confidence"),
        ("🩻", "X-ray Analysis", "Structured diagnostic reports"),
        ("🔬", "CT Scan Reports", "Comprehensive density analysis"),
        ("🧠", "MRI Interpretation", "Signal & sequence analysis"),
        ("🔊", "Ultrasound", "Echogenicity & Doppler assessment"),
        ("📊", "History Tracking", "Access previous 10 analyses"),
    ]
    
    for i, (icon, title, desc) in enumerate(features_list):
        col = col1 if i % 2 == 0 else col2
        with col:
            st.markdown(f'<div class="card"><h3>{icon} {title}</h3><p style="color:#6b7280">{desc}</p></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="disclaimer"><h4 style="color:#dc2626">⚠️ Disclaimer</h4><p>AI-generated preliminary analysis. Requires professional validation.</p></div>', unsafe_allow_html=True)
    
    st.markdown("### 👥 Team")
    team = {"👨‍✈️ Captain": "Mohd Zaheeruddin", "🎖️ Vice Captain": "Suman Suhan", 
            "👤 Member": "Subiya Mahveen", "👤 Member ": "Syed Amaan Hussani", "👤 Member  ": "Humayun Attar"}
    for role, name in team.items():
        st.markdown(f"**{role}**: {name}")

# HISTORY PAGE
elif "History" in page:
    st.markdown('<h1 class="main-header">📊 Analysis History</h1>', unsafe_allow_html=True)
    
    if st.session_state.history:
        for i, record in enumerate(reversed(st.session_state.history)):
            with st.expander(f"{record['type']} - {record['timestamp'].strftime('%Y-%m-%d %H:%M')}"):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(record['image'], use_container_width=True)
                with col2:
                    st.markdown(record['report'])
    else:
        st.info("No analysis history yet. Start by analyzing some images!")

# COMPARE PAGE
elif "Compare" in page:
    st.markdown('<h1 class="main-header">🔄 Image Comparison</h1>', unsafe_allow_html=True)
    st.markdown("Upload two images for side-by-side comparison (e.g., before/after, different views)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📤 Image 1")
        file1 = st.file_uploader("Upload first image", type=["jpg", "jpeg", "png"], key="file1")
        if file1:
            img1 = process_image(file1)
            st.image(img1, use_container_width=True)
    
    with col2:
        st.markdown("### 📤 Image 2")
        file2 = st.file_uploader("Upload second image", type=["jpg", "jpeg", "png"], key="file2")
        if file2:
            img2 = process_image(file2)
            st.image(img2, use_container_width=True)
    
    if file1 and file2 and st.button("🔍 Compare Images", use_container_width=True, type="primary"):
        prompt = """Compare these two medical images. Provide:
        1. Similarities and differences
        2. Changes observed (if temporal comparison)
        3. Clinical significance of differences
        4. Recommendations"""
        
        result = generate_report(img1, prompt)
        if result:
            st.markdown('<div class="report-box">' + result + '</div>', unsafe_allow_html=True)

# ANALYSIS PAGES
elif any(key in page for key in FEATURES.keys()):
    feature_key = next(key for key in FEATURES.keys() if key in page)
    config = FEATURES[feature_key]
    
    st.markdown(f'<h1 class="main-header">{config["title"]}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p style="text-align:center;color:#6b7280">{config["desc"]}</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Patient info (collapsible)
    with st.expander("📋 Patient Information (Optional)"):
        col1, col2 = st.columns(2)
        with col1:
            patient_id = st.text_input("Patient ID")
            patient_age = st.text_input("Age")
        with col2:
            patient_gender = st.selectbox("Gender", ["", "Male", "Female", "Other"])
            physician = st.text_input("Physician")
    
    # Upload
    uploaded_file = st.file_uploader("📤 Upload Medical Image", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 🖼️ Image")
            image = process_image(uploaded_file)
            if image:
                st.image(image, use_container_width=True)
                st.markdown(f'<div class="card"><b>File:</b> {uploaded_file.name}<br><b>Size:</b> {uploaded_file.size/1024:.1f} KB<br><b>Dimensions:</b> {image.size[0]}×{image.size[1]}</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown("### 📊 Analysis")
            
            if st.button("🚀 Analyze", use_container_width=True, type="primary"):
                result = generate_report(image, config["prompt"], include_confidence=True)
                
                if result:
                    st.markdown(f'<div class="report-box">{result}</div>', unsafe_allow_html=True)
                    
                    # Save to session & history
                    st.session_state['report_text'] = result
                    st.session_state['report_image'] = image
                    st.session_state['report_type'] = config["title"]
                    save_to_history(config["title"], image, result)
                    
                    st.success("✅ Analysis complete!")
        
        # Download section
        if 'report_text' in st.session_state:
            st.markdown("---")
            st.markdown("### 📥 Export")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.download_button("📄 Text", st.session_state['report_text'],
                    f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "text/plain", use_container_width=True)
            
            with col2:
                patient_info = {k:v for k,v in {"Patient ID": patient_id, "Age": patient_age, 
                    "Gender": patient_gender, "Physician": physician}.items() if v}
                
                pdf_data = create_pdf(st.session_state['report_text'], st.session_state['report_image'],
                    st.session_state['report_type'], patient_info or None)
                
                if pdf_data:
                    st.download_button("📑 PDF", pdf_data,
                        f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", 
                        "application/pdf", use_container_width=True, type="primary")
            
            with col3:
                if st.button("🔄 Clear", use_container_width=True):
                    for key in ['report_text', 'report_image', 'report_type']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()

# Footer
st.markdown("---")
st.markdown('<div style="text-align:center;padding:1rem;background:white;border-radius:10px"><p style="color:#6b7280;font-size:0.9rem">⚠️ AI-generated analysis. Requires professional review.</p><p style="color:#9ca3af;font-size:0.8rem">Powered by Google Gemini AI | © 2024 MedInsight AI</p></div>', unsafe_allow_html=True)