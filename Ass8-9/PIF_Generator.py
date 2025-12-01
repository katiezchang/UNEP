#!/usr/bin/env python3
"""
PIF_Generator.py - Generates PIF sections based on country information from
Ass9 File Upload output files and Supabase database.
"""

import os
import sys
import json
import requests
from pathlib import Path

# Try to import required libraries
try:
    import openai
except ImportError:
    print("Error: openai library not found. Please install it with: pip install openai")
    sys.exit(1)

# Supabase configuration
SUPABASE_URL = "https://tulbxwdifnzquliytsog.supabase.co"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR1bGJ4d2RpZm56cXVsaXl0c29nIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI5OTg0MTAsImV4cCI6MjA3ODU3NDQxMH0.pRnak9Ii7Eqli-o8AEYX0DCyaWOi04OlEhLoynw88wU"

def validate_openai_api_key(api_key):
    """
    Validate an OpenAI API key by making a test API call.
    Returns True if valid, False otherwise.
    """
    if not api_key or not api_key.strip():
        return False
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key.strip())
        
        # Make a simple test call to validate the key
        response = client.models.list()
        return True
    except Exception as e:
        # If there's any error, the key is invalid
        return False

def get_openai_api_key():
    """
    Prompt user for OpenAI API key with validation.
    Returns the API key string if valid.
    """
    while True:
        user_input = input("Please provide an OpenAI API key: ").strip()
        
        if not user_input:
            print("API key cannot be empty. Please try again.")
            continue
        
        # Validate the API key
        print("Validating API key...")
        if validate_openai_api_key(user_input):
            print("✓ Valid API key.")
            return user_input
        else:
            print("✗ Invalid API key. Please try again.")

def search_output_files(country_name, output_folder):
    """
    Search for country-related files in the Ass9 File Upload Output folder.
    Returns list of file paths and their contents.
    """
    country_name_lower = country_name.lower()
    found_files = []
    
    if not os.path.exists(output_folder):
        print(f"Warning: Output folder {output_folder} does not exist.")
        return found_files
    
    # Search for files containing country name
    for file_path in Path(output_folder).glob('*'):
        if file_path.is_file():
            filename_lower = file_path.name.lower()
            if country_name_lower in filename_lower:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    found_files.append({
                        'filename': file_path.name,
                        'content': content
                    })
                    print(f"Found file: {file_path.name}")
                except Exception as e:
                    print(f"Error reading {file_path.name}: {e}")
    
    return found_files

def get_country_data_from_supabase(country_name):
    """
    Query Supabase database for country information.
    Returns list of matching country records with their sections data.
    """
    try:
        # Query Supabase REST API
        url = f"{SUPABASE_URL}/rest/v1/countries"
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        # Try to get all countries first, then filter
        # This handles cases where 'names' might be JSON or text
        try:
            # First try with ilike filter (if names is a text column)
            params = {
                "select": "*",
                "names": f"ilike.%{country_name}%"
            }
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            countries = response.json()
        except:
            # If that fails, get all records and filter manually
            response = requests.get(url, headers=headers, params={"select": "*"}, timeout=30)
            response.raise_for_status()
            countries = response.json()
        
        # Filter by country name (case-insensitive)
        matching_countries = []
        country_name_lower = country_name.lower()
        
        for country in countries:
            # Check if country name matches (case-insensitive)
            country_names = country.get('names', '')
            matched = False
            
            if isinstance(country_names, str):
                if country_name_lower in country_names.lower():
                    matched = True
            elif isinstance(country_names, list):
                for name in country_names:
                    if country_name_lower in str(name).lower():
                        matched = True
                        break
            
            # Also check if country name appears anywhere in the record
            if not matched:
                country_str = json.dumps(country).lower()
                if country_name_lower in country_str:
                    matched = True
            
            if matched and country not in matching_countries:
                matching_countries.append(country)
        
        return matching_countries
    
    except Exception as e:
        print(f"Error querying Supabase: {e}")
        import traceback
        traceback.print_exc()
        return []

