"""
Setup Master Sheets for Vinaysa Infra Daily Log
This script creates and populates Master_Vehicles and Master_Drivers sheets
"""

import gspread
from google.oauth2.service_account import Credentials
import sys

def get_credentials():
    """Get Google Sheets credentials"""
    print("📋 Setting up credentials...")
    
    # You can either:
    # 1. Use secrets.toml if running from Streamlit
    # 2. Use credentials.json file
    
    try:
        # Try loading from credentials.json first
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_file(
            'credentials.json',
            scopes=scopes
        )
        return credentials
    except FileNotFoundError:
        print("❌ credentials.json not found!")
        print("💡 Please place your credentials.json file in the same folder as this script")
        sys.exit(1)

def setup_master_vehicles(spreadsheet):
    """Create and populate Master_Vehicles sheet"""
    print("\n🚛 Setting up Master_Vehicles sheet...")
    
    try:
        # Try to get existing worksheet
        worksheet = spreadsheet.worksheet("Master_Vehicles")
        print("   ⚠️  Master_Vehicles sheet already exists")
        
        response = input("   Do you want to recreate it? (y/n): ").lower()
        if response != 'y':
            print("   ⏭️  Skipping Master_Vehicles")
            return
        
        # Delete and recreate
        spreadsheet.del_worksheet(worksheet)
        print("   🗑️  Deleted existing sheet")
    except gspread.WorksheetNotFound:
        pass
    
    # Create new worksheet
    worksheet = spreadsheet.add_worksheet(title="Master_Vehicles", rows=100, cols=10)
    
    # Add headers
    headers = [
        "Vehicle ID",
        "Vehicle Name",
        "Registration Number",
        "Vehicle Type",
        "Status",
        "Date Added",
        "Notes"
    ]
    worksheet.append_row(headers)
    
    # Add default vehicles
    default_vehicles = [
        ["V001", "Old Tipper CG15 EJ 3598 (Ginni)", "CG15EJ3598", "Tipper", "Active", "2024-01-01", ""],
        ["V002", "JCB Backhoe Loader", "-", "Backhoe Loader", "Active", "2024-01-01", ""],
        ["V003", "Mahindra Backhoe Loader", "-", "Backhoe Loader", "Active", "2024-01-01", ""],
        ["V004", "New Tipper CG15 EK 3598 (Siyaram)", "CG15EK3598", "Tipper", "Active", "2024-01-01", ""]
    ]
    
    for vehicle in default_vehicles:
        worksheet.append_row(vehicle)
    
    # Format header row
    worksheet.format('A1:G1', {
        "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
    })
    
    print("   ✅ Master_Vehicles sheet created with 4 default vehicles")

def setup_master_drivers(spreadsheet):
    """Create and populate Master_Drivers sheet"""
    print("\n👷 Setting up Master_Drivers sheet...")
    
    try:
        # Try to get existing worksheet
        worksheet = spreadsheet.worksheet("Master_Drivers")
        print("   ⚠️  Master_Drivers sheet already exists")
        
        response = input("   Do you want to recreate it? (y/n): ").lower()
        if response != 'y':
            print("   ⏭️  Skipping Master_Drivers")
            return
        
        # Delete and recreate
        spreadsheet.del_worksheet(worksheet)
        print("   🗑️  Deleted existing sheet")
    except gspread.WorksheetNotFound:
        pass
    
    # Create new worksheet
    worksheet = spreadsheet.add_worksheet(title="Master_Drivers", rows=100, cols=10)
    
    # Add headers
    headers = [
        "Driver ID",
        "Driver Name",
        "Phone Number",
        "Status",
        "Date Added",
        "Notes"
    ]
    worksheet.append_row(headers)
    
    # Add default drivers
    default_drivers = [
        ["D001", "Girish Lal", "9876543210", "Active", "2024-01-01", ""],
        ["D002", "Virender", "9876543211", "Active", "2024-01-01", ""],
        ["D003", "Siya Ram", "9876543212", "Active", "2024-01-01", ""],
        ["D004", "Gini Paikra", "9876543213", "Active", "2024-01-01", ""]
    ]
    
    for driver in default_drivers:
        worksheet.append_row(driver)
    
    # Format header row
    worksheet.format('A1:F1', {
        "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 0.4},
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
    })
    
    print("   ✅ Master_Drivers sheet created with 4 default drivers")

def main():
    """Main setup function"""
    print("\n" + "="*60)
    print("🚀 Vinaysa Infra Daily Log - Master Sheets Setup")
    print("="*60)
    
    # Get credentials
    credentials = get_credentials()
    client = gspread.authorize(credentials)
    
    # Open spreadsheet
    spreadsheet_name = "Vinaysa_Infra_Daily_Log"
    print(f"\n📊 Opening spreadsheet: {spreadsheet_name}")
    
    try:
        spreadsheet = client.open(spreadsheet_name)
        print(f"   ✅ Spreadsheet found!")
    except gspread.SpreadsheetNotFound:
        print(f"   ❌ Spreadsheet '{spreadsheet_name}' not found!")
        print(f"   💡 Please create a Google Sheet named '{spreadsheet_name}' first")
        sys.exit(1)
    
    # Setup master sheets
    setup_master_vehicles(spreadsheet)
    setup_master_drivers(spreadsheet)
    
    print("\n" + "="*60)
    print("✨ Setup Complete!")
    print("="*60)
    print("\n📝 Next Steps:")
    print("   1. Open your Google Sheet and verify the Master_Vehicles and Master_Drivers sheets")
    print("   2. To add new vehicles/drivers, simply add rows to these sheets")
    print("   3. Set Status to 'Active' for items to appear in the app")
    print("   4. Set Status to 'Inactive' to hide items without deleting")
    print("   5. Run your Streamlit app: streamlit run app.py")
    print("\n💡 Tips:")
    print("   - Vehicle Name and Driver Name are what appears in dropdowns")
    print("   - Changes reflect in the app within 5 minutes (auto-refresh)")
    print("   - Use the 'Refresh Master Data' button in app for instant updates")
    print("\n")

if __name__ == "__main__":
    main()
