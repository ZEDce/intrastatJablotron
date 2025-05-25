"""
Report generator for Intrastat declarations.
Process CSV files with invoice data and generate summary reports.
"""

import pandas as pd
import os
import re
import shutil # Added for moving files

# Define the directory for input CSVs (outputs from main.py) and output reports
INPUT_DIR = "data_output"
OUTPUT_DIR = "dovozy" # Or a new directory like "reports" if preferred
DATA_DIR = "data" # For col_sadz.csv
# Directory for archiving processed CSV and META files from data_output after report generation
DATA_OUTPUT_ARCHIV_DIR = "data_output_archiv/"

# Directory where main.py moves PDFs after creating their CSV in data_output
# This is now the final directory for PDFs whose data has been reported.
SOURCE_PROCESSED_PDF_DIR = "spracovane_faktury/"
# ARCHIV_FAKTUR_S_REPORTOM_DIR is no longer needed as per user request.
# # New directory for PDFs after a report has been generated from their data
# ARCHIV_FAKTUR_S_REPORTOM_DIR = "archiv_faktur_s_reportom/"

def round_report_values(df):
    """Zaokrúhľuje všetky číselné hodnoty v reporte na správny počet desatinných miest."""
    # Zaokrúhli hmotnosti a ceny na 2 desatinné miesta
    numeric_columns = ['Súčet Hrubá Hmotnosť', 'Súčet Čistá Hmotnosť', 'Súčet Celková Cena']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].round(2)
    
    # Zaokrúhli množstvo na 1 desatinné miesto
    if 'Súčet Počet Kusov' in df.columns:
        df['Súčet Počet Kusov'] = df['Súčet Počet Kusov'].round(1)
    
    return df

def list_csv_files(directory):
    """Lists CSV files in the specified directory."""
    if not os.path.exists(directory):
        print(f"Directory not found: {directory}")
        return []
    files = [f for f in os.listdir(directory) if f.endswith('.csv') and os.path.isfile(os.path.join(directory, f))]
    return files

def get_customs_code_descriptions():
    """Loads customs code descriptions from col_sadz.csv."""
    col_sadz_path = os.path.join(DATA_DIR, "col_sadz.csv")
    if not os.path.exists(col_sadz_path):
        print(f"Error: Customs code descriptions file not found at {col_sadz_path}")
        return pd.DataFrame() # Return empty DataFrame if file not found

    try:
        # Adjust delimiter and encoding if necessary based on actual file format
        df_sadz = pd.read_csv(col_sadz_path, sep=';', encoding='utf-8')
        # Actual column names from file are 'col_sadz' and 'Popis'
        # Rename them to 'Colný kód' (lowercase k) and 'Popis Colného Kódu'
        df_sadz = df_sadz.rename(columns={'col_sadz': 'Colný kód', 'Popis': 'Popis Colného Kódu'})

        if 'Colný kód' not in df_sadz.columns or 'Popis Colného Kódu' not in df_sadz.columns:
            print(f"Warning: Could not find expected columns ('Colný kód', 'Popis Colného Kódu') after attempting to rename from 'col_sadz' and 'Popis' in {col_sadz_path}.")
            print(f"Available columns after rename attempt: {df_sadz.columns.tolist()}")
            return pd.DataFrame()
        return df_sadz[['Colný kód', 'Popis Colného Kódu']].drop_duplicates(subset=['Colný kód'])
    except Exception as e:
        print(f"Error reading {col_sadz_path}: {e}")
        return pd.DataFrame()


