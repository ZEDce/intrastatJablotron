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
import shutil # Added for moving files

# Import functions from report.py
from report import list_csv_files, get_customs_code_descriptions, generate_single_report, INPUT_DIR as REPORT_INPUT_DIR, prompt_and_generate_report


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
MODEL_NAME = "gemini-2.0-flash-lite"
CUSTOMS_ASSIGNMENT_MODEL_NAME = "gemini-2.0-flash-lite"
# PACKAGING_WEIGHT_PER_UNIT_KG = 0.050 # Removed: User will provide target gross weight

INPUT_PDF_DIR = "invoices/" # Define input directory for PDFs
OUTPUT_CSV_DIR = "data_output/" # Define output directory for CSVs
PDF_IMAGE_DIR = "pdf_images/" # Define directory for images extracted from PDFs
PROCESSED_PDF_DIR = "processed_invoices/" # Define directory for processed PDFs

def load_product_weights(file_path="data/product_weight.csv"):
    """
    Loads product weights from a CSV file.
    Assumes CSV format: Registrační číslo;JV Váha komplet SK
    where weights use comma as decimal separator.
    """
    weights = {}
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as csvfile: # Changed to utf-8-sig
            reader = csv.reader(csvfile, delimiter=';')
            header = next(reader) # Skip header row
            if header != ["Registrační číslo", "JV Váha komplet SK"]:
                print(f"VAROVANIE: Neočakávaná hlavička v súbore {file_path}: {header}. Pokračuje sa s opatrnosťou.") # Translated

            for row_num, row in enumerate(reader, 2): # Start row_num from 2 for messages
                if len(row) == 2:
                    item_code = row[0].strip()
                    weight_str = row[1].strip().replace(',', '.')
                    if item_code and weight_str: # Ensure neither is empty
                        try:
                            weights[item_code] = float(weight_str)
                        except ValueError:
                            print(f"VAROVANIE: Nepodarilo sa konvertovať hmotnosť '{row[1]}' na číslo pre kód položky '{item_code}' v súbore {file_path} na riadku {row_num}. Táto položka sa preskakuje.") # Translated
                    else:
                        if not item_code : print(f"VAROVANIE: Chýbajúci kód položky v súbore {file_path} na riadku {row_num}. Tento riadok sa preskakuje.") # Translated
                        if not weight_str and item_code : print(f"VAROVANIE: Chýbajúca hmotnosť pre kód položky '{item_code}' v súbore {file_path} na riadku {row_num}. Táto položka sa preskakuje.") # Translated
                elif row: # If row is not empty but doesn't have 2 columns
                    print(f"VAROVANIE: Preskakuje sa nesprávne formátovaný riadok (očakávané 2 stĺpce, nájdené {len(row)}) v súbore {file_path} na riadku {row_num}: {row}") # Translated
        # print(f"Successfully loaded {len(weights)} product weights from {file_path}") # Removed
        return weights
    except FileNotFoundError:
        print(f"CHYBA: Súbor s hmotnosťami produktov nebol nájdený na ceste: {file_path}. Výpočet čistej hmotnosti bude preskočený.") # Translated
        return {}
    except Exception as e:
        print(f"CHYBA pri načítaní produktových hmotností zo súboru {file_path}: {e}") # Translated
        return {}

def load_customs_tariff_codes(file_path="data/col_sadz.csv"):
    """
    Loads customs tariff codes and their descriptions from a CSV file.
    Assumes CSV format: col_sadz;Popis
    """
    # print(f"DEBUG: Attempting to load customs codes from: {file_path}") # New debug print # Removed
    customs_codes = {}
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as csvfile: # Changed to utf-8-sig to handle BOM
            reader = csv.reader(csvfile, delimiter=';')
            header = next(reader) # Skip header row
            expected_header = ["col_sadz", "Popis"]
            # Normalize header for comparison (e.g., remove BOM if not handled by utf-8-sig)
            normalized_header = [h.lstrip('\ufeff') for h in header]

            if normalized_header != expected_header:
                print(f"VAROVANIE: Neočakávaná hlavička v súbore {file_path}: {header} (normalizovaná: {normalized_header}). Očakávaná {expected_header}. Pokračuje sa s opatrnosťou.") # Translated

            for row_num, row in enumerate(reader, 2): # Start row_num from 2 for messages
                if len(row) == 2:
                    code_raw = row[0].strip()
                    description = row[1].strip()
                    code = code_raw.replace(" ", "") # Normalize code by removing spaces
                    
                    if code and description: # Ensure neither is empty
                        if not re.fullmatch(r"[0-9]+", code):
                            print(f"VAROVANIE: Neplatné znaky v colnom kóde '{code_raw}' (normalizovaný na '{code}') v súbore {file_path} na riadku {row_num}. Očakávané sú iba číslice. Táto položka sa preskakuje.") # Translated
                            continue
                        customs_codes[code] = description
                    else:
                        if not code_raw: print(f"VAROVANIE: Chýbajúci col_sadz v súbore {file_path} na riadku {row_num}. Tento riadok sa preskakuje.") # Translated
                        # Check original code_raw for missing description message
                        if not description and code_raw: print(f"VAROVANIE: Chýbajúci Popis pre col_sadz '{code_raw}' v súbore {file_path} na riadku {row_num}. Táto položka sa preskakuje.") # Translated
                elif row: # If row is not empty but doesn't have 2 columns
                    print(f"VAROVANIE: Preskakuje sa nesprávne formátovaný riadok (očakávané 2 stĺpce, nájdené {len(row)}) v súbore {file_path} na riadku {row_num}: {row}") # Translated
        # print(f"Successfully loaded {len(customs_codes)} customs tariff codes from {file_path}") # Removed
        # print(f"DEBUG: Loaded customs codes map: {customs_codes}") # Uncommented for debugging # Removed
        return customs_codes
    except FileNotFoundError:
        print(f"CHYBA: Súbor s colnými kódmi nebol nájdený na ceste: {file_path}. Priradenie colných kódov bude ovplyvnené.") # Translated
        return {}
    except Exception as e:
        print(f"CHYBA pri načítaní colných kódov zo súboru {file_path}: {type(e).__name__} - {e}") # Translated (added more specific error type)
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
        return image_paths
    except Exception as e:
        print(f"CHYBA pri konverzii PDF '{pdf_path}' na obrázky: {e}") # Translated
        return []

