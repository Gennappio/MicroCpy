# Sharing OpenCellComms with Your Team

This guide explains how to share the OpenCellComms project with your team members.

## What's Been Set Up

Your project now has everything needed for easy team collaboration:

### ✅ One-Click Installation
- `install.sh` - macOS/Linux installer
- `install.bat` - Windows installer

### ✅ One-Click Launch
- `run.sh` - macOS/Linux launcher
- `run.bat` - Windows launcher

### ✅ Comprehensive Documentation
- `README.md` - Project overview and quick start
- `docs/INSTALL.md` - Detailed installation guide
- `docs/USAGE.md` - Usage guide for GUI and CLI

### ✅ Cross-Platform Support
All scripts work on Windows, macOS, and Linux

## How to Share

### Option 1: Git Repository (Recommended)

If you're using GitHub, GitLab, or similar:

```bash
# Push your changes
git push origin NodeObservability

# Share the repository URL with your team
```

Team members can then:
```bash
git clone <repository-url>
cd OpenCellComms
./install.sh  # or install.bat on Windows
./run.sh      # or run.bat on Windows
```

### Option 2: Zip Archive

If not using Git hosting:

```bash
# Create a zip archive (excluding unnecessary files)
zip -r opencellcomms.zip . -x "*.pyc" -x "*__pycache__*" -x "node_modules/*" -x ".venv/*" -x "*.egg-info/*"
```

Share the zip file with your team. They should:
1. Extract the archive
2. Run the installer
3. Run the launcher

## Team Member Instructions

Send this to your team:

---

### Getting Started with OpenCellComms

**Prerequisites:**
- Python 3.8+
- Node.js 18+
- npm 7+

**Installation (one-time):**

macOS/Linux:
```bash
cd OpenCellComms
chmod +x install.sh
./install.sh
```

Windows:
```batch
cd OpenCellComms
install.bat
```

**Running:**

macOS/Linux:
```bash
./run.sh
```

Windows:
```batch
run.bat
```

Then open http://localhost:3000 in your browser.

**Documentation:**
- See `docs/INSTALL.md` for detailed installation help
- See `docs/USAGE.md` for usage instructions
- See `README.md` for project overview

---

## Troubleshooting for Team Members

### "Python not found"
Install Python 3.8+ from https://www.python.org/downloads/

### "Node.js not found"
Install Node.js 18+ from https://nodejs.org/

### Permission errors on macOS/Linux
```bash
chmod +x install.sh run.sh
```

### Port already in use
If ports 3000 or 5001 are in use, stop other services or modify the ports in:
- Frontend: `opencellcomms_gui/vite.config.js`
- Backend: `opencellcomms_gui/server/api.py`

## Next Steps

1. **Push to Git** - Make sure all changes are pushed to your repository
2. **Share Repository URL** - Send the clone URL to your team
3. **Provide Quick Start** - Share the team member instructions above
4. **Set Up CI/CD** (Optional) - Consider GitHub Actions for automated testing

## Support

If team members have issues:
1. Check the documentation in `docs/`
2. Verify prerequisites are installed
3. Check the terminal output for specific error messages
4. Open an issue in your repository (if using Git hosting)

