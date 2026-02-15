import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import time

# Page config
st.set_page_config(
    page_title="Daily Log - Vinaysa Infra",
    page_icon="🚛",
    layout="wide"
)

# Cache TTL (Time To Live) - refresh master data every 5 minutes
CACHE_TTL = 300

# Google Sheets Setup
@st.cache_resource
def get_google_sheets_client():
    """Connect to Google Sheets using service account credentials"""
    try:
        # Credentials from Streamlit secrets
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds_dict = {
            "type": st.secrets["gcp_service_account"]["type"],
            "project_id": st.secrets["gcp_service_account"]["project_id"],
            "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
            "private_key": st.secrets["gcp_service_account"]["private_key"],
            "client_email": st.secrets["gcp_service_account"]["client_email"],
            "client_id": st.secrets["gcp_service_account"]["client_id"],
            "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
            "token_uri": st.secrets["gcp_service_account"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
        }
        
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {str(e)}")
        return None

def get_worksheet(sheet_name="Daily_Logs"):
    """Get or create worksheet"""
    try:
        client = get_google_sheets_client()
        if client is None:
            return None
            
        # Open the spreadsheet by name (will create if doesn't exist)
        spreadsheet_name = "Vinaysa_Infra_Daily_Log"
        
        try:
            spreadsheet = client.open(spreadsheet_name)
        except gspread.SpreadsheetNotFound:
            st.error(f"Spreadsheet '{spreadsheet_name}' not found. Please create it first.")
            return None
        
        # Try to get the worksheet, create if doesn't exist
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
            # Add headers
            headers = [
                "Timestamp", "Date of Activity", "Vehicle Idle?", "Idle Reason", 
                "Idle Notes", "Project Site", "Vehicle Name", 
                "Driver/Operator Name", "Diesel Cost (₹)", "Work Description", 
                "Work Amount (₹)", "Payment Received (₹)", 
                "Maintenance Done?", "Maintenance Items", 
                "Total Maintenance Cost (₹)", "Driver/Operator Payment (₹)", 
                "Driver Name for Payment"
            ]
            worksheet.append_row(headers)
        
        return worksheet
    except Exception as e:
        st.error(f"Error accessing worksheet: {str(e)}")
        return None

def get_unique_projects():
    """Get list of unique project sites from existing data"""
    try:
        worksheet = get_worksheet()
        if worksheet is None:
            return []
        
        # Get all records
        records = worksheet.get_all_records()
        if not records:
            return []
        
        # Extract unique project sites (column index 2, after Timestamp and Date)
        projects = set()
        for record in records:
            project = record.get("Project Site", "").strip()
            if project:
                projects.add(project)
        
        return sorted(list(projects))
    except Exception as e:
        st.error(f"Error fetching projects: {str(e)}")
        return []

@st.cache_data(ttl=CACHE_TTL)
def get_master_vehicles():
    """Get active vehicles from Master_Vehicles sheet"""
    try:
        client = get_google_sheets_client()
        if client is None:
            return []
        
        spreadsheet_name = "Vinaysa_Infra_Daily_Log"
        spreadsheet = client.open(spreadsheet_name)
        
        try:
            worksheet = spreadsheet.worksheet("Master_Vehicles")
            records = worksheet.get_all_records()
            
            # Filter only active vehicles and return vehicle names
            vehicles = []
            for record in records:
                status = record.get("Status", "").strip().lower()
                vehicle_name = record.get("Vehicle Name", "").strip()
                if status == "active" and vehicle_name:
                    vehicles.append(vehicle_name)
            
            return sorted(vehicles)
        except gspread.WorksheetNotFound:
            # Return default vehicles if master sheet doesn't exist yet
            return [
                "Old Tipper CG15 EJ 3598 (Ginni)",
                "JCB Backhoe Loader",
                "Mahindra Backhoe Loader",
                "New Tipper CG15 EK 3598 (Siyaram)"
            ]
    except Exception as e:
        st.error(f"Error fetching vehicles: {str(e)}")
        return []

@st.cache_data(ttl=CACHE_TTL)
def get_master_drivers():
    """Get active drivers from Master_Drivers sheet"""
    try:
        client = get_google_sheets_client()
        if client is None:
            return []
        
        spreadsheet_name = "Vinaysa_Infra_Daily_Log"
        spreadsheet = client.open(spreadsheet_name)
        
        try:
            worksheet = spreadsheet.worksheet("Master_Drivers")
            records = worksheet.get_all_records()
            
            # Filter only active drivers and return driver names
            drivers = []
            for record in records:
                status = record.get("Status", "").strip().lower()
                driver_name = record.get("Driver Name", "").strip()
                if status == "active" and driver_name:
                    drivers.append(driver_name)
            
            return sorted(drivers)
        except gspread.WorksheetNotFound:
            # Return default drivers if master sheet doesn't exist yet
            return ["Girish Lal", "Virender", "Siya Ram", "Gini Paikra"]
    except Exception as e:
        st.error(f"Error fetching drivers: {str(e)}")
        return []

def save_to_sheets(data):
    """Save form data to Google Sheets"""
    try:
        worksheet = get_worksheet()
        if worksheet is None:
            return False
        
        # Prepare row data
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp
            data["date"].strftime("%Y-%m-%d"),  # Date of Activity
            "Yes" if data.get("vehicle_idle", False) else "No",  # Vehicle Idle?
            data.get("idle_reason", ""),  # Idle Reason
            data.get("idle_notes", ""),  # Idle Notes
            data["project_site"],
            data["vehicle"],
            data["driver"],
            data["diesel_cost"],
            data["work_description"],
            data["work_amount"],
            data["payment_received"],
            data["has_maintenance"],
            data.get("maintenance_summary", ""),  # Maintenance Items (formatted)
            data.get("total_maintenance_cost", 0),  # Total Maintenance Cost
            data.get("driver_payment", 0),
            data.get("driver_name_payment", "N/A")
        ]
        
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Error saving to sheets: {str(e)}")
        return False