def generate_single_report(input_csv_path, output_csv_name, df_sadz):
    """Generates a summary report for a single input CSV file."""
    print(f"\nProcessing {input_csv_path}...")

    try:
        # Specify decimal separator for columns that use comma
        df = pd.read_csv(input_csv_path, sep=';', decimal=',')
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_csv_path}")
        return
    except Exception as e:
        print(f"Error reading {input_csv_path}: {e}")
        return

    # --- Step 3: Data Cleaning and Transformation ---
    numeric_cols = ['Total Gross Weight', 'Total Net Weight', 'Quantity', 'Total Price']
    # In main.py, these are 'Total Net Weight' and 'Total Gross Weight'. 'Quantity', 'Total Price'
    # The CSV from main.py has: 'Číslo Faktúry', 'Kód Položky', 'Názov Položky', 'Lokalita',
    # 'Množstvo', 'Jednotková Cena', 'Celková Cena', 'Colný Kód', 'Popis Colného Kódu',
    # 'Preliminary Net Weight', 'Total Net Weight', 'Total Gross Weight'

    # Rename columns from main.py's output to be more generic for processing, if needed, or use them directly.
    # For aggregation, we need:
    # 'Colný kód'
    # 'Lokalita' (for 'Krajina Pôvodu')
    # 'Total Gross Weight' (for 'Súčet Hrubá Hmotnosť')
    # 'Total Net Weight' (for 'Súčet Čistá Hmotnosť')
    # 'Množstvo' (for 'Súčet Počet Kusov') - This is 'Quantity' in the earlier summary, let's stick to CSV names.
    # 'Celková Cena' (for 'Súčet Celková Cena') - This is 'Total Price' in the earlier summary.

    required_cols_from_main_csv = ['Colný kód', 'Location', 'Total Gross Weight', 'Total Net Weight', 'Quantity', 'Total Price', 'description']
    for col in required_cols_from_main_csv:
        if col not in df.columns:
            print(f"Error: Required column '{col}' not found in {input_csv_path}. Cannot generate report.")
            return

    # Convert numerical columns to numeric, coercing errors
    # Define a list of expected non-numeric strings that should not trigger a warning
    # These typically come from main.py for weights when data is missing/problematic
    expected_non_numeric_placeholders = [
        "NENÁJDENÉ", "CHYBA_QTY", "CHÝBAJÚ_DÁTA_HMOTNOSTI", 
        "CHÝBA_KÓD_PRE_HMOTNOSŤ", "NOT_IN_AI_RESP", "AI_JSON_DECODE_ERR",
        "AI_BAD_FORMAT_NON_LIST", "AI_EXCEPTION", "ERROR", "AI_SKIP_NO_VALID_ITEMS",
        "ERR_GROSS_LT_NET", "ERR_NEGATIVE", "ERR_CONVERT", "ERR_AI_KEY_MISSING", "N/A"
    ]
    # Include variants that might appear in CSV due to errors or AI responses (e.g. with _ERR_ suffix from main.py)
    # This list can be expanded as needed.

    for col in numeric_cols:
        # Store original for comparison/warning
        original_series = df[col].copy()

        # If the column is of object type (likely string), attempt to replace comma with dot
        if df[col].dtype == 'object':
            # First, explicitly replace known placeholders with NaN before general comma replacement
            # This avoids issues if a placeholder itself contains a comma.
            # We will convert these NaNs to 0.0 later without warning.
            for placeholder in expected_non_numeric_placeholders:
                df[col] = df[col].replace(placeholder, pd.NA) # Replace with pandas NA
            
            # Now, replace commas for actual numbers
            df[col] = df[col].str.replace(',', '.', regex=False)

        df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Identify rows where coercion introduced NaNs
        # but the original value was not one of our expected placeholders.
        coerced_errors = original_series[df[col].isna() & original_series.notna()]
        for index, val in coerced_errors.items():
            # Check if the current row corresponds to a discount or fee item
            # These items might have their 'Colný kód' changed to "Zľava" or "Poplatok"
            # and their weight/price values might be intentionally non-numeric or zeroed out.
            is_special_item_row = False
            if 'Colný kód' in df.columns: # Ensure the column exists before accessing
                item_type_identifier = df.loc[index, 'Colný kód']
                if item_type_identifier in ["Zľava", "Poplatok"]:
                    is_special_item_row = True

            if is_special_item_row:
                continue # Skip warning for special rows like discount/fee

            # Check if the original value (before any processing in this loop) was an expected placeholder
            original_value_from_csv = str(original_series.loc[index]).strip()
            is_expected_placeholder = False
            for placeholder in expected_non_numeric_placeholders:
                if original_value_from_csv == placeholder or original_value_from_csv.startswith(placeholder + "_ERR") :
                    is_expected_placeholder = True
                    break
            
            if not is_expected_placeholder:
                print(f"Warning: Neočakávaná nečíselná hodnota '{val}' nájdená v stĺpci '{col}', riadok {index+2} súboru {input_csv_path}. Spracovaná ako 0.0 pre sčítanie.")
        
        df[col] = df[col].fillna(0.0)


    # Handle 'Lokalita' for 'Krajina Pôvodu'
    df['Krajina Pôvodu'] = df['Location'].fillna("NEŠPECIFIKOVANÁ").replace('', "NEŠPECIFIKOVANÁ")

    # Prepare columns for adjusted summation based on item descriptions
    # Ensure 'Quantity' and 'Total Price' are numeric before copying
    df['Adjusted Quantity'] = df['Quantity'].copy()
    df['Adjusted Total Price'] = df['Total Price'].copy()

    # Identify discount and handling fee rows based on 'description' column
    # Using regex=False for literal string matching, case-insensitive
    if 'description' in df.columns: # Ensure the column exists
        is_discount = df['description'].str.contains("Sleva zákazníkovi", case=False, na=False, regex=False)
        is_handling_fee = df['description'].str.contains("Manipulační poplatek", case=False, na=False, regex=False)

        # For discount rows, change 'Colný kód' and 'Location' for specific reporting
        df.loc[is_discount, 'Colný kód'] = "Zľava"
        df.loc[is_discount, 'Location'] = "Zľava"
        # For handling fee rows that might also be NEURCENE, we can also give them a specific code if desired
        # df.loc[is_handling_fee, 'Colný kód'] = "Poplatok" # Example, if we want to separate them
        # df.loc[is_handling_fee, 'Location'] = "Poplatok"

        # Set quantity to 0 for both discount and handling fee
        df.loc[is_discount | is_handling_fee, 'Adjusted Quantity'] = 0
        
        # Set total price to 0 for handling fee (it will be ignored in sum)
        # Discount's total price remains to be included in the sum
        df.loc[is_handling_fee, 'Adjusted Total Price'] = 0
    else:
        print(f"Warning: Column 'description' not found in {input_csv_path}. Cannot apply filtering for discount/handling fee.")


    # --- Step 4: Grouping and Aggregation ---
    grouped = df.groupby(['Colný kód', 'Krajina Pôvodu'], as_index=False).agg(
        Súčet_Hrubá_Hmotnosť=('Total Gross Weight', 'sum'),
        Súčet_Čistá_Hmotnosť=('Total Net Weight', 'sum'),
        Súčet_Počet_Kusov=('Adjusted Quantity', 'sum'),
        Súčet_Celková_Cena=('Adjusted Total Price', 'sum')
    )

    # --- Step 5: Adding Customs Code Descriptions ---
    if not df_sadz.empty:
        report_df = pd.merge(grouped, df_sadz, on='Colný kód', how='left')
        report_df['Popis Colného Kódu'] = report_df['Popis Colného Kódu'].fillna("Popis nenájdený")
    else:
        report_df = grouped.copy()
        report_df['Popis Colného Kódu'] = "Popis nenájdený (col_sadz.csv nebol načítaný)"


    # --- Step 6: Formatting the Output DataFrame ---
    report_df = report_df.rename(columns={
        'Colný kód': 'Colná sadzba', # Final output column name
        'Súčet_Hrubá_Hmotnosť': 'Súčet Hrubá Hmotnosť',
        'Súčet_Čistá_Hmotnosť': 'Súčet Čistá Hmotnosť',
        'Súčet_Počet_Kusov': 'Súčet Počet Kusov',
        'Súčet_Celková_Cena': 'Súčet Celková Cena'
    })

    # Order columns as specified
    final_columns_ordered = [
        'Colná sadzba', # Output column can be lowercase 'k'
        'Krajina Pôvodu',
        'Súčet Hrubá Hmotnosť', 'Súčet Čistá Hmotnosť',
        'Súčet Počet Kusov', 'Súčet Celková Cena'
    ]
    report_df = report_df[final_columns_ordered]

    # Filter out NEURCENE rows where all sum values are zero
    report_df = report_df[~(
        (report_df['Colná sadzba'] == 'NEURCENE') &
        (report_df['Súčet Hrubá Hmotnosť'] == 0) &
        (report_df['Súčet Čistá Hmotnosť'] == 0) &
        (report_df['Súčet Počet Kusov'] == 0) &
        (report_df['Súčet Celková Cena'] == 0)
    )]

    # --- Step 7: Zaokrúhľovanie a Spolu riadok ---
    # Vypočítaj "Spolu" riadok z pôvodných (nezaokrúhlených) agregovaných hodnôt
    # report_df v tomto bode obsahuje výsledky z df.groupby(...).agg(...)
    # tieto hodnoty by mali byť ešte presné (nezaokrúhlené na 2 des. miesta)
    
    spolu_row = {
        'Colná sadzba': 'Spolu',
        'Krajina Pôvodu': '',
        'Súčet Hrubá Hmotnosť': round(report_df['Súčet Hrubá Hmotnosť'].sum(), 2),
        'Súčet Čistá Hmotnosť': round(report_df['Súčet Čistá Hmotnosť'].sum(), 2),
        'Súčet Počet Kusov': round(report_df['Súčet Počet Kusov'].sum(), 1), # Množstvo sa zaokrúhľuje na 1 des. miesto
        'Súčet Celková Cena': round(report_df['Súčet Celková Cena'].sum(), 2)
    }
    
    # Teraz zaokrúhli hodnoty v jednotlivých riadkoch pre zobrazenie
    report_df = round_report_values(report_df)
    
    # Pridaj "Spolu" riadok (ktorý bol vypočítaný z presnejších súčtov)
    report_df = pd.concat([report_df, pd.DataFrame([spolu_row])], ignore_index=True)

    # --- Step 8: Saving the Report ---
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Sanitize output_csv_name to ensure it's a valid filename
    sane_output_csv_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', output_csv_name)
    if not sane_output_csv_name.endswith(".csv"):
        sane_output_csv_name += ".csv"

    output_path = os.path.join(OUTPUT_DIR, sane_output_csv_name)
    try:
        report_df.to_csv(output_path, index=False, sep=';', decimal='.') # Using semicolon as separator
        print(f"Report successfully generated: {output_path}")
    except Exception as e:
        print(f"Error writing report to {output_path}: {e}")
        return # Return early if report writing fails, so we don't attempt to move PDF or delete files

    # After successfully generating the report, try to archive the original PDF
    # input_csv_path is the path to the CSV in data_output, e.g., "data_output/processed_invoice_XY.csv"
    try:
        # This function now logs the status of the PDF in SOURCE_PROCESSED_PDF_DIR
        log_final_pdf_status(input_csv_path, SOURCE_PROCESSED_PDF_DIR)
    except Exception as e:
        # Log an error if logging status fails, but don't let it crash the report generation flow
        print(f"Chyba počas zaznamenávania stavu pôvodného PDF súvisiaceho s {input_csv_path}: {e}")
    
    # Regardless of PDF archiving outcome (it might have been archived previously, or meta missing),
    # if the report was successfully generated, we should clean up the source CSV and its .meta file from data_output.
    meta_filepath_to_delete = input_csv_path + ".meta"
    # Delete the .meta file
    if os.path.exists(meta_filepath_to_delete):
        try:
            # Ensure archive directory exists
            os.makedirs(DATA_OUTPUT_ARCHIV_DIR, exist_ok=True)
            # Move .meta file to archive
            shutil.move(meta_filepath_to_delete, os.path.join(DATA_OUTPUT_ARCHIV_DIR, os.path.basename(meta_filepath_to_delete)))
            print(f"Úspešne archivovaný meta súbor: {os.path.join(DATA_OUTPUT_ARCHIV_DIR, os.path.basename(meta_filepath_to_delete))}")
        except Exception as e:
            print(f"Chyba pri archivácii meta súboru {meta_filepath_to_delete} do {DATA_OUTPUT_ARCHIV_DIR}: {e}")
    else:
        # This is not an error for cleanup, meta might not exist if PDF was processed by older main.py version
        print(f"Poznámka: Meta súbor {meta_filepath_to_delete} nebol nájdený na archiváciu (môže byť v poriadku).")

    # Delete the processed data CSV file from data_output
    if os.path.exists(input_csv_path):
        try:
            # Ensure archive directory exists (might be redundant if already created for .meta, but safe)
            os.makedirs(DATA_OUTPUT_ARCHIV_DIR, exist_ok=True)
            # Move .csv file to archive
            shutil.move(input_csv_path, os.path.join(DATA_OUTPUT_ARCHIV_DIR, os.path.basename(input_csv_path)))
           
        except Exception as e:
            print(f"Chyba pri archivácii spracovaného CSV súboru {input_csv_path} do {DATA_OUTPUT_ARCHIV_DIR}: {e}")
    else:
        # This case should ideally not happen if we just processed it, but good to note.
        print(f"Varovanie: Spracovaný CSV súbor {input_csv_path} nebol nájdený na archiváciu.")


