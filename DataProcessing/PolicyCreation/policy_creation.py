import os
import shutil
import json
from PyPDF2 import PdfReader, PdfWriter
import fitz
from openai import OpenAI

def chunk_pdf(input_pdf_path, output_dir, chunk_size=50):
    """
    Splits a PDF into smaller chunks of a specified number of pages.

    Args:
        input_pdf_path (str): The file path of the input PDF.
        output_dir (str): The directory where the chunked PDFs will be saved.
        chunk_size (int, optional): The number of pages per chunk. Defaults to 50.

    Returns:
        list: A list of file paths for the generated PDF chunks.
    """
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
        
        output_pdf_path = f"{output_dir}/chunk_{i // chunk_size + 1}.pdf"
        with open(output_pdf_path, "wb") as output_pdf:
            writer.write(output_pdf)
        chunks.append(output_pdf_path)
    return chunks


def pdf2text(pdf_path):
    """
    Extracts text from a PDF using PyMuPDF.

    Args:
        pdf_path (str): The file path of the PDF.

    Returns:
        str: The extracted text from the PDF.
    """
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text.strip()

def generate_rules(prompt, text, client, model='gpt-4o'):
    """
    Generates structured audit rules using the OpenAI API based on the provided text and prompt.

    Args:
        prompt (str): The prompt providing context or instructions.
        text (str): The text extracted from the PDF.
        client (OpenAI): The OpenAI client instance.
        model (str, optional): The model to be used for generating rules. Defaults to 'gpt-4o'.

    Returns:
        list: A list of audit rules generated by the OpenAI API.
    """
    rules = []
    try:
        client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system',
                 'content': prompt},
                {'role': 'user',
                 'content': text}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "audit_rule_schema",
                    "schema": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "rule_id": {
                                    "description": "A unique identifier for the rule, formatted as PCAOB-XXXX",
                                    "type": "string"
                                },
                                "standard": {
                                    "description": "The auditing standard reference number and title (e.g., AS 2401 - [Standard Title])",
                                    "type": "string"
                                },
                                "description": {
                                    "description": "A brief summary explaining the rule in simple terms",
                                    "type": "string"
                                },
                                "enforcement_guidelines": {
                                    "description": "A list of steps or guidelines for ensuring compliance with the rule",
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    }
                                }
                            },
                            "required": ["rule_id", "standard", "description", "enforcement_guidelines"],
                            "additionalProperties": False
                        }
                    }
                }
            }
        )
    except Exception as e:
        print(f'Error Generating Rules\nDetails: {str(e)}')
    return rules

def generate_policy(pdfs, prompt, output_path, client, model):
    """
    Generates a policy by processing multiple PDFs, extracting text, generating audit rules,
    and saving the results as a JSON file.

    Args:
        pdfs (list): A list of PDF file paths.
        prompt (str): The prompt used for generating rules.
        output_path (str): The directory where the output JSON file will be saved.
        client (OpenAI): The OpenAI client instance.
        model (str): The model to be used for generating rules.

    Returns:
        None
    """
    policy = []
    for pdf in pdfs:
        text = pdf2text(pdf)
        rules = generate_rules(prompt, text, client, model)
        policy.extend(rules)
    shutil.rmtree(os.path.dirname(pdfs[0]))
    with open(os.path.join(output_path, 'rules.json'), 'w', encoding='utf-8') as f:
        json.dump(policy, f, indent=4)

if __name__ == '__main__':
    standards_path = './docs/auditing_standards_audits_fybeginning_on_or_after_december_15_2024.pdf'
    prompt_path = './docs/prompt.txt'
    output_path = './docs'
    temp_path = './temp'
    model = 'gpt-4o'
    try:
        client = OpenAI()
        with open(prompt_path, 'r') as f:
            prompt = f.read()
        chunk_size = 50
        chunks = chunk_pdf(standards_path, temp_path, chunk_size)
        generate_policy(chunks, prompt, output_path, client, model)
        print('Policy Generation Successful!')
    except Exception as e:
        print(f'Policy Generation Failed\nDetails: {str(e)}')
