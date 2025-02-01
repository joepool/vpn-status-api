from flask import Flask, jsonify
import requests
import csv
import docker
from io import StringIO
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

PIA_SERVERS_URL = "https://raw.githubusercontent.com/Lars-/PIA-servers/refs/heads/master/export.csv"
PIA_SERVERS = []
def fetch_pia_servers():
    global PIA_SERVERS
    try:
        response = requests.get(PIA_SERVERS_URL, timeout=5)
        response.raise_for_status()
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        PIA_SERVERS = [
            {
                "ip": row["IP"],
                "region": row["Region"],
            }
            for row in reader
        ]
    except Exception as e:
        print(f"Error fetching PIA servers: {e}")
def get_container_ip():
    try:
        client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        container = client.containers.get("qbittorrent-vpn")
        exec_result = container.exec_run("curl -s ifconfig.me")
        return exec_result.output.decode("utf-8").strip()
    except Exception as e:
        print(f"Error getting container IP: {e}")
        return None
@app.route('/vpn-status', methods=['GET'])
def check_vpn_status():
    try:
        container_ip = get_container_ip()
        if not container_ip:
            return jsonify({
                "error": "Failed to fetch container IP"
            }), 500
        matching_server = next((server for server in PIA_SERVERS if server["ip"] == container_ip), None)
        if matching_server:
            vpn_status = "VPN active"
            server_details = matching_server
        else:
            vpn_status = "VPN inactive"
            server_details = None
        return jsonify({
            "ip_address": container_ip,
            "vpn_status": vpn_status,
            "connected_server": server_details
        })
    except Exception as e:
        return jsonify({
            "error": "Unexpected error occurred",
            "details": str(e)
        }), 500
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_pia_servers, 'interval', minutes=120)
    scheduler.start()
if __name__ == '__main__':
    fetch_pia_servers()
    start_scheduler()
    app.run(host='0.0.0.0', port=5000)
