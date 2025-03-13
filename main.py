import sys
from PySide6.QtWidgets import QApplication
from ui import SecureVaultApp

def main() -> None:
    """Run the Secure Vault application."""
    app = QApplication(sys.argv)
    window = SecureVaultApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()