import json
import os
import subprocess
import time
import logging
from flask import Flask, Response
from datetime import datetime
import threading
import re

app = Flask(__name__)

INPUT_FILE = "metric.json"
OUTPUT_FILE = "metrics.prom"
BASH_SCRIPT = "namespace.sh" 
UPDATE_INTERVAL = 15

def run_bash_script(script_path):
    """
    Run the bash script to generate the metric.json file.
    """
    try:
        subprocess.run(["bash", script_path], check=True)
        logging.info(f"Successfully executed {script_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running bash script {script_path}: {e}")

def convert_to_prometheus_metrics(input_file, output_file):
    """
    Convert JSON blocks in the input file to Prometheus metrics format.
    """
    metrics = []
    try:
        with open(input_file, 'r') as f:
            file_content = f.read()
    except FileNotFoundError:
        logging.error(f"Input file {input_file} not found.")
        return False
    except PermissionError:
        logging.error(f"Permission denied when reading {input_file}")
        return False

    blocks = re.findall(r'\[.*?\]', file_content, re.DOTALL)
    
    for block_str in blocks:
        try:
            block = json.loads(block_str)
            for pod in block:
                pod_name = pod.get('pod', 'unknown')
                cpu_usage = pod.get('cpu', '0')
                try:
                    if cpu_usage.endswith('m'):
                        cpu_usage = float(cpu_usage[:-1]) / 1000
                    else:
                        cpu_usage = float(cpu_usage)
                except ValueError:
                    cpu_usage = 0
                
                memory_usage = pod.get('memory', '0')
                try:
                    if memory_usage.endswith('Mi'):
                        memory_usage = float(memory_usage[:-2]) * 1024 * 1024
                    else:
                        memory_usage = float(memory_usage)
                except ValueError:
                    memory_usage = 0
                
                timestamp = int(datetime.now().timestamp())
                metrics.append(f'kube_pod_container_resource_cpu_usage_total{{pod="{pod_name}"}} {cpu_usage}')
                metrics.append(f'kube_pod_container_resource_memory_usage_bytes{{pod="{pod_name}"}} {memory_usage}')
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing block: {e}")
            continue

    try:
        with open(output_file, 'w') as f:
            f.write('\n'.join(metrics))
        logging.info(f"Converted {len(metrics)//2} pod metrics written to {output_file}")
        return True
    except PermissionError:
        logging.error(f"Permission denied when writing to {output_file}")
        return False

def serve_metrics():
    """
    Serve metrics to Prometheus.
    """
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r') as f:
            metrics_data = f.read()
        return Response(metrics_data, mimetype='text/plain')
    else:
        return Response("# No metrics available", mimetype='text/plain')

def background_worker():
    """
    Background worker to periodically collect metrics and convert them.
    """
    while True:
        run_bash_script(BASH_SCRIPT)
        
        success = convert_to_prometheus_metrics(INPUT_FILE, OUTPUT_FILE)
        if success:
            try:
                open(INPUT_FILE, 'w').close()
                logging.info(f"Cleared input file {INPUT_FILE}")
            except PermissionError:
                logging.error(f"Cannot clear input file {INPUT_FILE}")
        time.sleep(UPDATE_INTERVAL)

@app.route('/metrics', methods=['GET'])
def metrics_endpoint():
    """
    Flask endpoint to serve metrics.
    """
    return serve_metrics()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("metrics_collector.log"),
            logging.StreamHandler()
        ]
    )
    
    worker_thread = threading.Thread(target=background_worker, daemon=True)
    worker_thread.start()

    app.run(host="0.0.0.0", port=5000)
