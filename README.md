# Nutrition Label Generator

A Streamlit web application for generating FDA-compliant nutrition labels from Google Sheets data.

## Features

- 📊 **Google Sheets Integration**: Automatically loads nutrition data from Google Sheets
- 🏷️ **FDA-Compliant Labels**: Generates professional nutrition labels in PDF and PNG formats
- 🔄 **Batch Processing**: Generate multiple labels at once
- 🎨 **Customizable Design**: Admin panel for adjusting label dimensions, fonts, and styling
- ✅ **Real-time Connection Status**: Shows product count and connection status

## Requirements

- Python 3.8+
- Streamlit
- Google Sheet with nutrition data (must be publicly accessible)
- Pillow (PIL) - for PNG export (no poppler needed!)

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd nutritional_label_app
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run app.py
```

## Google Sheets Setup

1. Create a Google Sheet with the following columns:
   - Product
   - Serving Size
   - Energy
   - Total Fat
   - Saturated Fat
   - Trans Fat
   - Cholesterol
   - Sodium(mg)
   - Total Carbohydrate
   - Dietary Fiber
   - Total Sugars
   - Added Sugars
   - Protein
   - (Optional) Vitamin D, Calcium, Iron, Potassium

2. Make the sheet publicly accessible:
   - Click "Share" → "Change to anyone with the link" → "Viewer"

3. Update the `GOOGLE_SHEETS_URL` in `app.py` with your sheet URL

## Deployment to Streamlit Cloud

### Step 1: Push to GitHub

1. Create a new GitHub repository
2. Push your code:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

### Step 2: Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click "New app"
4. Select your repository and branch
5. Set the main file path to: `app.py`
6. Click "Deploy"

### Important Notes for Deployment

- ✅ The `fonts/` folder must be included in your repository
- ✅ Google Sheet must be publicly accessible
- ✅ PNG export works directly using PIL (no poppler needed!)
- ✅ No additional system dependencies required
- ✅ Works on all platforms (Windows, Mac, Linux, Streamlit Cloud)

## File Structure

```
nutritional_label_app/
├── app.py                 # Main application file
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .streamlit/
│   └── config.toml       # Streamlit configuration
└── fonts/
    └── Helvetica-Black.ttf  # Custom font file
```

## Usage

### User Mode
1. Select a product from the dropdown
2. Preview the nutrition label
3. Download as PDF or PNG

### Admin Mode
- Default password: `password`
- Access design controls for customizing label appearance
- View data source information
- Refresh data from Google Sheets

## Configuration

Key settings in `app.py`:
- `GOOGLE_SHEETS_URL`: Your Google Sheet URL
- `CACHE_DURATION`: Data cache duration in seconds (default: 300)
- `ADMIN_PASSWORD_HASH`: SHA-256 hash of admin password

## Troubleshooting

### Connection Issues
- Ensure Google Sheet is publicly accessible
- Check that the sheet URL is correct
- Verify column names match exactly

### PNG Export Not Working
- PNG export now uses direct PIL rendering (no poppler needed)
- Should work automatically on all platforms
- If issues occur, check that Pillow is installed: `pip install Pillow`

### Font Issues
- Ensure `fonts/Helvetica-Black.ttf` exists
- App will fall back to Helvetica-Bold if font not found

## License

This project is open source and available for use.

