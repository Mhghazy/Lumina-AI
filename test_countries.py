from supabase import create_client
import os

# Initialize Supabase
supabase = create_client(
    "https://wifxcwzyikwseouoxvwb.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndpZnhjd3p5aWt3c2VvdW94dndpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mjg3MjYyNDEsImV4cCI6MjA0NDMwMjI0MX0.kgG_3pqfGVKCqAUiZRCMh0-S-K4h7WtZAM7hR6z3Vhc"
)

# Get all unique countries
response = supabase.table('global_code_duplicate1').select('country').execute()
countries = set([row['country'] for row in response.data if row.get('country')])

print(f"\n📊 Total unique countries in database: {len(countries)}\n")
print("🌍 All countries:")
for country in sorted(countries):
    print(f"   • {country}")

# Test search for Germany
print("\n\n🔍 Testing search for 'Germany'...")
response = supabase.table('global_code_duplicate1').select("*").ilike('country', '%Germany%').execute()
print(f"Found {len(response.data)} vendors from Germany")

# Test universal search
print("\n\n🔍 Testing universal search for 'germany'...")
response = supabase.table('global_code_duplicate1').select("*").execute()
all_data = response.data
query_lower = "germany"
filtered_data = []

for row in all_data:
    match_found = False
    for key, value in row.items():
        if value and query_lower in str(value).lower():
            match_found = True
            break
    if match_found:
        filtered_data.append(row)

print(f"Found {len(filtered_data)} vendors with 'germany' in any column")
if filtered_data:
    print("First result:")
    print(f"   Name: {filtered_data[0].get('name')}")
    print(f"   Country: {filtered_data[0].get('country')}")
