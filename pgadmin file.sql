SELECT 
    'Decline Parameters' as table_name,
    COUNT(*) as row_count
FROM decline_parameters
UNION ALL
SELECT 'Monthly Production', COUNT(*) FROM monthly_production
UNION ALL
SELECT 'Production Forecast', COUNT(*) FROM production_forecast
UNION ALL
SELECT 'Daily Production', COUNT(*) FROM production;