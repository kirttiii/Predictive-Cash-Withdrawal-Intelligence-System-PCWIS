import requests
import psycopg2
import json

def fetch_atm_locations(city="Delhi"):
    print(f"Fetching ATM locations for {city} from OpenStreetMap via Overpass API...")
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    area[name="{city}"]->.searchArea;
    (
      node["amenity"="atm"](area.searchArea);
      node["amenity"="bank"](area.searchArea);
    );
    out center;
    """
    
    response = requests.post(overpass_url, data={'data': overpass_query})
    
    if response.status_code == 200:
        data = response.json()
        print(f"Fetched {len(data['elements'])} ATMs/Banks.")
        return data['elements']
    else:
        print(f"Failed to fetch from Overpass: {response.status_code}")
        return []

def setup_postgis(conn_params):
    try:
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        
        # Ensure PostGIS is enabled
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        
        # Create ATMs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS candidate_locations (
                id SERIAL PRIMARY KEY,
                osm_id BIGINT UNIQUE,
                type VARCHAR(50),
                name VARCHAR(255),
                geom geometry(Point, 4326)
            );
        """)
        # Create spatial index for ST_DWithin performance
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_candidate_locations_geom
            ON candidate_locations USING GIST(geom);
        """)
        conn.commit()
        return conn, cur
    except Exception as e:
        print(f"PostGIS setup failed: {e}")
        return None, None

def load_locations_to_postgis(elements, conn_params):
    conn, cur = setup_postgis(conn_params)
    if not conn:
        print("Skipping DB insertion (dry-run/error).")
        return
        
    print("Loading locations into PostGIS...")
    inserted = 0
    for el in elements:
        try:
            osm_id = el.get('id')
            lat = el.get('lat') or (el.get('center', {}).get('lat'))
            lon = el.get('lon') or (el.get('center', {}).get('lon'))
            
            tags = el.get('tags', {})
            name = tags.get('name', 'Unknown ATM/Bank')
            type_val = tags.get('amenity', 'unknown')
            
            if lat and lon:
                cur.execute("""
                    INSERT INTO candidate_locations (osm_id, type, name, geom)
                    VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                    ON CONFLICT (osm_id) DO NOTHING
                """, (osm_id, type_val, name, lon, lat))
                inserted += 1
        except Exception as e:
            pass # skip duplicates or errors
            
    conn.commit()
    print(f"Successfully inserted {inserted} locations into PostGIS.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    db_params = {
        'dbname': 'cybercrime_gis',
        'user': 'postgres',
        'password': 'postgres',
        'host': 'localhost',
        'port': '5432'
    }
    
    # We will fetch a small subset for a specific area to avoid overloading the API
    atms = fetch_atm_locations("New Delhi")
    if atms:
        load_locations_to_postgis(atms, db_params)
