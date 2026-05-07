import subprocess
import sys
import time

def main():
    print("Starting FastAPI Server...")
    import os
    port = os.environ.get("PORT", "8000")
    # Start the FastAPI server on 0.0.0.0 and the correct port for cloud hosting
    server_process = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", port])
    
    # Wait 15 seconds to let the server fully load heavy ML models into memory
    time.sleep(15)
    
    print("Starting Live Simulator...")
    # Start the live simulator
    simulator_process = subprocess.Popen([sys.executable, "live_simulator.py"])
    
    try:
        # Keep the launcher running and waiting
        server_process.wait()
        simulator_process.wait()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\nShutting down both processes...")
        server_process.terminate()
        simulator_process.terminate()
        server_process.wait()
        simulator_process.wait()
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
