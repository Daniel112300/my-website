SELECT 
    d.device_name AS '設備名稱',
    pl.energy_consumed AS '用電量(kWh)',
    pl.cost AS '電費(元)'
FROM power_logs pl
JOIN devices d ON pl.device_id = d.device_id
WHERE pl.log_date = CURDATE()
ORDER BY pl.cost DESC;