def extract_sections_from_country_data(country_data_list):
    """
    Extract NDC Tracking Module, Support Needed and Received Module, and Other Baseline Initiatives
    from the country data sections.
    Returns a dictionary with the three sections.
    """
    sections_data = {
        'NDC Tracking Module': [],
        'Support Needed and Received Module': [],
        'Other Baseline Initiatives': []
    }
    
    for country_data in country_data_list:
        sections = country_data.get('sections', [])
        
        if isinstance(sections, str):
            # If sections is a JSON string, parse it
            try:
                sections = json.loads(sections)
            except:
                sections = []
        
        if not isinstance(sections, list):
            continue
        
        for section in sections:
            section_name = section.get('name', '')
            
            # Match section names (case-insensitive, flexible matching)
            if 'NDC Tracking' in section_name or 'NDC tracking' in section_name:
                sections_data['NDC Tracking Module'].append(section)
            elif 'Support Needed' in section_name or 'Support needed' in section_name or 'Support Needed and Received' in section_name:
                sections_data['Support Needed and Received Module'].append(section)
            elif 'Other Baseline' in section_name or 'Other baseline' in section_name or 'Baseline Initiatives' in section_name:
                sections_data['Other Baseline Initiatives'].append(section)
    
    return sections_data

def format_sections_text(sections_data):
    """
    Format the extracted sections data into readable text.
    """
    formatted_text = ""
    
    for section_name, section_list in sections_data.items():
        if section_list:
            formatted_text += f"\n=== {section_name} ===\n"
            for section in section_list:
                documents = section.get('documents', [])
                if documents:
                    for doc in documents:
                        doc_type = doc.get('doc_type', 'Unknown')
                        extracted_text = doc.get('extracted_text', '')
                        if extracted_text:
                            formatted_text += f"\n[From {doc_type}]:\n{extracted_text}\n"
                else:
                    # If no documents, try to get text directly from section
                    section_text = section.get('text', '') or section.get('content', '')
                    if section_text:
                        formatted_text += f"\n{section_text}\n"
            formatted_text += "\n"
    
    return formatted_text

def read_section_examples():
    """
    Read the Section Examples.txt file.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    examples_path = os.path.join(script_dir, 'Section Examples.txt')
    
    try:
        with open(examples_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Could not read Section Examples.txt: {e}")
        return ""

def generate_sections_with_ai(api_key, country_name, output_files_content, supabase_sections_text, section_examples):
    """
    Use OpenAI to generate the three sections based on all gathered information.
    """
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    # Combine all information
    all_info = f"""
COUNTRY: {country_name}

=== Information from Ass9 File Upload Output Files ===
{output_files_content}

=== Information from Supabase Database ===
{supabase_sections_text}

=== EXAMPLE SECTIONS (Reference Only - These are example answers showing desired format, style, and level of detail) ===
The following examples demonstrate how the sections should be written. Use these as a reference for:
- Paragraph structure and flow
- Level of detail and explanation
- Professional tone and factual presentation
- How to integrate quantitative and qualitative information
- Format for Other Baseline Initiatives (table structure)

{section_examples}
"""
    
    prompt = f"""You are an expert at drafting PIF (Project Identification Form) sections for climate transparency projects.

CRITICAL: Focus on FACTUALITY and ACCURACY. Reduce creativity. Base everything strictly on the provided information.

The "=== EXAMPLE SECTIONS (Reference Only) ===" section above contains EXAMPLE ANSWERS that demonstrate the desired format, style, paragraph structure, and level of detail. These examples show how to write in paragraph format with multiple paragraphs, how to integrate quantitative and qualitative information, and how to structure the Other Baseline Initiatives section as a table. Use these examples as your primary reference for how to structure and write your sections.

Based on the information provided above for {country_name}, write three comprehensive sections:

1. NDC TRACKING MODULE
   - Write in PARAGRAPH FORMAT (multiple paragraphs, similar to the examples)
   - MINIMUM length: 350 words, GOAL: approximately 400 words
   - Include as much detail and explanation as possible
   - Cover: NDC structure, MRV systems, institutional arrangements, progress tracking, challenges, gaps, needs, achievements
   - Use factual information only - no speculation or creative interpretation
   - Include specific numbers, dates, project names, and quantitative data when available
   - If additional details are needed to reach the minimum word count, you may reference PATPA and ICAT sources or UNEP trusted sources, but MUST cite them correctly (e.g., "According to [ICAT/PATPA document name]" or "As reported in [source]")

2. SUPPORT NEEDED AND RECEIVED MODULE
   - Write in PARAGRAPH FORMAT (multiple paragraphs, similar to the examples)
   - MINIMUM length: 350 words, GOAL: approximately 400 words
   - Include as much detail and explanation as possible
   - Cover: support tracking systems, financial flows, technical assistance, capacity building, funding sources, gaps, needs
   - Use factual information only - no speculation or creative interpretation
   - Include specific amounts, dates, donor names, and quantitative data when available
   - If additional details are needed to reach the minimum word count, you may reference PATPA and ICAT sources or UNEP trusted sources, but MUST cite them correctly (e.g., "According to [ICAT/PATPA document name]" or "As reported in [source]")