def analyze_image_with_gemini(image_path, prompt):
    """
    Analyzes an image using the Gemini API, expecting a JSON response.
    Sends image data inline.
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)

        with open(image_path, 'rb') as f:
            image_bytes = f.read()

        mime_type = "image/png"  # Assuming PNG from pdf_to_images

        image_part = {
            "mime_type": mime_type,
            "data": image_bytes
        }

        response = model.generate_content([image_part, prompt])
        response.resolve() 
        
        if response.candidates and response.candidates[0].content.parts:
            raw_text_response = response.text
            
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
                print(f"CHYBA DEKÓDOVANIA JSON pre {image_path}: {je}. Surový text bol: '{cleaned_json_text}'") # Translated
                return {"error": "Nepodarilo sa dekódovať JSON odpoveď", "details": str(je), "raw_text": raw_text_response} # Translated error message
        else:
            print(f"VAROVANIE: Gemini API nevrátilo žiadny obsah alebo malo neočakávanú štruktúru pre {image_path}.") # Translated
            if hasattr(response, 'prompt_feedback'):
                print(f"Spätná väzba k promptu: {response.prompt_feedback}") # Translated
            return {"error": "Gemini API nevrátilo žiadny obsah."} # Translated error message

    except Exception as e:
        print(f"CHYBA pri analýze obrázka {image_path} pomocou Gemini: {e}") # Translated
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
            "description": "",
            "Location": "",
            "Quantity": "",
            "Unit Price": "",
            "Total Price": "",
            "Preliminary Net Weight": "", # Changed from Total Net Weight
            "Total Net Weight": "",      # Will be AI adjusted
            "Total Gross Weight": "",    # Will be AI adjusted
            "Colný kód": "",
            "Popis colného kódu": ""
        })
        return items_for_csv

    invoice_number = gemini_json_data.get("invoice_number", "N/A")
    items = gemini_json_data.get("items", [])
    
    if not items: # If items list is empty or not present
        print(f"Strana {page_number}: V Gemini odpovedi pre faktúru {invoice_number} neboli nájdené žiadne položky.") # Translated
        items_for_csv.append({
            "Page Number": page_number,
            "Invoice Number": invoice_number,
            "Item Name": "NO ITEMS FOUND IN RESPONSE",
            "description": "",
            "Location": "",
            "Quantity": "",
            "Unit Price": "",
            "Total Price": "",
            "Preliminary Net Weight": "",
            "Total Net Weight": "",
            "Total Gross Weight": "",
            "Colný kód": "",
            "Popis colného kódu": ""
        })
        return items_for_csv

    for item in items:
        raw_item_code = item.get("item_code")
        gemini_item_name_for_id = item.get("item_name", "N/A")

        if raw_item_code is None or str(raw_item_code).lower() == "null" or str(raw_item_code).strip() == "":
            csv_item_identifier = gemini_item_name_for_id
        else:
            csv_item_identifier = str(raw_item_code)

        gemini_item_name_desc = item.get("item_name", "")
        gemini_item_details = item.get("description", "")

        final_csv_description = gemini_item_name_desc
        if gemini_item_name_desc and gemini_item_details:
            final_csv_description = f"{gemini_item_name_desc} - {gemini_item_details}"
        elif gemini_item_details:
            final_csv_description = gemini_item_details

        item_code_for_weight_lookup = raw_item_code if raw_item_code is not None and str(raw_item_code).lower() != "null" else None

        quantity = item.get("quantity", 0)
        location_from_ai = item.get("location") # This will be 'NOT_ON_IMAGE', a country code, None, or N/A
        unit_price = item.get("unit_price", 0.0)
        total_price = item.get("total_price", 0.0)

        # --- Product identification and location input logic --- 
        is_product = True # Default assumption

        non_product_keywords = ["sleva", "zľava", "doprava", "preprava", "poplatek", "manipulační", "discount", "shipping", "fee", "handling"]
        
        raw_item_code_str = str(raw_item_code).strip() if raw_item_code is not None else ""
        raw_item_code_lower = raw_item_code_str.lower()
        
        item_name_lower_for_check = str(gemini_item_name_for_id).lower() # item_name from AI
        item_details_lower_for_check = str(gemini_item_details).lower() # description from AI

        has_specific_item_code = raw_item_code_str != "" and raw_item_code_lower not in ["null", "n/a"]

        # 1. Check if AI name/description strongly suggests non-product
        ai_suggests_non_product = False
        for keyword in non_product_keywords:
            if keyword in item_name_lower_for_check or keyword in item_details_lower_for_check:
                ai_suggests_non_product = True
                break
        
        # 2. Determine 'is_product'
        if has_specific_item_code:
            # If there's a specific item code, it's generally a product.
            # An exception is if the item_code ITSELF is a non-product keyword (e.g. code="DOPRAVA")
            item_code_is_itself_non_product = False
            for keyword in non_product_keywords:
                if keyword == raw_item_code_lower: # Exact match of item_code
                    item_code_is_itself_non_product = True
                    break
            
            if item_code_is_itself_non_product:
                is_product = False
            else:
                # Has a specific code that is NOT a non-product keyword itself.
                # Even if AI name contains keywords, the specific code implies product.
                is_product = True
        else: # No specific item_code
            if ai_suggests_non_product:
                is_product = False
            else:
                # No specific code, and AI doesn't suggest non-product.
                # Could be a product with missing code, or genuinely not a product.
                # Defaulting to True here means we might ask for country for items like "Poznámka",
                # but it's safer for actual products with missing codes.
                # The user can always press Enter if country is not applicable.
                is_product = True
        
        # Original refinement logic - can be removed or commented out as new logic is more comprehensive
        # if (raw_item_code is None or str(raw_item_code).lower() == "null" or str(raw_item_code).strip() == "" or str(raw_item_code).upper() == "N/A") and not is_product:
        #      pass 
        # elif (raw_item_code is None or str(raw_item_code).lower() == "null" or str(raw_item_code).strip() == "" or str(raw_item_code).upper() == "N/A") and is_product:
        #      pass 

        processed_location_for_csv = "" # Default to empty string for CSV output

        if is_product:
            is_valid_ai_country_code = False
            current_ai_location_val = item.get("location") # This is location_from_ai

            if current_ai_location_val is not None:
                stripped_ai_loc = str(current_ai_location_val).strip()
                # Check if AI provided a valid 2-letter code (case-insensitive)
                if re.fullmatch(r"[A-Za-z]{2}", stripped_ai_loc):
                    processed_location_for_csv = stripped_ai_loc.upper()
                    is_valid_ai_country_code = True
            
            # If AI did not provide a valid 2-letter code, prompt the user.
            # This covers:
            # - current_ai_location_val is None
            # - current_ai_location_val is an empty string "", " ", etc.
            # - current_ai_location_val is "N/A" or "NOT_ON_IMAGE" (these specific strings)
            # - current_ai_location_val is any other non-2-letter string (e.g., "China")
            if not is_valid_ai_country_code:
                item_identifier_for_prompt = csv_item_identifier
                if not item_identifier_for_prompt or item_identifier_for_prompt == "N/A": # Fallback identifier
                    item_identifier_for_prompt = gemini_item_name_desc if gemini_item_name_desc else f"Položka na strane {page_number}"

                prompt_reason_message = ""
                if current_ai_location_val is None:
                    prompt_reason_message = "nebola automaticky extrahovaná"
                elif str(current_ai_location_val).strip() == "":
                    prompt_reason_message = "bola AI vrátená ako prázdna"
                elif str(current_ai_location_val).strip().upper() == "N/A":
                    prompt_reason_message = "bola AI označená ako 'N/A'"
                elif str(current_ai_location_val).strip().upper() == "NOT_ON_IMAGE":
                    prompt_reason_message = "bola AI označená ako 'NOT_ON_IMAGE' (čo môže znamenať, že nie je na aktuálnom obrázku strany)"
                else:
                    prompt_reason_message = f"bola AI vrátená v neplatnom formáte: '{current_ai_location_val}'"

                print(f"VAROVANIE: Krajina pôvodu pre produkt '{item_identifier_for_prompt}' (strana {page_number}) {prompt_reason_message}.")
                print(f"           (Tip: Ak je krajina uvedená na inej strane PDF alebo ju viete, zadajte ju teraz.)")
                user_input_location = input(f"  Zadajte 2-písmenový kód krajiny (napr. CN, SK), alebo stlačte Enter, ak nie je známa/použiteľná: ").strip()
                
                if user_input_location: # If user provided some input
                    if re.fullmatch(r"[A-Za-z]{2}", user_input_location): # Validate user input (case-insensitive)
                        processed_location_for_csv = user_input_location.upper()
                    else:
                        print(f"  POZOR: Zadaný kód '{user_input_location}' nie je platný 2-písmenový kód krajiny. Krajina ostáva nevyplnená.")
                        processed_location_for_csv = "" # Invalid user input, set to blank
                else:
                    processed_location_for_csv = "" # User pressed Enter, confirming it's unknown or to be left blank
            # else: is_valid_ai_country_code was true, so processed_location_for_csv is already set from AI.

        else: # Not a product (is_product is False)
            current_ai_location_val = item.get("location")
            if current_ai_location_val is not None:
                stripped_ai_loc = str(current_ai_location_val).strip()
                # For non-products, we can still try to capture & standardize a 2-letter code if AI provides one.
                # Otherwise, it will remain blank. We don't prompt for non-products.
                if re.fullmatch(r"[A-Za-z]{2}", stripped_ai_loc):
                    processed_location_for_csv = stripped_ai_loc.upper()
                # If AI gives "N/A", "NOT_ON_IMAGE", None, empty, or other for a non-product, 'processed_location_for_csv' remains ""
        # --- End of product identification and location input logic ---

        # Calculate Preliminary Net Weight based on item_code_for_weight_lookup and quantity
        preliminary_net_weight = "" 
        if item_code_for_weight_lookup and product_weights_map:
            unit_weight = product_weights_map.get(item_code_for_weight_lookup)
            if unit_weight is not None:
                try:
                    numeric_quantity = float(quantity) if isinstance(quantity, (str, int, float)) else 0
                    preliminary_net_weight = numeric_quantity * unit_weight
                except ValueError:
                    if is_product: # Only warn for actual products
                        print(f"VAROVANIE: Nepodarilo sa konvertovať množstvo '{quantity}' na číslo pre kód položky '{csv_item_identifier}' (Názov: '{gemini_item_name_desc}'). Výpočet predbežnej hmotnosti preskočený.")
                    preliminary_net_weight = "CHYBA_QTY"
            else:
                if is_product: # Only warn for actual products
                    print(f"VAROVANIE: Hmotnosť nebola nájdená pre kód položky '{item_code_for_weight_lookup}' (Názov: '{gemini_item_name_desc}'). Výpočet predbežnej hmotnosti preskočený.")
                preliminary_net_weight = "NENÁJDENÉ" 
        elif not product_weights_map and is_product and item_code_for_weight_lookup: # Only if is_product and was expecting a code
            if is_product: # This check is redundant due to the elif condition, but kept for clarity on intent
                 print(f"VAROVANIE: Dáta o hmotnostiach produktov chýbajú. Predbežná hmotnosť pre '{csv_item_identifier}' nemôže byť vypočítaná.")
            preliminary_net_weight = "CHÝBAJÚ_DÁTA_HMOTNOSTI"
        elif not item_code_for_weight_lookup and is_product: # Product by name, but no code for weight lookup
            if is_product: # Again, for clarity
                print(f"VAROVANIE: Produkt '{csv_item_identifier}' nemá priradený kód pre vyhľadanie hmotnosti. Predbežná hmotnosť nebude vypočítaná.")
            preliminary_net_weight = "CHÝBA_KÓD_PRE_HMOTNOSŤ"


        items_for_csv.append({
            "Page Number": page_number,
            "Invoice Number": invoice_number,
            "Item Name": csv_item_identifier, # Changed: Now uses the item code
            "description": final_csv_description, # Changed: Now uses the combined descriptive text
            "Location": processed_location_for_csv, # Use the processed location (potentially user-input or from AI)
            "Quantity": quantity,
            "Unit Price": unit_price,
            "Total Price": total_price,
            "Preliminary Net Weight": preliminary_net_weight, 
            "Total Net Weight": "",
            "Total Gross Weight": "", 
            "Colný kód": "", 
            "Popis colného kódu": "" 
        })
    return items_for_csv

def prepare_item_details_for_ai(item_row_dict):
    """
    Prepares a dictionary of item details from an item_row for AI processing,
    specifically for assign_customs_code_with_ai.
    """
    item_identifier = item_row_dict.get("Item Name")
    item_description = item_row_dict.get("description")
    # item_row has "Location" (capital L), assign_customs_code_with_ai prompt expects lowercase "location"
    item_origin = item_row_dict.get("Location", "") 

    if not item_identifier: # If the main identifier (Item Name) is missing, it's hard to proceed meaningfully.
        print(f"    Item has no 'Item Name' (identifier). Insufficient for customs code AI. Item: {item_row_dict}")
        return "Item details are insufficient for AI processing."

    details_for_ai = {
        "item_code": item_identifier,    # Used in AI prompt as "Kód položky"
        "Item Name": item_identifier,    # Used by the hardcoded override logic in assign_customs_code_with_ai
        "description": item_description if item_description is not None else "", # Ensure string, AI handles empty as "Žiadny popis"
        "location": item_origin if item_origin is not None else ""          # Ensure string, AI handles empty as "N/A"
    }
    return details_for_ai

# Placeholder for the new AI model for customs code assignment
# We can make this configurable later (e.g., from .env or constants)
# CUSTOMS_ASSIGNMENT_MODEL_NAME is already defined at the top

def assign_customs_code_with_ai(item_details, all_customs_codes_map, genai_model_instance):
    """
    Assigns a customs code to an item using AI, with specific overrides.
    If a direct match for item_code is found in overrides, that is used.
    Otherwise, it uses AI and validates against all_customs_codes_map.
    Returns the assigned code (or "NEURCENE") and the reasoning or an error message.
    """
    # --- Start of new hardcoded override logic ---
    item_code_for_override = item_details.get("Item Name", "").strip() # Changed "item_code" to "Item Name"
    if item_code_for_override == "CZ-1263.1":
        customs_code = "85311030"
        # Fetch description from map if available, otherwise use a default
        customs_code_description = all_customs_codes_map.get(customs_code, "Poplachové zariadenia na ochranu budov") 
        # print(f"INFO: Hardcoded customs code {customs_code} ('{customs_code_description}') assigned to item {item_code_for_override} due to override rule.") # Removed user request
        return customs_code, "Hardkódované pravidlo pre CZ-1263.1" # Translated reason
    elif item_code_for_override == "JA-196J":
        customs_code = "85311030"
        customs_code_description = all_customs_codes_map.get(customs_code, "Poplachové zariadenia na ochranu budov")
        # print(f"INFO: Hardcoded customs code {customs_code} ('{customs_code_description}') assigned to item {item_code_for_override} due to override rule.") # Removed user request
        return customs_code, "Hardkódované pravidlo pre JA-196J" # Translated reason
    # --- End of new hardcoded override logic ---

    # Existing AI assignment logic starts here
    # (Assuming the rest of the function follows after this block)
    # if not item_details.get("description"):
    #     print(f"    Item {item_details.get('item_code', 'N/A')} has no description. Skipping AI customs code assignment, setting to NEURCENE.")
    #     return "NEURCENE", "No description provided"

    customs_codes_for_prompt = []
    if all_customs_codes_map:
        for code, desc in all_customs_codes_map.items():
            customs_codes_for_prompt.append(f"- Kód: {code}, Popis: {desc}")
    
    customs_codes_text = "\\n".join(customs_codes_for_prompt)
    if not customs_codes_text:
        customs_codes_text = "Zoznam colných kódov nebol poskytnutý."

    prompt = (
        "Si expert na colnú klasifikáciu tovaru pre spoločnosť zaoberajúcu sa bezpečnostnými a alarmovými systémami. "
        "Na základe nasledujúcich detailov položky:\\n"
        f"- Kód položky: {item_details.get('item_code', 'N/A')}\\n"
        f"- Popis položky: {item_details.get('description', 'Žiadny popis')}\\n"
        f"- Krajina pôvodu: {item_details.get('location', 'N/A')}\\n\\n"
        "A nasledujúceho zoznamu dostupných colných sadzobníkov a ich popisov:\\n"
        f"{customs_codes_text}\\n\\n"
        "Tvojou úlohou je vybrať JEDEN najvhodnejší 8-miestny kód colného sadzobníka (col_sadz) pre túto položku. "
        "Ber na vedomie, že veľa produktov spoločnosti (rôzne typy detektorov, senzorov, čidiel, sirén, ústrední alarmov, klávesníc) typicky patrí pod kód \'85311030\' (Poplachové zabezpečovacie systémy na ochranu budov). "
        "Ak popis položky silno naznačuje, že ide o takýto komponent alarmového systému, uprednostni kód \'85311030\'. "
        "Položky, ktoré sú príslušenstvom, doplnkom alebo sú priamo spojené s funkciou/identifikáciou alarmových systémov (napr. montážny materiál špecifický pre alarmy, informačné nálepky ALARM, batérie pre komponenty alarmu), by mali byť tiež klasifikované pod kód \'85311030\', pokiaľ pre ne neexistuje iný, jednoznačne vhodnejší a špecifickejší colný kód z poskytnutého zoznamu (napr. špecifický kód pre batérie ako \'8506xxxx\' alebo pre tlačené materiály ako \'4911xxxx\'). Ak však takýto špecifickejší kód nie je dostupný alebo vhodný, a položka jasne slúži systému pod kódom \'85311030\', použi \'85311030\' namiesto \'NEURCENE\'. "
        "Pre ostatné položky (napr. všeobecné káble, ktoré nie sú špecificky pre alarmy, bežný spojovací materiál) vyber najpresnejší kód podľa ich povahy. "
        "Zameraj sa na presnú zhodu s popisom položky a charakteristikami tovaru. "
        "Dôkladne zváž každý kód a jeho popis vo vzťahu k položke. Vysvetli stručne svoj postup v pár bodoch a na konci uveď iba samotný 8-miestny kód na novom riadku za textom 'VYSLEDNY_KOD: '.\\n"
        "Napríklad:\\n"
        "Zdôvodnenie: Položka je detektor pohybu, čo je súčasť alarmového systému.\\n"
        "VYSLEDNY_KOD: 85311030\\n\\n"
        "ALEBO\\n"
        "Zdôvodnenie: Položka je kábel.\\n"
        "VYSLEDNY_KOD: 85444920\\n\\n"
        "Ak nie je možné nájsť žiadny jednoznačne vhodný kód na základe poskytnutých informácií, alebo ak popis položky nie je dostatočný na jednoznačné určenie, vysvetli prečo a uveď VYSLEDNY_KOD: NEURCENE."
    )

    try:
        response = genai_model_instance.generate_content(prompt)
        raw_response_text = response.text.strip()
        # print(f"    DEBUG: Raw AI response for customs code assignment:\\n{raw_response_text}") # Log raw response # Already removed, kept for context

        # Try to extract the code after "VYSLEDNY_KOD: "
        # Regex made more flexible for whitespace and potential newlines around the code itself.
        code_match = re.search(r"VYSLEDNY_KOD:\s*([0-9]{8}|NEURCENE)", raw_response_text, re.IGNORECASE | re.DOTALL)
        
        assigned_code = "NEURCENE" # Default

        if code_match:
            extracted_value = code_match.group(1).strip()
            # print(f"    DEBUG: Regex matched. Extracted value: \'{extracted_value}\'") # Already removed
            if re.fullmatch(r"[0-9]{8}", extracted_value):
                if extracted_value in all_customs_codes_map:
                    assigned_code = extracted_value
                    # print(f"    INFO: AI assigned valid code: {assigned_code}") # Removed
                else:
                    print(f"    VAROVANIE: AI vrátil kód '{extracted_value}', ktorý má platný 8-miestny formát, ALE NIE JE v zozname známych colných kódov. Považuje sa za NEURCENE.") # Kept and already translated
                    # print(f"    Full AI reasoning: {raw_response_text}") # Removed
                    # assigned_code remains NEURCENE (default)
            elif extracted_value.upper() == "NEURCENE":
                assigned_code = "NEURCENE"
                # print(f"    INFO: AI explicitly assigned NEURCENE.") # Removed
            else:
                print(f"    VAROVANIE: Regex extrahoval '{extracted_value}', čo nie je ani 8-miestny kód ani NEURCENE. Považuje sa za NEURCENE.") # Kept and already translated
                # print(f"    Full AI reasoning: {raw_response_text}") # Removed
                # assigned_code remains NEURCENE (default)
        else:
            print(f"    VAROVANIE: Regex nenašiel 'VYSLEDNY_KOD: XXXXXXXX' alebo 'VYSLEDNY_KOD: NEURCENE' v AI odpovedi. Považuje sa za NEURCENE.") # Kept and already translated
            # print(f"    Full AI reasoning: {raw_response_text}") # Removed
            # assigned_code remains NEURCENE (default)
        
        return assigned_code, raw_response_text

    except Exception as e:
        print(f"    CHYBA počas AI priradenia colného kódu: {e}") # Translated
        return "NEURCENE", f"Chyba: {e}" # Translated error reason

def adjust_item_weights_to_target_totals_with_ai(items_data_list, target_total_net_kg, target_total_gross_kg, calculated_preliminary_total_net_kg, genai_model_instance):
    """
    Adjusts item net and gross weights to meet user-defined total targets using a generative AI model.

    Args:
        items_data_list (list): List of dictionaries, where each dictionary represents an item.
                                Expected keys: "Item Name" (item_code), "description", "Quantity",
                                "Preliminary Net Weight" (string, comma as decimal).
        target_total_net_kg (float): The user-defined target total net weight for the invoice.
        target_total_gross_kg (float): The user-defined target total gross weight for the invoice.
        calculated_preliminary_total_net_kg (float): The sum of "Preliminary Net Weight" for all items, as calculated by the script.
        genai_model_instance: An initialized generative model instance.

    Returns:
        list: A list of dictionaries, where each dictionary includes "Item Name",
              "Final Net Weight" (string, comma as decimal), and "Final Gross Weight" (string, comma as decimal).
              Returns an empty list or a list with error flags if AI processing fails.
    """
    if not items_data_list:
        print("    ADJUST_AI: No items provided for weight adjustment.")
        return []

    # Filter out items that don't have a valid preliminary net weight for the AI prompt
    # These might be header/footer rows misinterpreted as items, or items with actual weight data issues.
    valid_items_for_prompt = []
    non_product_keywords_for_weight_adjustment = ["sleva", "zľava", "doprava", "preprava", "poplatek", "manipulační", "discount", "shipping", "fee", "handling", "zľava", "poplatok"]
    # Also check for item codes that might have been set to non-product identifiers like "Zľava"

    for item in items_data_list:
        item_name_for_check = str(item.get("Item Name", "")).lower()
        item_description_for_check = str(item.get("description", "")).lower()
        prelim_weight_str = item.get("Preliminary Net Weight", "")

        # Determine if the item is likely a non-product type for weight adjustment purposes
        is_non_product_for_weights = False
        for keyword in non_product_keywords_for_weight_adjustment:
            if keyword in item_name_for_check or keyword in item_description_for_check:
                is_non_product_for_weights = True
                break
        # Also consider if the item_name itself is one of the special codes used in reporting for non-products
        if item_name_for_check in ["zľava", "poplatok"]: # These are codes set in generate_single_report, but good to check
            is_non_product_for_weights = True

        if prelim_weight_str and prelim_weight_str not in ["CHYBA_QTY", "NENÁJDENÉ", "CHÝBAJÚ_DÁTA_HMOTNOSTI", "CHÝBA_KÓD_PRE_HMOTNOSŤ"]:
            try:
                # Try converting to float to ensure it's a number before sending to AI
                float(str(prelim_weight_str).replace(',', '.'))
                valid_items_for_prompt.append({
                    "item_code": item.get("Item Name", "N/A"), # This is the Item Code / Identifier
                    "description": item.get("description", "N/A"),
                    "quantity": item.get("Quantity", "N/A"),
                    "preliminary_net_weight_kg_str": prelim_weight_str # Keep as string for AI
                })
            except ValueError:
                # Only warn if it's NOT a non-product type that we expect to have no valid weight
                if not is_non_product_for_weights:
                    print(f"VAROVANIE: Produktová položka '{item.get('Item Name')}' má neplatnú Predbežnú čistú hmotnosť '{prelim_weight_str}' a bude vylúčená z AI úpravy hmotností.")
        else:
            # If prelim_weight_str is one of the error/missing strings, or empty
            # Only print a warning if it's NOT a non-product type that we expect to have no valid weight.
            if not is_non_product_for_weights and prelim_weight_str: # only if there was some error string, not if it was just empty from a non-product
                 print(f"VAROVANIE: Produktová položka '{item.get('Item Name')}' nemá platnú Predbežnú čistú hmotnosť ('{prelim_weight_str}') a bude vylúčená z AI úpravy hmotností.")
            elif not is_non_product_for_weights and not prelim_weight_str:
                 # This case could be a product with genuinely missing weight info not caught by specific error strings
                 print(f"INFO: Produktová položka '{item.get('Item Name')}' nemá žiadnu predbežnú hmotnosť a bude vylúčená z AI úpravy hmotností.")

    if not valid_items_for_prompt:
        print("    ADJUST_AI: Neboli poskytnuté žiadne platné položky s predbežnými hmotnosťami pre AI úpravu.") # Translated
        # We need to return a structure that matches what the calling code expects for all original items.
        # So, we'll return the original items but flag that AI adjustment was skipped.
        result_list = []
        for item_orig in items_data_list:
            result_list.append({
                "Item Name": item_orig.get("Item Name", "N/A"),
                "Final Net Weight": item_orig.get("Preliminary Net Weight", "AI_SKIP_NO_VALID_ITEMS"), # Or use original if valid
                "Final Gross Weight": "AI_SKIP_NO_VALID_ITEMS"
            })
        return result_list

    items_json_for_prompt = json.dumps(valid_items_for_prompt, ensure_ascii=False, indent=2)

    prompt = (
        f"Si expert na logistiku a colnú deklaráciu. Tvojou úlohou je upraviť ČISTÚ a HRUBÚ hmotnosť pre každú položku faktúry tak, aby celkové súčty zodpovedali presne definovaným cieľovým hodnotám. "
        f"Musíš distribuovať rozdiely proporcionálne alebo logicky na základe predbežných hmotností položiek a ich množstva."
        f"\\n"
        f"Celková cieľová ČISTÁ hmotnosť faktúry (definovaná používateľom): {target_total_net_kg:.3f} kg\\n"
        f"Celková cieľová HRUBÁ hmotnosť faktúry (definovaná používateľom): {target_total_gross_kg:.3f} kg\\n"
        f"Predbežná celková ČISTÁ hmotnosť faktúry (vypočítaná skriptom zo súčtu položiek): {calculated_preliminary_total_net_kg:.3f} kg\\n"
        f"Rozdiel, ktorý treba alokovať pre čistú hmotnosť: {(target_total_net_kg - calculated_preliminary_total_net_kg):.3f} kg\\n"
        f"Celková hmotnosť obalov (rozdiel medzi cieľovou hrubou a cieľovou čistou hmotnosťou): {(target_total_gross_kg - target_total_net_kg):.3f} kg. Túto hmotnosť obalov musíš tiež logicky rozdeliť medzi položky."
        f"\\n"
        f"Nasleduje zoznam položiek faktúry s ich KÓDOM, POPISOM, MNOŽSTVOM a PREDBEŽNOU ČISTOU HMOTNOSŤOU (v kg, desatinná čiarka). "
        f"Množstvá a popisy položiek NEMEŇ!"
        f"Pre každú položku vráť jej KÓD POLOŽKY, finálnu ČISTÚ HMOTNOSŤ (Final Net Weight) a finálnu HRUBÚ HMOTNOSŤ (Final Gross Weight) v kg."
        f"\\n"
        f"Položky faktúry:\n{items_json_for_prompt}"
        f"\\n"
        f"PRAVIDLÁ pre úpravu:"
        f"1. Súčet všetkých 'Final Net Weight' sa MUSÍ PRESNE ROVNAŤ {target_total_net_kg:.3f} kg."
        f"2. Súčet všetkých 'Final Gross Weight' sa MUSÍ PRESNE ROVNAŤ {target_total_gross_kg:.3f} kg."
        f"3. Pre KAŽDÚ položku musí platiť: 'Final Gross Weight' >= 'Final Net Weight'."
        f"4. Hmotnosti nesmú byť záporné."
        f"5. Rozdelenie úpravy hmotnosti by malo byť čo najviac proporcionálne k 'preliminary_net_weight_kg_str' danej položky. Položky s vyššou predbežnou hmotnosťou by mali absorbovať väčšiu časť celkovej úpravy."
        f"6. Hmotnosť obalu pre každú položku (rozdiel medzi jej Final Gross Weight a Final Net Weight) by mala byť logická vzhľadom na typ a množstvo položky. Celkový súčet týchto individuálnych obalových hmotností musí zodpovedať celkovej hmotnosti obalov ({(target_total_gross_kg - target_total_net_kg):.3f} kg). Pri rozdeľovaní celkovej hmotnosti obalov medzi položky sa snažte o realistickú variabilitu. Nie všetky typy položiek budú mať rovnaký percentuálny podiel obalu na svojej čistej hmotnosti. Zohľadnite povahu položky (napr. krehkosť, veľkosť naznačená popisom alebo kódom) pri odhadovaní jej individuálneho obalu, pričom stále dodržujte presný celkový súčet hrubej hmotnosti. Jednotlivé priradené hmotnosti obalov (t.j. rozdiel 'Final Gross Weight' - 'Final Net Weight' pre každú položku) by NEMALI byť zaokrúhlené na jednoduché čísla (napr. 0.500, 1.000, 0.250). Mali by vyzerať ako presné, potenciálne 'menej pekné' čísla (napr. 0.537 kg, 0.281 kg, 1.079 kg), ktoré v súčte dajú presnú celkovú hmotnosť obalov."
        f"7. Výstup MUSÍ byť validný JSON zoznam (list of objects). Každý objekt musí obsahovať presne tieto tri kľúče: 'item_code' (string, presne ako v vstupe), 'Final Net Weight' (string, formát X.XXX kg, POUŽI DESATINNÚ BODKU), 'Final Gross Weight' (string, formát X.XXX kg, POUŽI DESATINNÚ BODKU)."
        f"Príklad požadovaného formátu jedného objektu v JSON zozname: {{ \"item_code\": \"KOD123\", \"Final Net Weight\": \"10.500\", \"Final Gross Weight\": \"11.200\" }}"
        f"\\n"
        f"DÔLEŽITÉ UPOZORNENIE: Over si svoje výpočty pred odoslaním odpovede! Súčet všetkých vrátených 'Final Net Weight' sa MUSÍ PRESNE ROVNAŤ {target_total_net_kg:.3f} kg. Súčet všetkých vrátených 'Final Gross Weight' sa MUSÍ PRESNE ROVNAŤ {target_total_gross_kg:.3f} kg. Akékoľvek odchýlky sú NEAKCEPTOVATEĽNÉ."
        f"Dôkladne skontroluj súčty pred vrátením výsledku! Poskytni IBA JSON zoznam ako odpoveď, bez akéhokoľvek ďalšieho textu alebo vysvetlenia."
    )

    # print(f"    ADJUST_AI: Prompt pre AI na úpravu hmotností:\\n{prompt}") # Removed

    try:
        response = genai_model_instance.generate_content(prompt)
        raw_response_text = response.text.strip()
        # print(f"    ADJUST_AI: Raw AI response for weight adjustment:\\n{raw_response_text}") # Removed

        # Clean the response if it's wrapped in ```json ... ```
        cleaned_json_text = raw_response_text
        if cleaned_json_text.startswith("```json"):
            cleaned_json_text = cleaned_json_text[len("```json"):].strip()
        if cleaned_json_text.startswith("```"): # General ``` removal
            cleaned_json_text = cleaned_json_text[len("```"):].strip()
        if cleaned_json_text.endswith("```"):
            cleaned_json_text = cleaned_json_text[:-len("```")].strip()
        
        try:
            adjusted_items_raw = json.loads(cleaned_json_text)
        except json.JSONDecodeError as je:
            print(f"    ADJUST_AI: CHYBA DEKÓDOVANIA JSON pri úprave hmotností: {je}. Surový text bol: '{cleaned_json_text}'") # Translated
            # Fallback: return original items with error flags
            result_list = []
            for item_orig in items_data_list:
                result_list.append({
                    "Item Name": item_orig.get("Item Name", "N/A"),
                    "Final Net Weight": item_orig.get("Preliminary Net Weight", "AI_JSON_DECODE_ERR"),
                    "Final Gross Weight": "AI_JSON_DECODE_ERR"
                })
            return result_list

        # Validate AI response structure and content
        if not isinstance(adjusted_items_raw, list):
            print("    ADJUST_AI: Odpoveď AI nie je zoznam.") # Translated
            # Fallback
            result_list = []
            for item_orig in items_data_list:
                result_list.append({
                    "Item Name": item_orig.get("Item Name", "N/A"),
                    "Final Net Weight": item_orig.get("Preliminary Net Weight", "AI_BAD_FORMAT_NON_LIST"),
                    "Final Gross Weight": "AI_BAD_FORMAT_NON_LIST"
                })
            return result_list

        # Convert AI response to the desired format and map it back to original items
        # This ensures we return a list that corresponds to the full `items_data_list`
        # including items that might have been filtered out from the AI prompt.
        final_adjusted_results_map = {adj_item.get("item_code"): adj_item for adj_item in adjusted_items_raw if isinstance(adj_item, dict)}
        
        output_list_for_all_items = []
        sum_final_net_kg_check = 0.0
        sum_final_gross_kg_check = 0.0

        # Temporary list to hold items with float weights from AI for correction
        items_for_programmatic_correction = [] 

        for original_item in items_data_list:
            item_code_original = original_item.get("Item Name", "N/A")
            ai_adjusted_data = final_adjusted_results_map.get(item_code_original)

            # Initialize with error/fallback values
            current_item_details_for_correction = {
                "Item Name": item_code_original,
                "original_preliminary_net_weight_str": original_item.get("Preliminary Net Weight", ""),
                "ai_final_net_kg": 0.0, # Parsed from AI, dot decimal
                "ai_final_gross_kg": 0.0, # Parsed from AI, dot decimal
                "is_error": True,
                "error_type": "ERROR_AI_NO_DATA"
            }

            if ai_adjusted_data:
                final_net_str = ai_adjusted_data.get("Final Net Weight")
                final_gross_str = ai_adjusted_data.get("Final Gross Weight")

                if final_net_str is not None and final_gross_str is not None:
                    try:
                        net_val = float(str(final_net_str)) 
                        gross_val = float(str(final_gross_str))

                        if gross_val < net_val:
                            print(f"    ADJUST_AI_VALIDATION: Pre položku '{item_code_original}', AI vrátilo Hrubú hmotnosť ({gross_val}) < Čistá hmotnosť ({net_val}). Označuje sa.") # Translated
                            current_item_details_for_correction["error_type"] = "ERR_GROSS_LT_NET"
                            # Still use the values for now, correction might fix or propagate error string
                            current_item_details_for_correction["ai_final_net_kg"] = net_val
                            current_item_details_for_correction["ai_final_gross_kg"] = gross_val
                        elif net_val < 0:
                            print(f"    ADJUST_AI_VALIDATION: Pre položku '{item_code_original}', AI vrátilo zápornú Čistú hmotnosť ({net_val}). Označuje sa.") # Translated
                            current_item_details_for_correction["error_type"] = "ERR_NEGATIVE"
                            current_item_details_for_correction["ai_final_net_kg"] = net_val
                            current_item_details_for_correction["ai_final_gross_kg"] = gross_val 
                        else:
                            current_item_details_for_correction["ai_final_net_kg"] = net_val
                            current_item_details_for_correction["ai_final_gross_kg"] = gross_val
                            current_item_details_for_correction["is_error"] = False # Mark as initially valid from AI
                            sum_final_net_kg_check += net_val # Sum for initial AI check
                            sum_final_gross_kg_check += gross_val # Sum for initial AI check

                    except ValueError as ve:
                        print(f"    ADJUST_AI: CHYBA HODNOTY pri konverzii AI hmotností pre položku '{item_code_original}': {ve}. Hodnoty: Čistá='{final_net_str}', Hrubá='{final_gross_str}'. Označuje sa.") # Translated
                        current_item_details_for_correction["error_type"] = "ERR_CONVERT"
                else:
                    print(f"    ADJUST_AI: Chýbajúci kľúč 'Final Net Weight' alebo 'Final Gross Weight' od AI pre položku '{item_code_original}'.") # Translated
                    current_item_details_for_correction["error_type"] = "ERR_AI_KEY_MISSING"
            else:
                # This item was not in AI's response (e.g., it was filtered out)
                print(f"    ADJUST_AI: Položka '{item_code_original}' nebola nájdená v upravenom zozname AI.") # Translated
                current_item_details_for_correction["error_type"] = "NOT_IN_AI_RESP"
            
            items_for_programmatic_correction.append(current_item_details_for_correction)

        # Initial check of AI sums (before programmatic correction)
        tolerance = 0.001 * len(valid_items_for_prompt) 
        if not (abs(sum_final_net_kg_check - target_total_net_kg) < tolerance):
            print(f"    ADJUST_AI_VALIDÁCIA (Pred-korekciou): Súčet AI čistých hmotností ({sum_final_net_kg_check:.3f} kg) SA NEROVNÁ cieľu ({target_total_net_kg:.3f} kg). Rozdiel: {(sum_final_net_kg_check - target_total_net_kg):.3f} kg") # Corrected and Translated
        if not (abs(sum_final_gross_kg_check - target_total_gross_kg) < tolerance):
            print(f"    ADJUST_AI_VALIDÁCIA (Pred-korekciou): Súčet AI hrubých hmotností ({sum_final_gross_kg_check:.3f} kg) SA NEROVNÁ cieľu ({target_total_gross_kg:.3f} kg). Rozdiel: {(sum_final_gross_kg_check - target_total_gross_kg):.3f} kg") # Corrected and Translated

        # --- Programmatic Sum Correction --- 
        # 1. Correct Net Weights
        current_sum_ai_net_kg = sum(item['ai_final_net_kg'] for item in items_for_programmatic_correction if not item['is_error'] and item["error_type"] != "NOT_IN_AI_RESP")
        net_difference = target_total_net_kg - current_sum_ai_net_kg
        
        # Distribute net_difference proportionally among non-error items
        # Use preliminary net weights for proportion if AI weights are zero or problematic for proportion
        # For simplicity, if ai_final_net_kg is 0, it won't get any adjustment from this proportional step.
        # This could be refined if items legitimately have 0 net weight but need to absorb some diff.
        total_proportional_net_base = sum(item['ai_final_net_kg'] for item in items_for_programmatic_correction if not item['is_error'] and item['ai_final_net_kg'] > 0 and item["error_type"] != "NOT_IN_AI_RESP")

        if abs(net_difference) > 1e-9: # If there is a notable difference
            # print(f"    PROGRAMMATIC_CORRECTION: Net difference to distribute: {net_difference:.6f} kg") # Removed
            if total_proportional_net_base > 1e-9:
                for item in items_for_programmatic_correction:
                    if not item['is_error'] and item['ai_final_net_kg'] > 0 and item["error_type"] != "NOT_IN_AI_RESP":
                        proportion = item['ai_final_net_kg'] / total_proportional_net_base
                        item['corrected_final_net_kg'] = item['ai_final_net_kg'] + (net_difference * proportion)
                    elif not item['is_error'] and item["error_type"] != "NOT_IN_AI_RESP": # Item had 0 net weight from AI, keep it 0
                        item['corrected_final_net_kg'] = 0.0
                    else: # Error items or items not in AI response
                        item['corrected_final_net_kg'] = item['ai_final_net_kg'] # Keep AI's (potentially 0) or error state
            else: # All items had 0 net weight or no valid items; distribute equally if possible (rare case)
                # This case needs careful handling; for now, log and don't adjust if no base for proportion
                print("    PROGRAMMATIC_CORRECTION: Warning - Cannot distribute net difference proportionally, no positive net weights from AI or no valid items.")
                for item in items_for_programmatic_correction:
                    item['corrected_final_net_kg'] = item['ai_final_net_kg'] # Fallback
        else: # No significant net difference
            for item in items_for_programmatic_correction:
                item['corrected_final_net_kg'] = item['ai_final_net_kg']

        # 2. Correct Gross Weights (based on corrected net weights)
        sum_of_corrected_final_net_weights = sum(item['corrected_final_net_kg'] for item in items_for_programmatic_correction if not item['is_error'] and item["error_type"] != "NOT_IN_AI_RESP")
        total_packaging_allowance = target_total_gross_kg - sum_of_corrected_final_net_weights
        current_sum_ai_packaging_kg = sum(max(0, item['ai_final_gross_kg'] - item['ai_final_net_kg']) for item in items_for_programmatic_correction if not item['is_error'] and item["error_type"] != "NOT_IN_AI_RESP")

        packaging_difference = total_packaging_allowance - current_sum_ai_packaging_kg

        # Base for distributing packaging difference: AI's originally intended packaging weight per item (Gross-Net)
        # Use a small epsilon for items where AI had Gross == Net, so they can still receive some packaging if needed.
        epsilon_packaging = 1e-6 
        total_proportional_packaging_base = sum(max(epsilon_packaging, item['ai_final_gross_kg'] - item['ai_final_net_kg']) for item in items_for_programmatic_correction if not item['is_error'] and item["error_type"] != "NOT_IN_AI_RESP")
        
        if abs(packaging_difference) > 1e-9:
            # print(f"    PROGRAMMATIC_CORRECTION: Packaging difference to distribute: {packaging_difference:.6f} kg") # Removed
            if total_proportional_packaging_base > 1e-9:
                for item in items_for_programmatic_correction:
                    if not item['is_error'] and item["error_type"] != "NOT_IN_AI_RESP":
                        ai_item_packaging = max(epsilon_packaging, item['ai_final_gross_kg'] - item['ai_final_net_kg'])
                        proportion = ai_item_packaging / total_proportional_packaging_base
                        item_packaging_adjustment = packaging_difference * proportion
                        item['corrected_final_gross_kg'] = item['corrected_final_net_kg'] + ai_item_packaging + item_packaging_adjustment
                        # Ensure gross >= net after correction
                        if item['corrected_final_gross_kg'] < item['corrected_final_net_kg']:
                            item['corrected_final_gross_kg'] = item['corrected_final_net_kg'] # Set to net if undershot
                    else: # Error items or items not in AI response
                        item['corrected_final_gross_kg'] = item['ai_final_gross_kg'] # Keep AI's or error state
            else:
                print("    PROGRAMOVÁ KOREKCIA: VAROVANIE - Nie je možné proporcionálne rozdeliť rozdiel v balení, žiadne kladné hmotnosti balenia od AI alebo žiadne platné položky.") # Translated
                for item in items_for_programmatic_correction:
                    # Fallback: make gross = corrected net + some equal share if possible, or just corrected net
                    # This path means AI gave all items Gross == Net, and we need to add packaging_difference
                    # For now, just set gross = corrected net, if packaging_difference is positive, it won't be distributed here
                    item['corrected_final_gross_kg'] = item['corrected_final_net_kg'] 
                    if not item['is_error'] and item["error_type"] != "NOT_IN_AI_RESP" and packaging_difference > 0 and len([i for i in items_for_programmatic_correction if not i['is_error']]) > 0:
                        item['corrected_final_gross_kg'] += packaging_difference / len([i for i in items_for_programmatic_correction if not i['is_error']])
        else: # No significant packaging difference
             for item in items_for_programmatic_correction:
                if not item['is_error'] and item["error_type"] != "NOT_IN_AI_RESP":
                    # Use AI's gross if it was valid, otherwise ensure it respects corrected net
                    # This re-bases gross on the corrected_final_net_kg + AI's intended packaging
                    item_ai_packaging = item['ai_final_gross_kg'] - item['ai_final_net_kg']
                    item['corrected_final_gross_kg'] = item['corrected_final_net_kg'] + item_ai_packaging
                    if item['corrected_final_gross_kg'] < item['corrected_final_net_kg']:
                         item['corrected_final_gross_kg'] = item['corrected_final_net_kg']
                else:
                    item['corrected_final_gross_kg'] = item['ai_final_gross_kg']

        # --- End Programmatic Sum Correction ---

        # Prepare final list for output, converting to string with comma decimal
        output_list_for_all_items = []
        final_sum_net_check = 0.0
        final_sum_gross_check = 0.0

        for item_detail in items_for_programmatic_correction:
            final_net_val_to_str = "ERROR"
            final_gross_val_to_str = "ERROR"

            if item_detail['is_error']:
                final_net_val_to_str = item_detail.get('original_preliminary_net_weight_str', item_detail['error_type'])
                final_gross_val_to_str = item_detail['error_type']
                if item_detail["error_type"] == "ERR_GROSS_LT_NET": # Special case from AI, try to use numbers
                    final_net_val_to_str = f"{item_detail['ai_final_net_kg']:.3f}".replace('.', ',')
                    final_gross_val_to_str = f"{item_detail['ai_final_gross_kg']:.3f}".replace('.', ',') + "_ERR_GROSS_LT_NET"
                elif item_detail["error_type"] == "ERR_NEGATIVE":
                    final_net_val_to_str = f"{item_detail['ai_final_net_kg']:.3f}".replace('.', ',') + "_ERR_NEGATIVE"
                    final_gross_val_to_str = f"{item_detail['ai_final_gross_kg']:.3f}".replace('.', ',')

            else:
                # Ensure gross is not less than net after all corrections for valid items
                if item_detail['corrected_final_gross_kg'] < item_detail['corrected_final_net_kg']:
                    item_detail['corrected_final_gross_kg'] = item_detail['corrected_final_net_kg']
                    # print(f"    POST_CORRECTION_ADJUST: Item '{item_detail['Item Name']}' had gross < net, setting gross = net.") # Removed
                
                # Ensure weights are not negative after corrections
                if item_detail['corrected_final_net_kg'] < 0:
                    item_detail['corrected_final_net_kg'] = 0.0 # Force non-negative
                    print(f"    POKOREKČNÁ ÚPRAVA: Položka '{item_detail['Item Name']}' mala zápornú čistú hmotnosť, nastavená na 0.") # Translated
                if item_detail['corrected_final_gross_kg'] < 0:
                    item_detail['corrected_final_gross_kg'] = 0.0 # Force non-negative
                    print(f"    POKOREKČNÁ ÚPRAVA: Položka '{item_detail['Item Name']}' mala zápornú hrubú hmotnosť, nastavená na 0.") # Translated


                final_net_val_to_str = f"{item_detail['corrected_final_net_kg']:.3f}".replace('.', ',')
                final_gross_val_to_str = f"{item_detail['corrected_final_gross_kg']:.3f}".replace('.', ',')
                final_sum_net_check += item_detail['corrected_final_net_kg']
                final_sum_gross_check += item_detail['corrected_final_gross_kg']
            
            output_list_for_all_items.append({
                "Item Name": item_detail["Item Name"],
                "Total Net Weight": final_net_val_to_str,
                "Total Gross Weight": final_gross_val_to_str
            })
        
        # Final check of sums after programmatic correction
        # Use a slightly more forgiving tolerance for the final check due to potential cascading float issues
        final_tolerance = 1e-5 # Very small tolerance for final check
        if not (abs(final_sum_net_check - target_total_net_kg) < final_tolerance):
            print(f"    PROGRAMOVÁ KOREKCIA VALIDÁCIA: FINÁLNY Súčet čistých hmotností ({final_sum_net_check:.6f} kg) SA NEROVNÁ cieľu ({target_total_net_kg:.3f} kg) v rámci tolerancie {final_tolerance}. Rozdiel: {(final_sum_net_check - target_total_net_kg):.6f} kg") # Corrected and Translated
        else:
            # print(f"    PROGRAMMATIC_CORRECTION_VALIDATION: FINAL Sum of Net Weights ({final_sum_net_check:.6f} kg) matches target ({target_total_net_kg:.3f} kg) perfectly or within tolerance.") # Removed
            pass

        if not (abs(final_sum_gross_check - target_total_gross_kg) < final_tolerance):
            print(f"    PROGRAMOVÁ KOREKCIA VALIDÁCIA: FINÁLNY Súčet hrubých hmotností ({final_sum_gross_check:.6f} kg) SA NEROVNÁ cieľu ({target_total_gross_kg:.3f} kg) v rámci tolerancie {final_tolerance}. Rozdiel: {(final_sum_gross_check - target_total_gross_kg):.6f} kg") # Corrected and Translated
        else:
            # print(f"    PROGRAMMATIC_CORRECTION_VALIDATION: FINAL Sum of Gross Weights ({final_sum_gross_check:.6f} kg) matches target ({target_total_gross_kg:.3f} kg) perfectly or within tolerance.") # Removed
            pass

        return output_list_for_all_items

    except Exception as e:
        print(f"    ADJUST_AI: CHYBA počas volania AI na úpravu hmotností: {e}") # Translated
        # Fallback: return original items with error flags
        result_list = []
        for item_orig in items_data_list:
            result_list.append({
                "Item Name": item_orig.get("Item Name", "N/A"),
                "Final Net Weight": item_orig.get("Preliminary Net Weight", "AI_EXCEPTION"),
                "Final Gross Weight": "AI_EXCEPTION"
            })
        return result_list

def run_pdf_processing_flow():
    """
    Main flow to process PDF invoices.
    Converts PDFs to images, analyzes with Gemini, assigns customs codes,
    adjusts weights, and writes data to CSV.
    """
    # print(f"Starting PDF processing flow...") # Removed

    # Ensure output directories exist
    os.makedirs(OUTPUT_CSV_DIR, exist_ok=True)
    os.makedirs(PDF_IMAGE_DIR, exist_ok=True)
    os.makedirs(PROCESSED_PDF_DIR, exist_ok=True) # Create processed_invoices directory

    product_weights = load_product_weights() # Load weights once
    all_customs_codes_map = load_customs_tariff_codes() # Load all codes once

    # Initialize AI Models (ensure API key is configured before this point if needed by genai.GenerativeModel)
    # This is typically handled in main() before calling this function.
    # Consider passing model instances if they are initialized outside.
    # For now, assuming genai.configure has been called.
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY not found. AI features will be unavailable.")
        # return # Exit if AI is critical

    # It's better to initialize models once if possible, or pass them as arguments
    # For simplicity here, initializing as needed, but be mindful of quotas/performance
    # genai.configure(api_key=os.getenv("GOOGLE_API_KEY")) # Ensure this is called before model creation
    
    customs_model = genai.GenerativeModel(CUSTOMS_ASSIGNMENT_MODEL_NAME)
    weight_adjustment_model = genai.GenerativeModel(MODEL_NAME)


    # Determine which PDFs to process
    pdf_files_to_process = [f for f in os.listdir(INPUT_PDF_DIR) if f.lower().endswith(".pdf")]
    if not pdf_files_to_process:
        print(f"No PDF files found in '{INPUT_PDF_DIR}'. Nothing to process.")
        return
    # print(f"Found {len(pdf_files_to_process)} PDF files to process in '{INPUT_PDF_DIR}'.") # Removed

    # Iterate through all PDF files in the input directory
    for pdf_file in pdf_files_to_process:
        pdf_path = os.path.join(INPUT_PDF_DIR, pdf_file)
        print(f"\\n--- Spracovávam PDF: {pdf_path} ---") # Changed message to be more user-friendly
        all_items_for_invoice = [] # Holds all items from all pages of a single PDF
        invoice_id_for_filename = os.path.splitext(pdf_file)[0] # Use PDF name as default invoice ID

        # --- Step 1: Convert PDF to Images ---
        # Ensure PDF_IMAGE_DIR is cleaned or managed appropriately if images persist
        # For simplicity, we are overwriting images if names clash from previous runs not related to current PDF
        image_paths_current_pdf = pdf_to_images(pdf_path, PDF_IMAGE_DIR)

        if not image_paths_current_pdf:
            print(f"Skipping {pdf_file} as it could not be converted to images.")
            continue # Move to the next PDF file

        # --- Step 2: Analyze Images with Gemini ---
        gemini_extraction_prompt_template = """