def log_final_pdf_status(processed_data_csv_path, source_pdf_dir):
    """Reads a .meta file associated with processed_data_csv_path to find the original
    PDF filename and logs that the PDF in source_pdf_dir is now considered reported.
    It no longer moves the PDF.
    """
    meta_filepath = processed_data_csv_path + ".meta"

    if not os.path.exists(meta_filepath):
        print(f"Varovanie: Meta súbor {meta_filepath} nebol nájdený. Stav pôvodného PDF nemôže byť potvrdený.")
        return

    original_pdf_filename = ""
    try:
        with open(meta_filepath, 'r', encoding='utf-8') as mf:
            original_pdf_filename = mf.read().strip()
    except Exception as e:
        print(f"Chyba pri čítaní meta súboru {meta_filepath}: {e}. Stav pôvodného PDF nemôže byť potvrdený.")
        return

    if not original_pdf_filename:
        print(f"Varovanie: Meta súbor {meta_filepath} je prázdny. Stav pôvodného PDF nemôže byť potvrdený.")
        return

    source_pdf_full_path = os.path.join(source_pdf_dir, original_pdf_filename)

    if not os.path.exists(source_pdf_full_path):
        print(f"Varovanie: Pôvodný PDF súbor '{original_pdf_filename}' (uvedený v {meta_filepath}) nebol nájdený v adresári {source_pdf_dir}. Mohol byť presunutý alebo nespracovaný správne.")
    else:
        print(f"Potvrdenie: Dáta z PDF súboru '{original_pdf_filename}' (v '{source_pdf_dir}') boli použité na generovanie reportu.")

    # Deletion of .meta and .csv is handled in generate_single_report after this function call.

    # except Exception as e:
    #     print(f"Chyba pri presúvaní PDF súboru '{original_pdf_filename}' z '{source_pdf_dir}' do '{archive_pdf_dir}': {e}")


