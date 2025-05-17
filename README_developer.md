# PDF Invoice Data Extractor - Technical Breakdown

**Project Goal:** To extract structured line-item data from multiple PDF invoices into CSV files, including a calculated total net weight for each item, using AI-powered image analysis with the Google Gemini API and a local product weight lookup file.

**Core Workflow & Components:**

1.  **Environment Setup:**
    *   Utilizes a `.env` file to securely manage the `GOOGLE_API_KEY`.
    *   Imports necessary libraries: `glob` for finding PDF files, `fitz` (PyMuPDF) for PDF handling, `google.generativeai` for Gemini API interaction, `os` for file operations, `csv` for CSV I/O, `json` for parsing AI responses.
    *   **Input Files:**
        *   PDF invoices placed in the `data/` directory.
        *   `data/product_weight.csv`: A CSV file mapping product codes (`Registrační číslo`) to their unit weights (`JV Váha komplet SK`), using a semicolon delimiter and comma for decimals in weights.

2.  **Product Weight Loading (`load_product_weights` function):**
    *   Reads `data/product_weight.csv`.
    *   Parses the CSV, expecting a header `Registrační číslo;JV Váha komplet SK`.
    *   Converts weight strings (e.g., "0,168") to float values.
    *   Returns a dictionary mapping `item_code` (string) to `unit_weight` (float).
    *   Includes error handling for file not found, malformed rows, and value conversion errors.

3.  **PDF to Image Conversion (`pdf_to_images` function):**
    *   Takes a PDF file path and a specific `output_folder` for that PDF's images as input.
    *   Uses `fitz.open()` to open the PDF.
    *   Iterates through each page, loading it and converting it to a PNG image using `page.get_pixmap(dpi=200)`.
    *   Saves these images to the specified `output_folder` (e.g., `pdf_images/invoice_name/page_1.png`).
    *   Returns a list of paths to the generated images.

4.  **Image Analysis with Gemini (`analyze_image_with_gemini` function):**
    *   Takes an image path and a detailed prompt string as input.
    *   Configures the Gemini model (currently `gemini-1.5-flash-latest`).
    *   Reads the image file as bytes.
    *   Constructs an `image_part` dictionary with `mime_type` and `data` (inline image data).
    *   Sends the image part and the prompt to the Gemini API using `model.generate_content()`.
    *   **Prompt Engineering:** The crucial prompt instructs Gemini to:
        *   Extract the overall invoice number.
        *   Identify line items and extract specific fields for each: `item_code`, `location`, `quantity`, `unit_price`, `total_price`.
        *   Return the entire result as a single, valid JSON object with a top-level `invoice_number` and a list of `items` (each item being an object with the requested fields).
    *   Handles the API response:
        *   Logs the raw text response from Gemini.
        *   Cleans the response by stripping potential markdown ```json ... ``` fences.
        *   Parses the cleaned text into a Python dictionary using `json.loads()`.
    *   Includes robust error handling for API calls and JSON decoding errors, returning an error dictionary if issues occur.

5.  **Processing Gemini's JSON Response (`process_gemini_response_to_csv_rows` function):**
    *   Takes the parsed JSON data from Gemini, the page number, and the `product_weights_map` dictionary as input.
    *   If the input indicates an error or unexpected JSON structure, it creates a placeholder/error row for the CSV (including a blank "Total Net Weight").
    *   Extracts `invoice_number` and `items` list from the JSON.
    *   For each item:
        *   Maps JSON fields (`item_code`, `location`, `quantity`, `unit_price`, `total_price`) to CSV fields.
        *   **Net Weight Calculation:**
            *   Retrieves `item_code` and `quantity` from the item data.
            *   Looks up the `unit_weight` in `product_weights_map` using `item_code`.
            *   Converts the `quantity` string (potentially with comma decimal) to a float.
            *   If both `unit_weight` and `quantity_float` are valid, calculates `total_net_weight = quantity_float * unit_weight`.
            *   Formats the `total_net_weight` to a string with 3 decimal places, using a comma as the decimal separator.
            *   Handles cases where `item_code` is not found in `product_weights_map` (sets weight to "NO_WEIGHT_DATA") or `quantity` cannot be converted (sets weight to "QTY_ERR").
        *   Adds the `Total Net Weight` to the dictionary for the CSV row.
    *   Returns a list of dictionaries, each representing a CSV row.

