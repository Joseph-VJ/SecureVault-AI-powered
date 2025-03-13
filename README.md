# SecureVault

## A Desktop Application for Secure File Encryption, Decryption, and Data Wiping

SecureVault is a comprehensive security application built with PySide6 that provides robust file encryption, decryption, and secure data wiping capabilities with an intuitive graphical user interface.

SecureVault Logo

## Features

- **File Encryption & Decryption**
  - Multiple encryption methods (Fernet, AES-128, AES-192, AES-256, AES-256-GCM)
  - Password-based encryption with strong key derivation
  - Chunk-based processing for large files
  - Progress visualization during operations

- **Secure Data Wiping**
  - Multiple wiping standards including:
    - DoD 5220.22-M (3 Passes)
    - Gutmann (35 Passes)
    - Zero Fill (1 Pass)
    - Brigadier (5 Passes)
    - VSITR (7 Passes)
    - Russian GOST R 50739-95 (2 Passes)
    - British HMG IS5 (3 Passes)
  - Directory and file wiping
  - Secure wiping visualization and statistics
  - Special handling for SSDs

- **Key Management**
  - Generation of cryptographic keys (Fernet, AES)
  - Secure storage and loading of keys

- **Modern User Interface**
  - Clean, intuitive design with PySide6
  - Progress tracking for all operations
  - Operation summaries with performance metrics
  - Dark mode UI with modern controls

- **Advanced Security Features**
  - GPU acceleration support (when available)
  - Multi-threaded processing for better performance
  - Detailed security logging
  - Memory usage optimization

## Requirements

- Python 3.7+
- Dependencies:
  - PySide6
  - cryptography
  - matplotlib
  - joblib
  - psutil
  - wmi (Windows only)
  - pywin32 (Windows only)
  - loguru
  - numpy (optional, for GPU acceleration)
  - openai

## Installation

 Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

 Run the application:
   ```bash
   python main.py
   ```

## Usage

### File Encryption

1. Click on "Generate Key" to create a new encryption key
2. Select your preferred encryption method from the dropdown
3. Click "Encrypt File" and select the file you want to encrypt
4. Choose the key file when prompted
5. Monitor the encryption progress and review the summary when complete

### File Decryption

1. Click "Decrypt File" and select the encrypted file
2. Choose the corresponding key file when prompted
3. The application will automatically detect the encryption method used
4. Monitor the decryption progress and review the summary when complete

### Secure Wiping

1. Select your preferred wiping method from the dropdown
2. Click "Wipe Directory" and select the directory to wipe
3. Confirm the operation (this cannot be undone!)
4. Monitor the wiping progress with detailed statistics
5. Review the summary including time taken for each pass

## Project Structure

```
SecureVault/
├── main.py                   # Application entry point
├── ui.py                     # Main UI implementation
├── main_content.py           # UI content implementation
├── encryption.py             # Encryption/decryption functionality
├── key_manager.py            # Cryptographic key management
├── secure_wipe.py            # Secure data wiping implementation
├── progress_visualization.py # Progress tracking utilities
├── gpu_acceleration.py       # GPU acceleration support
├── logs.py                   # Logging functionality
└── assets/                   # Application assets
    └── prompt.json           # AI assistant prompts
```

## Security Considerations

- Always store your encryption keys in a secure location
- For maximum security, consider using hardware-based key storage
- Remember that securely wiped data may still be recoverable with specialized hardware
- Consider the strength of your encryption based on your security needs


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This tool is provided for legitimate security purposes only. Always ensure you have proper authorization before encrypting or wiping any data. The developers are not responsible for any misuse or data loss.

