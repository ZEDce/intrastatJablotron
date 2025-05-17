import fitz  # PyMuPDF
import google.generativeai as genai
# We might not need a separate import for types if we construct the part as a dict
# import google.generativeai.types as genai_types 
import os
# PIL is no longer strictly needed in analyze_image_with_gemini if we send bytes,
# but it's good to keep for other potential image manipulations or if we revert.
# from PIL import Image 
import io
from dotenv import load_dotenv # Added for .env support
import csv # Added for CSV output
import re # For regular expression based text parsing
import json # Added for JSON parsing
import glob # Added to find all PDF files

# Load environment variables from .env file
load_dotenv()

# --- DEBUGGING ---
# print(f"DEBUG: GOOGLE_API_KEY from env after load_dotenv: {os.getenv('GOOGLE_API_KEY')}")
# --- END DEBUGGING ---

# Configure the Gemini API key (loaded from environment)
# This is now handled in the __main__ block after checking if the key exists.

# --- Model Configuration ---
# Using gemini-1.5-flash-latest as a stable and capable model for this task.
# The user's log showed "gemini-2.5-flash-preview-04-17", we can switch back if needed,
# but 1.5-flash is generally recommended for cost/performance balance.
MODEL_NAME = "gemini-1.5-flash-latest" 

def load_product_weights(file_path="data/product_weight.csv"):
    """
    Loads product weights from a CSV file.
    Assumes CSV format: Registrační číslo;JV Váha komplet SK
    where weights use comma as decimal separator.
    """
    weights = {}
    try:
        with open(file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            header = next(reader) # Skip header row
            if header != ["Registrační číslo", "JV Váha komplet SK"]:
                print(f"Warning: Unexpected header in {file_path}: {header}. Proceeding with caution.")

            for row_num, row in enumerate(reader, 2): # Start row_num from 2 for messages
                if len(row) == 2:
                    item_code = row[0].strip()
                    weight_str = row[1].strip().replace(',', '.')
                    if item_code and weight_str: # Ensure neither is empty
                        try:
                            weights[item_code] = float(weight_str)
                        except ValueError:
                            print(f"Warning: Could not convert weight '{row[1]}' to float for item_code '{item_code}' in {file_path} at row {row_num}. Skipping this item.")
                    else:
                        if not item_code : print(f"Warning: Missing item_code in {file_path} at row {row_num}. Skipping this row.")
                        if not weight_str and item_code : print(f"Warning: Missing weight for item_code '{item_code}' in {file_path} at row {row_num}. Skipping this item.")
                elif row: # If row is not empty but doesn't have 2 columns
                    print(f"Warning: Skipping malformed row (expected 2 columns, got {len(row)}) in {file_path} at row {row_num}: {row}")
        print(f"Successfully loaded {len(weights)} product weights from {file_path}")
        return weights
    except FileNotFoundError:
        print(f"Error: Product weight file not found at {file_path}. Net weight calculation will be skipped.")
        return {}
    except Exception as e:
        print(f"Error loading product weights from {file_path}: {e}")
        return {}

def pdf_to_images(pdf_path, output_folder="pdf_images"):
    """
    Converts each page of a PDF file into an image.

    Args:
        pdf_path (str): The path to the PDF file.
        output_folder (str): The folder to save the output images.

    Returns:
        list: A list of paths to the saved images.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    image_paths = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=200) # dpi can be adjusted
            image_path = os.path.join(output_folder, f"page_{page_num + 1}.png")
            pix.save(image_path)
            image_paths.append(image_path)
        doc.close()
        print(f"Successfully converted {len(image_paths)} pages from '{pdf_path}' to images in '{output_folder}'.")
        return image_paths
    except Exception as e:
        print(f"Error converting PDF '{pdf_path}' to images: {e}")
        return []

def analyze_image_with_gemini(image_path, prompt):
    """
    Analyzes an image using the Gemini API, expecting a JSON response.
    Sends image data inline.
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)

        print(f"Reading image {image_path} as bytes...")
        with open(image_path, 'rb') as f:
            image_bytes = f.read()

        mime_type = "image/png"  # Assuming PNG from pdf_to_images

        print(f"Attempting to analyze {image_path} (inline data) with {MODEL_NAME}...")
        
        image_part = {
            "mime_type": mime_type,
            "data": image_bytes
        }

        # Generate content with safety settings if needed, though default should be fine for invoices
        response = model.generate_content([image_part, prompt])
        response.resolve() 
        
        if response.candidates and response.candidates[0].content.parts:
            raw_text_response = response.text
            print(f"Raw Gemini response for {image_path}:\\n{raw_text_response}") # Log raw response
            
            # Attempt to clean and parse JSON
            # Gemini might wrap JSON in ```json ... ```
            cleaned_json_text = raw_text_response.strip()
            if cleaned_json_text.startswith("```json"):
                cleaned_json_text = cleaned_json_text[len("```json"):].strip()
            if cleaned_json_text.startswith("```"): # General ``` removal
                cleaned_json_text = cleaned_json_text[len("```"):].strip()
            if cleaned_json_text.endswith("```"):
                cleaned_json_text = cleaned_json_text[:-len("```")].strip()
            
            try:
                parsed_json = json.loads(cleaned_json_text)
                return parsed_json
            except json.JSONDecodeError as je:
                print(f"JSONDecodeError for {image_path}: {je}. Raw text was: '{cleaned_json_text}'")
                return {"error": "Failed to decode JSON response", "details": str(je), "raw_text": raw_text_response}
        else:
            print(f"Warning: Gemini API returned no content or unexpected structure for {image_path}.")
            if hasattr(response, 'prompt_feedback'):
                print(f"Prompt Feedback: {response.prompt_feedback}")
            return {"error": "Gemini API returned no content."}

    except Exception as e:
        print(f"Error analyzing image {image_path} with Gemini: {e}")
        # Add more detailed error logging if available
        error_detail = str(e)
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            error_detail += f" API Response Error: {e.response.text}"
        
        error_type_str = str(type(e))
        if "BlockedPromptException" in error_type_str:
            error_detail += " (Gemini API Blocked Prompt)"
        elif "StopCandidateException" in error_type_str:
            error_detail += " (Gemini API Stop Candidate)"
        elif 'google.api_core.exceptions' in error_type_str or 'GoogleAPIError' in error_type_str:
             error_detail += f" (Google API Error Details: {getattr(e, 'message', str(e))})"
        
        return {"error": f"Error during Gemini analysis: {error_detail}"}

