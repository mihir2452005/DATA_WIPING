import os
import sys
import subprocess

def list_disks():
    """
    Show available disks and partitions.
    """
    print("\n=== Available Disks & Partitions ===")
    if os.name == 'nt':  # Windows
        try:
            result = subprocess.run(['wmic', 'logicaldisk', 'get', 'name,size,freespace'], capture_output=True, text=True)
            print(result.stdout)
        except Exception as e:
            print(f"Unable to list disks: {e}")
    else:
        os.system("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT")
    print("====================================\n")


def wipe_directory(dir_path: str, passes: int = 3, block_size: int = 1024 * 1024):
    """
    Securely wipes all files in a directory by overwriting them with random data.

    Args:
        dir_path (str): Path of the directory.
        passes (int): Number of overwrite passes.
        block_size (int): Size of random data chunks.
    """
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r+b') as f:
                    f.seek(0, 2)
                    size = f.tell()
                    f.seek(0)
                    for p in range(passes):
                        f.seek(0)
                        remaining = size
                        while remaining > 0:
                            chunk_size = min(block_size, remaining)
                            data = os.urandom(chunk_size)
                            f.write(data)
                            remaining -= chunk_size
                        f.flush()
                        os.fsync(f.fileno())
                os.remove(file_path)
                print(f"[+] Wiped and deleted {file_path}")
            except Exception as e:
                print(f"[-] Error wiping {file_path}: {e}")


def secure_wipe(device: str, passes: int = 3, block_size: int = 1024 * 1024):
    """
    Securely wipes a disk/partition or directory by overwriting with random data.

    Args:
        device (str): Path of disk/partition (e.g., /dev/sdb, /dev/sda1) or directory.
        passes (int): Number of overwrite passes.
        block_size (int): Size of random data chunks written at once.
    """
    if not os.path.exists(device):
        print(f"[-] Path {device} not found!")
        return

    print(f"\n[!] WARNING: This will ERASE all data on {device}")
    confirm = input("Type YES to confirm: ")
    if confirm != "YES":
        print("[-] Aborted.")
        return

    print(f"[+] Starting secure wipe on {device} ...")
    if os.path.isdir(device):
        wipe_directory(device, passes, block_size)
    else:
        try:
            with open(device, "wb") as f:
                for p in range(passes):
                    print(f"[*] Pass {p+1}/{passes} ... (this may take time)")
                    try:
                        while True:
                            data = os.urandom(block_size)
                            written = f.write(data)
                            if written < len(data):  # Reached end of device
                                break
                    except OSError:
                        # Likely end of disk reached
                        pass
                    f.flush()
                    os.fsync(f.fileno())
        except PermissionError:
            if os.name == 'nt':
                print("[-] Permission denied! Run as administrator.")
            else:
                print("[-] Permission denied! Run as root.")
            return
        except Exception as e:
            print(f"[-] Error wiping device: {e}")
            return

    print(f"[+] Secure wipe completed for {device}")
