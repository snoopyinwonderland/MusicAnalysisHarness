"""Audit sealed Stage92 results with the original per-graph segment caps."""
import argparse
import json
from musicanote_harness.harmony_exact_beat_dev_audit_v2 import run

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    print(json.dumps(run(p.parse_args().root), indent=2), flush=True)