Analyze the provided invoice image to extract structured data.
The invoice contains information about items, quantities, prices, and potentially an overall invoice number.
Please return the data in JSON format with the following structure:
{
  "invoice_number": "INV12345", // Extract if present, otherwise use "N/A" or derive from filename if instructed
  "items": [
    {
      "item_code": "CODE123", // Product code or registration number, if available. Can be alphanumeric.
      "item_name": "Product Name Example", // Full name of the item.
      "description": "Detailed description of the item, including any additional notes or specifications found on the invoice. (e.g. recyklační příspěvek 0,2951 EUR bez DPH / 1 kg)", // Detailed description
      "quantity": 10, // Number of units. Must be a number.
      "unit_price": 25.99, // Price per unit. Must be a number.
      "total_price": 259.90, // Total price for the item (quantity * unit_price). Must be a number.
      "location": "COUNTRY OF ORIGIN (e.g., CZ, GB, CN). This is a CRITICAL field. Search carefully for a 2-letter ISO code or phrases like 'Made in [Country]' for EACH item. If the origin is genuinely ABSENT from the image for a specific item, use the exact string \\\"NOT_ON_IMAGE\\\". Otherwise, if found, provide the code.",
      "currency": "EUR" // Currency code (e.g., EUR, USD, CZK). Extract if present, default to "EUR" if not specified.
    }
    // ... more items
  ]
}

