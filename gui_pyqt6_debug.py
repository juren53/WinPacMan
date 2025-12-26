"""Debug version to isolate FluentWindow crash."""

import sys
from PyQt6.QtWidgets import QApplication

print("Step 1: Imports starting...")

try:
    from qfluentwidgets import FluentWindow, FluentIcon, PushButton
    print("Step 2: qfluentwidgets imported successfully")
except Exception as e:
    print(f"Step 2 FAILED: {e}")
    sys.exit(1)

print("Step 3: Creating QApplication...")
app = QApplication(sys.argv)
print("Step 4: QApplication created")

try:
    print("Step 5: Creating FluentWindow...")
    window = FluentWindow()
    print("Step 6: FluentWindow created")

    window.setWindowTitle("Debug Test")
    window.resize(800, 600)
    print("Step 7: Window configured")

    window.show()
    print("Step 8: Window shown")

    print("Step 9: Starting event loop...")
    sys.exit(app.exec())

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
