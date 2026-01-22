from supabase import create_client

# Initialize Supabase
supabase = create_client(
    "https://wifxcwzyikwseouoxvwb.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndpZnhjd3p5aWt3c2VvdW94dndiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDA0MDUzNjIsImV4cCI6MjA1NTk4MTM2Mn0.uf5HOh9CDq12U9CuIMMQEeS42b5eMvyWx3bRhrAcBa4"
)

print("🔍 Fetching sample data from database...\n")

# Get one row to see all columns
response = supabase.table('global_code_duplicate1').select("*").limit(1).execute()

if response.data:
    sample = response.data[0]
    print("📊 Available columns in database:")
    print("="*60)
    for key, value in sample.items():
        print(f"   • {key}: {value}")
    print("="*60)
    
    print("\n📋 All column names:")
    print(list(sample.keys()))
else:
    print("❌ No data found in database")

# Test color search
print("\n\n🎨 Testing Red color search...")
response = supabase.table('global_code_duplicate1').select("*").ilike('color_name', '%red%').limit(3).execute()
print(f"Found {len(response.data)} red vendors:")
for vendor in response.data:
    print(f"   • {vendor}")
