import sqlite3
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import os
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OceanDatabase:
    """
    Ocean AI Explorer Database Manager
    Handles SQLite database operations for ARGO float data
    Optimized for handling 1 million+ records efficiently
    """
    
    def __init__(self, db_path: str = "database/ocean_data.db"):
        """Initialize database connection and setup"""
        self.db_path = db_path
        self.ensure_directory()
        self.conn = None
        self.connect()
        self.setup_database()
    
    def ensure_directory(self):
        """Ensure database directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def connect(self):
        """Establish database connection with optimizations"""
        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0
        )
        
        # Performance optimizations for large datasets
        self.conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        self.conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes
        self.conn.execute("PRAGMA cache_size=10000")  # Larger cache
        self.conn.execute("PRAGMA temp_store=MEMORY")  # Memory temp storage
        self.conn.execute("PRAGMA mmap_size=268435456")  # Memory mapping (256MB)
        
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys=ON")
        
        logger.info(f"Connected to database: {self.db_path}")
    
    def setup_database(self):
        """Create tables and indexes from schema file"""
        try:
            with open("database/schema.sql", "r") as f:
                schema = f.read()
            
            # Execute schema in parts to handle multiple statements
            statements = schema.split(';')
            for statement in statements:
                if statement.strip():
                    self.conn.execute(statement)
            
            self.conn.commit()
            logger.info("Database schema created successfully")
            
        except FileNotFoundError:
            logger.error("Schema file not found. Creating basic tables...")
            self.create_basic_schema()
        except Exception as e:
            logger.error(f"Error setting up database: {e}")
            raise
    
    def create_basic_schema(self):
        """Create basic schema if schema.sql is not found"""
        basic_schema = """
        CREATE TABLE IF NOT EXISTS argo_floats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            float_id VARCHAR(20) NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            measurement_date DATETIME NOT NULL,
            ocean_region VARCHAR(50),
            status VARCHAR(20) DEFAULT 'active'
        );
        
        CREATE TABLE IF NOT EXISTS temperature_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            float_id VARCHAR(20) NOT NULL,
            measurement_date DATETIME NOT NULL,
            depth_meters REAL NOT NULL,
            temperature_celsius REAL NOT NULL
        );
        """
        self.conn.executescript(basic_schema)
        self.conn.commit()
    
    def import_csv_data(self, csv_file_path: str, data_type: str = "temperature", 
                       batch_size: int = 1000, region_mapping: Dict = None):
        """
        Import CSV data in batches for memory efficiency
        
        Args:
            csv_file_path: Path to CSV file
            data_type: Type of data ('temperature', 'salinity', 'oxygen', 'floats')
            batch_size: Number of rows to process at once
            region_mapping: Dictionary to map coordinates to regions
        """
        if not os.path.exists(csv_file_path):
            logger.error(f"CSV file not found: {csv_file_path}")
            return False
        
        try:
            logger.info(f"Starting import of {data_type} data from {csv_file_path}")
            
            # Read CSV in chunks for memory efficiency
            chunk_iter = pd.read_csv(csv_file_path, chunksize=batch_size)
            total_rows = 0
            
            for chunk_num, chunk in enumerate(chunk_iter):
                # Clean and prepare data
                chunk = self.clean_data(chunk, data_type)
                
                # Add region mapping if provided
                if region_mapping and data_type == "floats":
                    chunk['ocean_region'] = chunk.apply(
                        lambda row: self.get_ocean_region(row['latitude'], row['longitude'], region_mapping),
                        axis=1
                    )
                
                # Insert data based on type
                if data_type == "floats":
                    self.insert_float_data(chunk)
                elif data_type == "temperature":
                    self.insert_temperature_data(chunk)
                elif data_type == "salinity":
                    self.insert_salinity_data(chunk)
                elif data_type == "oxygen":
                    self.insert_oxygen_data(chunk)
                
                total_rows += len(chunk)
                
                if chunk_num % 10 == 0:  # Log progress every 10 chunks
                    logger.info(f"Processed {total_rows} rows...")
            
            self.conn.commit()
            logger.info(f"Successfully imported {total_rows} rows of {data_type} data")
            return True
            
        except Exception as e:
            logger.error(f"Error importing CSV data: {e}")
            self.conn.rollback()
            return False
    
    def clean_data(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """Clean and validate data"""
        # Remove rows with missing critical values
        if data_type == "floats":
            df = df.dropna(subset=['float_id', 'latitude', 'longitude'])
            # Validate latitude/longitude ranges
            df = df[(df['latitude'] >= -90) & (df['latitude'] <= 90)]
            df = df[(df['longitude'] >= -180) & (df['longitude'] <= 180)]
        
        elif data_type in ["temperature", "salinity", "oxygen"]:
            df = df.dropna(subset=['float_id', 'measurement_date'])
        
        # Convert date columns
        if 'measurement_date' in df.columns:
            df['measurement_date'] = pd.to_datetime(df['measurement_date'], errors='coerce')
            df = df.dropna(subset=['measurement_date'])
        
        return df
    
    def get_ocean_region(self, lat: float, lon: float, region_mapping: Dict) -> str:
        """Determine ocean region based on coordinates"""
        # Simple region mapping - can be enhanced with more sophisticated logic
        if -30 <= lat <= 60 and -180 <= lon <= -30:
            return "Atlantic Ocean"
        elif -30 <= lat <= 60 and 30 <= lon <= 180:
            return "Pacific Ocean"
        elif -30 <= lat <= 30 and 20 <= lon <= 120:
            return "Indian Ocean"
        elif lat >= 60:
            return "Arctic Ocean"
        elif lat <= -30:
            return "Southern Ocean"
        else:
            return "Unknown"
    
    def insert_float_data(self, df: pd.DataFrame):
        """Insert ARGO float data"""
        data = []
        for _, row in df.iterrows():
            data.append((
                row.get('float_id'),
                row.get('platform_number'),
                row.get('cycle_number'),
                row.get('latitude'),
                row.get('longitude'),
                row.get('measurement_date'),
                row.get('ocean_region', 'Unknown'),
                row.get('status', 'active')
            ))
        
        self.conn.executemany("""
            INSERT OR REPLACE INTO argo_floats 
            (float_id, platform_number, cycle_number, latitude, longitude, 
             measurement_date, ocean_region, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
    
    def insert_temperature_data(self, df: pd.DataFrame):
        """Insert temperature measurement data"""
        data = []
        for _, row in df.iterrows():
            data.append((
                row.get('float_id'),
                row.get('measurement_date'),
                row.get('depth_meters', 0),
                row.get('temperature_celsius'),
                row.get('quality_flag', 1),
                row.get('pressure_dbar')
            ))
        
        self.conn.executemany("""
            INSERT INTO temperature_data 
            (float_id, measurement_date, depth_meters, temperature_celsius, 
             quality_flag, pressure_dbar)
            VALUES (?, ?, ?, ?, ?, ?)
        """, data)
    
    def insert_salinity_data(self, df: pd.DataFrame):
        """Insert salinity measurement data"""
        data = []
        for _, row in df.iterrows():
            data.append((
                row.get('float_id'),
                row.get('measurement_date'),
                row.get('depth_meters', 0),
                row.get('salinity_psu'),
                row.get('quality_flag', 1),
                row.get('conductivity')
            ))
        
        self.conn.executemany("""
            INSERT INTO salinity_data 
            (float_id, measurement_date, depth_meters, salinity_psu, 
             quality_flag, conductivity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, data)
    
    def insert_oxygen_data(self, df: pd.DataFrame):
        """Insert oxygen measurement data"""
        data = []
        for _, row in df.iterrows():
            data.append((
                row.get('float_id'),
                row.get('measurement_date'),
                row.get('depth_meters', 0),
                row.get('oxygen_mg_per_l'),
                row.get('oxygen_saturation'),
                row.get('quality_flag', 1)
            ))
        
        self.conn.executemany("""
            INSERT INTO oxygen_data 
            (float_id, measurement_date, depth_meters, oxygen_mg_per_l, 
             oxygen_saturation, quality_flag)
            VALUES (?, ?, ?, ?, ?, ?)
        """, data)
    
    def get_float_data(self, region: str = None, status: str = None, 
                      limit: int = 1000, offset: int = 0) -> List[Dict]:
        """Get ARGO float data with filtering and pagination"""
        query = "SELECT * FROM argo_floats WHERE 1=1"
        params = []
        
        if region:
            query += " AND ocean_region = ?"
            params.append(region)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY measurement_date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = self.conn.execute(query, params)
        columns = [description[0] for description in cursor.description]
        
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        return results
    
    def get_measurement_data(self, data_type: str, float_id: str = None, 
                           start_date: str = None, end_date: str = None,
                           region: str = None, limit: int = 1000) -> List[Dict]:
        """Get measurement data with filtering"""
        table_map = {
            'temperature': 'temperature_data',
            'salinity': 'salinity_data',
            'oxygen': 'oxygen_data'
        }
        
        if data_type not in table_map:
            raise ValueError(f"Invalid data type: {data_type}")
        
        table = table_map[data_type]
        
        if region:
            query = f"""
                SELECT td.*, af.ocean_region 
                FROM {table} td
                JOIN argo_floats af ON td.float_id = af.float_id
                WHERE af.ocean_region = ?
            """
            params = [region]
        else:
            query = f"SELECT * FROM {table} WHERE 1=1"
            params = []
        
        if float_id:
            query += " AND td.float_id = ?" if region else " AND float_id = ?"
            params.append(float_id)
        
        if start_date:
            query += " AND td.measurement_date >= ?" if region else " AND measurement_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND td.measurement_date <= ?" if region else " AND measurement_date <= ?"
            params.append(end_date)
        
        query += f" ORDER BY {'td.' if region else ''}measurement_date DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.conn.execute(query, params)
        columns = [description[0] for description in cursor.description]
        
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        return results
    
    def get_statistics(self, data_type: str, region: str = None) -> Dict:
        """Get statistical summary for data type"""
        if data_type == "floats":
            return self.get_float_statistics(region)
        else:
            return self.get_measurement_statistics(data_type, region)
    
    def get_float_statistics(self, region: str = None) -> Dict:
        """Get float statistics"""
        query = """
            SELECT 
                COUNT(*) as total_floats,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_floats,
                COUNT(CASE WHEN status = 'inactive' THEN 1 END) as inactive_floats,
                ocean_region
            FROM argo_floats
        """
        
        if region:
            query += " WHERE ocean_region = ? GROUP BY ocean_region"
            params = [region]
        else:
            query += " GROUP BY ocean_region"
            params = []
        
        cursor = self.conn.execute(query, params)
        results = cursor.fetchall()
        
        if region:
            return {
                'total_floats': results[0][0] if results else 0,
                'active_floats': results[0][1] if results else 0,
                'inactive_floats': results[0][2] if results else 0
            }
        else:
            return {
                'regions': [
                    {
                        'region': row[3],
                        'total_floats': row[0],
                        'active_floats': row[1],
                        'inactive_floats': row[2]
                    }
                    for row in results
                ]
            }
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

# Example usage and data import script
if __name__ == "__main__":
    # Initialize database
    db = OceanDatabase()
    
    # Example CSV import (adjust paths as needed)
    csv_files = {
        "floats": "data/argo_floats.csv",
        "temperature": "data/temperature_data.csv",
        "salinity": "data/salinity_data.csv",
        "oxygen": "data/oxygen_data.csv"
    }
    
    # Import data from CSV files
    for data_type, csv_path in csv_files.items():
        if os.path.exists(csv_path):
            print(f"Importing {data_type} data...")
            db.import_csv_data(csv_path, data_type)
        else:
            print(f"CSV file not found: {csv_path}")
    
    # Test queries
    print("\nTesting database queries...")
    
    # Get float statistics
    stats = db.get_statistics("floats")
    print(f"Float statistics: {stats}")
    
    # Get recent temperature data
    temp_data = db.get_measurement_data("temperature", limit=10)
    print(f"Found {len(temp_data)} temperature records")
    
    # Close connection
    db.close()