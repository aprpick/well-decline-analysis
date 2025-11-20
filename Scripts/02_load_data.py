"""
Load petroleum production data into PostgreSQL
"""

import pandas as pd
from sqlalchemy import create_engine

# =============================================================================
# CONFIGURATION
# =============================================================================

# CSV file path
CSV_PATH = R"E:\Documents-E\Full-Stack Analyst Project\Production Data\Raw\petroleum.csv"

# PostgreSQL connection details
DB_USER = "postgres"
DB_PASSWORD = "motorola"  # ← CHANGE THIS!
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "well_decline_analysis"

# =============================================================================
# LOAD DATA
# =============================================================================

def load_data():
    """Load CSV data into PostgreSQL"""
    
    print("=" * 70)
    print("LOADING PETROLEUM DATA INTO POSTGRESQL")
    print("=" * 70)
    
    # 1. Read CSV (ignore the index column)
    print(f"\n📁 Reading CSV file...")
    df = pd.read_csv(CSV_PATH, index_col=0)  # Skip the unnamed index column
    print(f"✅ Loaded {len(df):,} rows")
    print(f"✅ Columns: {list(df.columns)}")
    
    # 2. Rename columns to match database table
    print(f"\n🔄 Renaming columns to match database...")
    df.columns = [
        'production_date',
        'avg_downhole_pressure',
        'avg_downhole_temperature',
        'avg_dp_tubing',
        'avg_choke_size_p',
        'avg_whp_p',
        'avg_wht_p',
        'dp_choke_size',
        'oil_volume',
        'gas_volume',
        'water_volume'
    ]
    print(f"✅ Columns renamed")
    
    # 3. Convert date column to datetime
    print(f"\n📅 Converting dates...")
    df['production_date'] = pd.to_datetime(df['production_date'])
    print(f"✅ Dates converted")
    
    # 4. Show data preview
    print(f"\n🔍 Data preview:")
    print(df.head())
    print(f"\n📊 Date range: {df['production_date'].min()} to {df['production_date'].max()}")
    print(f"📊 Total rows: {len(df):,}")
    
    # 5. Connect to PostgreSQL
    print(f"\n🔌 Connecting to PostgreSQL...")
    connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(connection_string)
    print(f"✅ Connected to database: {DB_NAME}")
    
    # 6. Load data into table
    print(f"\n⬆️  Loading data into 'production' table...")
    print(f"   This may take a moment...")
    
    df.to_sql(
        'production',
        engine,
        if_exists='append',  # Add to existing table
        index=False,         # Don't include pandas index
        method='multi',      # Fast bulk insert
        chunksize=1000       # Insert 1000 rows at a time
    )
    
    print(f"✅ Successfully loaded {len(df):,} rows into database!")
    
    # 7. Verify data was loaded
    print(f"\n🔍 Verifying data in database...")
    verify_query = "SELECT COUNT(*) as total_rows FROM production;"
    result = pd.read_sql(verify_query, engine)
    print(f"✅ Database now contains {result['total_rows'][0]:,} rows")
    
    # 8. Show sample data from database
    print(f"\n📋 Sample data from database:")
    sample_query = """
    SELECT 
        production_date, 
        oil_volume, 
        gas_volume, 
        water_volume 
    FROM production 
    ORDER BY production_date 
    LIMIT 5;
    """
    sample_data = pd.read_sql(sample_query, engine)
    print(sample_data)
    
    print(f"\n{'=' * 70}")
    print("✅ DATA LOAD COMPLETE!")
    print(f"{'=' * 70}")
    print("\nNext steps:")
    print("1. Refresh pgAdmin to see the data")
    print("2. Run SQL queries to analyze the data")
    print("3. Build decline curve analysis")
    print("4. Create Power BI dashboard")
    print("\nPress Enter to exit...")
    input()

if __name__ == "__main__":
    try:
        load_data()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nPress Enter to exit...")
        input()