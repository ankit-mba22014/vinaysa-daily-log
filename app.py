import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd

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
            
        # Open the spreadsheet by name
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
        
        # Extract unique project sites
        projects = set()
        for record in records:
            project = record.get("Project Site", "").strip()
            if project and project != "N/A - Vehicle Idle":
                projects.add(project)
        
        return sorted(list(projects))
    except Exception as e:
        st.error(f"Error fetching projects: {str(e)}")
        return []

@st.cache_data(ttl=CACHE_TTL)
def get_master_vehicles():
    """Get active vehicles from Master_Vehicles sheet with default drivers"""
    try:
        client = get_google_sheets_client()
        if client is None:
            return []
        
        spreadsheet_name = "Vinaysa_Infra_Daily_Log"
        spreadsheet = client.open(spreadsheet_name)
        
        try:
            worksheet = spreadsheet.worksheet("Master_Vehicles")
            records = worksheet.get_all_records()
            
            # Return vehicle data with default driver
            vehicles = []
            for record in records:
                status = record.get("Status", "").strip().lower()
                vehicle_name = record.get("Vehicle Name", "").strip()
                default_driver = record.get("Default Driver", "").strip()
                
                if status == "active" and vehicle_name:
                    vehicles.append({
                        "name": vehicle_name,
                        "default_driver": default_driver if default_driver else ""
                    })
            
            return vehicles
        except gspread.WorksheetNotFound:
            # Return default vehicles if master sheet doesn't exist yet
            return [
                {"name": "Old Tipper CG15 EJ 3598 (Ginni)", "default_driver": "Girish Lal"},
                {"name": "JCB Backhoe Loader", "default_driver": "Virender"},
                {"name": "Mahindra Backhoe Loader", "default_driver": "Siya Ram"},
                {"name": "New Tipper CG15 EK 3598 (Siyaram)", "default_driver": "Siya Ram"}
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

def save_vehicle_entry(date, vehicle_data):
    """Save single vehicle entry to Google Sheets"""
    try:
        worksheet = get_worksheet()
        if worksheet is None:
            return False
        
        # Prepare row data
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp
            date.strftime("%Y-%m-%d"),  # Date of Activity
            "Yes" if vehicle_data.get("is_idle", False) else "No",  # Vehicle Idle?
            vehicle_data.get("idle_reason", ""),  # Idle Reason
            vehicle_data.get("idle_notes", ""),  # Idle Notes
            vehicle_data.get("project_site", ""),
            vehicle_data.get("vehicle_name", ""),
            vehicle_data.get("driver", "N/A"),
            vehicle_data.get("diesel_cost", 0),
            vehicle_data.get("work_description", ""),
            vehicle_data.get("work_amount", 0),
            vehicle_data.get("payment_received", 0),
            vehicle_data.get("has_maintenance", "No"),
            vehicle_data.get("maintenance_summary", ""),
            vehicle_data.get("total_maintenance_cost", 0),
            vehicle_data.get("driver_payment", 0),
            vehicle_data.get("driver_name_payment", "N/A")
        ]
        
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Error saving entry for {vehicle_data.get('vehicle_name')}: {str(e)}")
        return False

# Main App
st.title("🚛 Daily Log Book - Vinaysa Infra")
st.markdown("*Multi-vehicle daily log - fill all vehicles in one go!*")
st.divider()

# Get master data
existing_projects = get_unique_projects()
master_vehicles = get_master_vehicles()
master_drivers = get_master_drivers()

# Maintenance types
MAINTENANCE_TYPES = [
    "Servicing", "Urea Refuel", "Welding", "Hydraulic Oil", "Grease",
    "Pipe", "Tax", "Mobil", "Repair (Datta)", "Transmission Oil", "Washing", "Other"
]

IDLE_REASONS = [
    "Under Maintenance/Repair", "No Project Assigned", "Weather/Rain",
    "Driver Absent", "Waiting for Parts", "Permit/Documentation Issues",
    "Scheduled Rest", "Other"
]

