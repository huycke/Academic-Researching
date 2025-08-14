import os
import argparse
from bs4 import BeautifulSoup
import re

# --- Configuration ---
CONFIG = {
    "input_dir": "output_xml",  # Directory containing the XML files from GROBID
    "output_dir": "output_md", # Directory to save the final Markdown files
    "force_reprocess": False   # Set to True to re-process files even if MD exists
}

def clean_text(text: str) -> str:
    """
    Cleans and normalizes text extracted from XML elements.
    - Replaces multiple spaces/newlines with a single space.
    - Strips leading/trailing whitespace.

    Args:
        text (str): The input string.

    Returns:
        str: The cleaned string.
    """
    # Replace multiple whitespace characters (including newlines, tabs) with a single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def table_to_markdown(table_element) -> str:
    """
    Converts a BeautifulSoup table element into a Markdown table string.

    Args:
        table_element: A BeautifulSoup object representing a <table> tag.

    Returns:
        str: A string containing the formatted Markdown table.
    """
    markdown_table = []
    header_processed = False
    
    # Process each row in the table
    for row in table_element.find_all('row'):
        # Extract cell text from the row
        cells = [clean_text(cell.get_text()) for cell in row.find_all('cell')]
        
        # Create the Markdown row string
        markdown_table.append(f"| {' | '.join(cells)} |")
        
        # Add the header separator line after the first row
        if not header_processed:
            separator = '|' + '|'.join(['---'] * len(cells)) + '|'
            markdown_table.append(separator)
            header_processed = True
            
    return "\n".join(markdown_table) + "\n"


def convert_xml_to_md(xml_path: str, md_path: str):
    """
    Parses a single GROBID TEI/XML file and converts it into a clean,
    LLM-ready Markdown file based on a defined extraction strategy.

    Args:
        xml_path (str): The full path to the input XML file.
        md_path (str): The full path to the output Markdown file.
    """
    try:
        with open(xml_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'lxml-xml')

        markdown_parts = []

        # --- 1. Discard Unwanted Elements First ---
        # Remove all in-text citation references (<ref type="bibr">)
        for ref in soup.find_all('ref', {'type': 'bibr'}):
            ref.decompose()
        # Remove all footnotes
        for note in soup.find_all('note', {'place': 'foot'}):
            note.decompose()

        # --- 2. Extract Core Content ---
        # Title
        title_element = soup.find('titleStmt').find('title')
        if title_element:
            title = clean_text(title_element.get_text())
            markdown_parts.append(f"# {title}\n")

        # Abstract
        abstract = soup.find('abstract')
        if abstract:
            markdown_parts.append("## Abstract\n")
            # The abstract text is often inside a div > p structure
            for p in abstract.find_all('p'):
                markdown_parts.append(clean_text(p.get_text()) + "\n")

        # Body Content (Sections, Paragraphs, Figures, Tables)
        body = soup.find('body')
        if body:
            # Process each major section (div) in the body
            for div in body.find_all('div', recursive=False):
                # Section Headings
                head = div.find('head')
                if head:
                    # Determine heading level based on 'n' attribute (e.g., "1.2" -> ###)
                    level = head.get('n', '1').count('.') + 2 
                    heading_marker = '#' * level
                    heading_text = clean_text(head.get_text())
                    markdown_parts.append(f"{heading_marker} {heading_text}\n")
                
                # Process all content elements within the section
                # We iterate through all children to preserve order
                for element in div.find_all(['p', 'formula', 'figure'], recursive=False):
                    if element.name == 'p':
                        markdown_parts.append(clean_text(element.get_text()) + "\n")
                    elif element.name == 'formula':
                        formula_text = clean_text(element.get_text())
                        markdown_parts.append(f"$$\n{formula_text}\n$$\n")
                    elif element.name == 'figure':
                        # Handle both tables and images within figures
                        if element.find('table'):
                            markdown_parts.append(table_to_markdown(element.find('table')))
                        
                        fig_desc = element.find('figDesc')
                        if fig_desc:
                            desc_text = clean_text(fig_desc.get_text())
                            markdown_parts.append(f"[Image: {desc_text}]\n")

        # --- 3. Write to Markdown File ---
        final_markdown = "\n".join(markdown_parts)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(final_markdown)
        
        print(f"  -> Success! Converted to '{os.path.basename(md_path)}'")

    except Exception as e:
        print(f"  -> Error processing {os.path.basename(xml_path)}: {e}")


def batch_process_folder(config: dict):
    """
    Orchestrates the conversion of all XML files in a source directory
    to Markdown files in a target directory.
    """
    input_dir = config["input_dir"]
    output_dir = config["output_dir"]

    if not os.path.isdir(input_dir):
        print(f"❌ Error: Input directory '{input_dir}' not found.")
        print("   This should be the folder containing your XML files (e.g., 'output_xml').")
        return

    os.makedirs(output_dir, exist_ok=True)
    
    xml_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".xml")]

    if not xml_files:
        print(f"No XML files found in '{input_dir}'.")
        return

    print(f"\nFound {len(xml_files)} XML file(s). Starting conversion to Markdown...")
    print("-" * 50)

    for filename in xml_files:
        xml_path = os.path.join(input_dir, filename)
        md_filename = os.path.splitext(filename)[0] + ".md"
        md_path = os.path.join(output_dir, md_filename)

        print(f"Processing: {filename}")

        if not config["force_reprocess"] and os.path.exists(md_path):
            print("  -> Skipping, Markdown file already exists.")
            continue
        
        convert_xml_to_md(xml_path, md_path)

    print("-" * 50)
    print("✅ Conversion complete.")
    print(f"Your Markdown files are located in the '{output_dir}' directory.")


if __name__ == "__main__":
    # --- Command-Line Argument Parsing ---
    parser = argparse.ArgumentParser(description="Convert GROBID TEI/XML files to clean Markdown for LLMs.")
    parser.add_argument("--input", dest="input_dir", default=CONFIG["input_dir"],
                        help=f"Directory containing XML files. (Default: {CONFIG['input_dir']})")
    parser.add_argument("--output", dest="output_dir", default=CONFIG["output_dir"],
                        help=f"Directory to save the Markdown files. (Default: {CONFIG['output_dir']})")
    parser.add_argument("--force", dest="force_reprocess", action="store_true",
                        help="Force reprocessing of all XMLs, even if output MD already exists.")
    
    args = parser.parse_args()

    # Update config with command-line arguments
    cli_config = vars(args)
    CONFIG.update(cli_config)

    # Run the main batch processing function
    batch_process_folder(CONFIG)
