/*
  # Create Database Tables for I.T.S-Group

  1. New Tables
    - `clients`
      - `id` (bigserial, primary key)
      - `name` (text)
      - `phone` (text)
      - `company` (text)
      - `category` (text)
      - `website` (text)
      - `email` (text)
      - `registration_date` (date, defaults to today)
      - `created_at` (timestamptz, defaults to now)
    
    - `hot_vendors`
      - `id` (bigserial, primary key)
      - `vendor_name` (text)
      - `contact_person` (text)
      - `phone` (text)
      - `email` (text)
      - `category` (text)
      - `rating` (numeric)
      - `status` (text)
      - `created_at` (timestamptz, defaults to now)
    
    - `global_code` (vendors)
      - `id` (bigserial, primary key)
      - `company` (text)
      - `country` (text)
      - `color_name` (text)
      - `color_hex` (text)
      - `product_code` (text)
      - `description` (text)
      - `created_at` (timestamptz, defaults to now)

  2. Security
    - Enable RLS on all tables
    - Add policies for public access (as per original design)
*/

-- Create clients table
CREATE TABLE IF NOT EXISTS clients (
  id bigserial PRIMARY KEY,
  name text DEFAULT '',
  phone text DEFAULT '',
  company text DEFAULT '',
  category text DEFAULT '',
  website text DEFAULT '',
  email text DEFAULT '',
  registration_date date DEFAULT CURRENT_DATE,
  created_at timestamptz DEFAULT now()
);

-- Create hot_vendors table
CREATE TABLE IF NOT EXISTS hot_vendors (
  id bigserial PRIMARY KEY,
  vendor_name text DEFAULT '',
  contact_person text DEFAULT '',
  phone text DEFAULT '',
  email text DEFAULT '',
  category text DEFAULT '',
  rating numeric DEFAULT 0,
  status text DEFAULT 'active',
  created_at timestamptz DEFAULT now()
);

-- Create global_code table (vendors)
CREATE TABLE IF NOT EXISTS global_code (
  id bigserial PRIMARY KEY,
  company text DEFAULT '',
  country text DEFAULT '',
  color_name text DEFAULT '',
  color_hex text DEFAULT '',
  product_code text DEFAULT '',
  description text DEFAULT '',
  created_at timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE hot_vendors ENABLE ROW LEVEL SECURITY;
ALTER TABLE global_code ENABLE ROW LEVEL SECURITY;

-- Create policies for public access (matching original design)
CREATE POLICY "Allow public read access on clients"
  ON clients FOR SELECT
  TO anon, authenticated
  USING (true);

CREATE POLICY "Allow public insert on clients"
  ON clients FOR INSERT
  TO anon, authenticated
  WITH CHECK (true);

CREATE POLICY "Allow public update on clients"
  ON clients FOR UPDATE
  TO anon, authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow public delete on clients"
  ON clients FOR DELETE
  TO anon, authenticated
  USING (true);

CREATE POLICY "Allow public read access on hot_vendors"
  ON hot_vendors FOR SELECT
  TO anon, authenticated
  USING (true);

CREATE POLICY "Allow public insert on hot_vendors"
  ON hot_vendors FOR INSERT
  TO anon, authenticated
  WITH CHECK (true);

CREATE POLICY "Allow public update on hot_vendors"
  ON hot_vendors FOR UPDATE
  TO anon, authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow public delete on hot_vendors"
  ON hot_vendors FOR DELETE
  TO anon, authenticated
  USING (true);

CREATE POLICY "Allow public read access on global_code"
  ON global_code FOR SELECT
  TO anon, authenticated
  USING (true);

CREATE POLICY "Allow public insert on global_code"
  ON global_code FOR INSERT
  TO anon, authenticated
  WITH CHECK (true);

CREATE POLICY "Allow public update on global_code"
  ON global_code FOR UPDATE
  TO anon, authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow public delete on global_code"
  ON global_code FOR DELETE
  TO anon, authenticated
  USING (true);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_clients_category ON clients(category);
CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);
CREATE INDEX IF NOT EXISTS idx_hot_vendors_category ON hot_vendors(category);
CREATE INDEX IF NOT EXISTS idx_global_code_company ON global_code(company);
CREATE INDEX IF NOT EXISTS idx_global_code_country ON global_code(country);