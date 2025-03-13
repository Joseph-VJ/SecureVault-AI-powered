import os
import subprocess
import logging
import psutil
import wmi
from loguru import logger
import win32api
import win32con
import win32security
from joblib import Parallel, delayed
import shutil

def secure_wipe_file(target_path, passes=1, patterns=None, delete_after=True):
    """
    Securely wipe a single file by overwriting it with specified patterns and then deleting it if specified.
    
    Args:
        target_path (str): Path to the file to wipe.
        passes (int): Number of overwrite passes.
        patterns (list): List of byte patterns to use for overwriting.
        delete_after (bool): Whether to delete the file after wiping (default: True).
    """
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Path not found: {target_path}")

    size = os.path.getsize(target_path)
    buffer_size = 1024 * 1024  # 1MB
    zero_buffer = b'\x00' * buffer_size

    with open(target_path, "r+b") as f:
        for i in range(passes):
            pattern = patterns[i % len(patterns)] if patterns else b'\x00'
            pattern_buffer = pattern * (buffer_size // len(pattern) + 1)
            pattern_buffer = pattern_buffer[:buffer_size]

            # Overwrite with pattern
            f.seek(0)
            for offset in range(0, size, buffer_size):
                chunk_size = min(buffer_size, size - offset)
                f.write(pattern_buffer[:chunk_size])
                f.flush()

            # Overwrite with zeros
            f.seek(0)
            for offset in range(0, size, buffer_size):
                chunk_size = min(buffer_size, size - offset)
                f.write(zero_buffer[:chunk_size])
                f.flush()

        if delete_after:
            # Final overwrite with zeros before deletion
            f.seek(0)
            for offset in range(0, size, buffer_size):
                chunk_size = min(buffer_size, size - offset)
                f.write(zero_buffer[:chunk_size])
                f.flush()

    if delete_after:
        os.remove(target_path)

class WipeMethod:
    """Base class for defining wipe methods with specific names, passes, and patterns."""
    def __init__(self, name, passes, patterns):
        self.name = name
        self.passes = passes
        self.patterns = patterns

    def validate(self):
        """Validate the wipe method parameters."""
        if not isinstance(self.passes, int) or self.passes < 1:
            raise ValueError("Invalid pass count")

    def execute(self, drive_path):
        """Execute the wipe operation on the specified path."""
        secure_wipe_drive(drive_path, self.passes, self.patterns)

class DoD522022M(WipeMethod):
    """DoD 5220.22-M wipe method with 3 passes."""
    def __init__(self):
        super().__init__("DoD 5220.22-M (3 Passes)", 3, [b'\x00', b'\xFF', b'\x55'])

class Gutmann35(WipeMethod):
    """Gutmann wipe method with 35 passes."""
    def __init__(self):
        super().__init__("Gutmann (35 Passes)", 35, [
            b'\x55', b'\xAA', b'\x92\x49\x24', b'\x49\x24\x92', b'\x24\x92\x49',
            b'\x00', b'\x11', b'\x22', b'\x33', b'\x44', b'\x55', b'\x66', b'\x77',
            b'\x88', b'\x99', b'\xAA', b'\xBB', b'\xCC', b'\xDD', b'\xEE', b'\xFF',
            b'\x92\x49\x24', b'\x49\x24\x92', b'\x24\x92\x49', b'\x6D\xB6\xDB',
            b'\xB6\xDB\x6D', b'\xDB\x6D\xB6', b'\x00', b'\x00', b'\x00', b'\x00',
            b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00'
        ])

class ZeroFill(WipeMethod):
    """Zero Fill wipe method with 1 pass."""
    def __init__(self):
        super().__init__("Zero Fill (1 Pass)", 1, [b'\x00'])

class Brigadier(WipeMethod): 
    """Brigadier wipe method with 5 passes."""
    def __init__(self):
        super().__init__("Brigadier (5 Passes)", 5, [b'\x00', b'\xFF', b'\xAA', b'\x55', b'\x00'])

class VSITR(WipeMethod):
    """VSITR wipe method with 7 passes."""
    def __init__(self):
        super().__init__("VSITR (7 Passes)", 7, [b'\x00', b'\xFF', b'\x00', b'\xFF', b'\x00', b'\xFF', b'\xAA'])

class RussianGOSTR5073995(WipeMethod):
    """Russian GOST R 50739-95 wipe method with 2 passes."""
    def __init__(self):
        super().__init__("Russian GOST R 50739-95 (2 Passes)", 2, [b'\x00', b'\xFF'])

class BritishHMGIS5(WipeMethod):
    """British HMG IS5 wipe method with 3 passes."""
    def __init__(self):
        super().__init__("British HMG IS5 (3 Passes)", 3, [b'\x00', b'\xFF', b'\x00'])

def get_available_wipe_methods():
    """Return a dictionary of available wipe methods."""
    return {
        cls().name: cls()
        for cls in [DoD522022M, Gutmann35, ZeroFill, Brigadier, VSITR, RussianGOSTR5073995, BritishHMGIS5]
    }

def secure_wipe_drive(path, passes=1, patterns=None, delete_after=True):
    """
    Securely wipe a file or directory.
    
    Args:
        path (str): Path to the file or directory to wipe.
        passes (int): Number of overwrite passes.
        patterns (list): List of byte patterns to use for overwriting.
        delete_after (bool): Whether to delete the files and directories after wiping (default : True).
    """
    if os.path.isfile(path):
        secure_wipe_file(path, passes, patterns, delete_after)
    elif os.path.isdir(path):
        # Collect all file paths
        file_paths = []
        for root, dirs, files in os.walk(path):
            # Skip 'System Volume Information' directory
            if 'System Volume Information' in dirs:
                dirs.remove('System Volume Information')
            for file in files:
                file_paths.append(os.path.join(root, file))

        # Wipe files in parallel
        for i in range(passes):
            pattern = patterns[i % len(patterns)] if patterns else b'\x00'
            Parallel(n_jobs=-1)(delayed(secure_wipe_file)(fp, 1, [pattern], False) for fp in file_paths)

        if delete_after:
            # Final overwrite with zeros before deletion
            for fp in file_paths:
                secure_wipe_file(fp, 1, [b'\x00'], True)

            # Remove directories bottom-up
            for root, dirs, _ in os.walk(path, topdown=False):
                # Skip 'System Volume Information' directory
                if 'System Volume Information' in dirs:
                    dirs.remove('System Volume Information')
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
    elif os.path.ismount(path):
        # Handle drive wiping
        drive_letter = path[-1] + ":\\"
        total_space = shutil.disk_usage(drive_letter).total
        buffer_size = 1024 * 1024  # 1MB
        zero_buffer = b'\x00' * buffer_size

        for i in range(passes):
            pattern = patterns[i % len(patterns)] if patterns else b'\x00'
            pattern_buffer = pattern * (buffer_size // len(pattern) + 1)
            pattern_buffer = pattern_buffer[:buffer_size]

            with open(f"{drive_letter}$Extend$UsnJrnl:$J", "r+b") as f:
                f.seek(0)
                for offset in range(0, total_space, buffer_size):
                    chunk_size = min(buffer_size, total_space - offset)
                    f.write(pattern_buffer[:chunk_size])
                    f.flush()

            # Overwrite with zeros
            with open(f"{drive_letter}$Extend$UsnJrnl:$J", "r+b") as f:
                f.seek(0)
                for offset in range(0, total_space, buffer_size):
                    chunk_size = min(buffer_size, total_space - offset)
                    f.write(zero_buffer[:chunk_size])
                    f.flush()

        if delete_after:
            # Final overwrite with zeros before deletion
            with open(f"{drive_letter}$Extend$UsnJrnl:$J", "r+b") as f:
                f.seek(0)
                for offset in range(0, total_space, buffer_size):
                    chunk_size = min(buffer_size, total_space - offset)
                    f.write(zero_buffer[:chunk_size])
                    f.flush()
    else:
        raise ValueError(f"Path {path} is neither a file, directory, nor a mounted drive")

def wipe_drive(drive_path, method, progress_callback=None):
    """
    Perform a secure wipe on the specified path using the given method.
    
    Args:
        drive_path (str): Path to wipe.
        method (WipeMethod): The wipe method to use.
        progress_callback (callable, optional): Callback function to update progress after each pass.
    """
    try:
        method.validate()
        patterns = method.patterns
        total_passes = method.passes
        for i in range(total_passes):
            pattern = patterns[i % len(patterns)]
            secure_wipe_drive(drive_path, 1, [pattern], delete_after=False)
            if progress_callback:
                progress_callback(i + 1, total_passes)
        # Final erase with zeros and delete
        secure_wipe_drive(drive_path, 1, [b'\x00'], delete_after=True)
        if progress_callback:
            progress_callback(total_passes, total_passes)
        logger.info(f"Wiped path: {drive_path} with {method.name}")
    except Exception as e:
        logger.error(f"Wipe failed: {str(e)}")
        raise RuntimeError(f"Wipe failed: {str(e)}")

def verify_wipe(file_path, expected_pattern):
    """
    Verify that a file has been wiped with the expected pattern.
    
    Args:
        file_path (str): Path to the file to verify.
        expected_pattern (bytes): The expected byte pattern.
    """
    with open(file_path, "rb") as f:
        chunk = f.read(4096)
        while chunk:
            if not all(b == expected_pattern for b in chunk):
                raise RuntimeError(f"Verification failed: Data not completely overwritten at {file_path}")
            chunk = f.read(4096)
    logger.info(f"Verification successful: {file_path} is completely overwritten.")

def get_drive_type(device_path):
    """Determine the type of drive (e.g., SSD or HDD)."""
    drive_letter = device_path[0]
    c = wmi.WMI()
    for disk in c.Win32_DiskDrive():
        if f"\\\\.\\{drive_letter}:" in disk.DeviceID:
            return disk.MediaType
    raise RuntimeError(f"Unsupported drive type for {device_path}")

def is_ssd(drive_path):
    """Check if the drive is an SSD."""
    drive_type = get_drive_type(drive_path)
    return "SSD" in drive_type

def ssd_secure_erase(drive_path):
    """Perform an ATA Secure Erase on an SSD."""
    try:
        drive_letter = drive_path[0]
        device_path = f"\\\\.\\{drive_letter}:"
        if is_ssd(device_path):
            security_descriptor = win32security.SECURITY_DESCRIPTOR()
            sd = win32security.GetFileSecurity(device_path, win32security.DACL_SECURITY_INFORMATION)
            sd.SetSecurityDescriptorDacl(1, [], 0)
            win32security.SetFileSecurity(device_path, win32security.DACL_SECURITY_INFORMATION, sd)
            logger.info(f"ATA Secure Erase initiated for {device_path}")
        else:
            logger.warning(f"Device {device_path} is not an SSD. Skipping ATA Secure Erase.")
    except Exception as e:
        logger.error(f"Failed to perform SSD secure erase: {str(e)}")

def blkdiscard(device_path):
    """Discard unused blocks on a device using blkdiscard."""
    try:
        subprocess.run(
            ["blkdiscard", "-f", device_path],
            check=True
        )
        logger.info(f"Blkdiscard successful for {device_path}")
    except Exception as e:
        logger.error(f"Failed to perform blkdiscard: {str(e)}")