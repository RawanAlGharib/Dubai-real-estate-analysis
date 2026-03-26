import pandas as pd
import numpy as np

# ==========================================
# STEP 1: LOAD THE MASSIVE DATASET
# ==========================================
# Using low_memory=False because the dataset is 1.41 GB and pandas might 
# struggle to guess the data types for each column across millions of rows.
print("Loading data... this might take a minute.")
file_path = 'DLD_Rents.csv' 
df = pd.read_csv(file_path, low_memory=False)

print(f"Initial Data Shape: {df.shape[0]} rows and {df.shape[1]} columns")


# ==========================================
# STEP 2: HANDLE CRITICAL MISSING VALUES (NULLS)
# ==========================================
# The dataset description notes up to 35% nulls. We cannot calculate prices 
# if the actual transaction amount or area is missing.
# Note: Adjust the column names in quotes to match the exact headers in your CSV.

critical_columns = ['annual_amount', 'actual_area', 'property_usage_en']

# Drop rows where critical financial or area data is missing
df_clean = df.dropna(subset=critical_columns).copy()

# For less critical columns (like property subtype), fill nulls with 'Unknown' 
# so we don't lose the transaction data entirely.
df_clean['ejari_property_type_en'] = df_clean['ejari_property_type_en'].fillna('Unknown')


# STEP 3: STANDARDIZE MEASUREMENT UNITS (SQF vs SQM)
# ==========================================
# The data has undefined area sizes (SQF vs SQM). We need to standardize 
# everything to Square Meters (SQM) for consistent analysis.
# 1 Square Meter = 10.7639 Square Feet

# Assuming there is a column indicating the unit (e.g., 'Area Unit')
# If the unit is missing, we will leave it as is, or you can write a rule to guess 
# based on the raw number (e.g., if area > 5000, it's likely SQF).

def standardize_to_sqm(row):
    # Check if the unit column indicates Square Feet
    if pd.notna(row.get('Area Unit')) and 'SQF' in str(row['Area Unit']).upper():
        return row['actual_area'] / 10.7639
    # Otherwise, assume it is already SQM
    return row['actual_area']

# Apply the function to create a clean, standardized Area column
df_clean['Area_SQM_Standardized'] = df_clean.apply(standardize_to_sqm, axis=1)

# ==========================================
# STEP 4: CALCULATE NEW FINANCIAL METRICS
# ==========================================
# Now that area is standardized and nulls are handled, we can create the 
# key metric that real estate analysts use: Price per Square Meter.

df_clean['Price_Per_SQM'] = df_clean['annual_amount'] / df_clean['Area_SQM_Standardized']


# ==========================================
# TEMPORAL ANOMALY CLEANING (Fixing Future Dates)
# ==========================================
print("Cleaning date anomalies...")

# 1. Ensure the column is treated as official dates
df_clean['contract_start_date'] = pd.to_datetime(df_clean['contract_start_date'], errors='coerce')

# 2. Filter out any rows where the year is greater than the current year (2026)
current_year = 2026
df_clean = df_clean[df_clean['contract_start_date'].dt.year <= current_year].copy()

# 3. Optional: Drop rows where the date was completely missing/invalid
df_clean = df_clean.dropna(subset=['contract_start_date']).copy()

print(f"Timeline fixed. True market data ends in: {df_clean['contract_start_date'].max().date()}")


# ==========================================
# STEP 5: EXPORT CLEAN DATA FOR TABLEAU
# ==========================================
print(f"Clean Data Shape: {df_clean.shape[0]} rows and {df_clean.shape[1]} columns")

# Save the cleaned dataset to a new CSV. 
# This file will be much lighter and ready to connect directly to Tableau.
output_path = 'Cleaned_Dubai_Real_Estate.csv'
df_clean.to_csv(output_path, index=False)
print("Data cleaning complete. Clean file saved for Tableau visualization!")



#Phase 2

import pandas as pd
import numpy as np

# 1. Load the Data
print("Loading data...")
# Assuming you already ran Phase 1 and have a cleaned base dataset
df_clean = pd.read_csv('Cleaned_Dubai_Real_Estate.csv', low_memory=False)


# 2. Clean the Area Data & Calculate the Core KPI
# First, remove any rows where the actual_area is 0 or less to prevent 'inf' errors
df_clean = df_clean[df_clean['actual_area'] > 0].copy()

# Now it is safe to calculate the rent per area
df_clean['annual_rent_per_area'] = df_clean['annual_amount'] / df_clean['actual_area']


# 3. Statistical Outlier Detection (The IQR Method)
# We apply this to 'annual_amount' to remove abnormally high luxury leases 
# or data entry errors (e.g., someone typing an extra zero) that would skew your trends.
Q1 = df_clean['annual_amount'].quantile(0.25)
Q3 = df_clean['annual_amount'].quantile(0.75)
IQR = Q3 - Q1

lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

# Filter the dataset to keep typical market leases
df_typical_market = df_clean[(df_clean['annual_amount'] >= lower_bound) & 
                             (df_clean['annual_amount'] <= upper_bound)].copy()

print(f"Removed extreme outliers. Normal market records remaining: {len(df_typical_market)}")

# 4. Aggregate Trends for Strategic Decision Making
# Grouping by 'property_usage_en' (e.g., Commercial vs Residential) to identify patterns
market_trends = df_typical_market.groupby(['property_usage_en']).agg({
    'annual_amount': 'mean',          # Average annual rent
    'annual_rent_per_area': 'mean',   # Average rent per sq measure
    'actual_area': 'count'            # Total number of lease contracts (Volume)
}).reset_index()

# Rename the count column so it makes sense on a dashboard
market_trends.rename(columns={'actual_area': 'total_lease_contracts'}, inplace=True)

# 5. Export for Tableau
market_trends.to_csv('Dubai_Rental_Market_Trends.csv', index=False)
print("Aggregated market trends ready for visualization.")