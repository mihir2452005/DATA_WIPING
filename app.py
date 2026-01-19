from flask import Flask, jsonify, request, render_template
import threading
import os
import subprocess
from wipe import wipe_directory

app = Flask(__name__)

def get_disks():
    disks = []
    if os.name == 'nt':  # Windows
        try:
            result = subprocess.run(['wmic', 'logicaldisk', 'get', 'name,size,freespace'], capture_output=True, text=True)
            lines = result.stdout.strip().splitlines()
            # Skip header line
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 1:
                    disk = {
                        'name': parts[0],
                        'size': parts[1] if len(parts) > 1 else '',
                        'freespace': parts[2] if len(parts) > 2 else ''
                    }
                    disks.append(disk)
        except Exception as e:
            disks.append({'error': f"Unable to list disks: {e}"})
    else:
        try:
            result = subprocess.run(['lsblk', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT', '-J'], capture_output=True, text=True)
            import json
            blk = json.loads(result.stdout)
            for device in blk.get('blockdevices', []):
                disks.append({
                    'name': device.get('name'),
                    'size': device.get('size'),
                    'type': device.get('type'),
                    'mountpoint': device.get('mountpoint')
                })
        except Exception as e:
            disks.append({'error': f"Unable to list disks: {e}"})
    return disks

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/disks', methods=['GET'])
def api_disks():
    disks = get_disks()
    return jsonify(disks)

wipe_status = {
    'running': False,
    'logs': []
}

def wipe_worker(device, passes):
    wipe_status['running'] = True
    wipe_status['logs'] = []
    if not os.path.exists(device):
        wipe_status['logs'].append(f"[-] Path {device} not found!")
        wipe_status['running'] = False
        return
    wipe_status['logs'].append(f"[!] WARNING: This will ERASE all data on {device}")
    # For web, assume confirmation done on frontend
    wipe_status['logs'].append(f"[+] Starting secure wipe on {device} ...")
    if os.path.isdir(device):
        try:
            wipe_directory(device, passes)
            wipe_status['logs'].append(f"[+] Secure wipe completed for directory {device}")
        except Exception as e:
            wipe_status['logs'].append(f"[-] Error wiping directory: {e}")
    else:
        try:
            block_size = 1024 * 1024
            with open(device, "wb") as f:
                for p in range(passes):
                    wipe_status['logs'].append(f"[*] Pass {p+1}/{passes} ... (this may take time)")
                    try:
                        while True:
                            data = os.urandom(block_size)
                            written = f.write(data)
                            if written < len(data):
                                break
                    except OSError:
                        # Likely end of disk reached
                        break
                    f.flush()
                    os.fsync(f.fileno())
            wipe_status['logs'].append(f"[+] Secure wipe completed for device {device}")
        except PermissionError:
            if os.name == 'nt':
                wipe_status['logs'].append("[-] Permission denied! Run as administrator.")
            else:
                wipe_status['logs'].append("[-] Permission denied! Run as root.")
        except Exception as e:
            wipe_status['logs'].append(f"[-] Error wiping device: {e}")
    wipe_status['running'] = False

@app.route('/api/wipe', methods=['POST'])
def api_wipe():
    if wipe_status['running']:
        return jsonify({'status': 'error', 'message': 'Wipe already in progress'}), 400
    data = request.json
    device = data.get('device')
    passes = data.get('passes', 3)
    if not device:
        return jsonify({'status': 'error', 'message': 'Device path is required'}), 400
    try:
        passes = int(passes)
    except ValueError:
        passes = 3
    thread = threading.Thread(target=wipe_worker, args=(device, passes))
    thread.start()
    return jsonify({'status': 'started', 'message': f'Started wiping {device} with {passes} passes'})

@app.route('/api/wipe_status', methods=['GET'])
def api_wipe_status():
    return jsonify(wipe_status)

if __name__ == '__main__':
    app.run(debug=True)
