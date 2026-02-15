# 🚛 Vinaysa Infra - Daily Log Book

A simple, powerful app to track daily vehicle activities, costs, and project-wise operations for your infrastructure firm.

## ✨ Features

✅ **Project Tracking** - Autocomplete remembers all your project sites  
✅ **Dynamic Master Data** - Add vehicles/drivers in Google Sheets, no code changes!  
✅ **Vehicle & Driver Management** - Track all vehicles and operators  
✅ **Cost Recording** - Diesel, work amount, maintenance, payments  
✅ **Mobile Friendly** - Enter data from site using phone  
✅ **Google Sheets Backend** - All data stored securely  
✅ **No Login Required** - Quick data entry for your team  
✅ **Auto-refresh** - Master data updates every 5 minutes

## 🏗️ Architecture

```
Google Sheet: Vinaysa_Infra_Daily_Log
│
├── 📋 Daily_Logs          → Your daily entries
├── 🚛 Master_Vehicles     → Manage vehicles (add/edit here!)
├── 👷 Master_Drivers      → Manage drivers (add/edit here!)
└── 🏗️ Master_Projects     → Auto-populated from entries
```

**Key Innovation**: Add new vehicles or drivers by simply adding a row in the Google Sheet - no code deployment needed!  

## 🚀 Quick Start

See **[SETUP_GUIDE.md](SETUP_GUIDE.md)** for complete installation instructions.

**Summary:**
1. Create Google Cloud project + service account
2. Create Google Sheet named `Vinaysa_Infra_Daily_Log`
3. Share sheet with service account
4. Run `python setup_master_sheets.py` to create Master_Vehicles and Master_Drivers
5. Configure secrets
6. Run: `streamlit run app.py`

**Managing Vehicles/Drivers:**
See **[MASTER_DATA_GUIDE.md](MASTER_DATA_GUIDE.md)** for how to add/remove vehicles and drivers by editing Google Sheets.

## 📱 Screenshots

**Data Entry Form:**
- Date picker
- Project site autocomplete
- Vehicle and driver selection
- All cost fields
- Optional maintenance section

## 🎯 Roadmap

- [x] Data capture with project tracking
- [ ] Dashboard with project-wise analytics
- [ ] Profit/loss calculations
- [ ] Monthly reports
- [ ] Export to Excel

## 💾 Data Storage

All data is stored in your Google Sheet with these sheets:

**Daily_Logs** - Daily entries with columns:
- Timestamp, Date of Activity, Project Site
- Vehicle Name, Driver/Operator Name
- Diesel Cost, Work Description, Work Amount, Payment Received
- Maintenance details, Driver payments

**Master_Vehicles** - Your vehicle fleet:
- Vehicle ID, Name, Registration, Type, Status
- Edit this sheet to add/remove vehicles!

**Master_Drivers** - Your drivers/operators:
- Driver ID, Name, Phone, Status
- Edit this sheet to add/remove drivers!

**Master_Projects** - (Future) Auto-populated project list

## 📞 Support

If you encounter any issues during setup, share the error message and I'll help you fix it!

---

**Built with Streamlit • Powered by Google Sheets**
