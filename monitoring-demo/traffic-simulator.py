import requests
import time
import random
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
ENDPOINTS = ["/", "/api/data", "/health"]

def make_request():
    while True:
        endpoint = random.choice(ENDPOINTS)
        url = f"{BASE_URL}{endpoint}"
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            latency = time.time() - start_time
            
            logger.info(f"Request to {endpoint} - Status: {response.status_code} - Latency: {latency:.3f}s")
            
        except Exception as e:
            logger.error(f"Request to {endpoint} failed: {str(e)}")
        
        # Random delay between requests
        time.sleep(random.uniform(0.1, 1.0))

def simulate_traffic(num_threads=5):
    threads = []
    
    for i in range(num_threads):
        thread = threading.Thread(target=make_request, daemon=True)
        threads.append(thread)
        thread.start()
        logger.info(f"Started traffic thread {i+1}")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping traffic simulation")

if __name__ == "__main__":
    print("Starting traffic simulation...")
    simulate_traffic(num_threads=5)