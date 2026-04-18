import os
os.environ['QT_QPA_PLATFORM'] = 'xcb'

import sys
import traceback

def log(msg):
    print(f"[MODUL910] {msg}", flush=True)

log("Starting...")

try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import Qt
    
    app = QApplication(sys.argv)
    
    log("Importing exec_DMMCD...")
    from pages.Modul910.mainDMMCD import exec_DMMCD
    
    log("Calling exec_DMMCD...")
    window = exec_DMMCD(nama="Test User", npm="12345", kelompok="K01")
    
    log(f"Window: {window}")
    log(f"Window type: {type(window)}")
    
    # Force window to be visible and on screen
    window.setWindowFlags(window.windowFlags() | Qt.Window)
    window.activateWindow()
    window.raise_()
    
    log("Window flags set")
    
    # Check if window has a valid geometry
    screen_geo = app.desktop().screenGeometry()
    log(f"Screen geometry: {screen_geo}")
    
    # Center window on screen
    window_geo = window.geometry()
    log(f"Window geometry before: {window_geo}")
    
    x = (screen_geo.width() - window.width()) // 2
    y = (screen_geo.height() - window.height()) // 2
    window.move(x, y)
    log(f"Window moved to ({x}, {y})")
    
    window.show()
    window.activateWindow()
    window.raise_()
    
    log("Window should be visible now")
    
    # Force process events
    app.processEvents()
    
    log("Entering event loop...")
    sys.exit(app.exec_())
    
except Exception as e:
    log(f"ERROR: {e}")
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)
