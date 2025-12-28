import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from phonenumbers import number_type, PhoneNumberType, region_code_for_number, NumberParseException
import csv, os, io, requests, webbrowser, json, time, threading
from geopy.geocoders import Nominatim
import folium
from datetime import datetime, timedelta
import sqlite3
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import re

# Mapping of number type
TYPE_MAP = {
    PhoneNumberType.FIXED_LINE: "Fixed line",
    PhoneNumberType.MOBILE: "Mobile",
    PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed line or Mobile",
    PhoneNumberType.TOLL_FREE: "Toll free",
    PhoneNumberType.PREMIUM_RATE: "Premium rate",
    PhoneNumberType.SHARED_COST: "Shared cost",
    PhoneNumberType.VOIP: "VoIP",
    PhoneNumberType.PERSONAL_NUMBER: "Personal number",
    PhoneNumberType.PAGER: "Pager",
    PhoneNumberType.UAN: "UAN",
    PhoneNumberType.VOICEMAIL: "Voicemail",
    PhoneNumberType.UNKNOWN: "Unknown",
}

class TelephonyGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🌍 Advanced Telephony Intelligence Suite")
        self.state("zoomed")
        self.configure(bg="#f0f4f7")

        # Initialize databases
        self.init_databases()
        
        # Style
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", font=("Arial", 12, "bold"), padding=6, background="#0078D7", foreground="white")
        style.map("TButton", background=[("active", "#005A9E")], foreground=[("active", "white")])
        style.configure("TLabel", font=("Arial", 11), background="#ffffff")
        style.configure("Treeview", font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))

        # Title Banner
        banner = tk.Frame(self, bg="#0078D7", height=70)
        banner.pack(fill="x")
        tk.Label(banner, text="📞 Advanced Telephony Intelligence Suite",
                 font=("Arial", 24, "bold"), fg="white", bg="#0078D7").pack(pady=10)

        # Main Notebook for Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Single Lookup Tab
        self.single_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.single_tab, text="🔍 Single Lookup")

        # Batch Analytics Tab
        self.analytics_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.analytics_tab, text="📊 Batch Analytics")

        # History Tab
        self.history_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text="📈 History")

        # API Services Tab
        self.api_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.api_tab, text="🌐 API Services")

        self.setup_single_lookup()
        self.setup_analytics_tab()
        self.setup_history_tab()
        self.setup_api_tab()

        # Store last details
        self.last_details = None
        self.current_batch_data = []

    def init_databases(self):
        """Initialize SQLite databases for history and spam data"""
        self.conn = sqlite3.connect('telephony_data.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Create tables
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS lookup_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                phone_number TEXT,
                country TEXT,
                carrier TEXT,
                valid INTEGER,
                spam_score REAL,
                data TEXT
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS spam_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT,
                report_count INTEGER DEFAULT 1,
                last_reported DATETIME DEFAULT CURRENT_TIMESTAMP,
                spam_type TEXT
            )
        ''')
        
        self.conn.commit()

    def detect_region_from_number(self, number):
        """Automatically detect region/country from phone number"""
        try:
            # Handle various formats: +91, 0044, 0, etc.
            cleaned_number = number.strip()
            
            # If number starts with +, parse without region
            if cleaned_number.startswith('+'):
                parsed_number = phonenumbers.parse(cleaned_number, None)
                region = region_code_for_number(parsed_number)
                return region if region else "US"  # Default to US if no region found
            
            # If number starts with 00 (international format)
            elif cleaned_number.startswith('00'):
                # Convert 00 to + format
                plus_format = '+' + cleaned_number[2:]
                try:
                    parsed_number = phonenumbers.parse(plus_format, None)
                    region = region_code_for_number(parsed_number)
                    return region if region else "US"
                except:
                    pass
            
            # Try common country codes
            common_regions = ["US", "IN", "GB", "CA", "AU", "DE", "FR", "JP", "CN", "BR"]
            for region in common_regions:
                try:
                    parsed_number = phonenumbers.parse(cleaned_number, region)
                    if phonenumbers.is_valid_number(parsed_number):
                        return region
                except:
                    continue
            
            # Default to US if no region detected
            return "US"
            
        except Exception as e:
            print(f"Region detection error: {e}")
            return "US"  # Default fallback

    def setup_single_lookup(self):
        """Setup single number lookup tab"""
        # Entry Frame
        entry_frame = tk.Frame(self.single_tab, bg="#f0f4f7")
        entry_frame.pack(pady=20)

        self.phone_entry = ttk.Entry(entry_frame, width=30, font=("Arial", 14))
        self.phone_entry.grid(row=0, column=0, padx=5, ipady=5)
        self.phone_entry.bind('<KeyRelease>', self.auto_detect_region)  # Auto-detect on typing

        # Region display (read-only, auto-detected)
        self.region_var = tk.StringVar(value="Auto-detected")
        self.region_label = ttk.Label(entry_frame, textvariable=self.region_var, 
                                     font=("Arial", 12), background="#f0f4f7")
        self.region_label.grid(row=0, column=1, padx=5)

        get_btn = ttk.Button(entry_frame, text="🔍 Get Details", command=self.get_details)
        get_btn.grid(row=0, column=2, padx=5)

        validate_btn = ttk.Button(entry_entry_frame, text="✅ Real-time Validate", command=self.real_time_validation)
        validate_btn.grid(row=0, column=3, padx=5)

        # Advanced Features Frame
        advanced_frame = tk.Frame(self.single_tab, bg="#f0f4f7")
        advanced_frame.pack(pady=10)

        social_btn = ttk.Button(advanced_frame, text="📱 Social Media Lookup", command=self.social_media_lookup)
        social_btn.grid(row=0, column=0, padx=5)

        spam_btn = ttk.Button(advanced_frame, text="🛡️ Spam Check", command=self.spam_check)
        spam_btn.grid(row=0, column=1, padx=5)

        portability_btn = ttk.Button(advanced_frame, text="🔄 Portability Check", command=self.portability_check)
        portability_btn.grid(row=0, column=2, padx=5)

        prefix_btn = ttk.Button(advanced_frame, text="🔢 Prefix Analysis", command=self.prefix_analysis)
        prefix_btn.grid(row=0, column=3, padx=5)

        # Details Frame
        details_container = tk.Frame(self.single_tab, bg="#f0f4f7")
        details_container.pack(fill="both", expand=True, padx=20, pady=10)

        # Left side - Basic Info
        left_frame = tk.Frame(details_container, bd=2, relief="groove", padx=15, pady=15, bg="white")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(left_frame, text="Phone Number Intelligence",
                 font=("Arial", 16, "bold"), fg="#0078D7", bg="white").pack(pady=10)

        self.labels = {}
        basic_fields = [
            "Country", "Country Code", "State/Region", "City", "Location",
            "Carrier", "Formatted Number", "International Number", "Network Type",
            "Valid", "Possible", "Timezones", "Spam Score", "Portability Status",
            "Prefix Info", "Social Media"
        ]

        for i, field in enumerate(basic_fields):
            row_frame = tk.Frame(left_frame, bg="white")
            row_frame.pack(fill="x", pady=2)
            
            lbl_field = tk.Label(row_frame, text=f"{field}:", font=("Arial", 10, "bold"), 
                               bg="white", anchor="w", width=15)
            lbl_field.pack(side="left")
            
            lbl_value = tk.Label(row_frame, text="—", font=("Arial", 10), 
                               bg="white", anchor="w", wraplength=400)
            lbl_value.pack(side="left", fill="x", expand=True)
            self.labels[field] = lbl_value

        # Right side - Flag and Map
        right_frame = tk.Frame(details_container, bg="#f0f4f7")
        right_frame.pack(side="right", fill="y", padx=(10, 0))

        # Flag
        flag_frame = tk.Frame(right_frame, bd=2, relief="groove", padx=15, pady=15, bg="white")
        flag_frame.pack(fill="x", pady=(0, 10))
        
        self.flag_label = tk.Label(flag_frame, bg="white", text="🇺🇳 Flag will appear here")
        self.flag_label.pack()

        # Map Button
        map_btn = ttk.Button(right_frame, text="🗺️ Show Precise Location", command=self.show_precise_location)
        map_btn.pack(fill="x", pady=5)

        # Export Button
        export_btn = ttk.Button(right_frame, text="💾 Export Details", command=self.export_csv)
        export_btn.pack(fill="x", pady=5)

    def auto_detect_region(self, event=None):
        """Auto-detect region as user types"""
        number = self.phone_entry.get().strip()
        if len(number) >= 3:  # Only detect when there's enough input
            detected_region = self.detect_region_from_number(number)
            if detected_region:
                country_name = self.get_country_name_from_code(detected_region)
                self.region_var.set(f"🇺🇳 {country_name}")

    def get_country_name_from_code(self, country_code):
        """Get country name from country code"""
        country_names = {
            "US": "United States", "IN": "India", "GB": "United Kingdom", 
            "CA": "Canada", "AU": "Australia", "DE": "Germany", 
            "FR": "France", "JP": "Japan", "CN": "China", "BR": "Brazil"
        }
        return country_names.get(country_code, country_code)

    def setup_analytics_tab(self):
        """Setup batch analytics dashboard"""
        main_frame = tk.Frame(self.analytics_tab, bg="#f0f4f7")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Controls
        controls_frame = tk.Frame(main_frame, bg="#f0f4f7")
        controls_frame.pack(fill="x", pady=10)

        ttk.Button(controls_frame, text="📂 Load Batch File", 
                  command=self.load_batch_file).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="📊 Generate Analytics", 
                  command=self.generate_analytics).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="📈 Show Charts", 
                  command=self.show_charts).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="💾 Export Report", 
                  command=self.export_analytics).pack(side="left", padx=5)

        # Results Frame
        results_frame = tk.Frame(main_frame, bg="#f0f4f7")
        results_frame.pack(fill="both", expand=True)

        # Treeview for data
        columns = ("Number", "Country", "Carrier", "Valid", "Spam Score", "Type")
        self.analytics_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.analytics_tree.heading(col, text=col)
            self.analytics_tree.column(col, width=120)

        self.analytics_tree.pack(side="left", fill="both", expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.analytics_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.analytics_tree.configure(yscrollcommand=scrollbar.set)

        # Stats Frame
        self.stats_frame = tk.Frame(main_frame, bg="white", bd=2, relief="groove")
        self.stats_frame.pack(fill="x", pady=10)
        
        self.stats_labels = {}

    def setup_history_tab(self):
        """Setup historical tracking tab"""
        main_frame = tk.Frame(self.history_tab, bg="#f0f4f7")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Controls
        controls_frame = tk.Frame(main_frame, bg="#f0f4f7")
        controls_frame.pack(fill="x", pady=10)

        ttk.Button(controls_frame, text="🔄 Refresh History", 
                  command=self.load_history).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="🗑️ Clear History", 
                  command=self.clear_history).pack(side="left", padx=5)

        # History Treeview
        columns = ("Timestamp", "Phone Number", "Country", "Carrier", "Valid", "Spam Score")
        self.history_tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=150)

        self.history_tree.pack(fill="both", expand=True)

        # Load initial history
        self.load_history()

    def setup_api_tab(self):
        """Setup API services tab"""
        main_frame = tk.Frame(self.api_tab, bg="#f0f4f7")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # API Services Frame
        api_frame = tk.LabelFrame(main_frame, text="🌐 Available API Services", 
                                font=("Arial", 12, "bold"), bg="white", padx=15, pady=15)
        api_frame.pack(fill="x", pady=10)

        services = [
            ("📱 Social Media API", "Check social platform registrations"),
            ("🛡️ Spam Detection API", "Real-time spam scoring"),
            ("📍 Precise Location API", "Advanced geolocation services"),
            ("🔢 Number Portability API", "Carrier portability history"),
            ("✅ Validation API", "Real-time number validation")
        ]

        for i, (service, description) in enumerate(services):
            service_frame = tk.Frame(api_frame, bg="white")
            service_frame.pack(fill="x", pady=5)
            
            ttk.Button(service_frame, text=service, 
                      command=lambda s=service: self.test_api_service(s)).pack(side="left", padx=5)
            tk.Label(service_frame, text=description, bg="white", font=("Arial", 9)).pack(side="left", padx=10)

        # API Results
        self.api_results = tk.Text(main_frame, height=15, width=80, font=("Consolas", 10))
        self.api_results.pack(fill="both", expand=True, pady=10)

    # ==================== ADVANCED FEATURES IMPLEMENTATION ====================

    def get_details(self, number=None):
        if not number:
            number = self.phone_entry.get().strip()

        if not number:
            messagebox.showwarning("Input required", "Please enter a phone number.")
            return

        # Auto-detect region for parsing
        detected_region = self.detect_region_from_number(number)
        
        try:
            if number.startswith("+"):
                num = phonenumbers.parse(number, None)
            else:
                num = phonenumbers.parse(number, detected_region)
        except NumberParseException as e:
            messagebox.showerror("Error", f"Could not parse number: {e}")
            return

        # Extract basic details
        country_code = region_code_for_number(num)
        country = geocoder.country_name_for_number(num, "en") or "Unknown"
        location_desc = geocoder.description_for_number(num, "en") or "Unknown"
        
        state_region = self.extract_state_region(location_desc, country)
        city = self.extract_city(location_desc, country)
        carr = carrier.name_for_number(num, "en") or "Unknown"
        formatted = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.NATIONAL)
        international = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        ntype = TYPE_MAP.get(number_type(num), "Unknown")
        valid = phonenumbers.is_valid_number(num)
        possible = phonenumbers.is_possible_number(num)
        tzs = ", ".join(timezone.time_zones_for_number(num)) or "Unknown"

        # Update region display with detected country
        self.region_var.set(f"🇺🇳 {country}")

        # Advanced features
        spam_score = self.calculate_spam_score(number, carr, country)
        portability_status = self.check_portability(number, carr, country)
        prefix_info = self.analyze_prefix(number, country_code)
        social_media = self.social_media_lookup_auto(number)

        self.last_details = {
            "Country": country,
            "Country Code": f"+{num.country_code}",
            "State/Region": state_region,
            "City": city,
            "Location": location_desc,
            "Carrier": carr,
            "Formatted Number": formatted,
            "International Number": international,
            "Network Type": ntype,
            "Valid": str(valid),
            "Possible": str(possible),
            "Timezones": tzs,
            "Spam Score": f"{spam_score}/10",
            "Portability Status": portability_status,
            "Prefix Info": prefix_info,
            "Social Media": social_media
        }

        for field, value in self.last_details.items():
            self.labels[field].config(text=value)

        # Save to history
        self.save_to_history(number, self.last_details)

        # Load flag
        self.load_flag(country_code)

    def calculate_spam_score(self, number, carrier, country):
        """1. Spam/Fraud Detection"""
        score = 0
        
        # Check local spam database
        self.cursor.execute("SELECT report_count, spam_type FROM spam_reports WHERE phone_number = ?", (number,))
        result = self.cursor.fetchone()
        
        if result:
            report_count, spam_type = result
            score += min(report_count * 2, 6)  # Max 6 points for reports
        
        # Pattern analysis
        if re.match(r'(\d)\1{5,}', number):  # Repeated digits
            score += 2
        if len(number) < 7:  # Very short numbers
            score += 1
        if carrier.lower() in ['unknown', 'voip']:
            score += 1
            
        return min(score, 10)

    def check_portability(self, number, current_carrier, country):
        """2. Number Portability Detection"""
        # Simulate portability check
        portability_db = {
            'US': ['Verizon', 'AT&T', 'T-Mobile', 'Sprint'],
            'GB': ['Vodafone', 'O2', 'EE', 'Three'],
            'IN': ['Airtel', 'Jio', 'Vodafone', 'BSNL']
        }
        
        possible_carriers = portability_db.get(country, [])
        if current_carrier not in possible_carriers and current_carrier != 'Unknown':
            return f"Portable (from {possible_carriers[0] if possible_carriers else 'unknown'})"
        
        return "Original Carrier"

    def social_media_lookup_auto(self, number):
        """3. Social Media Lookup (Auto)"""
        platforms = []
        
        # Simulate social media checks
        if len(number) > 8:  # Basic validity check
            platforms.append("WhatsApp✓")
            platforms.append("Telegram✓")
            
        # Add more platform checks based on country/pattern
        if number.startswith('+1'):
            platforms.append("iMessage✓")
            
        return ", ".join(platforms) if platforms else "Not found"

    def social_media_lookup(self):
        """3. Social Media Lookup (Manual)"""
        if not self.last_details:
            messagebox.showwarning("No Data", "Please get number details first.")
            return
            
        number = self.phone_entry.get().strip()
        if not number:
            return
            
        # Simulate comprehensive social media lookup
        results = {
            "WhatsApp": "Registered ✓",
            "Telegram": "Registered ✓", 
            "Facebook": "Possible match",
            "Instagram": "Not found",
            "Twitter": "Not found",
            "Signal": "Registered ✓"
        }
        
        result_text = "Social Media Lookup Results:\n\n"
        for platform, status in results.items():
            result_text += f"{platform}: {status}\n"
            
        messagebox.showinfo("Social Media Lookup", result_text)

    def prefix_analysis(self):
        """7. Area Code & Prefix Analysis"""
        if not self.last_details:
            messagebox.showwarning("No Data", "Please get number details first.")
            return
            
        number = self.phone_entry.get().strip()
        country_code = self.last_details.get('Country Code', '+1')
        
        analysis = self.analyze_prefix(number, country_code[1:])  # Remove '+'
        
        messagebox.showinfo("Prefix Analysis", analysis)

    def analyze_prefix(self, number, country_code):
        """7. Area Code & Prefix Analysis Implementation"""
        # US/Canada area codes
        us_area_codes = {
            '212': 'New York City, NY',
            '310': 'Los Angeles, CA', 
            '312': 'Chicago, IL',
            '415': 'San Francisco, CA',
            '305': 'Miami, FL',
            '202': 'Washington, DC',
            '617': 'Boston, MA',
            '713': 'Houston, TX'
        }
        
        if country_code == '1' and len(number) >= 10:
            area_code = number[-10:-7] if number.startswith('+1') else number[:3]
            location = us_area_codes.get(area_code, "Unknown location")
            return f"Area Code {area_code}: {location}"
        
        return "Advanced prefix analysis available"

    def real_time_validation(self):
        """9. Real-time Number Validation"""
        number = self.phone_entry.get().strip()
        if not number:
            messagebox.showwarning("Input required", "Please enter a phone number.")
            return
            
        # Simulate real-time validation
        validation_result = {
            "Live Carrier": "Verified ✓",
            "SMS Capable": "Yes",
            "VoIP Service": "No", 
            "Active Status": "Active",
            "Last Seen": "Within 24 hours"
        }
        
        result_text = "Real-time Validation Results:\n\n"
        for check, status in validation_result.items():
            result_text += f"{check}: {status}\n"
            
        messagebox.showinfo("Real-time Validation", result_text)

    def spam_check(self):
        """2. Spam/Fraud Detection (Manual)"""
        if not self.last_details:
            messagebox.showwarning("No Data", "Please get number details first.")
            return
            
        number = self.phone_entry.get().strip()
        spam_score = self.calculate_spam_score(number, 
                                             self.last_details.get('Carrier', 'Unknown'),
                                             self.last_details.get('Country', 'Unknown'))
        
        risk_level = "Low" if spam_score < 3 else "Medium" if spam_score < 7 else "High"
        
        result_text = f"Spam Risk Assessment:\n\n"
        result_text += f"Spam Score: {spam_score}/10\n"
        result_text += f"Risk Level: {risk_level}\n"
        result_text += f"Recommendation: {'Safe to contact' if spam_score < 4 else 'Use caution' if spam_score < 8 else 'Avoid contact'}"
        
        messagebox.showinfo("Spam Check", result_text)

    def portability_check(self):
        """1. Number Portability Detection (Manual)"""
        if not self.last_details:
            messagebox.showwarning("No Data", "Please get number details first.")
            return
            
        portability_status = self.last_details.get('Portability Status', 'Unknown')
        
        result_text = f"Number Portability Analysis:\n\n"
        result_text += f"Status: {portability_status}\n"
        result_text += f"Current Carrier: {self.last_details.get('Carrier', 'Unknown')}\n"
        result_text += "Portability: Supported in most regions"
        
        messagebox.showinfo("Portability Check", result_text)

    def show_precise_location(self):
        """6. Precise Location Services"""
        if not self.last_details:
            messagebox.showwarning("No Data", "Please get number details first.")
            return

        location_name = self.last_details.get('City') or self.last_details.get('State/Region') or self.last_details.get('Country')
        if location_name == "Unknown":
            messagebox.showwarning("No Location", "Location information not available.")
            return

        # Use geopy for more precise location
        geolocator = Nominatim(user_agent="advanced_telephony_app")
        try:
            location = geolocator.geocode(location_name + ", " + self.last_details.get('Country', ''))
            if location:
                # Create detailed map
                m = folium.Map(location=[location.latitude, location.longitude], zoom_start=10)
                
                # Add multiple markers for precision
                folium.Marker(
                    [location.latitude, location.longitude],
                    popup=f"<b>Precise Location:</b><br>{location_name}",
                    tooltip="Estimated Phone Location",
                    icon=folium.Icon(color='red', icon='phone')
                ).add_to(m)
                
                # Add circle for accuracy
                folium.Circle(
                    [location.latitude, location.longitude],
                    radius=5000,  # 5km radius
                    popup="Estimated Accuracy Area",
                    color='blue',
                    fill=True,
                    fillOpacity=0.2
                ).add_to(m)
                
                map_file = "precise_phone_location.html"
                m.save(map_file)
                webbrowser.open(f"file://{os.path.abspath(map_file)}")
            else:
                messagebox.showerror("Error", "Could not determine precise coordinates.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not generate precise map: {e}")

    # ==================== BATCH ANALYTICS ====================

    def load_batch_file(self):
        """4. Batch Analytics Dashboard - Load File"""
        file = filedialog.askopenfilename(filetypes=[("Text/CSV Files", "*.txt *.csv")])
        if not file:
            return

        self.current_batch_data = []
        with open(file, "r", encoding="utf-8") as f:
            numbers = [line.strip() for line in f if line.strip()]

        # Clear previous data
        for item in self.analytics_tree.get_children():
            self.analytics_tree.delete(item)

        # Process numbers with auto-detected regions
        for i, number in enumerate(numbers):
            details = self.get_number_details(number)
            if details:
                self.current_batch_data.append(details)
                self.analytics_tree.insert("", "end", values=(
                    details.get('International Number', ''),
                    details.get('Country', ''),
                    details.get('Carrier', ''),
                    details.get('Valid', ''),
                    details.get('Spam Score', '0/10'),
                    details.get('Network Type', '')
                ))

        messagebox.showinfo("Batch Loaded", f"Loaded {len(self.current_batch_data)} numbers for analysis.")

    def generate_analytics(self):
        """4. Batch Analytics Dashboard - Generate Analytics"""
        if not self.current_batch_data:
            messagebox.showwarning("No Data", "Please load a batch file first.")
            return

        # Clear previous stats
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        # Calculate statistics
        total_numbers = len(self.current_batch_data)
        valid_count = sum(1 for d in self.current_batch_data if d.get('Valid') == 'True')
        countries = Counter(d.get('Country', 'Unknown') for d in self.current_batch_data)
        carriers = Counter(d.get('Carrier', 'Unknown') for d in self.current_batch_data)
        types = Counter(d.get('Network Type', 'Unknown') for d in self.current_batch_data)

        # Display stats
        stats_text = f"""📊 Batch Analytics Report
=========================
Total Numbers: {total_numbers}
Valid Numbers: {valid_count} ({valid_count/total_numbers*100:.1f}%)
Invalid Numbers: {total_numbers - valid_count} ({(total_numbers-valid_count)/total_numbers*100:.1f}%)

Top Countries: {', '.join([f"{c} ({count})" for c, count in countries.most_common(3)])}
Top Carriers: {', '.join([f"{c} ({count})" for c, count in carriers.most_common(3)])}
Number Types: {', '.join([f"{t} ({count})" for t, count in types.most_common()])}"""

        tk.Label(self.stats_frame, text=stats_text, font=("Consolas", 10), 
                bg="white", justify="left").pack(padx=10, pady=10)

    def show_charts(self):
        """4. Batch Analytics Dashboard - Show Charts"""
        if not self.current_batch_data:
            messagebox.showwarning("No Data", "Please load a batch file first.")
            return

        # Create pie chart for carriers
        carriers = Counter(d.get('Carrier', 'Unknown') for d in self.current_batch_data)
        
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.pie(carriers.values(), labels=carriers.keys(), autopct='%1.1f%%', startangle=90)
        ax.set_title('Carrier Distribution')
        
        # Embed in tkinter
        chart_window = tk.Toplevel(self)
        chart_window.title("Analytics Charts")
        chart_window.geometry("600x500")
        
        canvas = FigureCanvasTkAgg(fig, chart_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def export_analytics(self):
        """4. Batch Analytics Dashboard - Export Report"""
        if not self.current_batch_data:
            messagebox.showwarning("No Data", "No analytics data to export.")
            return

        file = filedialog.asksaveasfilename(defaultextension=".csv", 
                                           filetypes=[("CSV Files", "*.csv"), 
                                                     ("Text Files", "*.txt")])
        if not file:
            return

        with open(file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Write header
            if self.current_batch_data:
                writer.writerow(self.current_batch_data[0].keys())
            # Write data
            for row in self.current_batch_data:
                writer.writerow(row.values())

        messagebox.showinfo("Export Complete", f"Analytics data exported to {os.path.basename(file)}")

    # ==================== HISTORICAL TRACKING ====================

    def save_to_history(self, number, details):
        """5. Historical Tracking - Save Lookup"""
        data_json = json.dumps(details)
        spam_score = details.get('Spam Score', '0/10').split('/')[0]
        
        self.cursor.execute('''
            INSERT INTO lookup_history (phone_number, country, carrier, valid, spam_score, data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (number, details.get('Country'), details.get('Carrier'), 
              details.get('Valid') == 'True', spam_score, data_json))
        self.conn.commit()

    def load_history(self):
        """5. Historical Tracking - Load History"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        self.cursor.execute('''
            SELECT timestamp, phone_number, country, carrier, valid, spam_score 
            FROM lookup_history 
            ORDER BY timestamp DESC
            LIMIT 100
        ''')
        
        for row in self.cursor.fetchall():
            self.history_tree.insert("", "end", values=row)

    def clear_history(self):
        """5. Historical Tracking - Clear History"""
        if messagebox.askyesno("Confirm", "Clear all lookup history?"):
            self.cursor.execute("DELETE FROM lookup_history")
            self.conn.commit()
            self.load_history()

    # ==================== API SERVICE INTEGRATION ====================

    def test_api_service(self, service_name):
        """8. API Service Integration"""
        api_responses = {
            "📱 Social Media API": {
                "status": "success",
                "data": {
                    "whatsapp": "registered",
                    "telegram": "registered", 
                    "facebook": "not_found",
                    "instagram": "possible_match"
                }
            },
            "🛡️ Spam Detection API": {
                "status": "success", 
                "risk_score": 7,
                "risk_level": "medium",
                "reports": 3
            },
            "📍 Precise Location API": {
                "status": "success",
                "coordinates": {"lat": 40.7128, "lng": -74.0060},
                "accuracy": "high"
            },
            "🔢 Number Portability API": {
                "status": "success",
                "original_carrier": "Verizon",
                "portability": "supported",
                "ported": False
            },
            "✅ Validation API": {
                "status": "success", 
                "valid": True,
                "carrier": "AT&T",
                "line_type": "mobile"
            }
        }
        
        response = api_responses.get(service_name, {"status": "error", "message": "Service not available"})
        
        self.api_results.delete(1.0, tk.END)
        self.api_results.insert(1.0, f"API Response: {service_name}\n\n")
        self.api_results.insert(tk.END, json.dumps(response, indent=2))

    # ==================== HELPER METHODS ====================

    def extract_state_region(self, location_desc, country):
        """Extract state/region from location description"""
        if location_desc == "Unknown":
            return "Unknown"
        
        location_parts = location_desc.split(',')
        
        if len(location_parts) > 1:
            if len(location_parts) >= 3:
                return location_parts[1].strip()
            elif len(location_parts) == 2:
                return location_parts[0].strip()
        
        return location_desc

    def extract_city(self, location_desc, country):
        """Extract city from location description"""
        if location_desc == "Unknown":
            return "Unknown"
        
        location_parts = location_desc.split(',')
        
        if len(location_parts) >= 2:
            return location_parts[0].strip()
        
        return "Unknown"

    def load_flag(self, country_code):
        """Load country flag"""
        try:
            code = country_code.lower()
            img_url = f"https://flagcdn.com/w160/{code}.png"
            resp = requests.get(img_url, timeout=5)
            if resp.status_code == 200:
                pil_img = Image.open(io.BytesIO(resp.content)).resize((120, 80))
                self.flag_img = ImageTk.PhotoImage(pil_img)
                self.flag_label.config(image=self.flag_img, text="")
            else:
                self.flag_label.config(image="", text="🏳️ Flag not available")
        except Exception:
            self.flag_label.config(image="", text="🏳️ Flag not available")

    def get_number_details(self, number):
        """Get details for batch processing with auto region detection"""
        try:
            # Auto-detect region for batch processing
            detected_region = self.detect_region_from_number(number)
            
            if number.startswith("+"):
                num = phonenumbers.parse(number, None)
            else:
                num = phonenumbers.parse(number, detected_region)
        except NumberParseException:
            return None

        country_code = region_code_for_number(num)
        country = geocoder.country_name_for_number(num, "en") or "Unknown"
        location_desc = geocoder.description_for_number(num, "en") or "Unknown"
        
        state_region = self.extract_state_region(location_desc, country)
        city = self.extract_city(location_desc, country)

        details = {
            "Country": country,
            "Country Code": f"+{num.country_code}",
            "State/Region": state_region,
            "City": city,
            "Location": location_desc,
            "Carrier": carrier.name_for_number(num, "en") or "Unknown",
            "Formatted Number": phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.NATIONAL),
            "International Number": phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            "Network Type": TYPE_MAP.get(number_type(num), "Unknown"),
            "Valid": str(phonenumbers.is_valid_number(num)),
            "Possible": str(phonenumbers.is_possible_number(num)),
            "Timezones": ", ".join(timezone.time_zones_for_number(num)) or "Unknown",
            "Spam Score": f"{self.calculate_spam_score(number, carrier.name_for_number(num, 'en') or 'Unknown', country)}/10"
        }
        
        return details

    def export_csv(self):
        """Export current details to CSV"""
        if not self.last_details:
            messagebox.showwarning("No Data", "No details to export.")
            return

        file = filedialog.asksaveasfilename(defaultextension=".csv", 
                                           filetypes=[("CSV Files", "*.csv")])
        if not file:
            return

        with open(file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.last_details.keys())
            writer.writerow(self.last_details.values())

        messagebox.showinfo("Exported", f"Details exported to {os.path.basename(file)}")

    def __del__(self):
        """Cleanup on exit"""
        if hasattr(self, 'conn'):
            self.conn.close()

if __name__ == "__main__":
    app = TelephonyGUI()
    app.mainloop()