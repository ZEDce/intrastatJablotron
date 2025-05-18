import pandas as pd
import os
import re

# Define the directory for input CSVs (outputs from main.py) and output reports
INPUT_DIR = "data_output"
OUTPUT_DIR = "dovozy" # Or a new directory like "reports" if preferred
DATA_DIR = "data" # For col_sadz.csv

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
    # Expected columns from main.py's output (adjust if these names are different)
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
    for col in numeric_cols:
        # Store original for comparison/warning
        original_series = df[col].copy()

        # If the column is of object type (likely string), attempt to replace comma with dot
        if df[col].dtype == 'object':
            df[col] = df[col].str.replace(',', '.', regex=False)

        df[col] = pd.to_numeric(df[col], errors='coerce')
        # Identify rows where coercion introduced NaNs (meaning original was not numeric)
        coerced_errors = original_series[df[col].isna() & original_series.notna()]
        for index, val in coerced_errors.items():
            print(f"Warning: Non-numeric value '{val}' found in column '{col}', row {index+2} of {input_csv_path}. Treated as 0.0 for summation.")
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

    # --- Step 7: Adding the "Spolu" (Grand Total) Row ---
    spolu_row = {
        'Colná sadzba': 'Spolu', # Matches the renamed 'Colný kód'
        'Krajina Pôvodu': '',
        'Súčet Hrubá Hmotnosť': report_df['Súčet Hrubá Hmotnosť'].sum(),
        'Súčet Čistá Hmotnosť': report_df['Súčet Čistá Hmotnosť'].sum(),
        'Súčet Počet Kusov': report_df['Súčet Počet Kusov'].sum(),
        'Súčet Celková Cena': report_df['Súčet Celková Cena'].sum()
    }
    # Use pd.concat instead of append for future compatibility
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
    Otherwise, it lists all CSVs in REPORT_INPUT_DIR.
    """
    print("\\n--- Generovanie Súhrnného Reportu ---")
    
    source_csv_paths_for_selection = []
    input_files_display_names = []
    # REPORT_INPUT_DIR is imported and should point to "dovozy/"
    # base_dir_for_paths_msg is used for user messages about where files are listed from.

    if available_csvs_paths: # If a specific list of CSVs is provided (e.g., just processed)
        source_csv_paths_for_selection = available_csvs_paths
        input_files_display_names = [os.path.basename(p) for p in source_csv_paths_for_selection]
        base_dir_for_paths_msg = os.path.dirname(available_csvs_paths[0]) if available_csvs_paths else INPUT_DIR
    else: # If no specific list, list all CSVs in the default input directory for reports
        print(f"Prehľadávam adresár '{INPUT_DIR}' pre CSV súbory...")
        all_filenames_in_dir = list_csv_files(INPUT_DIR) # From report.py, returns filenames
        input_files_display_names = all_filenames_in_dir
        source_csv_paths_for_selection = [os.path.join(INPUT_DIR, fname) for fname in all_filenames_in_dir]
        base_dir_for_paths_msg = INPUT_DIR

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

    if not selected_csv_full_path: # Should not be reached if loop breaks correctly
        return

    # Prepare default output name for the summary report
    default_report_name = f"summary_report_{os.path.splitext(selected_csv_filename_for_default)[0]}.csv"
    output_report_name_input = input(f"Zadajte názov pre výstupný súbor reportu (predvolené: {default_report_name}): ")
    final_output_report_name = output_report_name_input.strip() if output_report_name_input.strip() else default_report_name
    
    # Ensure it ends with .csv
    if not final_output_report_name.lower().endswith(".csv"):
        final_output_report_name += ".csv"

    print("Načítavam colné kódy pre report...")
    df_sadz = get_customs_code_descriptions() # From report.py
    if df_sadz.empty:
        print("Varovanie: Colné kódy neboli načítané. Report bude pokračovať bez popisov colných kódov.")

    print(f"Generujem report pre {selected_csv_full_path} -> {final_output_report_name}...")
    # generate_single_report (from report.py) handles saving to its defined OUTPUT_DIR
    generate_single_report(selected_csv_full_path, final_output_report_name, df_sadz)

if __name__ == "__main__":
    main() 