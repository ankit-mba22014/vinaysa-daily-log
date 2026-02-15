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

# Initialize session state for form values
if 'vehicle_data' not in st.session_state:
    st.session_state.vehicle_data = {}

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
    st.caption("💡 Set these to auto-fill all vehicles. Override per vehicle if needed.")
    
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
                    help="Select if most vehicles worked on same project"
                )
            else:
                default_project = st.text_input(
                    "Default Project Site",
                    placeholder="e.g., Highway NH-30 Extension",
                    help="Enter new project name"
                )
        else:
            default_project = st.text_input(
                "Default Project Site",
                placeholder="e.g., Highway NH-30 Extension",
                help="Enter project name"
            )
    
    with col_default2:
        default_description = st.text_area(
            "Default Work Description",
            placeholder="e.g., Excavation and material transport",
            help="Common work description for all vehicles",
            height=100
        )
    
    st.divider()
    
    # Vehicle Cards
    st.subheader("🚛 Vehicle Entries")
    st.caption(f"📋 {len(master_vehicles)} vehicles loaded. Expand cards to fill details.")
    
    # Help message about entry creation
    with st.expander("ℹ️ How entries are created", expanded=False):
        st.markdown("""
        **An entry is created for a vehicle when:**
        - ✅ **Work Amount > 0** (vehicle worked and has billable amount), OR
        - ✅ **Vehicle marked as Idle** AND idle reason selected
        
        **An entry is NOT created when:**
        - ❌ Card left empty or collapsed
        - ❌ Work Amount = 0 and not marked idle
        - ❌ Marked idle but no reason selected
        
        💡 **Tip:** Fill only the vehicles you actually used today!
        """)
    
    vehicle_entries = []
    
    for idx, vehicle in enumerate(master_vehicles):
        vehicle_name = vehicle["name"]
        default_driver = vehicle.get("default_driver", "")
        
        with st.expander(f"🚛 **{vehicle_name}**", expanded=False):
            
            # Vehicle status checkboxes
            col_status1, col_status2 = st.columns(2)
            
            with col_status1:
                vehicle_idle = st.checkbox(
                    "🛑 Vehicle Idle",
                    key=f"idle_{idx}",
                    help="Check if vehicle was idle/not working today"
                )
            
            # If vehicle is idle, show idle-specific fields
            if vehicle_idle:
                st.markdown("**🛑 Idle Vehicle Details**")
                
                idle_reason = st.selectbox(
                    "Idle Reason",
                    options=[""] + IDLE_REASONS,
                    key=f"idle_reason_{idx}"
                )
                
                if idle_reason == "Other":
                    idle_reason_other = st.text_input(
                        "Specify Reason",
                        key=f"idle_reason_other_{idx}",
                        placeholder="e.g., Festival holiday"
                    )
                    final_idle_reason = idle_reason_other
                else:
                    final_idle_reason = idle_reason
                
                idle_notes = st.text_area(
                    "Idle Notes (optional)",
                    key=f"idle_notes_{idx}",
                    placeholder="Additional details...",
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
                
                # Store idle vehicle data
                if idle_reason:  # Only if idle reason is selected
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
                
                # Project (with default pre-fill)
                st.markdown("**🏗️ Project Site**")
                
                if default_project:
                    # Show override option only if default exists
                    project_override = st.checkbox(
                        f"Override default ({default_project})",
                        key=f"project_override_{idx}",
                        value=False,
                        help="Check to use a different project for this vehicle"
                    )
                    
                    if project_override:
                        # User wants different project
                        if existing_projects:
                            project_type = st.radio(
                                "Project type",
                                options=["Select existing", "Enter new"],
                                horizontal=True,
                                key=f"project_type_{idx}",
                                label_visibility="collapsed"
                            )
                            
                            if project_type == "Select existing":
                                vehicle_project = st.selectbox(
                                    "Project",
                                    options=[""] + existing_projects,
                                    key=f"project_{idx}",
                                    label_visibility="collapsed"
                                )
                            else:
                                vehicle_project = st.text_input(
                                    "Project",
                                    key=f"project_new_{idx}",
                                    placeholder="Enter project name",
                                    label_visibility="collapsed"
                                )
                        else:
                            vehicle_project = st.text_input(
                                "Project Site",
                                key=f"project_{idx}",
                                placeholder="Enter project name"
                            )
                    else:
                        # Use default
                        st.info(f"✅ Using default project")
                        vehicle_project = default_project
                else:
                    # No default, always show input
                    if existing_projects:
                        project_type = st.radio(
                            "Project type",
                            options=["Select existing", "Enter new"],
                            horizontal=True,
                            key=f"project_type_{idx}",
                            label_visibility="collapsed"
                        )
                        
                        if project_type == "Select existing":
                            vehicle_project = st.selectbox(
                                "Project",
                                options=[""] + existing_projects,
                                key=f"project_{idx}",
                                label_visibility="collapsed"
                            )
                        else:
                            vehicle_project = st.text_input(
                                "Project",
                                key=f"project_new_{idx}",
                                placeholder="Enter project name",
                                label_visibility="collapsed"
                            )
                    else:
                        vehicle_project = st.text_input(
                            "Project Site",
                            key=f"project_{idx}",
                            placeholder="Enter project name"
                        )
                
                # Description (with default pre-fill)
                st.markdown("**📝 Work Description**")
                
                if default_description:
                    # Show override option only if default exists
                    description_override = st.checkbox(
                        "Override default description",
                        key=f"description_override_{idx}",
                        value=False,
                        help="Check to use a different description for this vehicle"
                    )
                    
                    if description_override:
                        vehicle_description = st.text_area(
                            "Description",
                            key=f"description_{idx}",
                            placeholder="Describe work performed...",
                            height=100,
                            label_visibility="collapsed"
                        )
                    else:
                        st.info(f"✅ Using default description")
                        vehicle_description = default_description
                else:
                    # No default, always show input
                    vehicle_description = st.text_area(
                        "Description",
                        key=f"description_{idx}",
                        placeholder="Describe work performed...",
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
                        help="Auto-creates entry when filled"
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
                        help="Quick entry - or expand below for details"
                    )
                
                # Expandable detailed maintenance
                # Initialize variables before conditional to avoid NameError
                maintenance_summary = ""
                maintenance_items = []
                
                if maintenance_total > 0:
                    with st.expander("🔧 Maintenance Breakdown (Optional)", expanded=False):
                        st.caption("Break down the ₹{:,.2f} maintenance cost by type".format(maintenance_total))
                        
                        selected_maintenance = st.multiselect(
                            "Maintenance Types",
                            options=MAINTENANCE_TYPES,
                            key=f"maintenance_types_{idx}"
                        )
                        
                        maintenance_costs = {}
                        
                        if selected_maintenance:
                            st.markdown("**Enter cost for each:**")
                            cols_per_row = 2
                            for i in range(0, len(selected_maintenance), cols_per_row):
                                cols = st.columns(cols_per_row)
                                
                                for j, col in enumerate(cols):
                                    idx_m = i + j
                                    if idx_m < len(selected_maintenance):
                                        mtype = selected_maintenance[idx_m]
                                        
                                        with col:
                                            if mtype == "Other":
                                                other_desc = st.text_input(
                                                    "Specify",
                                                    key=f"other_desc_{idx}_{idx_m}",
                                                    placeholder="e.g., Tire replacement"
                                                )
                                                cost = st.number_input(
                                                    f"Cost (₹)",
                                                    min_value=0.0,
                                                    step=100.0,
                                                    key=f"cost_other_{idx}_{idx_m}"
                                                )
                                                if cost > 0 and other_desc:
                                                    maintenance_costs[other_desc] = cost
                                                    maintenance_items.append(f"{other_desc}: ₹{cost:,.2f}")
                                            else:
                                                cost = st.number_input(
                                                    f"{mtype} (₹)",
                                                    min_value=0.0,
                                                    step=100.0,
                                                    key=f"cost_{idx}_{mtype.replace(' ', '_')}"
                                                )
                                                if cost > 0:
                                                    maintenance_costs[mtype] = cost
                                                    maintenance_items.append(f"{mtype}: ₹{cost:,.2f}")
                        
                        maintenance_summary = "; ".join(maintenance_items) if maintenance_items else f"Maintenance: ₹{maintenance_total:,.2f}"
                
                # If no maintenance, summary already initialized to ""
                
                # Validation: Create entry if work_amount > 0
                if work_amount > 0:
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
                        "driver_payment": 0,  # Can add later if needed
                        "driver_name_payment": "N/A"
                    })
    
    st.divider()
    
    # Summary before submit
    if vehicle_entries:
        with st.container():
            st.markdown("### 📊 Summary")
            
            working_count = sum(1 for v in vehicle_entries if not v.get("is_idle"))
            idle_count = sum(1 for v in vehicle_entries if v.get("is_idle"))
            
            col_sum1, col_sum2, col_sum3 = st.columns(3)
            with col_sum1:
                st.metric("Working Vehicles", working_count)
            with col_sum2:
                st.metric("Idle Vehicles", idle_count)
            with col_sum3:
                st.metric("Total Entries", len(vehicle_entries))
            
            # Show list of vehicles
            st.markdown("**Vehicles to be logged:**")
            for v in vehicle_entries:
                status = "🛑 Idle" if v.get("is_idle") else "✅ Working"
                st.markdown(f"• {status} - {v['vehicle_name']}")
    
    # Submit button
    submitted = st.form_submit_button(
        f"💾 Submit All Entries ({len(vehicle_entries)} entries)" if vehicle_entries else "💾 Submit (No entries to save)",
        use_container_width=True,
        type="primary",
        disabled=len(vehicle_entries) == 0
    )
    
    if submitted:
        if len(vehicle_entries) == 0:
            st.warning("⚠️ No entries to save. Fill at least one vehicle's work amount or mark as idle.")
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
    Master data auto-refreshes every 5 minutes</small>
</div>
""", unsafe_allow_html=True)
