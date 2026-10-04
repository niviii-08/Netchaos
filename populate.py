import urllib.request
import urllib.parse
import json
import time

BASE = "http://localhost:8000/api"

def req(url, method="GET", body=None):
    req_obj = urllib.request.Request(f"{BASE}{url}", method=method)
    if body is not None:
        req_obj.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode("utf-8")
    else:
        data = None
    try:
        with urllib.request.urlopen(req_obj, data=data) as f:
            res = f.read()
            return json.loads(res) if res else None
    except urllib.error.HTTPError as e:
        print(f"Error {e.code} on {method} {url}: {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"Error on {method} {url}: {e}")
        return None

print("Fetching networks...")
networks = req("/networks")
if not networks:
    print("No networks found. Exiting.")
    exit(1)

net_id = networks[0]["network_id"]
print(f"Using network: {net_id}")

print("\n--- Running Traffic Simulation ---")
traffic = req(f"/networks/{net_id}/traffic/simulations", "POST", {
    "source": "node_e1_001",
    "destination": "node_e2_001",
    "packet_count": 500,
    "packet_size": 1500,
    "store_packets": False
})
if traffic:
    print("Created Traffic:", traffic.get("simulation_id"))
    req(f"/networks/{net_id}/traffic/simulations/{traffic['simulation_id']}/run", "POST")
    print("Traffic Simulation Completed.")

print("\n--- Injecting Chaos ---")
chaos = req(f"/networks/{net_id}/chaos/link-failure", "POST", {
    "link_id": "link_001_net001"
})
if chaos:
    print("Chaos Injected:", chaos.get("experiment_id"))

print("\n--- Creating Monitoring Snapshot ---")
monitoring = req(f"/networks/{net_id}/monitoring/snapshot", "POST")
print("Monitoring captured.")

print("\n--- Running Experiment Plan ---")
plan = req("/experiment-plans", "POST", {
    "name": "Resilience Baseline Dataset Generation",
    "description": "Auto-generated test",
    "network_id": net_id,
    "target_simulations": [traffic['simulation_id']] if traffic else [],
    "chaos_events": [
        {"type": "link_failure", "link_id": "link_004_net001"}
    ],
    "recovery_strategy": "shortest_hop"
})
if plan:
    print("Created Experiment Plan:", plan.get("plan_id"))
    req(f"/experiment-plans/{plan['plan_id']}/run", "POST")
    print("Triggered Experiment Plan execution")
    time.sleep(2) # let the async runner complete it

print("\n--- Generating Clean Dataset ---")
dataset = req("/datasets", "POST", {
    "name": "Automated Baseline Dataset",
    "version": "1.0",
    "description": "Generated via python automation",
    "filters": {}
})
if dataset:
    print("Dataset successfully created:", dataset.get("metadata", {}).get("dataset_id"))
print("Done!")