Specific instructions for extraction:
- Ensure all numeric fields (quantity, unit_price, total_price) are numbers, not strings. Use dot (.) as decimal separator.
- If an item is a discount or a fee (e.g., "SLEVA", "DOPRAVA"), represent its value appropriately (e.g., negative for discount in unit_price or total_price). For such non-product lines, if a field like 'item_code' or 'location' is not applicable, use "N/A" or null respectively.
- For "item_code", prioritize the distinct product identifier.
- For "item_name", use the most descriptive name provided.
- For "description", capture any supplementary text associated with the item.
- "location" (Country of Origin): This field is ESSENTIAL. For EVERY item, meticulously find its origin (usually a 2-letter code like CZ, GB, or phrases like 'Made in...'). ONLY if the origin is genuinely ABSENT for a specific item on the invoice image, use the exact string \\\"NOT_ON_IMAGE\\\". Do not overlook this for any item. If present, provide the code.
- If an invoice spans multiple pages, process each page's items.
- Return ONLY the JSON structure. Do not include any other text or explanations before or after the JSON.
"""
        # Iterate over each image (page) from the PDF
        for i, image_path in enumerate(image_paths_current_pdf):
            # print(f"Analyzing page {i + 1} of {pdf_file} ({image_path})...") # Removed
            
            # If invoice_id_for_filename is already set from a previous page,
            # we might not need to ask Gemini for it again, or we could ask it to confirm.
            # For this version, we let Gemini try to extract it per page, and the CSV processing aggregates.
            current_page_prompt = gemini_extraction_prompt_template
            if invoice_id_for_filename != os.path.splitext(pdf_file)[0] and invoice_id_for_filename != "N/A":
                 current_page_prompt = gemini_extraction_prompt_template.replace(
                     'use "N/A" or derive from filename if instructed', 
                     f'This page belongs to invoice "{invoice_id_for_filename}". Please confirm or use this if no other number is found.'
                 )


            gemini_data_page = analyze_image_with_gemini(image_path, current_page_prompt)

            if gemini_data_page and "error" not in gemini_data_page:
                page_invoice_number = gemini_data_page.get("invoice_number")
                if page_invoice_number and (invoice_id_for_filename == os.path.splitext(pdf_file)[0] or invoice_id_for_filename == "N/A"):
                    # Prioritize invoice number found by Gemini if it's the first one or more specific
                    invoice_id_for_filename = page_invoice_number
                    # print(f"Invoice number set/updated to: '{invoice_id_for_filename}' from page {i+1}.") # Removed

                page_items = process_gemini_response_to_csv_rows(gemini_data_page, i + 1, product_weights)
                all_items_for_invoice.extend(page_items)
                # print(f"Found {len(page_items)} items on page {i + 1} of {pdf_file}.") # Removed
            else:
                error_msg = gemini_data_page.get("error", "Unknown error") if isinstance(gemini_data_page, dict) else "Raw analysis failed"
                print(f"Preskakujem stranu {i + 1} súboru {pdf_file} kvôli chybe pri analýze: {error_msg}") # Changed message
                # Add a placeholder row for the failed page if necessary for tracking
                all_items_for_invoice.append({
                    "Page Number": i + 1,
                    "Invoice Number": invoice_id_for_filename, # Use last known or default
                    "Item Name": f"PAGE ANALYSIS FAILED: {error_msg}",
                    "description": "", "Location": "", "Quantity": "", "Unit Price": "", "Total Price": "",
                    "Preliminary Net Weight": "", "Total Net Weight": "", "Total Gross Weight": "",
                    "Colný kód": "", "Popis colného kódu": ""
                })
        
        # Clean invoice_id_for_filename if it became too complex or still default
        if not invoice_id_for_filename or invoice_id_for_filename == os.path.splitext(pdf_file)[0]:
            invoice_id_for_filename = os.path.splitext(pdf_file)[0] # Fallback to filename
            # print(f"Using PDF filename as base for invoice ID: '{invoice_id_for_filename}'") # Removed
        elif invoice_id_for_filename == "N/A":
             invoice_id_for_filename = f"NeznameCisloFaktury_{os.path.splitext(pdf_file)[0]}" # Make it unique and Slovak
             print(f"Číslo faktúry nebolo nájdené AI, použije sa odvodené ID: '{invoice_id_for_filename}'") # Changed message


        # --- Step 3.1: AI Customs Code Assignment ---
        if all_items_for_invoice and all_customs_codes_map:
            # print(f"\\nAssigning customs codes for {len(all_items_for_invoice)} extracted items from invoice {invoice_id_for_filename}...") # Removed
            for item_row in all_items_for_invoice:
                # Skip if item is a placeholder for a failed page or has no name
                if "PAGE ANALYSIS FAILED" in item_row.get("Item Name", "") or not item_row.get("Item Name"):
                    continue

                item_details_for_ai = prepare_item_details_for_ai(item_row)
                if not item_details_for_ai or item_details_for_ai == "Item details are insufficient for AI processing.":
                    print(f"Skipping customs code assignment for item '{item_row.get('Item Name', 'Unknown Item')}' due to insufficient details.")
                    continue
                
                # print(f"DEBUG: Item details for AI (customs): {item_details_for_ai}") # Removed
                assigned_code, assigned_description = assign_customs_code_with_ai(
                    item_details_for_ai, 
                    all_customs_codes_map,
                    genai_model_instance=customs_model # Pass the initialized model
                )
                if assigned_code and assigned_code != "ERROR_NO_CODE_ASSIGNED":
                    item_row["Colný kód"] = assigned_code
                    # Fetch description from the map using the final assigned_code
                    item_row["Popis colného kódu"] = all_customs_codes_map.get(assigned_code, "Popis nenájdený") if assigned_code != "NEURCENE" else assigned_description # Use AI reasoning if NEURCENE
                    # print(f"Assigned customs code {assigned_code} to item: {item_row.get(\'Item Name\', \'Unknown Item\')}") # Removed
                else:
                    print(f"Nepodarilo sa priradiť colný kód pre položku: {item_row.get('Item Name', 'Neznáma položka')}") # Changed message
                    item_row["Colný kód"] = "NEPRIRADENÉ" # Explicitly mark as not assigned if AI fails
                    item_row["Popis colného kódu"] = "Chyba pri priradení AI"

        elif not all_customs_codes_map:
            print("Mapa colných kódov je prázdna. Preskakuje sa AI priradenie colných kódov.") # Changed message
        
        # print(f"DEBUG: All items for invoice {invoice_id_for_filename} after customs assignment: {all_items_for_invoice}") # Removed


        # --- Step 3.2: Ask for Target Gross and Net Weights for the current invoice ---
        # Only ask if there are items to process for this invoice
        if not all_items_for_invoice or all( "PAGE ANALYSIS FAILED" in item.get("Item Name","") for item in all_items_for_invoice ):
            print(f"Pre faktúru {invoice_id_for_filename} z {pdf_file} neboli extrahované žiadne platné položky. Preskakuje sa zadávanie hmotností a ich úprava.") # Translated
        else:
            print(f"\n--- Zadanie hmotností pre faktúru: {invoice_id_for_filename} (zo súboru {pdf_file}) ---") # Translated
            target_total_gross_kg = None
            target_total_net_kg = None
            while target_total_gross_kg is None:
                try:
                    target_total_gross_kg_str = input(f"Zadajte CIEĽOVÚ CELKOVÚ HRUBÚ hmotnosť (kg) pre faktúru {invoice_id_for_filename} (napr. 150.5): ") # Translated
                    target_total_gross_kg = float(target_total_gross_kg_str)
                except ValueError:
                    print("Neplatný vstup. Prosím, zadajte číselnú hodnotu pre hrubú hmotnosť.") # Translated
            
            while target_total_net_kg is None:
                try:
                    target_total_net_kg_str = input(f"Zadajte CIEĽOVÚ CELKOVÚ ČISTÚ hmotnosť (kg) pre faktúru {invoice_id_for_filename} (napr. 140.2): ") # Translated
                    target_total_net_kg = float(target_total_net_kg_str)
                except ValueError:
                    print("Neplatný vstup. Prosím, zadajte číselnú hodnotu pre čistú hmotnosť.") # Translated

            print(f"Cieľové hmotnosti pre {invoice_id_for_filename}: Hrubá={target_total_gross_kg} kg, Čistá={target_total_net_kg} kg")

            # --- Step 3.3: AI Weight Adjustment ---
            # Calculate the sum of "Preliminary Net Weight" for the current invoice
            calculated_preliminary_total_net_kg = 0
            valid_items_for_weight_adjustment = []
            for item_row in all_items_for_invoice:
                if "PAGE ANALYSIS FAILED" in item_row.get("Item Name", ""): # Skip failed pages
                    continue
                prelim_weight = item_row.get("Preliminary Net Weight")
                if isinstance(prelim_weight, (int, float)):
                    calculated_preliminary_total_net_kg += prelim_weight
                valid_items_for_weight_adjustment.append(item_row) # only include processable items
            
            # print(f"Calculated Preliminary Total Net Weight for {invoice_id_for_filename} (from {len(valid_items_for_weight_adjustment)} items): {calculated_preliminary_total_net_kg:.3f} kg") # Removed


            if (calculated_preliminary_total_net_kg > 0 or any(item.get("Quantity") for item in valid_items_for_weight_adjustment)) and valid_items_for_weight_adjustment:
                print(f"Prebieha úprava hmotností pre {len(valid_items_for_weight_adjustment)} položiek faktúry {invoice_id_for_filename} pomocou AI...") # Changed
                # Note: adjust_item_weights_to_target_totals_with_ai is expected to modify items_data_list in-place
                # or return a new list. The current implementation in snippets seems to modify in-place
                # and also return a structure. Let\'s adapt to ensure \'all_items_for_invoice\' is correctly updated.
                
                # Make a deep copy if the adjustment function doesn't handle it or if you want to compare
                # For now, passing the sub-list of valid items
                adjustment_result = adjust_item_weights_to_target_totals_with_ai(
                    items_data_list=valid_items_for_weight_adjustment, # Pass only valid items
                    target_total_net_kg=target_total_net_kg,
                    target_total_gross_kg=target_total_gross_kg,
                    calculated_preliminary_total_net_kg=calculated_preliminary_total_net_kg,
                    genai_model_instance=weight_adjustment_model
                )

                # The AI function might return the modified list directly or a dict containing it
                # Based on previous structure, it might be a dict with an "items" key or just the list.
                # Or it might modify in-place. Let's assume it returns the list of adjusted valid items.
                
                if isinstance(adjustment_result, list):
                    # Need to merge these changes back into all_items_for_invoice
                    # This assumes adjustment_result contains the same items as valid_items_for_weight_adjustment
                    # but with updated weights.
                    # A robust way is to map by a unique key if available, or by index if order is preserved.
                    # For simplicity, if lengths match, we assume order is preserved.
                    if len(adjustment_result) == len(valid_items_for_weight_adjustment):
                        for original_item, adjusted_item_data in zip(valid_items_for_weight_adjustment, adjustment_result):
                            original_item.update(adjusted_item_data) # Update the original item in the sublist
                        # print(f"Successfully applied AI weight adjustments for invoice {invoice_id_for_filename}.") # Removed
                    else:
                         print(f"AI úprava hmotnosti vrátila zoznam s inou dĺžkou pre faktúru '{invoice_id_for_filename}'. Vyžaduje sa manuálna kontrola. Aktualizácie neboli plne aplikované.")
                elif isinstance(adjustment_result, dict) and "error" in adjustment_result:
                    print(f"Chyba počas AI úpravy hmotnosti pre faktúru '{invoice_id_for_filename}': {adjustment_result['error']}. Používajú sa dáta pred úpravou.")
                elif isinstance(adjustment_result, dict) and "items" in adjustment_result and isinstance(adjustment_result["items"], list):
                    # Similar merging logic as above if it returns a dict with "items"
                    adjusted_items_list_from_dict = adjustment_result["items"]
                    if len(adjusted_items_list_from_dict) == len(valid_items_for_weight_adjustment):
                        for original_item, adjusted_item_data in zip(valid_items_for_weight_adjustment, adjusted_items_list_from_dict):
                            original_item.update(adjusted_item_data)
                        # print(f"Successfully applied AI weight adjustments for invoice {invoice_id_for_filename} (from dict).") # Removed
                    else:
                        print(f"AI úprava hmotnosti (z dict) vrátila zoznam s inou dĺžkou pre faktúru '{invoice_id_for_filename}'. Aktualizácie neboli plne aplikované.")
                else:
                    print(f"AI úprava hmotnosti pre faktúru '{invoice_id_for_filename}' vrátila neočakávaný výsledok alebo modifikovala dáta priamo. Skontrolujte dáta. Typ výsledku: {type(adjustment_result)}")
                    # If it modified in-place, valid_items_for_weight_adjustment (and thus items in all_items_for_invoice) are already updated.

            else:
                print(f"Preskakuje sa AI úprava hmotnosti pre faktúru '{invoice_id_for_filename}', pretože neexistujú žiadne platné položky s predbežnými hmotnosťami alebo množstvami.")
                # Populate Total Net/Gross as N/A or based on preliminary if no adjustment
                for item_row in all_items_for_invoice:
                    if "PAGE ANALYSIS FAILED" in item_row.get("Item Name", ""): continue
                    item_row.setdefault("Total Net Weight", item_row.get("Preliminary Net Weight", "N/A"))
                    item_row.setdefault("Total Gross Weight", "N/A")

        # --- Step 4: Write to CSV ---
        # Ensure all items (including failed pages) are written to the CSV for completeness.
        if all_items_for_invoice:
            safe_invoice_id = re.sub(r'[\\\\/*?:\"<>|]', "_", str(invoice_id_for_filename))
            safe_invoice_id = safe_invoice_id if safe_invoice_id else f"UNKNOWN_INVOICE_{os.path.splitext(pdf_file)[0]}"
            
            output_csv_filename = os.path.join(OUTPUT_CSV_DIR, f"processed_invoice_data_{safe_invoice_id}.csv")
            
            headers = [
                "Page Number", "Invoice Number", "Item Name", "description", "Location", 
                "Quantity", "Unit Price", "Total Price", 
                "Preliminary Net Weight", "Total Net Weight", "Total Gross Weight",
                "Colný kód", "Popis colného kódu"
            ]

            try:
                with open(output_csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=headers, delimiter=';')
                    writer.writeheader()
                    # Ensure all dictionaries have all header keys to prevent DictWriter errors
                    processed_rows_for_csv = []
                    for item_dict in all_items_for_invoice:
                        # Ensure 'Popis colného kódu' is correctly handled for NEURCENE or errors from AI customs assignment.
                        # The logic above in customs assignment part should set this. Here we just ensure it's present.
                        if item_dict.get("Colný kód") == "NEURCENE" and not item_dict.get("Popis colného kódu"):
                            item_dict["Popis colného kódu"] = "Kód nebol určený AI"
                        elif item_dict.get("Colný kód") == "NEPRIRADENÉ" and not item_dict.get("Popis colného kódu"):
                            item_dict["Popis colného kódu"] = "Chyba pri priradení AI"
                        
                        row = {header: item_dict.get(header, "") for header in headers}
                        processed_rows_for_csv.append(row)
                    writer.writerows(processed_rows_for_csv)
                print(f"Úspešne zapísané spracované dáta pre faktúru '{invoice_id_for_filename}' do '{output_csv_filename}'") # Changed

                # Move the processed PDF to processed_invoices directory
                source_pdf_path = os.path.join(INPUT_PDF_DIR, pdf_file) # pdf_file is just the filename
                destination_pdf_path = os.path.join(PROCESSED_PDF_DIR, pdf_file)
                try:
                    shutil.move(source_pdf_path, destination_pdf_path)
                    print(f"Úspešne presunuté spracované PDF '{pdf_file}' do '{PROCESSED_PDF_DIR}'") # Translated
                except Exception as e:
                    print(f"CHYBA pri presúvaní PDF '{pdf_file}' do '{PROCESSED_PDF_DIR}': {e}. Zdroj: {source_pdf_path}, Cieľ: {destination_pdf_path}") # Translated

            except IOError as e:
                print(f"CHYBA VSTUPU/VÝSTUPU pri zápise CSV pre faktúru '{invoice_id_for_filename}' do '{output_csv_filename}': {e}") # Translated
            except Exception as e:
                print(f"NeoČAKÁVANÁ CHYBA pri zápise CSV pre faktúru '{invoice_id_for_filename}' do '{output_csv_filename}': {e}") # Translated
        else:
            print(f"Žiadne položky na zápis do CSV pre faktúru z PDF: {pdf_file}") # Translated

        # Clean up images for the current PDF
        if image_paths_current_pdf:
            # print(f"Cleaning up {len(image_paths_current_pdf)} image(s) for {pdf_file}...") # Removed
            for image_path_to_delete in image_paths_current_pdf:
                try:
                    os.remove(image_path_to_delete)
                except OSError as e:
                    print(f"VAROVANIE: Nepodarilo sa vymazať obrázok {image_path_to_delete}: {e}") # Translated

    # For now, we'll let it try to proceed, but AI features will fail.
    # return # Uncomment to exit if API key is critical for all operations

    # Initialize the GenerativeModel instance (optional, can be done in functions)
    # genai.configure(api_key=GOOGLE_API_KEY) # This is now done before model init
    # model = genai.GenerativeModel(MODEL_NAME) # Moved into functions that use it or checked before use

    # --- Main Menu ---
    # Removed duplicated/commented out main menu logic.
    # The active menu is now only in the if __name__ == "__main__": block.

if __name__ == "__main__":
    # Ensure GOOGLE_API_KEY is set
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        print("CHYBA: Premenná prostredia GOOGLE_API_KEY nie je nastavená.")
        print("Uistite sa, že máte súbor .env v koreňovom adresári projektu s GOOGLE_API_KEY=VÁŠ_API_KĽÚČ")
        print("Alebo nastavte premennú prostredia vo vašom systéme.")
        # exit(1) # Consider enabling this if the API key is absolutely critical

    # Primary menu loop (this is the loop that should be active)
    while True:
        print("\\n--- Intrastat Asistent Menu ---") # Changed Menu Title
        print("1. Spracovať nové PDF faktúry")
        print("2. Generovať súhrnný report z CSV")
        print("3. Zobraziť colné kódy")
        print("4. Ukončiť")
        choice = input("Zadajte vašu voľbu (1-4): ").strip() # Changed prompt message

        if choice == '1':
            if GOOGLE_API_KEY:
                genai.configure(api_key=GOOGLE_API_KEY)
                # print("Google API Key configured for AI processing.") # Removed confirmation message
            else:
                print("UPOZORNENIE: GOOGLE_API_KEY nebol nájdený. Funkcie závislé od AI nemusia fungovať správne.") # Changed warning message
            run_pdf_processing_flow() # Removed processing_mode argument as it's not used
        
        elif choice == '2':
            prompt_and_generate_report(available_csvs_paths=None)
        
        elif choice == '3': 
            customs_data = load_customs_tariff_codes() # Assuming this function is defined elsewhere
            if customs_data:
                print("\\n--- Dostupné Colné Kódy ---")
                for code, description in customs_data.items():
                    print(f"Kód: {code} - Popis: {description}")
                print("---------------------------")
            else:
                print("Colné kódy sa nepodarilo načítať alebo nie sú dostupné.")
        
        elif choice == '4':
            print("Program sa ukončuje.")
            break
        else:
            print("Neplatná voľba, skúste znova.")
    
    # main() # This call should be commented out or removed # Already removed
    # ... (any other concluding comments) ...
