#!/bin/bash
# ================================================
#   TTS Virtual Mic - macOS Build Script
#   打包为 macOS 可执行文件 (使用 PyInstaller)
# ================================================

set -e

echo "================================================"
echo "  TTS Virtual Mic - macOS Build"
echo "================================================"
echo ""

# # ---- Check Python ----
# if ! command -v pytho。/n3 &>/dev/null; then
#     echo "[ERROR] Python 3 not found. Install via: brew install python@3.11"
#     exit 1
# fi

PYTHON=$(command -v python3)
echo "[INFO] Using Python: $PYTHON"
$PYTHON --version
echo ""

# ---- Check tkinter (for GUI) ----
echo "[INFO] Checking tkinter..."
if ! $PYTHON -c "import tkinter" 2>/dev/null; then
    echo "[WARN] tkinter not found. GUI version will not work."
    echo "       Install with: brew install python-tk@3.11"
    echo "       CLI version will still be built."
    BUILD_GUI=false
else
    BUILD_GUI=true
    echo "[OK] tkinter available"
fi
echo ""

# ---- Install dependencies ----
echo "[1/3] Installing dependencies..."
$PYTHON -m pip install -r requirements.txt --quiet
echo "[OK] Dependencies installed"
echo ""

# ---- Build CLI version ----
echo "[2/3] Building tts_mic (CLI version)..."
$PYTHON -m PyInstaller --noconfirm tts_mic.spec
echo "[OK] CLI build complete -> dist/tts_mic"
echo ""

# ---- Build GUI version (if tkinter available) ----
if [ "$BUILD_GUI" = true ]; then
    echo "[3/3] Building tts_mic_gui (GUI version)..."
    $PYTHON -m PyInstaller --noconfirm tts_mic_gui.spec
    echo "[OK] GUI build complete -> dist/tts_mic_gui"
else
    echo "[3/3] Skipping GUI build (tkinter not available)"
fi

echo ""
echo "================================================"
echo "  Build complete!"
echo "================================================"
echo ""
echo "Outputs:"
ls -lh dist/ 2>/dev/null
echo ""
echo "Usage:"
echo "  ./dist/tts_mic         # CLI version"
if [ "$BUILD_GUI" = true ]; then
    echo "  ./dist/tts_mic_gui     # GUI version"
fi
echo ""
echo "Prerequisites:"
echo "  brew install blackhole-2ch    # Virtual audio device"
echo "  brew install python-tk@3.11   # For GUI support"
echo ""