def process_gemini_response_to_csv_rows(gemini_json_data, page_number, product_weights_map):
    """
    Processes the JSON data from Gemini into a list of dictionaries for CSV writing,
    including calculating total net weight.
    
    Args:
        gemini_json_data (dict): The parsed JSON object from Gemini.
        page_number (int): The page number this data came from.
        product_weights_map (dict): A dictionary mapping item_code to unit weight.
        
    Returns:
        list: A list of dictionaries, where each dictionary represents an item (a CSV row).
    """
    items_for_csv = []

    if not isinstance(gemini_json_data, dict) or "error" in gemini_json_data:
        error_message = gemini_json_data.get("error", "Unknown error processing Gemini response")
        print(f"Page {page_number}: Skipping due to error in Gemini response: {error_message}")
        items_for_csv.append({
            "Page Number": page_number,
            "Invoice Number": "PARSING FAILED",
            "Item Name": gemini_json_data.get("details", error_message),
            "Location": "",
            "Quantity": "",
            "Unit Price": "",
            "Total Price": "",
            "Total Net Weight": "" # Add placeholder for new column
        })
        return items_for_csv

    invoice_number = gemini_json_data.get("invoice_number", "N/A")
    extracted_items = gemini_json_data.get("items", [])

    if not isinstance(extracted_items, list):
        print(f"Page {page_number}: 'items' field is not a list or is missing. Found: {type(extracted_items)}")
        items_for_csv.append({
            "Page Number": page_number,
            "Invoice Number": invoice_number if invoice_number else "N/A",
            "Item Name": "Error: 'items' field from AI was not a list.",
            "Location": "", "Quantity": "", "Unit Price": "", "Total Price": "", "Total Net Weight": ""
        })
        return items_for_csv

    if not extracted_items:
        print(f"Page {page_number}: No items found in Gemini JSON response. Invoice: {invoice_number}")
        items_for_csv.append({
            "Page Number": page_number,
            "Invoice Number": invoice_number if invoice_number else "NOT FOUND",
            "Item Name": "No items found on this page.",
            "Location": "", "Quantity": "", "Unit Price": "", "Total Price": "", "Total Net Weight": ""
        })
        return items_for_csv

    for item in extracted_items:
        if not isinstance(item, dict):
            print(f"Page {page_number}: Skipping an item that is not a dictionary: {item}")
            continue
        
        item_code = item.get("item_code") or ""
        quantity_str = item.get("quantity") or ""
        
        total_net_weight_val = "" # Default to empty string
        if item_code and quantity_str:
            unit_weight = product_weights_map.get(item_code)
            if unit_weight is not None: # Check if item_code was found in weights map
                try:
                    # Gemini might return quantity as "2.00" or "2", ensure it's float compatible
                    quantity_float = float(str(quantity_str).replace(',', '.')) 
                    calculated_weight = quantity_float * unit_weight
                    total_net_weight_val = f"{calculated_weight:.3f}".replace('.', ',') # Format to 3 dec places, use comma
                except ValueError:
                    print(f"Warning: Could not convert quantity '{quantity_str}' to float for item '{item_code}'. Net weight calculation skipped.")
                    total_net_weight_val = "QTY_ERR"
            else:
                print(f"Warning: Unit weight not found for item_code '{item_code}'. Net weight will be empty.")
                total_net_weight_val = "NO_WEIGHT_DATA"
        
        items_for_csv.append({
            "Page Number": page_number,
            "Invoice Number": invoice_number,
            "Item Name": item_code,
            "Location": item.get("location") or "",
            "Quantity": quantity_str,
            "Unit Price": item.get("unit_price") or "",
            "Total Price": item.get("total_price") or "",
            "Total Net Weight": total_net_weight_val
        })
    
    return items_for_csv