# Main App
st.title("🚛 Daily Log Book - Vinaysa Infra")
st.markdown("*Log daily activities and associated costs for operational tracking.*")
st.divider()

# Get master data
existing_projects = get_unique_projects()
master_vehicles = get_master_vehicles()
master_drivers = get_master_drivers()

# Show info if master data is being used
if master_vehicles and master_drivers:
    with st.expander("ℹ️ Master Data Info"):
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.info(f"📋 **{len(master_vehicles)} Active Vehicles** loaded from Master_Vehicles sheet")
        with col_info2:
            st.info(f"👷 **{len(master_drivers)} Active Drivers** loaded from Master_Drivers sheet")
        st.caption("💡 Tip: Add new vehicles/drivers in the Master sheets - they'll appear here automatically!")

# Form
with st.form("daily_log_form", clear_on_submit=True):
    st.subheader("📋 Activity Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        date_activity = st.date_input(
            "Date of Activity *",
            value=datetime.now(),
            help="Select the date of the activity"
        )
    
    with col2:
        # Idle vehicle checkbox
        vehicle_idle = st.checkbox(
            "🛑 Vehicle Idle Today (No Work)",
            help="Check if vehicle was idle/not working today"
        )
    
    st.divider()
    
    # Show project site only if NOT idle
    if not vehicle_idle:
        # Project site with autocomplete
        if existing_projects:
            project_site = st.selectbox(
                "Project Site *",
                options=[""] + existing_projects + ["+ Add New Project"],
                help="Select existing project or add new one"
            )
            
            if project_site == "+ Add New Project":
                project_site = st.text_input(
                    "Enter New Project Site Name *",
                    placeholder="e.g., Residential Complex - Raipur"
                )
        else:
            project_site = st.text_input(
                "Project Site *",
                placeholder="e.g., Residential Complex - Raipur",
                help="Enter the project site name"
            )
    else:
        project_site = "N/A - Vehicle Idle"
    
    col3, col4 = st.columns(2)
    
    with col3:
        # Dynamic vehicle dropdown from Master_Vehicles
        vehicle = st.selectbox(
            "Vehicle Name *",
            options=[""] + master_vehicles,
            help="Select the vehicle used (managed in Master_Vehicles sheet)"
        )
    
    with col4:
        # Dynamic driver dropdown from Master_Drivers
        driver = st.selectbox(
            "Driver/Operator Name" + (" *" if not vehicle_idle else ""),
            options=[""] + master_drivers,
            help="Select the driver or operator (managed in Master_Drivers sheet)" + (" - Optional for idle vehicles" if vehicle_idle else "")
        )
    
    # If vehicle is idle, show idle-specific fields
    idle_reason = ""
    idle_reason_other = ""
    idle_notes = ""
    
    if vehicle_idle:
        st.divider()
        st.subheader("🛑 Idle Vehicle Details")
        
        col_idle1, col_idle2 = st.columns(2)
        
        with col_idle1:
            idle_reason = st.selectbox(
                "Idle Reason *",
                options=[
                    "",
                    "Under Maintenance/Repair",
                    "No Project Assigned",
                    "Weather/Rain",
                    "Driver Absent",
                    "Waiting for Parts",
                    "Permit/Documentation Issues",
                    "Scheduled Rest",
                    "Other"
                ],
                help="Why was the vehicle idle?"
            )
        
        with col_idle2:
            if idle_reason == "Other":
                idle_reason_other = st.text_input(
                    "Specify Reason *",
                    placeholder="e.g., Festival holiday"
                )
        
        idle_notes = st.text_area(
            "Additional Notes",
            placeholder="Any additional details about why vehicle was idle...",
            help="Optional - add any relevant details"
        )
    
    st.divider()
    st.subheader("💰 Cost Details")
    
    col5, col6, col7 = st.columns(3)
    
    with col5:
        diesel_cost = st.number_input(
            "Diesel Cost (₹)" + (" *" if not vehicle_idle else ""),
            min_value=0.0,
            step=100.0,
            format="%.2f",
            help="Enter diesel cost in rupees" + (" (0 if no diesel purchased)" if vehicle_idle else "")
        )
    
    # Show work amount and payment only if NOT idle
    if not vehicle_idle:
        with col6:
            work_amount = st.number_input(
                "Work Amount (₹) *",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                help="Enter work amount in rupees"
            )
        
        with col7:
            payment_received = st.number_input(
                "Payment Received (₹) *",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                help="Enter payment received in rupees"
            )
        
        work_description = st.text_area(
            "Work Description *",
            placeholder="Describe the work performed...",
            help="Provide detailed description of work"
        )
    else:
        # Set defaults for idle vehicles
        work_amount = 0.0
        payment_received = 0.0
        final_idle_reason = idle_reason_other if idle_reason == "Other" else idle_reason
        work_description = f"Vehicle Idle - {final_idle_reason if final_idle_reason else 'No Work'}"
    
    st.divider()
    st.subheader("🔧 Maintenance & Expenses")
    
    # Predefined maintenance types
    maintenance_types = [
        "Servicing",
        "Urea Refuel", 
        "Welding",
        "Hydraulic Oil",
        "Grease",
        "Pipe",
        "Tax",
        "Mobil",
        "Repair (Datta)",
        "Transmission Oil",
        "Washing",
        "Other"
    ]
    
    has_maintenance = st.radio(
        "Any Maintenance/Expenses Today? *",
        options=["No", "Yes"],
        horizontal=True,
        help="Select Yes if there were any maintenance work or expenses"
    )
    
    # Initialize maintenance data structures
    maintenance_items = []
    maintenance_costs = {}
    maintenance_other_text = ""
    driver_payment = 0.0
    driver_name_payment = ""
    
    if has_maintenance == "Yes":
        st.markdown("**Select Maintenance Type(s) and Enter Costs**")
        st.caption("💡 You can select multiple items")
        
        # Use multiselect for maintenance types
        selected_maintenance = st.multiselect(
            "Maintenance Type(s)",
            options=maintenance_types,
            help="Select all maintenance types that were done today"
        )
        
        # Show cost inputs for selected maintenance types
        if selected_maintenance:
            st.markdown("**Enter Cost for Each Item:**")
            
            # Create two columns for better layout
            cols_per_row = 2
            for i in range(0, len(selected_maintenance), cols_per_row):
                cols = st.columns(cols_per_row)
                
                for j, col in enumerate(cols):
                    idx = i + j
                    if idx < len(selected_maintenance):
                        mtype = selected_maintenance[idx]
                        
                        with col:
                            # Special handling for "Other"
                            if mtype == "Other":
                                maintenance_other_text = st.text_input(
                                    "Specify Other Maintenance",
                                    placeholder="e.g., Tire replacement",
                                    key=f"other_desc"
                                )
                                cost = st.number_input(
                                    f"Cost (₹)",
                                    min_value=0.0,
                                    step=100.0,
                                    format="%.2f",
                                    key=f"cost_other",
                                    help=f"Enter cost for {maintenance_other_text if maintenance_other_text else 'other maintenance'}"
                                )
                            else:
                                cost = st.number_input(
                                    f"{mtype} Cost (₹)",
                                    min_value=0.0,
                                    step=100.0,
                                    format="%.2f",
                                    key=f"cost_{mtype}",
                                    help=f"Enter cost for {mtype}"
                                )
                            
                            if cost > 0:
                                if mtype == "Other" and maintenance_other_text:
                                    maintenance_costs[maintenance_other_text] = cost
                                    maintenance_items.append(f"{maintenance_other_text}: ₹{cost:,.2f}")
                                elif mtype != "Other":
                                    maintenance_costs[mtype] = cost
                                    maintenance_items.append(f"{mtype}: ₹{cost:,.2f}")
        
        st.divider()
        st.markdown("**Driver Payment (if any)**")
        
        col_driver1, col_driver2 = st.columns(2)
        
        with col_driver1:
            driver_payment = st.number_input(
                "Driver/Operator Payment (₹)",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                help="Payment made to driver/operator today"
            )
        
        with col_driver2:
            if driver_payment > 0:
                driver_name_payment = st.selectbox(
                    "Driver/Operator Name",
                    options=[""] + master_drivers,
                    help="Select driver who received payment"
                )
    
    st.divider()
    
    # Show summary if maintenance items selected
    if has_maintenance == "Yes" and (maintenance_items or driver_payment > 0):
        with st.expander("📋 **Expense Summary**", expanded=True):
            col_sum1, col_sum2 = st.columns(2)
            
            with col_sum1:
                if maintenance_items:
                    st.markdown("**Maintenance Items:**")
                    for item in maintenance_items:
                        st.markdown(f"• {item}")
                    st.markdown(f"**Total Maintenance: ₹{sum(maintenance_costs.values()):,.2f}**")
            
            with col_sum2:
                if driver_payment > 0:
                    st.markdown("**Driver Payment:**")
                    st.markdown(f"• {driver_name_payment if driver_name_payment else 'Driver'}: ₹{driver_payment:,.2f}")
            
            # Grand total
            grand_total = sum(maintenance_costs.values()) + driver_payment
            if grand_total > 0:
                st.markdown(f"### 💰 Total Expenses Today: ₹{grand_total:,.2f}")
    
    # Submit button
    submitted = st.form_submit_button("✅ Submit Entry", use_container_width=True, type="primary")
    
    if submitted:
        # Validation
        errors = []
        
        # Common validations (for both idle and working)
        if not vehicle:
            errors.append("Vehicle Name is required")
        
        # Idle-specific validations
        if vehicle_idle:
            if not idle_reason or idle_reason == "":
                errors.append("Idle Reason is required when vehicle is idle")
            if idle_reason == "Other" and not idle_reason_other:
                errors.append("Please specify the idle reason")
        # Working vehicle validations
        else:
            if not project_site or project_site == "":
                errors.append("Project Site is required")
            if not driver:
                errors.append("Driver/Operator Name is required")
            if diesel_cost <= 0:
                errors.append("Diesel Cost must be greater than 0")
            if not work_description.strip():
                errors.append("Work Description is required")
        
        if errors:
            for error in errors:
                st.error(f"❌ {error}")
        else:
            # Calculate total maintenance cost
            total_maintenance_cost = sum(maintenance_costs.values()) if maintenance_costs else 0.0
            
            # Create maintenance summary
            maintenance_summary = "; ".join(maintenance_items) if maintenance_items else ""
            
            # Prepare data
            form_data = {
                "date": date_activity,
                "vehicle_idle": vehicle_idle,
                "project_site": project_site,
                "vehicle": vehicle,
                "driver": driver if driver else "N/A",
                "diesel_cost": diesel_cost,
                "work_description": work_description,
                "work_amount": work_amount,
                "payment_received": payment_received,
                "has_maintenance": has_maintenance,
                "maintenance_items": maintenance_items,
                "maintenance_summary": maintenance_summary,
                "total_maintenance_cost": total_maintenance_cost,
                "driver_payment": driver_payment,
                "driver_name_payment": driver_name_payment if driver_name_payment else "N/A"
            }
            
            # Add idle-specific fields
            if vehicle_idle:
                final_idle_reason = idle_reason_other if idle_reason == "Other" else idle_reason
                form_data["idle_reason"] = final_idle_reason
                form_data["idle_notes"] = idle_notes
            else:
                form_data["idle_reason"] = ""
                form_data["idle_notes"] = ""
            
            # Save to Google Sheets
            with st.spinner("Saving data..."):
                if save_to_sheets(form_data):
                    st.success("✅ Entry saved successfully!")
                    st.balloons()
                    # Clear cache to refresh project list
                    get_unique_projects.clear()
                else:
                    st.error("❌ Failed to save entry. Please try again.")

# Footer
st.divider()

# Manual refresh button for master data
col_footer1, col_footer2, col_footer3 = st.columns([2, 1, 2])
with col_footer2:
    if st.button("🔄 Refresh Master Data", help="Reload vehicles and drivers from sheets"):
        get_master_vehicles.clear()
        get_master_drivers.clear()
        st.success("✅ Master data refreshed!")
        st.rerun()

st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <small>Vinaysa Infra Daily Log Book | Data stored securely in Google Sheets<br>
    Master data auto-refreshes every 5 minutes | Manage vehicles/drivers in Master sheets</small>
</div>
""", unsafe_allow_html=True)
