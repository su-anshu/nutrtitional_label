import streamlit as st
import pandas as pd
import io
import os
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black
import zipfile
from datetime import datetime
import hashlib
import re
import shutil

# Configuration - make these more flexible
class Config:
    FONT_PATH = "fonts/Helvetica-Black.ttf"
    # POPPLER_PATH: Set to None for auto-detect, or specify path like r"C:\poppler\Library\bin"
    POPPLER_PATH = r"C:\poppler\Library\bin"  # Windows path - set to None for auto-detect on other platforms
    GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/1GPxWXnx6fPJEmgjpsmUvlQdcMKRrc2yPGBcwdI6y10A/edit?usp=sharing"
    ADMIN_PASSWORD_HASH = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"  # "password" hashed
    CACHE_DURATION = 300  # Cache data for 5 minutes

def find_poppler_path():
    """Auto-detect poppler installation path"""
    # Check if poppler is in PATH
    poppler_bin = shutil.which("pdftoppm")
    if poppler_bin:
        # Return the directory containing the binary
        return os.path.dirname(poppler_bin)
    
    # Common installation paths
    common_paths = [
        "/usr/bin",  # Linux/Streamlit Cloud
        "/usr/local/bin",  # macOS/Linux
        r"C:\poppler\Library\bin",  # Windows
        r"C:\Program Files\poppler\bin",  # Windows alternative
    ]
    
    # Check for executables (with .exe on Windows)
    import platform
    is_windows = platform.system() == "Windows"
    exe_ext = ".exe" if is_windows else ""
    
    for path in common_paths:
        # Check for pdftoppm executable
        pdftoppm_path = os.path.join(path, f"pdftoppm{exe_ext}")
        if os.path.exists(pdftoppm_path):
            return path
        # Also check without extension (for Linux/Mac)
        if not is_windows and os.path.exists(os.path.join(path, "pdftoppm")):
            return path
    
    return None

# %DV Reference Values (FDA 2016 updates)
Config.DAILY_VALUES = {
    "Energy": 2000,
    "Total Fat": 78,
    "Saturated Fat": 20,
    "Cholesterol": 300,
    "Sodium(mg)": 2300,
    "Total Carbohydrate": 275,
    "Dietary Fiber": 28,
    "Added Sugars": 50,
    "Protein": 50,
    "Vitamin D": 20,  # mcg
    "Calcium": 1300,  # mg
    "Iron": 18,       # mg
    "Potassium": 4700 # mg
}

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_admin_password(password):
    """Verify admin password"""
    return hash_password(password) == Config.ADMIN_PASSWORD_HASH

def convert_google_sheets_url_to_csv(url):
    """Convert Google Sheets sharing URL to CSV export URL"""
    # Extract sheet ID from URL
    # Pattern: /d/{SHEET_ID}/
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if match:
        sheet_id = match.group(1)
        # Default to gid=0 (first sheet)
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
        return csv_url
    else:
        raise ValueError("Invalid Google Sheets URL format")

@st.cache_data(ttl=Config.CACHE_DURATION)
def load_data_from_google_sheets(url=None):
    """Load nutrition data from Google Sheets with caching"""
    if url is None:
        url = Config.GOOGLE_SHEETS_URL
    
    csv_url = convert_google_sheets_url_to_csv(url)
    # Read CSV directly from Google Sheets export URL
    df = pd.read_csv(csv_url)
    
    # Clean up column names (remove extra spaces, handle special characters)
    df.columns = df.columns.str.strip()
    
    return df

def show_connection_status():
    """Display Google Sheets connection status and product count"""
    try:
        df = load_data_from_google_sheets()
        product_count = len(df["Product"].dropna().unique()) if "Product" in df.columns else 0
        total_rows = len(df)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Success indicator with prominent display
        st.success(f"✅ **Connected to Google Sheets** | **{product_count} products loaded** | {total_rows} total rows | Last updated: {timestamp}")
        return True, df
    except Exception as e:
        st.error(f"❌ **Connection Failed**: Unable to load data from Google Sheets")
        st.warning(f"Error details: {str(e)}")
        st.info("💡 Make sure the Google Sheet is publicly accessible or shared with view permissions.")
        return False, None

