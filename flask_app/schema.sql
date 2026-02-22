-- Use the SQL Editor in Supabase to run this script

-- Create the Farmers table
CREATE TABLE IF NOT EXISTS farmers (
    id SERIAL PRIMARY KEY,
    mobile TEXT UNIQUE NOT NULL,
    name TEXT,
    district TEXT,
    mandal TEXT,
    language_preference TEXT DEFAULT 'en',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create the Fields table
CREATE TABLE IF NOT EXISTS fields (
    id SERIAL PRIMARY KEY,
    farmer_id INTEGER REFERENCES farmers(id) ON DELETE CASCADE,
    location TEXT,
    crop_type TEXT,
    variety TEXT,
    sowing_date DATE,
    area_sown FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create the Recommendations table
CREATE TABLE IF NOT EXISTS recommendations (
    id SERIAL PRIMARY KEY,
    farmer_id INTEGER REFERENCES farmers(id) ON DELETE CASCADE,
    field_id INTEGER REFERENCES fields(id) ON DELETE CASCADE,
    recommendation_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create Bookings table 
CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    farmer_id INTEGER REFERENCES farmers(id) ON DELETE CASCADE,
    fertilizer_name TEXT NOT NULL,
    quantity_kg FLOAT NOT NULL,
    total_price FLOAT NOT NULL,
    status TEXT DEFAULT 'Pending',
    delivery_address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create Disease History table
CREATE TABLE IF NOT EXISTS disease_history (
    id SERIAL PRIMARY KEY,
    farmer_id INTEGER REFERENCES farmers(id) ON DELETE CASCADE,
    image_base64 TEXT,
    plant_type TEXT,
    disease_name TEXT,
    is_healthy BOOLEAN,
    description TEXT,
    recommendation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create Complaints table
CREATE TABLE IF NOT EXISTS complaints (
    id SERIAL PRIMARY KEY,
    farmer_id INTEGER REFERENCES farmers(id) ON DELETE CASCADE,
    image_base64 TEXT,
    text_description TEXT,
    is_fake BOOLEAN,
    veracity_score FLOAT,
    status TEXT DEFAULT 'Pending Validation',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);
