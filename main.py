"""
VORTEX OSINT - Graphical Intelligence & Reconnaissance Suite
Entry Point
"""
import sys
import os

# Add root folder to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.app import VortexApp


def main():
    try:
        app = VortexApp()
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"[!] Critical Error launching VORTEX OSINT: {e}")
        raise e


if __name__ == "__main__":
    main()