def main():
    """Main function to drive the report generation."""
    df_sadz = get_customs_code_descriptions()
    if df_sadz.empty:
        print("Warning: Proceeding without customs code descriptions as col_sadz.csv could not be loaded or processed correctly.")

    input_files = list_csv_files(INPUT_DIR)
    if not input_files:
        print(f"No CSV files found in {INPUT_DIR} to process.")
        return

    print("Available CSV files for reporting:")
    for i, fname in enumerate(input_files):
        print(f"{i+1}. {fname}")

    while True:
        try:
            choice_str = input(f"Enter the number of the CSV file to process (1-{len(input_files)}): ")
            choice = int(choice_str) - 1
            if 0 <= choice < len(input_files):
                selected_csv_path = os.path.join(INPUT_DIR, input_files[choice])
                break
            else:
                print("Invalid selection. Please enter a number from the list.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    default_output_name = f"summary_report_{os.path.splitext(input_files[choice])[0]}.csv"
    output_filename = input(f"Enter the desired name for the output summary CSV file (default: {default_output_name}): ")
    if not output_filename:
        output_filename = default_output_name

    generate_single_report(selected_csv_path, output_filename, df_sadz)

def prompt_and_generate_report(available_csvs_paths=None):
    """
    Prompts the user to select a CSV file and generates a summary report for it.
    Uses functions imported from report.py.
    If available_csvs_paths is provided, it uses that list for selection. 
    Otherwise, it lists all CSVs in INPUT_DIR.
    """
    print("\n--- Generovanie Súhrnného Reportu ---")
    
    source_csv_paths_for_selection = []
    input_files_display_names = []
    base_dir_for_paths_msg = INPUT_DIR # Default

    if available_csvs_paths:
        source_csv_paths_for_selection = available_csvs_paths
        input_files_display_names = [os.path.basename(p) for p in source_csv_paths_for_selection]
        base_dir_for_paths_msg = os.path.dirname(available_csvs_paths[0]) if available_csvs_paths else INPUT_DIR
    else: # If no specific list, list all CSVs in the default input directory for reports
        # print(f"Prehľadávam adresár '{INPUT_DIR}' pre CSV súbory...") # User requested less verbose output
        all_filenames_in_dir = list_csv_files(INPUT_DIR)
        input_files_display_names = all_filenames_in_dir
        source_csv_paths_for_selection = [os.path.join(INPUT_DIR, fname) for fname in all_filenames_in_dir]
        # base_dir_for_paths_msg remains INPUT_DIR here

    if not input_files_display_names:
        print(f"Žiadne CSV súbory neboli nájdené na spracovanie v adresári '{base_dir_for_paths_msg}'.")
        return

    print("Dostupné CSV súbory na generovanie reportu:")
    for i, fname_display in enumerate(input_files_display_names):
        print(f"{i+1}. {fname_display}")

    selected_csv_full_path = None
    selected_csv_filename_for_default = None

    while True:
        try:
            choice_str = input(f"Zadajte číslo CSV súboru, pre ktorý chcete vygenerovať report (1-{len(input_files_display_names)}), alebo 'cancel' pre zrušenie: ").strip().lower()
            if choice_str == 'cancel':
                print("Generovanie reportu zrušené.")
                return
            choice_idx = int(choice_str) - 1
            if 0 <= choice_idx < len(source_csv_paths_for_selection):
                selected_csv_full_path = source_csv_paths_for_selection[choice_idx]
                selected_csv_filename_for_default = input_files_display_names[choice_idx]
                break
            else:
                print("Neplatný výber. Zadajte číslo zo zoznamu.")
        except ValueError:
            print("Neplatný vstup. Zadajte číslo.")

    if not selected_csv_full_path: # If 'cancel' was chosen or loop exited unexpectedly.
        return

    # Prepare default output name for the summary report
    default_report_name = f"summary_report_{os.path.splitext(selected_csv_filename_for_default)[0]}.csv"
    output_report_name_input = input(f"Zadajte názov pre výstupný súbor reportu (predvolené: {default_report_name}): ")
    final_output_report_name = output_report_name_input.strip() if output_report_name_input.strip() else default_report_name
    
    # Ensure it ends with .csv
    if not final_output_report_name.lower().endswith(".csv"):
        final_output_report_name += ".csv"

    # print("Načítavam colné kódy pre report...") # User requested less verbose output
    df_sadz = get_customs_code_descriptions()
    if df_sadz.empty:
        print("Varovanie: Colné kódy neboli načítané. Report bude pokračovať bez popisov colných kódov.")

    print(f"Generujem report pre {selected_csv_full_path} -> {final_output_report_name}...")
    generate_single_report(selected_csv_full_path, final_output_report_name, df_sadz)

if __name__ == "__main__":
    main() 