import os
import shutil
import json

from PyPDF2 import PdfReader, PdfWriter
import fitz
import openai

def chunk_pdf(input_pdf_path, output_dir, chunk_size=50):
    reader = PdfReader(input_pdf_path)
    total_pages = len(reader.pages)
    
    chunks = []
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for i in range(0, total_pages, chunk_size):
        writer = PdfWriter()
        chunk_pages = reader.pages[i:i + chunk_size]
        
        for page in chunk_pages:
            writer.add_page(page)
        
        output_pdf_path = f"{output_dir}/chunk_{i//chunk_size + 1}.pdf"
        with open(output_pdf_path, "wb") as output_pdf:
            writer.write(output_pdf)
        chunks.append(output_pdf_path)
    return chunks

def download_standards():
    standards_path = './docs/auditing_standards_audits_fybeginning_on_or_after_december_15_2024.pdf'
    return standards_path

def pdf2text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text+= page.get_text("text") + "\n"
    return text.strip()

def generate_rules(prompt, text, model='gpt-4o'):
    rules = []
    return rules

def generate_policy(pdfs, prompt, output_path, model):
    policy = []
    for pdf in pdfs:
        text = pdf2text(pdf)
        rules = generate_rules(prompt, text, model)
        policy.extend(rules)
    shutil.rmtree(os.path.dirname(pdfs[0]))
    with open(os.path.join(output_path, 'rules.json'),'w', encoding='utf-8') as f:
        json.dump(policy, f, indent=4)


if __name__=='__main__':
    prompt_path = './docs/prompt.txt'
    output_path = './docs'
    temp_path = './temp'
    model = 'gpt-4o'
    try:
        standards_path = download_standards()
        with open(prompt_path,'r') as f:
            prompt = f.read()
        chunk_size = 50
        chunks = chunk_pdf(standards_path, temp_path, chunk_size)
        generate_policy(chunks, prompt, output_path, model)
    except Exception as e:
        print(f'Policy Generation Failed\nDetails: {str(e)}')