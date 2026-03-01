import argparse

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backend server")
    parser.add_argument("--port", required=False, help="Port of the server", default=5000)
    return parser.parse_args()
