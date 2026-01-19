from wipe import list_disks, secure_wipe

def main():
    print("=== Data Wiper Tool (Python Edition) ===")
    list_disks()

    dev = input("Enter device path (e.g., /dev/sdb, /dev/sda1) or directory path: ").strip()
    try:
        passes = int(input("How many overwrite passes? (default=3): ") or "3")
    except ValueError:
        passes = 3

    secure_wipe(dev, passes)

if __name__ == "__main__":
    main()
