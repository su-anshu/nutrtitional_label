# Streamlit Cloud Deployment Checklist

## Pre-Deployment Checklist

- [x] ✅ All dependencies listed in `requirements.txt`
- [x] ✅ Google Sheets URL configured in `app.py`
- [x] ✅ Font file (`fonts/Helvetica-Black.ttf`) included in repository
- [x] ✅ `.streamlit/config.toml` created
- [x] ✅ `.gitignore` configured
- [x] ✅ PNG generation uses direct PIL rendering (no poppler needed!)
- [x] ✅ No hardcoded Windows paths
- [x] ✅ Google Sheet is publicly accessible

## Quick Deployment Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push
   ```

2. **Deploy on Streamlit Cloud**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Connect your GitHub repository
   - Set main file: `app.py`
   - Click "Deploy"

3. **Verify Deployment**
   - Check connection status shows product count
   - Test label generation
   - Verify PDF download works
   - Test PNG export (should work automatically)

## Post-Deployment

- [ ] Test Google Sheets connection
- [ ] Verify product count displays correctly
- [ ] Test PDF generation
- [ ] Test PNG generation
- [ ] Test batch label generation
- [ ] Verify admin panel access

## Troubleshooting

### If connection fails:
- Verify Google Sheet is publicly accessible
- Check sheet URL is correct
- Ensure column names match expected format

### If PNG export fails:
- PNG export now uses direct PIL rendering (no poppler needed)
- Should work automatically on all platforms
- Verify Pillow is installed: `pip install Pillow`

### If font not loading:
- Verify `fonts/Helvetica-Black.ttf` is in repository
- App will fall back to Helvetica-Bold if needed

