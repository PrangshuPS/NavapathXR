-- Ocean AI Explorer Database Schema
-- Optimized for handling 10 lakh (1 million) rows efficiently

-- ARGO Float Data Table
CREATE TABLE argo_floats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    float_id VARCHAR(20) NOT NULL,
    platform_number VARCHAR(20),
    cycle_number INTEGER,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    measurement_date DATETIME NOT NULL,
    ocean_region VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Temperature Measurements Table
CREATE TABLE temperature_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    float_id VARCHAR(20) NOT NULL,
    measurement_date DATETIME NOT NULL,
    depth_meters REAL NOT NULL,
    temperature_celsius REAL NOT NULL,
    quality_flag INTEGER DEFAULT 1,
    pressure_dbar REAL,
    FOREIGN KEY (float_id) REFERENCES argo_floats(float_id)
);

-- Salinity Measurements Table
CREATE TABLE salinity_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    float_id VARCHAR(20) NOT NULL,
    measurement_date DATETIME NOT NULL,
    depth_meters REAL NOT NULL,
    salinity_psu REAL NOT NULL,
    quality_flag INTEGER DEFAULT 1,
    conductivity REAL,
    FOREIGN KEY (float_id) REFERENCES argo_floats(float_id)
);

-- Dissolved Oxygen Data Table
CREATE TABLE oxygen_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    float_id VARCHAR(20) NOT NULL,
    measurement_date DATETIME NOT NULL,
    depth_meters REAL NOT NULL,
    oxygen_mg_per_l REAL NOT NULL,
    oxygen_saturation REAL,
    quality_flag INTEGER DEFAULT 1,
    FOREIGN KEY (float_id) REFERENCES argo_floats(float_id)
);

-- Prediction Results Cache Table
CREATE TABLE prediction_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_type VARCHAR(50) NOT NULL,
    ocean_region VARCHAR(50) NOT NULL,
    time_range VARCHAR(20) NOT NULL,
    latitude REAL,
    longitude REAL,
    prediction_data TEXT, -- JSON format
    confidence_percentage INTEGER,
    model_accuracy INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME
);

-- Performance Indexes
-- Spatial and temporal queries
CREATE INDEX idx_argo_floats_location ON argo_floats(latitude, longitude);
CREATE INDEX idx_argo_floats_date ON argo_floats(measurement_date);
CREATE INDEX idx_argo_floats_region ON argo_floats(ocean_region);
CREATE INDEX idx_argo_floats_status ON argo_floats(status);

-- Temperature data indexes
CREATE INDEX idx_temp_float_date ON temperature_data(float_id, measurement_date);
CREATE INDEX idx_temp_depth ON temperature_data(depth_meters);
CREATE INDEX idx_temp_date ON temperature_data(measurement_date);

-- Salinity data indexes
CREATE INDEX idx_salinity_float_date ON salinity_data(float_id, measurement_date);
CREATE INDEX idx_salinity_depth ON salinity_data(depth_meters);
CREATE INDEX idx_salinity_date ON salinity_data(measurement_date);

-- Oxygen data indexes
CREATE INDEX idx_oxygen_float_date ON oxygen_data(float_id, measurement_date);
CREATE INDEX idx_oxygen_depth ON oxygen_data(depth_meters);
CREATE INDEX idx_oxygen_date ON oxygen_data(measurement_date);

-- Prediction cache indexes
CREATE INDEX idx_prediction_type_region ON prediction_cache(prediction_type, ocean_region);
CREATE INDEX idx_prediction_expires ON prediction_cache(expires_at);

-- Views for common queries
-- Latest measurements per float
CREATE VIEW latest_measurements AS
SELECT 
    af.float_id,
    af.latitude,
    af.longitude,
    af.ocean_region,
    af.status,
    MAX(td.measurement_date) as latest_temp_date,
    MAX(sd.measurement_date) as latest_salinity_date,
    MAX(od.measurement_date) as latest_oxygen_date
FROM argo_floats af
LEFT JOIN temperature_data td ON af.float_id = td.float_id
LEFT JOIN salinity_data sd ON af.float_id = sd.float_id
LEFT JOIN oxygen_data od ON af.float_id = od.float_id
GROUP BY af.float_id;

-- Regional summary view
CREATE VIEW regional_summary AS
SELECT 
    ocean_region,
    COUNT(DISTINCT float_id) as total_floats,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_floats,
    COUNT(CASE WHEN status = 'inactive' THEN 1 END) as inactive_floats,
    AVG(latitude) as avg_latitude,
    AVG(longitude) as avg_longitude
FROM argo_floats
GROUP BY ocean_region;

-- Recent data view for dashboard
CREATE VIEW recent_data AS
SELECT 
    af.float_id,
    af.latitude,
    af.longitude,
    af.ocean_region,
    af.status,
    td.temperature_celsius,
    sd.salinity_psu,
    od.oxygen_mg_per_l,
    td.measurement_date
FROM argo_floats af
LEFT JOIN temperature_data td ON af.float_id = td.float_id 
    AND td.measurement_date = (
        SELECT MAX(measurement_date) 
        FROM temperature_data td2 
        WHERE td2.float_id = af.float_id
    )
LEFT JOIN salinity_data sd ON af.float_id = sd.float_id 
    AND sd.measurement_date = (
        SELECT MAX(measurement_date) 
        FROM salinity_data sd2 
        WHERE sd2.float_id = af.float_id
    )
LEFT JOIN oxygen_data od ON af.float_id = od.float_id 
    AND od.measurement_date = (
        SELECT MAX(measurement_date) 
        FROM oxygen_data od2 
        WHERE od2.float_id = af.float_id
    );