# Form
with st.form("multi_vehicle_log_form", clear_on_submit=True):
    
    # Date
    st.subheader("📅 Date")
    date_activity = st.date_input(
        "Date of Activity",
        value=datetime.now(),
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # Default Project and Description
    st.subheader("🏗️ Default Values (Optional)")
    st.caption("💡 Set these to auto-fill all vehicles. You can edit per vehicle if needed.")
    
    col_default1, col_default2 = st.columns(2)
    
    with col_default1:
        if existing_projects:
            default_project_type = st.radio(
                "Project Selection",
                options=["Select existing", "Enter new"],
                horizontal=True,
                label_visibility="collapsed",
                key="default_project_type"
            )
            
            if default_project_type == "Select existing":
                default_project = st.selectbox(
                    "Default Project Site",
                    options=[""] + existing_projects,
                    help="Will auto-fill all vehicles"
                )
            else:
                default_project = st.text_input(
                    "Default Project Site",
                    placeholder="e.g., Highway NH-30 Extension",
                    help="Will auto-fill all vehicles"
                )
        else:
            default_project = st.text_input(
                "Default Project Site",
                placeholder="e.g., Highway NH-30 Extension",
                help="Will auto-fill all vehicles"
            )
    
    with col_default2:
        default_description = st.text_area(
            "Default Work Description",
            placeholder="e.g., Excavation and material transport",
            help="Will auto-fill all vehicles",
            height=100
        )
    
    st.divider()
    
    # Vehicle Cards
    st.subheader("🚛 Vehicle Entries")
    st.caption(f"📋 {len(master_vehicles)} vehicles loaded. Expand cards to fill details.")
    
    for idx, vehicle in enumerate(master_vehicles):
        vehicle_name = vehicle["name"]
        default_driver = vehicle.get("default_driver", "")
        
        with st.expander(f"🚛 **{vehicle_name}**", expanded=False):
            
            # Vehicle idle checkbox
            vehicle_idle = st.checkbox(
                "🛑 Vehicle Idle",
                key=f"idle_{idx}",
                help="Check if vehicle was idle/not working today"
            )
            
            # If vehicle is idle, show idle-specific fields
            if vehicle_idle:
                st.markdown("**🛑 Idle Vehicle Details**")
                
                idle_reason = st.selectbox(
                    "Idle Reason *",
                    options=[""] + IDLE_REASONS,
                    key=f"idle_reason_{idx}"
                )
                
                if idle_reason == "Other":
                    idle_reason_other = st.text_input(
                        "Specify Reason *",
                        key=f"idle_reason_other_{idx}",
                        placeholder="e.g., Festival holiday"
                    )
                else:
                    idle_reason_other = ""
                
                idle_notes = st.text_area(
                    "Idle Notes (optional)",
                    key=f"idle_notes_{idx}",
                    placeholder="Additional details...",
                    height=80
                )
                
                # Project and description greyed out (disabled)
                st.markdown("**🏗️ Project Site** (N/A - Vehicle Idle)")
                st.text_input(
                    "Project (disabled)",
                    value="N/A - Vehicle Idle",
                    disabled=True,
                    key=f"idle_project_{idx}",
                    label_visibility="collapsed"
                )
                
                st.markdown("**📝 Work Description** (N/A - Vehicle Idle)")
                st.text_area(
                    "Description (disabled)",
                    value=f"Vehicle Idle - {idle_reason if idle_reason and idle_reason != 'Other' else idle_reason_other}",
                    disabled=True,
                    key=f"idle_desc_{idx}",
                    label_visibility="collapsed",
                    height=80
                )
                
                col_idle1, col_idle2 = st.columns(2)
                with col_idle1:
                    idle_diesel = st.number_input(
                        "Diesel Cost (₹)",
                        min_value=0.0,
                        step=100.0,
                        key=f"idle_diesel_{idx}",
                        help="Optional - if diesel purchased"
                    )
                
                with col_idle2:
                    idle_maintenance = st.number_input(
                        "Maintenance Cost (₹)",
                        min_value=0.0,
                        step=100.0,
                        key=f"idle_maintenance_{idx}",
                        help="Optional - if maintenance done"
                    )
            
            else:
                # Working vehicle fields
                st.markdown("**👷 Working Vehicle Details**")
                
                # Driver
                driver_idx = master_drivers.index(default_driver) + 1 if default_driver in master_drivers else 0
                driver = st.selectbox(
                    "Driver/Operator",
                    options=[""] + master_drivers,
                    index=driver_idx,
                    key=f"driver_{idx}",
                    help="Pre-filled with default driver"
                )
                
                # Project (auto-populated with default)
                st.markdown("**🏗️ Project Site**")
                vehicle_project = st.text_input(
                    "Project",
                    value=default_project if default_project else "",
                    key=f"project_{idx}",
                    placeholder="Enter project name (or use default above)",
                    label_visibility="collapsed"
                )
                
                # Description (auto-populated with default)
                st.markdown("**📝 Work Description**")
                vehicle_description = st.text_area(
                    "Description",
                    value=default_description if default_description else "",
                    key=f"description_{idx}",
                    placeholder="Describe work performed (or use default above)",
                    height=100,
                    label_visibility="collapsed"
                )
                
                # Costs
                st.markdown("**💰 Costs**")
                col1, col2 = st.columns(2)
                
                with col1:
                    diesel_cost = st.number_input(
                        "Diesel Cost (₹)",
                        min_value=0.0,
                        step=100.0,
                        key=f"diesel_{idx}"
                    )
                    
                    work_amount = st.number_input(
                        "Work Amount (₹)",
                        min_value=0.0,
                        step=100.0,
                        key=f"work_amount_{idx}",
                        help="Entry created when this is filled"
                    )
                
                with col2:
                    payment_received = st.number_input(
                        "Payment Received (₹)",
                        min_value=0.0,
                        step=100.0,
                        key=f"payment_{idx}"
                    )
                    
                    maintenance_total = st.number_input(
                        "Maintenance Total (₹)",
                        min_value=0.0,
                        step=100.0,
                        key=f"maintenance_total_{idx}",
                        help="Enter amount to show breakdown fields below"
                    )
                
                # Show maintenance breakdown ONLY when maintenance_total > 0
                if maintenance_total > 0:
                    st.markdown("**🔧 Maintenance Breakdown**")
                    st.caption("Select applicable maintenance types:")
                    
                    selected_maintenance = st.multiselect(
                        "Maintenance Types",
                        options=MAINTENANCE_TYPES,
                        key=f"maintenance_types_{idx}",
                        label_visibility="collapsed"
                    )
                    
                    maintenance_items = []
                    
                    if selected_maintenance:
                        st.markdown("**Enter cost for each type:**")
                        
                        for mtype in selected_maintenance:
                            col_m = st.columns([3, 2])[0]
                            with col_m:
                                if mtype == "Other":
                                    other_desc = st.text_input(
                                        "Specify Other Maintenance",
                                        key=f"other_desc_{idx}",
                                        placeholder="e.g., Tire replacement"
                                    )
                                    cost = st.number_input(
                                        f"Cost (₹)",
                                        min_value=0.0,
                                        step=100.0,
                                        key=f"cost_other_{idx}"
                                    )
                                    if cost > 0 and other_desc:
                                        maintenance_items.append(f"{other_desc}: ₹{cost:,.2f}")
                                else:
                                    cost = st.number_input(
                                        f"{mtype} Cost (₹)",
                                        min_value=0.0,
                                        step=100.0,
                                        key=f"cost_{mtype.replace(' ', '_')}_{idx}"
                                    )
                                    if cost > 0:
                                        maintenance_items.append(f"{mtype}: ₹{cost:,.2f}")
    
    st.divider()
    
    # Simple submit button
    submitted = st.form_submit_button(
        "💾 Submit All Entries",
        use_container_width=True,
        type="primary"
    )
    
    # Process form submission
    if submitted:
        vehicle_entries = []
        
        # Collect data from all vehicles
        for idx, vehicle in enumerate(master_vehicles):
            vehicle_name = vehicle["name"]
            
            # Check if vehicle was marked idle
            vehicle_idle = st.session_state.get(f"idle_{idx}", False)
            
            if vehicle_idle:
                # Idle vehicle
                idle_reason = st.session_state.get(f"idle_reason_{idx}", "")
                
                if idle_reason:  # Only if reason selected
                    idle_reason_other = st.session_state.get(f"idle_reason_other_{idx}", "")
                    final_idle_reason = idle_reason_other if idle_reason == "Other" else idle_reason
                    idle_notes = st.session_state.get(f"idle_notes_{idx}", "")
                    idle_diesel = st.session_state.get(f"idle_diesel_{idx}", 0)
                    idle_maintenance = st.session_state.get(f"idle_maintenance_{idx}", 0)
                    
                    vehicle_entries.append({
                        "vehicle_name": vehicle_name,
                        "is_idle": True,
                        "idle_reason": final_idle_reason,
                        "idle_notes": idle_notes,
                        "project_site": "N/A - Vehicle Idle",
                        "driver": "N/A",
                        "diesel_cost": idle_diesel,
                        "work_description": f"Vehicle Idle - {final_idle_reason}",
                        "work_amount": 0,
                        "payment_received": 0,
                        "has_maintenance": "Yes" if idle_maintenance > 0 else "No",
                        "maintenance_summary": f"Idle day maintenance: ₹{idle_maintenance:,.2f}" if idle_maintenance > 0 else "",
                        "total_maintenance_cost": idle_maintenance,
                        "driver_payment": 0,
                        "driver_name_payment": "N/A"
                    })
            else:
                # Working vehicle
                work_amount = st.session_state.get(f"work_amount_{idx}", 0)
                
                if work_amount > 0:  # Only if work amount filled
                    driver = st.session_state.get(f"driver_{idx}", "")
                    vehicle_project = st.session_state.get(f"project_{idx}", "")
                    vehicle_description = st.session_state.get(f"description_{idx}", "")
                    diesel_cost = st.session_state.get(f"diesel_{idx}", 0)
                    payment_received = st.session_state.get(f"payment_{idx}", 0)
                    maintenance_total = st.session_state.get(f"maintenance_total_{idx}", 0)
                    
                    # Build maintenance summary
                    maintenance_summary = ""
                    if maintenance_total > 0:
                        selected_types = st.session_state.get(f"maintenance_types_{idx}", [])
                        if selected_types:
                            items = []
                            for mtype in selected_types:
                                if mtype == "Other":
                                    other_desc = st.session_state.get(f"other_desc_{idx}", "")
                                    cost = st.session_state.get(f"cost_other_{idx}", 0)
                                    if cost > 0 and other_desc:
                                        items.append(f"{other_desc}: ₹{cost:,.2f}")
                                else:
                                    cost = st.session_state.get(f"cost_{mtype.replace(' ', '_')}_{idx}", 0)
                                    if cost > 0:
                                        items.append(f"{mtype}: ₹{cost:,.2f}")
                            maintenance_summary = "; ".join(items) if items else f"Maintenance: ₹{maintenance_total:,.2f}"
                        else:
                            maintenance_summary = f"Maintenance: ₹{maintenance_total:,.2f}"
                    
                    vehicle_entries.append({
                        "vehicle_name": vehicle_name,
                        "is_idle": False,
                        "idle_reason": "",
                        "idle_notes": "",
                        "project_site": vehicle_project if vehicle_project else "Not specified",
                        "driver": driver if driver else "N/A",
                        "diesel_cost": diesel_cost,
                        "work_description": vehicle_description if vehicle_description else "Work performed",
                        "work_amount": work_amount,
                        "payment_received": payment_received,
                        "has_maintenance": "Yes" if maintenance_total > 0 else "No",
                        "maintenance_summary": maintenance_summary,
                        "total_maintenance_cost": maintenance_total,
                        "driver_payment": 0,
                        "driver_name_payment": "N/A"
                    })
        
        # Now save all entries
        if len(vehicle_entries) == 0:
            st.warning("⚠️ No entries to save. Please fill at least one vehicle's work amount or mark as idle with a reason.")
        else:
            success_count = 0
            failed_count = 0
            
            with st.spinner(f"Saving {len(vehicle_entries)} entries..."):
                for vehicle_data in vehicle_entries:
                    if save_vehicle_entry(date_activity, vehicle_data):
                        success_count += 1
                    else:
                        failed_count += 1
            
            if success_count > 0:
                st.success(f"✅ Successfully saved {success_count} entries!")
                
                # Show summary
                working_count = sum(1 for v in vehicle_entries if not v.get("is_idle"))
                idle_count = sum(1 for v in vehicle_entries if v.get("is_idle"))
                
                st.info(f"📊 Summary: {working_count} working vehicles, {idle_count} idle vehicles")
                
                st.balloons()
            
            if failed_count > 0:
                st.error(f"❌ Failed to save {failed_count} entries. Please check and try again.")
            
            # Clear cache
            get_unique_projects.clear()

# Footer
st.divider()

col_footer1, col_footer2, col_footer3 = st.columns([2, 1, 2])
with col_footer2:
    if st.button("🔄 Refresh Master Data", help="Reload vehicles and drivers from sheets"):
        get_master_vehicles.clear()
        get_master_drivers.clear()
        st.success("✅ Master data refreshed!")
        st.rerun()

st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <small>Vinaysa Infra Daily Log Book | Multi-Vehicle Entry System<br>
    Fill work amount > 0 or mark idle to create entry</small>
</div>
""", unsafe_allow_html=True)