def get_default_design_params():
    """Get default design parameters"""
    return {
        'width': 270, 'height': 370,
        'line_thick': 3, 'line_thin': 0,
        'font_header': 27, 'font_subheader': 13,
        'font_nutrient': 10, 'font_footnote': 7,
        'header_spacing': 2, 'nutrient_leading': 17,
        'thick_spacing': 8, 'thin_offset': 5,
        'nutrients_gap': 33, 'footnote_start': 35,
        'footnote_spacing': 8
    }

# Initialize font registration with error handling
def setup_fonts():
    try:
        if os.path.exists(Config.FONT_PATH):
            pdfmetrics.registerFont(TTFont("Helvetica-Black", Config.FONT_PATH))
            return True
        else:
            return False
    except Exception as e:
        return False

# Enhanced PDF generator with better error handling
class NutritionLabelGenerator:
    def __init__(self, design_params):
        self.params = design_params
        self.has_custom_font = setup_fonts()
    
    def draw_spaced_text(self, c, text, x, y, font_name, font_size, spacing):
        """Draw text with custom letter spacing"""
        if not self.has_custom_font and font_name == "Helvetica-Black":
            font_name = "Helvetica-Bold"
        
        c.setFont(font_name, font_size)
        for ch in text:
            c.drawString(x, y, ch)
            x += pdfmetrics.stringWidth(ch, font_name, font_size) + spacing
    
    def format_value(self, value, unit="g"):
        """Format nutritional values consistently"""
        if pd.isna(value) or value == 0:
            return "0"
        
        if isinstance(value, (int, float)):
            if value == int(value):
                return str(int(value))
            else:
                return f"{value:.1f}".rstrip('0').rstrip('.')
        return str(value)
    
    def calculate_percent_dv(self, nutrient, value):
        """Calculate %Daily Value with better handling"""
        key = nutrient.strip()
        dv_val = Config.DAILY_VALUES.get(key)
        
        if not dv_val or pd.isna(value) or value <= 0:
            return ""
        
        percent = (value / dv_val) * 100
        if percent < 1:
            return "<1%"
        else:
            return f"{percent:.0f}%"
    
    def wrap_text(self, c, text, max_width, font_name, font_size):
        """Improved text wrapping"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = f"{current_line} {word}".strip()
            width = c.stringWidth(test_line, font_name, font_size)
            
            if width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def create_pdf(self, data: dict) -> bytes:
        """Generate nutrition label PDF with enhanced formatting"""
        p = self.params
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(p['width'], p['height']))
        
        # Calculate positions
        y_positions = self._calculate_positions(p)
        x_left = 10
        x_right = p['width'] - 10
        
        # Draw border
        c.setLineWidth(p['line_thick'])
        c.rect(0, 0, p['width'], p['height'])
        
        # Title
        title_font = "Helvetica-Black" if self.has_custom_font else "Helvetica-Bold"
        self.draw_spaced_text(c, "Nutrition Facts", x_left, y_positions['header'], 
                             title_font, p['font_header'], p['header_spacing'])
        
        # Separator after title
        c.setLineWidth(p['line_thin'])
        c.line(x_left, y_positions['header_sep'], x_right, y_positions['header_sep'])
        
        # Serving information
        c.setFont("Helvetica-Bold", p['font_subheader'])
        serving_text = f"Serving size                       {data.get('Serving Size', 'N/A')}"
        c.drawString(x_left + 2, y_positions['serving'], serving_text)
        
        # Serving note
        c.setFont("Helvetica", 8)
        note = "Number of servings may vary based on pack size and intended use."
        c.drawString(x_left + 2, y_positions['serving_note'], note)
        
        # Thick separator
        c.setLineWidth(p['line_thick'])
        c.line(x_left, y_positions['serving_sep'], x_right, y_positions['serving_sep'])
        
        # Energy/Calories
        c.setFont("Helvetica-Bold", p['font_subheader'])
        c.drawString(x_left + 2, y_positions['energy'], "Energy")
        c.setFont("Helvetica-Bold", 20)
        energy_val = self.format_value(data.get("Energy", 0), "")
        c.drawRightString(x_right - 2, y_positions['energy'], energy_val)
        
        c.line(x_left, y_positions['energy_sep'], x_right, y_positions['energy_sep'])
        
        # Nutrients
        self._draw_nutrients(c, data, y_positions, x_left, x_right, p)
        
        # Footnotes
        self._draw_footnotes(c, data, y_positions, x_left, p)
        
        c.showPage()
        c.save()
        return buffer.getvalue()
    
    def create_png(self, data: dict, dpi: int = 300) -> bytes:
        """Generate nutrition label PNG with high quality"""
        try:
            # First create PDF
            pdf_bytes = self.create_pdf(data)
            
            # Convert PDF to PNG using pdf2image
            from pdf2image import convert_from_bytes
            
            # Auto-detect poppler path if not set
            poppler_path = Config.POPPLER_PATH
            if not poppler_path:
                poppler_path = find_poppler_path()
            
            # Validate poppler path if specified
            if poppler_path:
                import platform
                is_windows = platform.system() == "Windows"
                exe_ext = ".exe" if is_windows else ""
                pdftoppm_path = os.path.join(poppler_path, f"pdftoppm{exe_ext}")
                if not os.path.exists(pdftoppm_path):
                    # Path doesn't exist, try auto-detection
                    poppler_path = find_poppler_path()
            
            # Try conversion with detected/specified poppler path
            try:
                images = convert_from_bytes(
                    pdf_bytes, 
                    dpi=dpi,
                    poppler_path=poppler_path
                )
            except Exception as e:
                # If that fails, try without poppler_path (system PATH)
                if poppler_path:
                    try:
                        images = convert_from_bytes(
                            pdf_bytes, 
                            dpi=dpi,
                            poppler_path=None
                        )
                    except:
                        raise e  # Re-raise original error if PATH also fails
                else:
                    raise
            
            if images:
                # Convert PIL image to bytes
                img_buffer = io.BytesIO()
                images[0].save(img_buffer, format='PNG', optimize=True)
                return img_buffer.getvalue()
            else:
                raise Exception("No images generated from PDF")
                
        except ImportError:
            raise Exception("pdf2image library is required for PNG export. Please install: pip install pdf2image")
        except Exception as e:
            error_msg = str(e)
            if "poppler" in error_msg.lower() or "pdftoppm" in error_msg.lower():
                raise Exception(f"PNG conversion failed: Poppler not found. Please ensure poppler-utils is installed. Error: {error_msg}")
            raise Exception(f"PNG conversion failed: {error_msg}")
    
    def _calculate_positions(self, p):
        """Calculate all Y positions for layout elements"""
        positions = {}
        positions['header'] = p['height'] - 10 - p['font_header']
        positions['header_sep'] = positions['header'] - p['thick_spacing']
        positions['serving'] = positions['header_sep'] - 20
        positions['serving_note'] = positions['serving'] - 12
        positions['serving_sep'] = positions['serving_note'] - 6
        positions['energy'] = positions['serving_sep'] - 20
        positions['energy_sep'] = positions['energy'] - p['thick_spacing']
        positions['nutrients_start'] = positions['energy_sep'] - p['nutrients_gap']
        return positions
    
    def _draw_nutrients(self, c, data, y_positions, x_left, x_right, p):
        """Draw all nutrient information"""
        nutrient_order = [
            "Total Fat", "  Saturated Fat", "   Trans Fat", "Cholesterol", "Sodium(mg)",
            "Total Carbohydrate", "  Dietary Fiber", "  Total Sugars", "   Added Sugars", 
            "Protein", "Vitamin D", "Calcium", "Iron", "Potassium"
        ]
        
        y_pos = y_positions['nutrients_start']
        # Add "% Daily Value" text above nutrients
        c.setFont("Helvetica-Bold", p['font_nutrient'])
        dv_text = "% Daily Value *"
        c.drawRightString(x_right - 2, y_pos + p['nutrient_leading'], dv_text)
        # Add thin line under the "% Daily Value" text
        c.setLineWidth(p['line_thin'])
        c.line(x_left, y_pos + p['nutrient_leading'] - p['thin_offset'], 
            x_right, y_pos + p['nutrient_leading'] - p['thin_offset'])
        
        
        
        
        for nutrient in nutrient_order:
            if nutrient not in data or pd.isna(data[nutrient]):
                continue
                
            value = data[nutrient]
            # Show all nutrients regardless of value
            
            # Font selection
            font = "Helvetica" if nutrient.startswith("  ") else "Helvetica-Bold"
            c.setFont(font, p['font_nutrient'])
            
            # Unit determination
            if nutrient in ["Cholesterol", "Sodium(mg)", "Calcium", "Iron", "Potassium"]:
                unit = "mg"
            elif nutrient == "Vitamin D":
                unit = "mcg"
            else:
                unit = "g"
            
            # Format label
            val_str = self.format_value(value, unit)
            clean_name = nutrient.replace("(mg)", "")
            label = f"{clean_name} {val_str}{unit}"
            
            # Calculate %DV
            percent = self.calculate_percent_dv(nutrient, value)
            
            # Draw nutrient line
            c.drawString(x_left + 2, y_pos, label)
            if percent:
                c.drawRightString(x_right - 2, y_pos, percent)
            
            # Separator line
            if nutrient not in ["Protein", "Potassium"]:  # No line after last nutrient
                c.setLineWidth(p['line_thin'])
                c.line(x_left, y_pos - p['thin_offset'], x_right, y_pos - p['thin_offset'])
            
            y_pos -= p['nutrient_leading']
        
        # Final thick line (closer to last nutrient)
        c.setLineWidth(p['line_thick'])
        c.line(x_left, y_pos + p['nutrient_leading'] - p['thin_offset'], x_right, y_pos + p['nutrient_leading'] - p['thin_offset'])
    
    def _draw_footnotes(self, c, data, y_positions, x_left, p):
        """Draw footnote text with proper wrapping"""
        c.setFont("Helvetica", p['font_footnote'])
        max_width = p['width'] - 20
        
        # Default footnote
        footnote1 = data.get("Footnote", 
            "* The % Daily Value (DV) tells you how much a nutrient in a serving "
            "of food contributes to a daily diet. 2,000 calories a day is used "
            "for general nutrition advice.")
        
        lines1 = self.wrap_text(c, footnote1, max_width, "Helvetica", p['font_footnote'])
        
        y = p['footnote_start'] + (len(lines1) - 1) * p['footnote_spacing']
        for line in lines1:
            c.drawString(x_left + 2, y, line)
            y -= p['footnote_spacing']
        
        # Optional second footnote
        if "Footnote2" in data and data["Footnote2"]:
            y -= p['footnote_spacing']
            lines2 = self.wrap_text(c, data["Footnote2"], max_width, "Helvetica", p['font_footnote'])
            for line in lines2:
                c.drawString(x_left + 2, y, line)
                y -= p['footnote_spacing']

def admin_panel():
    """Admin panel with design controls and file upload"""
    st.header("🔒 Admin Panel")
    
    # Admin controls with better organization
    st.subheader("🛠 Label Design Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📐 Dimensions**")
        label_width = st.slider("Label Width", 200, 400, 270, 10)
        label_height = st.slider("Label Height", 300, 800, 370, 10)
        
        st.markdown("**📝 Typography**")
        font_header = st.slider("Header Font Size", 16, 36, 27)
        font_subheader = st.slider("Subheader Font Size", 8, 20, 13)
        font_nutrient = st.slider("Nutrient Font Size", 6, 18, 10)
        font_footnote = st.slider("Footnote Font Size", 4, 10, 7)
        header_spacing = st.slider("Header Letter Spacing", 0, 5, 2)
    
    with col2:
        st.markdown("**📏 Lines & Spacing**")
        line_thick = st.slider("Thick Line Width", 1, 5, 3)
        line_thin = st.slider("Thin Line Width", 0, 2, 0)
        nutrient_leading = st.slider("Line Spacing", 10, 30, 17)
        thick_spacing = st.slider("Thick Line Padding", 0, 15, 8)
        thin_offset = st.slider("Thin Line Offset", 0, 12, 5)
        nutrients_gap = st.slider("Nutrients Start Gap", 5, 50, 33)
        
        st.markdown("**📄 Footnotes**")
        footnote_start = st.slider("Footnote Start Y", 20, 80, 35)
        footnote_spacing = st.slider("Footnote Line Spacing", 5, 20, 8)
    
    st.markdown("**🖼️ PNG Export Settings**")
    png_dpi = st.slider("PNG Quality (DPI)", 150, 600, 300, 50)
    st.info("Higher DPI = better quality but larger file size")
    
    # Google Sheets data section
    st.subheader("📊 Data Source")
    
    # Show connection status at the top
    st.markdown("---")
    connection_ok, df = show_connection_status()
    st.markdown("---")
    
    if not connection_ok:
        return
    
    # Show data preview
    try:
        st.markdown("**Data Preview:**")
        st.dataframe(df.head(), use_container_width=True)
        product_count = len(df["Product"].dropna().unique()) if "Product" in df.columns else 0
        st.info(f"📊 **{product_count} products** available | Data cached for {Config.CACHE_DURATION // 60} minutes")
        
        # Refresh button
        if st.button("🔄 Refresh Data", use_container_width=True):
            load_data_from_google_sheets.clear()
            st.rerun()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.info("💡 Make sure the Google Sheet is publicly accessible or shared with view permissions.")
    
    return {
        'width': label_width, 'height': label_height,
        'line_thick': line_thick, 'line_thin': line_thin,
        'font_header': font_header, 'font_subheader': font_subheader,
        'font_nutrient': font_nutrient, 'font_footnote': font_footnote,
        'header_spacing': header_spacing, 'nutrient_leading': nutrient_leading,
        'thick_spacing': thick_spacing, 'thin_offset': thin_offset,
        'nutrients_gap': nutrients_gap, 'footnote_start': footnote_start,
        'footnote_spacing': footnote_spacing, 'png_dpi': png_dpi
    }

def user_panel(design_params):
    """User panel with limited functionality"""
    st.header("🥗 Nutrition Label Generator")
    st.markdown("Generate FDA-compliant nutrition labels")
    
    # Show connection status at the top
    st.markdown("---")
    connection_ok, df = show_connection_status()
    st.markdown("---")
    
    if not connection_ok:
        return
    
    try:
        
        # Enhanced column validation
        required_columns = {
            "Product", "Serving Size", "Energy", "Total Fat", "Saturated Fat", 
            "Trans Fat", "Cholesterol", "Sodium(mg)", "Total Carbohydrate", 
            "Dietary Fiber", "Total Sugars", "Added Sugars", "Protein"
        }
        
        missing_cols = required_columns - set(df.columns)
        if missing_cols:
            st.error(f"❌ Data file missing required columns: {', '.join(missing_cols)}")
            st.info("💡 Please contact administrator to fix the data file.")
            return
        
        # Product selection
        products = df["Product"].dropna().unique()
        if len(products) == 0:
            st.warning("No products found in the data.")
            return
        
        # Multi-select for batch processing
        batch_mode = st.checkbox("🔄 Batch Mode - Generate multiple labels")
        
        if batch_mode:
            selected_products = st.multiselect("Select products to generate", products, default=[products[0]])
        else:
            selected_product = st.selectbox("Choose Product", products)
            selected_products = [selected_product] if selected_product else []
        
        if selected_products:
            generator = NutritionLabelGenerator(design_params)
            
            if len(selected_products) == 1:
                # Single label generation
                product = selected_products[0]
                row = df[df["Product"] == product].iloc[0]
                data = prepare_data(row)
                
                # Generate and preview
                pdf_bytes = generator.create_pdf(data)
                preview_label(pdf_bytes , preview_width=300)
                
                # Download buttons in columns
                col1, col2 = st.columns(2)
                
                with col1:
                    st.download_button(
                        label="⬇️ Download as PDF",
                        data=pdf_bytes,
                        file_name=f"{product}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                
                with col2:
                    # PNG generation with error handling
                    try:
                        png_bytes = generator.create_png(data, dpi=design_params.get('png_dpi', 300))
                        st.download_button(
                            label="🖼️ Download as PNG",
                            data=png_bytes,
                            file_name=f"{product}.png",
                            mime="image/png",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"PNG generation failed: {e}")
                        if "pdf2image" in str(e):
                            st.info("💡 PNG export not available - missing dependencies")
            else:
                # Batch generation
                st.info(f"🔄 Generating {len(selected_products)} labels...")
                
                # Batch download options
                format_choice = st.radio(
                    "Choose batch download format:",
                    ["PDF Only", "PNG Only", "Both PDF and PNG"],
                    horizontal=True
                )
                
                if format_choice == "PDF Only":
                    zip_buffer = create_batch_labels(df, selected_products, generator, format_type="pdf")
                    file_ext = "pdf"
                elif format_choice == "PNG Only":
                    zip_buffer = create_batch_labels(df, selected_products, generator, format_type="png", png_dpi=design_params.get('png_dpi', 300))
                    file_ext = "png"
                else:  # Both
                    zip_buffer = create_batch_labels(df, selected_products, generator, format_type="both", png_dpi=design_params.get('png_dpi', 300))
                    file_ext = "mixed"
                
                if zip_buffer:
                    st.download_button(
                        label=f"⬇️ Download All Labels ({len(selected_products)} files)",
                        data=zip_buffer,
                        file_name=f"NutritionLabels_{file_ext}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip"
                    )
    
    except Exception as e:
        st.error(f"Error processing data: {e}")

# Streamlit UI
def main():
    st.set_page_config(
        page_title="Nutrition Label Generator Pro", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'design_params' not in st.session_state:
        st.session_state.design_params = get_default_design_params()
    
    # Sidebar for admin login
    with st.sidebar:
        st.title("🔐 Access Control")
        
        if not st.session_state.is_admin:
            st.markdown("### Admin Login")
            password = st.text_input("Enter Admin Password", type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Login as Admin", use_container_width=True):
                    if verify_admin_password(password):
                        st.session_state.is_admin = True
                        st.success("✅ Admin access granted!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid password")
            
            with col2:
                if st.button("Continue as User", use_container_width=True):
                    st.session_state.is_admin = False
                    st.info("👤 User mode selected")
        else:
            st.success("🔒 Admin Mode Active")
            if st.button("Logout", use_container_width=True):
                st.session_state.is_admin = False
                st.session_state.design_params = get_default_design_params()
                st.rerun()
        
        st.markdown("---")
        st.markdown("**Current Mode:** " + ("🔒 Admin" if st.session_state.is_admin else "👤 User"))
    
    # Main content area
    if st.session_state.is_admin:
        # Admin panel
        st.session_state.design_params = admin_panel()
        
        # Divider
        st.markdown("---")
        st.markdown("## 👤 User View Preview")
        user_panel(st.session_state.design_params)
    else:
        # User panel only
        user_panel(st.session_state.design_params)
        
        # Show sample data format for users
        with st.expander("📋 Sample Data Format"):
            sample_data = {
                "Product": ["Sample Product 1", "Sample Product 2"],
                "Serving Size": ["1 cup (240g)", "2 pieces (85g)"],
                "Energy": [150, 200],
                "Total Fat": [8.0, 12.0],
                "Saturated Fat": [3.0, 4.5],
                "Trans Fat": [0.0, 0.0],
                "Cholesterol": [25, 30],
                "Sodium(mg)": [580, 650],
                "Total Carbohydrate": [15.0, 18.0],
                "Dietary Fiber": [3.0, 2.0],
                "Total Sugars": [5.0, 8.0],
                "Added Sugars": [2.0, 6.0],
                "Protein": [8.0, 10.0]
            }
            st.dataframe(pd.DataFrame(sample_data))

def prepare_data(row):
    """Prepare nutrition data from DataFrame row"""
    data = {
        "Serving Size": str(row["Serving Size"]),
        "Energy": float(row["Energy"]) if pd.notna(row["Energy"]) else 0,
        "Total Fat": float(row["Total Fat"]) if pd.notna(row["Total Fat"]) else 0,
        "  Saturated Fat": float(row["Saturated Fat"]) if pd.notna(row["Saturated Fat"]) else 0,
        "   Trans Fat": float(row["Trans Fat"]) if pd.notna(row["Trans Fat"]) else 0,
        "Cholesterol": float(row["Cholesterol"]) if pd.notna(row["Cholesterol"]) else 0,
        "Sodium(mg)": float(row["Sodium(mg)"]) if pd.notna(row["Sodium(mg)"]) else 0,
        "Total Carbohydrate": float(row["Total Carbohydrate"]) if pd.notna(row["Total Carbohydrate"]) else 0,
        "  Dietary Fiber": float(row["Dietary Fiber"]) if pd.notna(row["Dietary Fiber"]) else 0,
        "  Total Sugars": float(row["Total Sugars"]) if pd.notna(row["Total Sugars"]) else 0,
        "   Added Sugars": float(row["Added Sugars"]) if pd.notna(row["Added Sugars"]) else 0,
        "Protein": float(row["Protein"]) if pd.notna(row["Protein"]) else 0,
    }
    
    # Optional nutrients
    optional_nutrients = ["Vitamin D", "Calcium", "Iron", "Potassium"]
    for nutrient in optional_nutrients:
        if nutrient in row.index and pd.notna(row[nutrient]):
            data[nutrient] = float(row[nutrient])
    
    # Footnotes
    data["Footnote"] = row.get("Footnote", 
        "* The % Daily Value (DV) tells you how much a nutrient in a serving "
        "of food contributes to a daily diet. 2,000 calories a day is used "
        "for general nutrition advice.")
    
    # Add default Footnote2 or use custom one from Google Sheets
    data["Footnote2"] = row.get("Footnote2", 
        "* Values are approximate and based on standard food composition tables. "
        "Actual values may vary.")
    
    return data

def preview_label(pdf_bytes, preview_width=300):
    """Show label preview if possible"""
    try:
        from pdf2image import convert_from_bytes
        
        # Auto-detect poppler path if not set
        poppler_path = Config.POPPLER_PATH
        if not poppler_path:
            poppler_path = find_poppler_path()
        
        try:
            images = convert_from_bytes(pdf_bytes, poppler_path=poppler_path, dpi=150)
        except:
            # Fallback to system PATH
            images = convert_from_bytes(pdf_bytes, poppler_path=None, dpi=150)
        
        st.image(images[0], caption="📋 Nutrition Label Preview", width=preview_width, use_container_width=False)
    except ImportError:
        st.info("💡 Install pdf2image and poppler to see label preview")
    except Exception as e:
        st.warning(f"Preview not available: {e}")

def create_batch_labels(df, products, generator, format_type="pdf", png_dpi=300):
    """Create ZIP file with multiple nutrition labels in specified format(s)"""
    zip_buffer = io.BytesIO()
    
    try:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for product in products:
                try:
                    row = df[df["Product"] == product].iloc[0]
                    data = prepare_data(row)
                    
                    # Clean filename
                    safe_name = "".join(c for c in product if c.isalnum() or c in (' ', '-', '_')).strip()
                    
                    if format_type in ["pdf", "both"]:
                        # Generate PDF
                        pdf_bytes = generator.create_pdf(data)
                        pdf_filename = f"{safe_name}.pdf"
                        zip_file.writestr(pdf_filename, pdf_bytes)
                    
                    if format_type in ["png", "both"]:
                        # Generate PNG
                        try:
                            png_bytes = generator.create_png(data, dpi=png_dpi)
                            png_filename = f"{safe_name}.png"
                            zip_file.writestr(png_filename, png_bytes)
                        except Exception as png_error:
                            st.warning(f"PNG generation failed for {product}: {png_error}")
                            # Continue with other products
                        
                except Exception as e:
                    st.warning(f"Error generating label for {product}: {e}")
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    except Exception as e:
        st.error(f"Batch generation failed: {e}")
        return None

if __name__ == "__main__":
    main()