"""
Decline Curve Analysis for Well Production Data
================================================
Analyzes production data and fits hyperbolic decline curves
"""

import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# =============================================================================
# CONFIGURATION
# =============================================================================

DB_USER = "postgres"
DB_PASSWORD = "motorola"  # ← UPDATE THIS
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "well_decline_analysis"

# =============================================================================
# DECLINE CURVE FUNCTIONS
# =============================================================================

def hyperbolic_decline(t, qi, Di, b):
    """
    Hyperbolic decline curve equation
    
    Parameters:
    - t: time (months)
    - qi: initial production rate (bbl/month)
    - Di: initial decline rate (1/month)
    - b: hyperbolic exponent (0 = exponential, 1 = harmonic)
    
    Returns: production rate at time t
    """
    return qi / ((1 + b * Di * t) ** (1/b))


def calculate_eur(qi, Di, b, economic_limit=10):
    """
    Calculate Estimated Ultimate Recovery (EUR)
    
    Parameters:
    - qi: initial production rate
    - Di: decline rate
    - b: hyperbolic exponent
    - economic_limit: minimum economic production rate (bbl/month)
    
    Returns: EUR in barrels
    """
    # Find time to reach economic limit
    t_max = ((qi/economic_limit)**b - 1) / (b * Di)
    
    # Integrate decline curve from 0 to t_max
    time_points = np.linspace(0, t_max, 1000)
    production_points = hyperbolic_decline(time_points, qi, Di, b)
    eur = np.trapz(production_points, time_points)
    
    return eur

# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def analyze_production():
    """Main decline curve analysis function"""
    
    print("=" * 70)
    print("DECLINE CURVE ANALYSIS")
    print("=" * 70)
    
    # 1. Connect to database
    print("\n🔌 Connecting to PostgreSQL...")
    connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(connection_string)
    print("✅ Connected!")
    
    # 2. Load daily production data
    print("\n📊 Loading production data...")
    query = """
    SELECT 
        production_date,
        oil_volume,
        gas_volume,
        water_volume
    FROM production
    ORDER BY production_date;
    """
    df = pd.read_sql(query, engine)
    
    # Convert to datetime (fix for .dt accessor)
    df['production_date'] = pd.to_datetime(df['production_date'])
    
    print(f"✅ Loaded {len(df):,} days of data")
    print(f"   Date range: {df['production_date'].min()} to {df['production_date'].max()}")
    
    # 3. Aggregate to monthly production
    print("\n📅 Aggregating to monthly production...")
    df['year_month'] = df['production_date'].dt.to_period('M')
    
    monthly = df.groupby('year_month').agg({
        'oil_volume': 'sum',
        'gas_volume': 'sum',
        'water_volume': 'sum'
    }).reset_index()
    
    monthly['year_month'] = monthly['year_month'].dt.to_timestamp()
    monthly['months_on_production'] = range(len(monthly))
    
    print(f"✅ Created {len(monthly)} months of aggregated data")
    print(f"\n📈 Monthly production statistics:")
    print(monthly[['oil_volume', 'gas_volume']].describe())
    
    # 4. Fit hyperbolic decline curve to oil production (LAST 20 MONTHS ONLY)
    print("\n🔧 Fitting hyperbolic decline curve to last 20 months...")

    # Filter to last 20 months only (months 70-89)
    recent_data = monthly[monthly['months_on_production'] >= 70].copy()

    # Reset time to start at 0 for fitting
    t = (recent_data['months_on_production'] - 70).values
    q = recent_data['oil_volume'].values

    print(f"   Using months 70-89 ({len(t)} data points)")
    
    # Initial guesses for parameters (from recent data)
    qi_guess = recent_data['oil_volume'].iloc[0]  # First month of recent period
    Di_guess = 0.10  # 10% monthly decline (expect higher for depleted well)
    b_guess = 0.0    # Start with exponential
    
    try:
        # Fit the curve
        params, covariance = curve_fit(
            hyperbolic_decline,
            t, q,
            p0=[qi_guess, Di_guess, b_guess],
            bounds=([0, 0, 0], [np.inf, 1, 2]),  # Parameter bounds
            maxfev=10000
        )
        
        qi_fit, Di_fit, b_fit = params
        
        # Calculate R² (goodness of fit)
        q_pred = hyperbolic_decline(t, qi_fit, Di_fit, b_fit)
        ss_res = np.sum((q - q_pred) ** 2)
        ss_tot = np.sum((q - np.mean(q)) ** 2)
        r_squared = 1 - (ss_res / ss_tot)
        
        print("✅ Decline curve fitted successfully!")
        print(f"\n📊 Decline Curve Parameters:")
        print(f"   qi (Initial Rate):     {qi_fit:,.2f} bbl/month")
        print(f"   Di (Decline Rate):     {Di_fit*100:.2f}% per month ({Di_fit*12*100:.1f}% per year)")
        print(f"   b (Hyperbolic Factor): {b_fit:.4f}")
        print(f"   R² (Model Fit):        {r_squared:.4f}")
        
        # 5. Calculate EUR (future production + historical)
        print("\n🎯 Calculating EUR...")

        # Future production from month 20 onwards (210 months total life from fitting start)
        time_future = np.arange(20, 210)
        production_future = hyperbolic_decline(time_future, qi_fit, Di_fit, b_fit)
        future_reserves = np.trapezoid(production_future, time_future)

        # Historical cumulative
        cumulative_to_date = monthly['oil_volume'].sum()

        # Total EUR
        eur = cumulative_to_date + future_reserves
        remaining_reserves = future_reserves
        
        print(f"   Cumulative Production: {cumulative_to_date:,.0f} bbls")
        print(f"   EUR (Total Recovery):  {eur:,.0f} bbls")
        print(f"   Remaining Reserves:    {remaining_reserves:,.0f} bbls")
        print(f"   Recovery Factor:       {(cumulative_to_date/eur)*100:.1f}%")
        
        # 6. Generate forecast (starting from month 90)
        print("\n🔮 Generating 10-year production forecast...")
        forecast_months = 120  # 10 years
        # Forecast starts at month 90, offset by 70 (our fitting baseline)
        t_forecast = np.arange(20, 20 + forecast_months)  # 20 months from fitting start
        q_forecast = hyperbolic_decline(t_forecast, qi_fit, Di_fit, b_fit)
        
        # Create forecast dataframe
        last_date = monthly['year_month'].max()
        forecast_dates = pd.date_range(
            start=last_date + pd.DateOffset(months=1),
            periods=forecast_months,
            freq='MS'
        )
        
        forecast_df = pd.DataFrame({
            'forecast_date': forecast_dates,
            'months_on_production': np.arange(90, 90 + forecast_months),  # Changed this line
            'predicted_oil': q_forecast
        })
        
        print(f"✅ Generated {len(forecast_df)} months of forecast")
        
        # 7. Create visualization
        print("\n📊 Creating visualization...")
        plt.figure(figsize=(12, 6))
        
        # Plot historical data
        plt.plot(monthly['year_month'], monthly['oil_volume'], 
                'o', label='Actual Production', markersize=4)
        
        # Plot fitted curve
        t_all = np.concatenate([t, t_forecast])
        q_all = hyperbolic_decline(t_all, qi_fit, Di_fit, b_fit)
        dates_all = pd.date_range(
            start=monthly['year_month'].min(),
            periods=len(t_all),
            freq='MS'
        )
        plt.plot(dates_all[:len(t)], q_all[:len(t)], 
                'r-', label='Decline Curve Fit', linewidth=2)
        
        # Plot forecast
        plt.plot(dates_all[len(t):], q_all[len(t):], 
                'g--', label='Forecast', linewidth=2)
        
        plt.xlabel('Date')
        plt.ylabel('Oil Production (bbl/month)')
        plt.title('Well Production Decline Curve Analysis')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save plot
        plot_path = r"E:\Documents-E\Full-Stack Analyst Project\decline_curve.png"
        plt.savefig(plot_path, dpi=300)
        print(f"✅ Chart saved to: {plot_path}")
        plt.close()
        
        # 8. Save results to database
        print("\n💾 Saving results to database...")
        
        # Save decline parameters
        params_df = pd.DataFrame([{
            'well_id': 'WELL_001',
            'qi': qi_fit,
            'di': Di_fit,
            'b_factor': b_fit,
            'r_squared': r_squared,
            'eur': eur,
            'cumulative_production': cumulative_to_date,
            'remaining_reserves': remaining_reserves,
            'analysis_date': datetime.now()
        }])
        
        params_df.to_sql('decline_parameters', engine, 
                        if_exists='replace', index=False)
        print("✅ Decline parameters saved")
        
        # Save forecast
        forecast_df.to_sql('production_forecast', engine,
                          if_exists='replace', index=False)
        print("✅ Forecast saved")
        
        # Save monthly aggregated data
        monthly[['year_month', 'months_on_production', 'oil_volume', 
                'gas_volume', 'water_volume']].to_sql(
            'monthly_production', engine,
            if_exists='replace', index=False
        )
        print("✅ Monthly production saved")
        
        print(f"\n{'=' * 70}")
        print("✅ ANALYSIS COMPLETE!")
        print(f"{'=' * 70}")
        print("\nNew database tables created:")
        print("  - decline_parameters (decline curve metrics)")
        print("  - production_forecast (10-year forecast)")
        print("  - monthly_production (aggregated monthly data)")
        print("\nNext step: Build Power BI dashboard!")
        
    except Exception as e:
        print(f"❌ Error fitting decline curve: {e}")
        print("This could be due to insufficient data or poor fit.")
        raise

if __name__ == "__main__":
    try:
        analyze_production()
        print("\nPress Enter to exit...")
        input()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\nPress Enter to exit...")
        input()