import os
import requests
import time
import argparse

# --- Configuration ---
# This dictionary holds the default configuration values.
# They can be overridden by command-line arguments.
CONFIG = {
    "grobid_server_url": "http://localhost:8070",
    "input_dir": "input_pdfs",   # Default folder for your PDF files
    "output_dir": "output_xml", # Default folder for the XML output
    "timeout_seconds": 60,       # Timeout for the request to GROBID
    "force_reprocess": False   # Set to True to re-process files even if XML exists
}

def check_grobid_server(url: str) -> bool:
    """
    Checks if the GROBID server is running and accessible.

    Args:
        url (str): The base URL of the GROBID server.

    Returns:
        bool: True if the server is up, False otherwise.
    """
    ping_url = f"{url}/api/isalive"
    try:
        response = requests.get(ping_url, timeout=5)
        if response.status_code == 200:
            print(f"✅ GROBID server is active at {url}")
            return True
        else:
            print(f"⚠️ GROBID server responded with status {response.status_code}. Check if it's running correctly.")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not connect to GROBID server at {url}.")
        print(f"   Error: {e}")
        print("   Please ensure the GROBID Docker container is running and the URL is correct.")
        return False

def process_directory(config: dict):
    """
    Processes all PDF files in the input directory and converts them to TEI/XML
    using the GROBID service.

    Args:
        config (dict): A dictionary containing configuration parameters.
    """
    input_dir = config["input_dir"]
    output_dir = config["output_dir"]
    grobid_url = config["grobid_server_url"]
    api_url = f"{grobid_url}/api/processFulltextDocument"

    # --- 1. Initial Checks ---
    if not check_grobid_server(grobid_url):
        return # Stop execution if server is not available

    if not os.path.isdir(input_dir):
        print(f"❌ Error: Input directory '{input_dir}' not found. Please create it and add your PDFs.")
        return

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print(f"No PDF files found in '{input_dir}'.")
        return

    print(f"\nFound {len(pdf_files)} PDF(s) to process. Starting conversion...")
    print("-" * 40)

    # --- 2. Process Each PDF ---
    for i, filename in enumerate(pdf_files):
        pdf_path = os.path.join(input_dir, filename)
        xml_filename = os.path.splitext(filename)[0] + ".xml"
        xml_path = os.path.join(output_dir, xml_filename)

        print(f"({i+1}/{len(pdf_files)}) Processing: {filename}")

        # Skip if the file has already been processed, unless force_reprocess is True
        if not config["force_reprocess"] and os.path.exists(xml_path):
            print("  -> Skipping, XML output already exists.")
            continue

        try:
            with open(pdf_path, 'rb') as pdf_file:
                # The file is sent as multipart-form data
                files = {'input': (filename, pdf_file, 'application/pdf', {'Expires': '0'})}
                
                # Make the request to the GROBID API
                response = requests.post(api_url, files=files, timeout=config["timeout_seconds"])

            # --- 3. Handle Response ---
            if response.status_code == 200:
                # Write the successful response content to the XML file
                with open(xml_path, 'w', encoding='utf-8') as xml_f:
                    xml_f.write(response.text)
                print(f"  -> Success! Saved XML to '{xml_path}'")
            else:
                # Handle API errors (e.g., bad request, server error)
                print(f"  -> Error: GROBID returned status {response.status_code}")
                print(f"     Response: {response.text[:200]}...") # Print first 200 chars of error

        except requests.exceptions.Timeout:
            print(f"  -> Error: The request timed out after {config['timeout_seconds']} seconds.")
            print("     Consider increasing the timeout for very large or complex PDFs.")
        except requests.exceptions.RequestException as e:
            print(f"  -> Error: A network error occurred: {e}")

        # A small delay to be polite to the server, can be removed if not needed
        time.sleep(1)

    print("-" * 40)
    print("✅ Processing complete.")


if __name__ == "__main__":
    # --- Command-Line Argument Parsing ---
    # This allows users to easily change settings from the command line
    # without editing the script.
    parser = argparse.ArgumentParser(description="Process PDF files using a local GROBID instance.")
    parser.add_argument("--input", dest="input_dir", default=CONFIG["input_dir"],
                        help=f"Directory containing PDF files to process. (Default: {CONFIG['input_dir']})")
    parser.add_argument("--output", dest="output_dir", default=CONFIG["output_dir"],
                        help=f"Directory to store the resulting XML files. (Default: {CONFIG['output_dir']})")
    parser.add_argument("--server", dest="grobid_server_url", default=CONFIG["grobid_server_url"],
                        help=f"URL of the GROBID server. (Default: {CONFIG['grobid_server_url']})")
    parser.add_argument("--force", dest="force_reprocess", action="store_true",
                        help="Force reprocessing of all PDFs, even if output XML already exists.")

    args = parser.parse_args()

    # Update the config dictionary with any command-line arguments provided
    cli_config = vars(args)
    CONFIG.update(cli_config)

    # Run the main processing function
    process_directory(CONFIG)
