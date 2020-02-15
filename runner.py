from pathlib import Path
import subprocess

from main import EXIT_INDICATOR

script_file = Path(__file__).parent / "main.py"
log_file = Path.home() / 'photobooth.log' 


def run_app():
    with open(log_file, 'a') as log: 
        try:
            subprocess.run(['python3', str(script_file)], stdout=log, stderr=log)
        except subprocess.CalledProcessError as e:
            log.write(str(e))
        
        
    if not EXIT_INDICATOR.exists():
        print("Restarting selfie app.")
        run_app()
    else:
        print("Selfie app is closing.")


if __name__ == "__main__":
    if log_file.exists():
        log_file.unlink()
    run_app()
