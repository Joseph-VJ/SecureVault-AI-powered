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

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/SecureVault.git
   cd SecureVault
   ```

2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
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

## License

[Specify your license here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This tool is provided for legitimate security purposes only. Always ensure you have proper authorization before encrypting or wiping any data. The developers are not responsible for any misuse or data loss.

Citations:
[1] https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/31836909/89eb5d52-0e30-4a05-84e9-39c83b5fcc04/progress_visualization.py
[2] https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/31836909/9a41e6b3-2667-4f95-b08c-997ef84e5be4/gpu_acceleration.py
[3] https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/31836909/1ce15652-c2b8-4e2a-98d7-017147a3ddf0/main.py
[4] https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/31836909/5a22afff-251e-414b-b26e-e8396f3be94a/encryption.py
[5] https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/31836909/d8d0c059-2036-4dd6-b81b-d29b9587f041/key_manager.py
[6] https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/31836909/7c01be2d-8ae3-4373-8921-df22f1e9c3e8/logs.py
[7] https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/31836909/a905d174-d816-4d32-8848-89e455875bc5/secure_wipe.py
[8] https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/31836909/27767f10-b267-44ad-a392-e77074075814/ui.py
[9] https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/31836909/bfdeb8bb-2b6f-4b4c-a4d7-5a887efc1155/main_content.py
[10] https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/31836909/0d7f3fc5-f756-4e94-92d1-775cc905560c/prompt.json

---
Answer from Perplexity: pplx.ai/share