def main():
    pdf_input_directory = "data"  # Directory containing PDFs
    data_output_directory = "data_output" # New directory for CSV outputs
    base_image_output_directory = "pdf_images" # Base directory for page images

    # Create the output directories if they don't exist
    os.makedirs(data_output_directory, exist_ok=True)
    os.makedirs(base_image_output_directory, exist_ok=True) # Ensure pdf_images also exists

    # Define the path for the single combined CSV file within the new output directory
    combined_csv_output_file = os.path.join(data_output_directory, "extracted_invoice_data.csv")
    
    # Load product weights
    product_weights = load_product_weights() # Default path "data/product_weight.csv"
    if not product_weights:
        print("Continuing without net weight calculations as product weights could not be loaded.")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in environment variables. Please set it in your .env file.")
        return
    try:
        genai.configure(api_key=api_key)
        print("Google API Key configured.")
    except Exception as e:
        print(f"Error configuring Google API Key: {e}")
        return

    pdf_file_paths = glob.glob(os.path.join(pdf_input_directory, "*.pdf"))

    if not pdf_file_paths:
        print(f"No PDF files found in directory: '{pdf_input_directory}'. Please place your PDFs there.")
        return
    
    print(f"Found {len(pdf_file_paths)} PDF files to process: {pdf_file_paths}")

    # Ask user for CSV output preference in Slovak, using numbers
    user_choice_internal = ""
    while True:
        print("Prajete si:")
        print("1. Jeden spoločný CSV súbor pre všetky faktúry")
        print("2. Samostatné CSV súbory pre každú faktúru")
        choice_input = input("Zadajte číslo (1 alebo 2): ").strip()
        if choice_input == '1':
            user_choice_internal = 'single'
            break
        elif choice_input == '2':
            user_choice_internal = 'separate'
            break
        else:
            print("Neplatná voľba. Zadajte prosím 1 alebo 2.")

    # This prompt is used for all PDFs and all pages
    extraction_prompt = (
        "Analyze the invoice page. Extract the overall invoice number. "
        "Then, identify all line items. For each line item, extract its item code (e.g., CC-01, JA-103K-7AH), "
        "location, quantity, unit price, and total price. The item's textual description is secondary but can be extracted if easily available. "
        "Return the information as a single JSON object. The JSON object should have two top-level keys: "
        "1. 'invoice_number': A string for the invoice number (use null if not found). "
        "2. 'items': A list of objects, where each object represents a line item and has the following keys: "
        "'item_code' (string, e.g., CC-01), 'location' (string), 'quantity' (string or number), "
        "'unit_price' (string or number), 'total_price' (string or number). You may also include 'description' if it's distinct and useful. "
        "If an item is missing one of these primary fields (item_code, location, quantity, unit_price, total_price), use an empty string or null. "
        "If no line items are found on the page, 'items' should be an empty list. "
        "Ensure the entire output is a valid JSON. Example item object (within the 'items' list): "
        "{\"item_code\": \"CC-01\", \"location\": \"SK\", \"quantity\": \"2.00\", \"unit_price\": \"86.73\", \"total_price\": \"173.46\"}"
    )
    
    master_data_from_all_pdfs = [] # To store processed data from all PDFs
    first_pdf_processed = True # Flag to control separator for single CSV

    for pdf_path in pdf_file_paths:
        pdf_filename = os.path.basename(pdf_path)
        pdf_name_without_ext = os.path.splitext(pdf_filename)[0]
        
        # Create a unique output folder for this PDF's images
        current_pdf_image_folder = os.path.join(base_image_output_directory, pdf_name_without_ext)
        if not os.path.exists(current_pdf_image_folder):
            os.makedirs(current_pdf_image_folder)
            print(f"Created image subfolder: {current_pdf_image_folder}")

        print(f"\\nProcessing PDF: {pdf_filename}...")
        image_paths_for_current_pdf = pdf_to_images(pdf_path, current_pdf_image_folder)
        
        if not image_paths_for_current_pdf:
            print(f"Skipping PDF {pdf_filename} due to image conversion errors.")
            # Add a placeholder to master_data if single CSV is chosen, so user knows it was skipped
            if user_choice_internal == 'single':
                master_data_from_all_pdfs.append({
                    "Invoice Number": "CONVERSION FAILED",
                    "Page Number": "",
                    "Row Number": "",
                    "Item Name": f"Failed to convert {pdf_filename} to images",
                    "Location": "", "Quantity": "", "Unit Price": "", "Total Price": "", "Total Net Weight": ""
                })
            continue

        all_items_from_current_pdf = []
        
        # Add separator row for single CSV output, if not the first PDF
        if user_choice_internal == 'single' and not first_pdf_processed:
            master_data_from_all_pdfs.append({
                "Invoice Number": "---",
                "Page Number": "---",
                "Row Number": "---",
                "Item Name": f"--- NEW INVOICE: {pdf_filename} ---",
                "Location": "---", "Quantity": "---", "Unit Price": "---", "Total Price": "---", "Total Net Weight": "---"
            })
        first_pdf_processed = False # Reset for subsequent PDFs if single output

        page_counter_for_pdf = 1
        for image_path in image_paths_for_current_pdf:
            print(f"Analyzing page {page_counter_for_pdf} of {pdf_filename} (image: {os.path.basename(image_path)})...")
            gemini_response = analyze_image_with_gemini(image_path, extraction_prompt)
            
            # Pass the relative page number for the current PDF and the product weights
            processed_page_items = process_gemini_response_to_csv_rows(gemini_response, page_counter_for_pdf, product_weights)
            all_items_from_current_pdf.extend(processed_page_items)
            page_counter_for_pdf += 1

        # Add row numbers for the items extracted from the current PDF
        # This ensures row numbers restart for each PDF
        items_from_current_pdf_with_row_numbers = []
        current_row_number = 1
        for item_data in all_items_from_current_pdf:
            # Only add row numbers to actual data rows, not error/placeholder rows from process_gemini_response
            if item_data.get("Invoice Number") not in ["PARSING FAILED", "CONVERSION FAILED"] and "No items found" not in item_data.get("Item Name", ""):
                 # and "Error:" not in item_data.get("Item Name", ""): # More specific check for actual items
                item_data_with_rn = {"Row Number": current_row_number, **item_data}
                current_row_number += 1
            else: # Keep placeholder/error rows as they are, without adding a new Row Number
                item_data_with_rn = {**item_data} # Ensure "Row Number" key exists if not already
                if "Row Number" not in item_data_with_rn:
                    item_data_with_rn["Row Number"] = ""


            items_from_current_pdf_with_row_numbers.append(item_data_with_rn)
        
        if user_choice_internal == 'single':
            master_data_from_all_pdfs.extend(items_from_current_pdf_with_row_numbers)
        elif user_choice_internal == 'separate':
            # Define headers for CSV
            headers = ["Invoice Number", "Page Number", "Row Number", "Item Name", "Location", "Quantity", "Unit Price", "Total Price", "Total Net Weight"]
            individual_csv_filename = os.path.join(data_output_directory, f"{pdf_name_without_ext}_extracted.csv")
            print(f"Writing extracted data for {pdf_filename} to {individual_csv_filename}...")
            
            if items_from_current_pdf_with_row_numbers:
                try:
                    with open(individual_csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=headers)
                        writer.writeheader()
                        writer.writerows(items_from_current_pdf_with_row_numbers)
                    print(f"Successfully wrote data for {pdf_filename} to {individual_csv_filename}")
                except IOError as e:
                    print(f"IOError writing CSV for {pdf_filename}: {e}")
            else:
                # Create an empty CSV with headers if no items were extracted or conversion failed earlier
                # but we still want a file representing this PDF
                try:
                    with open(individual_csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=headers)
                        writer.writeheader()
                        # Optionally write a single row indicating no data or conversion failure
                        writer.writerow({
                            "Invoice Number": "N/A or CONVERSION FAILED", 
                            "Page Number": "", 
                            "Row Number": "", 
                            "Item Name": f"No data extracted or conversion failed for {pdf_filename}",
                            "Location": "", "Quantity": "", "Unit Price": "", "Total Price": "", "Total Net Weight": ""
                        })
                    print(f"Wrote empty/placeholder CSV for {pdf_filename} to {individual_csv_filename} as no data was extracted or conversion failed.")
                except IOError as e:
                    print(f"IOError writing empty CSV for {pdf_filename}: {e}")


    # CSV Writing Logic - now conditional
    if user_choice_internal == 'single':
        if master_data_from_all_pdfs:
            # Define headers for CSV
            headers = ["Invoice Number", "Page Number", "Row Number", "Item Name", "Location", "Quantity", "Unit Price", "Total Price", "Total Net Weight"]
            print(f"\\nWriting all extracted data to {combined_csv_output_file}...")
            try:
                with open(combined_csv_output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(master_data_from_all_pdfs)
                print(f"Successfully wrote all data to {combined_csv_output_file}")
            except IOError as e:
                print(f"IOError writing combined CSV: {e}")
        else:
            print("\\nNo data was extracted from any PDF to write to the combined CSV file.")
            # Optionally, create an empty CSV with headers
            headers = ["Invoice Number", "Page Number", "Row Number", "Item Name", "Location", "Quantity", "Unit Price", "Total Price", "Total Net Weight"]
            try:
                with open(combined_csv_output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=headers)
                    writer.writeheader()
                    writer.writerow({
                        "Invoice Number": "NO DATA", "Page Number": "", "Row Number": "",
                        "Item Name": "No data extracted from any PDF files.", 
                        "Location": "", "Quantity": "", "Unit Price": "", "Total Price": "", "Total Net Weight": ""
                    })
                print(f"Created an empty placeholder CSV: {combined_csv_output_file}")
            except IOError as e:
                print(f"IOError creating empty placeholder CSV: {e}")

    print("\\n--- Script Finished ---")

if __name__ == "__main__":
    # Check for GOOGLE_API_KEY existence before running main
    # The configuration now happens inside main() to print messages appropriately.
    # This top-level check is a good pre-flight.
    if not os.getenv("GOOGLE_API_KEY"):
        print("CRITICAL: GOOGLE_API_KEY is not set in the environment or .env file.")
        print("Please ensure your .env file is correctly set up with GOOGLE_API_KEY=your_key_here")
    else:
        print("GOOGLE_API_KEY found in environment. Proceeding with main execution.")
    
    main()

    print("\\nPlease note: The accuracy of the extraction depends on the AI's ability to understand the document image and follow JSON instructions.")
    print("Review the CSV and the raw Gemini responses printed in the console for any discrepancies.")
    print("If parsing fails, check the 'Raw Gemini response' logs and JSONDecodeError messages.")