3. OTHER BASELINE INITIATIVES
   - Format as a TABLE or STRUCTURED LIST (not paragraph format)
   - Include columns: Program/Project name, Leading Ministry/Entities, Brief description, Duration (start and end year), Value (USD), Relationship with ETF and transparency system
   - List all relevant projects, programs, and initiatives from ICAT and PATPA sources
   - Be comprehensive and include all available details

STRICT REQUIREMENTS:
- Use the information provided above as the PRIMARY source. You may supplement with information from PATPA and ICAT sources or UNEP trusted sources if needed to reach the minimum word count, but ALL such references MUST be properly cited.
- Do not invent, infer, or speculate beyond what is explicitly stated in sources.
- If information is missing, clearly state what is missing or what gaps exist - do not fill gaps with assumptions.
- Follow the paragraph style and format of the example sections provided.
- Include ALL relevant quantitative data (numbers, amounts, dates, percentages) exactly as they appear in the sources.
- Include ALL relevant qualitative information (descriptions, assessments, challenges, achievements).
- When referencing projects/initiatives from ICAT and PATPA documents, cite them properly (e.g., "According to ICAT [document name]" or "As reported in PATPA [document name]").
- When using UNEP or other trusted sources, cite them appropriately.
- Write in a professional, factual tone - avoid creative language or embellishment.
- Prioritize accuracy and completeness. Ensure NDC Tracking and Support Needed modules meet the minimum 350 words (goal 400 words).

Write the three sections now, ensuring maximum detail and factual accuracy:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert at drafting PIF sections for climate transparency projects. Your primary focus is FACTUALITY and ACCURACY. You extract and synthesize information from provided sources without adding creative elements. You write comprehensive, detailed sections in paragraph format (except for Other Baseline Initiatives which uses table format). You strictly adhere to the information provided and do not invent or speculate."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10000,  # Increased for more detailed output
            temperature=0.1  # Lower temperature for more factual, less creative output
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

def main():
    # Step 1: Get country name
    country_name = input("What country do you want to draft the PIF for: ").strip()
    
    if not country_name:
        print("Error: Country name cannot be empty.")
        return
    
    print(f"\nProcessing PIF generation for {country_name}...")
    
    # Step 2: Search for files in Ass9 File Upload Output folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ass9_output_folder = os.path.join(script_dir, '..', 'Ass9 File Upload', 'Output')
    ass9_output_folder = os.path.abspath(ass9_output_folder)
    
    print(f"\nSearching for files in: {ass9_output_folder}")
    output_files = search_output_files(country_name, ass9_output_folder)
    
    # Combine output file contents
    output_files_content = ""
    if output_files:
        for file_data in output_files:
            output_files_content += f"\n--- From {file_data['filename']} ---\n{file_data['content']}\n"
    else:
        output_files_content = "[No matching files found in Ass9 File Upload Output folder]"
        print("No matching files found in Ass9 File Upload Output folder.")
    
    # Step 3: Query Supabase for country data
    print(f"\nQuerying Supabase database for {country_name}...")
    country_data_list = get_country_data_from_supabase(country_name)
    
    if country_data_list:
        print(f"Found {len(country_data_list)} matching country record(s) in Supabase.")
    else:
        print("No matching country records found in Supabase database.")
    
    # Step 4: Extract sections from Supabase data
    sections_data = extract_sections_from_country_data(country_data_list)
    supabase_sections_text = format_sections_text(sections_data)
    
    if not supabase_sections_text.strip():
        supabase_sections_text = "[No section data found in Supabase database]"
    
    # Step 5: Read section examples
    section_examples = read_section_examples()
    
    # Step 6: Get OpenAI API key
    print("\n" + "="*80)
    api_key = get_openai_api_key()
    
    # Step 7: Generate sections with AI
    print("\nGenerating PIF sections with AI...")
    generated_sections = generate_sections_with_ai(
        api_key,
        country_name,
        output_files_content,
        supabase_sections_text,
        section_examples
    )
    
    if not generated_sections:
        print("Error: Failed to generate sections.")
        return
    
    # Step 8: Save to output file
    output_folder = os.path.join(script_dir, 'Output')
    os.makedirs(output_folder, exist_ok=True)
    
    output_filename = f"{country_name} section draft.txt"
    output_path = os.path.join(output_folder, output_filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"PIF SECTIONS FOR {country_name.upper()}\n")
        f.write("=" * 80 + "\n\n")
        f.write(generated_sections)
    
    print(f"\n✓ Output file created: {output_path}")
    print(f"  Generated sections for: {country_name}")

if __name__ == "__main__":
    main()