6.  **Main Orchestration (`main` function):**
    *   Defines input/output directories (`data/`, `pdf_images/`, `data_output/`).
    *   **Loads Product Weights:** Calls `load_product_weights()` to get the `product_weights` dictionary. Prints a message if loading fails and proceeds without weight calculation.
    *   Performs API key check and configuration.
    *   Uses `glob.glob()` to find all `*.pdf` files in the input directory.
    *   **User CSV Output Choice:** Prompts the user (in Slovak) to choose between a single combined CSV file (enter '1') or separate CSV files for each invoice (enter '2'). Internally maps '1' to 'single' and '2' to 'separate'.
    *   Iterates through each found PDF file:
        *   Creates a unique sub-folder within `pdf_images/` (e.g., `pdf_images/invoice_name/`) for the current PDF's page images.
        *   Calls `pdf_to_images` to convert the current PDF to images, saving them in its dedicated sub-folder.
        *   If generating a **single CSV** and it's not the first PDF being processed, adds a separator row to the master data list. This row clearly indicates a new invoice in the CSV, using the PDF filename.
        *   Iterates through the generated images for the current PDF:
            *   Calls `analyze_image_with_gemini`.
            *   Calls `process_gemini_response_to_csv_rows`, passing the `product_weights` dictionary.
            *   Collects data from all pages.
        *   **Row Number Generation (Per PDF):** After processing all pages of the current PDF, it iterates through the collected data for *this PDF* and prepends a sequential "Row Number" (starting from 1 for each PDF) to each item dictionary.
        *   If generating a **single CSV**, appends the processed and numbered data from the current PDF to a `master_data_from_all_pdfs` list.
        *   If generating **separate CSVs**, the processed and numbered data for the current PDF is immediately written to its own CSV file within the `data_output/` directory (e.g., `data_output/invoice_name_extracted.csv`).
    *   **CSV Writing:**
        *   Defines CSV `headers`: `"Invoice Number", "Page Number", "Row Number", "Item Name", "Location", "Quantity", "Unit Price", "Total Price", "Total Net Weight"`.
        *   Writes data to the chosen CSV file(s) in `data_output/`.
        *   Placeholder rows also include a blank "Total Net Weight".

7.  **Execution:**
    *   The `if __name__ == "__main__":` block ensures `main()` is called when the script is run directly.
    *   Includes pre-flight checks for the API key and informative print statements for the user.
    *   **Net Weight Calculation:** The script now calculates the total net weight for each item by multiplying its quantity (from the invoice) with its unit weight (from `data/product_weight.csv`).
    *   **User Choice for CSV Output:** Added an option for the user to decide whether to generate a single combined CSV or separate CSV files for each processed invoice, providing more flexibility.
    *   **Multi-PDF Processing:** The script now handles all PDFs in a specified directory, consolidating their data into one CSV.

**Key Design Decisions & Simplifications Made:**

*   **User Choice for CSV Output:** Added an option for the user to decide whether to generate a single combined CSV or separate CSV files for each processed invoice, providing more flexibility.
*   **Multi-PDF Processing:** The script now handles all PDFs in a specified directory, consolidating their data into one CSV.
*   **Organized Image Storage:** Page images from different PDFs are stored in separate sub-folders.
*   **Clear CSV Separation:** Separator rows are added to the CSV to distinguish data from different invoices.
*   **Shift to JSON Output from AI:** This was a foundational improvement, eliminating complex regex parsing and making data extraction more robust.
*   **Clear Separation of Concerns:** Functions maintain distinct responsibilities.
*   **Targeted Prompting:** The prompt is specific, improving AI output reliability.
*   **Error Handling:** Comprehensive error handling for API calls and JSON parsing remains.
*   **CSV Column Customization:** The script was adapted to allow flexible definition and ordering of CSV columns.
*   **Redundancy Removal:** Removed unnecessary placeholder logic in the main loop as the processing function already handled it.

## API Usage Costs (Gemini 1.5 Flash)

The project uses the `gemini-1.5-flash-latest` model. The costs associated with the Gemini API are based on the number of tokens in the input (images + text prompt) and the output (generated JSON).

As of August 2024, the pricing for Gemini 1.5 Flash (paid tier, for prompts up to 128k tokens) is approximately:
*   **Input tokens:** $0.075 per 1 million tokens
*   **Output tokens:** $0.30 per 1 million tokens

**Estimated Cost for this Extractor:**

Based on typical PDF page complexity and the amount of data extracted:
*   **Input per page (image + prompt):** ~1600 tokens
*   **Output per page (JSON data):** ~200 tokens

This results in an estimated cost of roughly **$0.00018 per PDF page** (less than 0.02 US cents).

*   Processing **1,000 pages**: approximately **$0.18**
*   Processing **10,000 pages**: approximately **$1.80**

**Note:**
*   These are estimates. Actual costs can vary based on image resolution/detail, prompt length, and the volume of extracted data.
*   Google offers a free tier for the Gemini API which has usage limits. For extensive use, you will likely be on the paid tier.
*   It's recommended to monitor your usage and billing in the Google Cloud Console.
*   Prices are subject to change. Always refer to the official Google AI pricing page for the latest information. 