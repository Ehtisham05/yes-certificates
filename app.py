
import streamlit as st
import pandas as pd
import qrcode
import io
import os
from fpdf import FPDF
from PyPDF2 import PdfReader, PdfWriter
from supabase import create_client, Client

# Supabase credentials (add to .streamlit/secrets.toml for deployment)
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_qr_code(link):
    qr = qrcode.make(link)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def protect_pdf(input_pdf, password):
    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=password)
    protected_pdf = io.BytesIO()
    writer.write(protected_pdf)
    protected_pdf.seek(0)
    return protected_pdf

def generate_certificate(data_row):
    full_name = data_row["Full Name"]
    father_name = data_row["Father Name"]
    start_date = data_row["Start Date"]
    end_date = data_row["End Date"]
    cert_id = data_row["Certificate ID"]
    slug = data_row["QR Slug"]
    
    cert_text = f"{full_name}\nS/o {father_name}\nFrom {start_date} to {end_date}\nCert ID: {cert_id}"
    qr_link = f"https://{SUPABASE_URL.split('//')[1]}/storage/v1/object/public/certificates/{slug}.pdf"
    
    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.multi_cell(0, 10, cert_text)
    
    # Add QR
    qr = generate_qr_code(qr_link)
    with open("qr.png", "wb") as f:
        f.write(qr.read())
    pdf.image("qr.png", x=10, y=pdf.get_y()+10, w=40)

    # Save temporary PDF
    pdf_file = f"{slug}_unprotected.pdf"
    pdf.output(pdf_file)

    # Protect PDF
    with open(pdf_file, "rb") as f:
        protected = protect_pdf(f, "theyes123")

    # Upload to Supabase
    file_bytes = protected.read()
    supabase.storage.from_("certificates").upload(f"{slug}.pdf", file_bytes, {"content-type": "application/pdf", "x-upsert": "true"})

    # Public URL
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/certificates/{slug}.pdf"
    return full_name, cert_id, public_url

# Streamlit UI
st.title("Certificate Generator")
uploaded_file = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    results = []
    for _, row in df.iterrows():
        name, cert_id, url = generate_certificate(row)
        results.append((name, cert_id, url))
    st.success("Certificates generated and uploaded!")
    for name, cert_id, url in results:
        st.markdown(f"**{name}** — {cert_id} — [View PDF]({url})")
    st.info("Password for all PDFs: theyes123")
