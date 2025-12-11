import os
import re
import pandas as pd
import numpy as np
import sys as argv


try:
    fraction_core=argv[1]
except IndexError:
    print("Usage: python3 convertexcel.py <fraction_core>")
    exit(1)
    
INPUT_DOMAINS_DIR = "input/domains"
RWOPT_OUTPUT_DIR = "output/7domains_8banks_8ranks_addressmapping2"
OUT_XLSX = f"output/metrics_by_{fraction_core}.xlsx"

def int_from_re(m):
    return int(m.group(1).replace(',', '')) if m else None

def parse_log_text(text):
# extract quantities
    cycles = re.findall(r"Cycles\s+([0-9]+)", text)
    cycles = int(cycles[-1]) if cycles else None

    reads = re.search(r"Total Reads Serviced\s*[:=]?\s*([0-9,]+)", text, re.IGNORECASE)
    if not reads:
        reads = re.search(r"Total Reads\s*[:=]?\s*([0-9,]+)", text, re.IGNORECASE)
    writes = re.search(r"Total Writes Serviced\s*[:=]?\s*([0-9,]+)", text, re.IGNORECASE)
    if not writes:
        writes = re.search(r"Total Writes\s*[:=]?\s*([0-9,]+)", text, re.IGNORECASE)

    reads_n = int_from_re(reads) or 0
    writes_n = int_from_re(writes) or 0

    reads_merged = int_from_re(re.search(r"Num reads merged\s*[:=]?\s*([0-9,]+)", text, re.IGNORECASE)) or 0
    writes_merged = int_from_re(re.search(r"Num writes merged\s*[:=]?\s*([0-9,]+)", text, re.IGNORECASE)) or 0

    sum_exec = int_from_re(re.search(r"Sum of execution times for all programs\s*[:=]?\s*([0-9,]+)", text, re.IGNORECASE)) or None

    # per-core committed
    core_pattern = re.compile(r"Done:\s*Core\s*(\d+):\s*Fetched\s*([0-9,]+)\s*:\s*Committed\s*([0-9,]+)\s*:\s*At time\s*:\s*([0-9,]+)", re.IGNORECASE)
    cores = core_pattern.findall(text)
    committed_sum = 0
    core_count = 0
    core_committed_list = []
    for c in cores:
        core_count += 1
        committed_c = int(c[2].replace(',', ''))
        core_committed_list.append(committed_c)
        committed_sum += committed_c

# bank stats
    bank_pattern = re.compile(r"Bank\s*(\d+):\s*Writes:\s*([0-9,]+),\s*Reads:\s*([0-9,]+)", re.IGNORECASE)
    banks = bank_pattern.findall(text)
    bank_accesses = []
    for b in banks:
        writes_b = int(b[1].replace(',', ''))
        reads_b = int(b[2].replace(',', ''))
        bank_accesses.append(writes_b + reads_b)

    # Queue latency
    qlat = re.search(r"(?:Average )?Queue Latency\s*[:=]?\s*([0-9.+-eE]+)", text, re.IGNORECASE)
    queue_latency = float(qlat.group(1)) if qlat else None

    # aggressive precharges
    aggr = re.search(r"(?:Number of aggressive precharges|Num aggressive precharges|Aggressive precharges)\s*[:=]?\s*([0-9,]+)", text, re.IGNORECASE)
    num_aggressive_pre = int_from_re(aggr) or 0

    return {
    "cycles": cycles,
    "reads": reads_n,
    "writes": writes_n,
    "reads_merged": reads_merged,
    "writes_merged": writes_merged,
    "sum_exec_times": sum_exec,
    "committed_sum": committed_sum if core_count>0 else None,
    "num_cores_reported": core_count,
    "bank_accesses": bank_accesses,
    "queue_latency": queue_latency,
    "num_aggressive_precharges": num_aggressive_pre
    }

def compute_metrics(parsed):
    p = parsed
    cycles = p["cycles"]
    reads = p["reads"]
    writes = p["writes"]
    total_serviced = reads + writes if (reads or writes) else None

    metrics = {}
    metrics["Total_Simulation_Cycles"] = cycles
    metrics["Total_Reads_Serviced"] = reads
    metrics["Total_Writes_Serviced"] = writes
    metrics["Merged_Request_Count"] = (p["reads_merged"] + p["writes_merged"])
    metrics["Num_Reads_Merged"] = p["reads_merged"]
    metrics["Num_Writes_Merged"] = p["writes_merged"]
    metrics["Num_Aggressive_Precharges"] = p["num_aggressive_precharges"]
    metrics["Queue_Latency"] = p["queue_latency"]

    # MLP
    metrics["MLP"] = (total_serviced / cycles) if (total_serviced is not None and cycles) else None
    # RD/WR ratios
    metrics["RD_request_ratio"] = (reads / total_serviced) if (total_serviced and reads is not None) else None
    metrics["WR_request_ratio"] = (writes / total_serviced) if (total_serviced and writes is not None) else None
    # IPC
    metrics["Sum_committed"] = p["committed_sum"]
    metrics["IPC"] = (p["committed_sum"] / cycles) if (p["committed_sum"] is not None and cycles) else None
    # WSU (weighted speedup) = sum exec times / cycles
    metrics["Sum_of_execution_times"] = p["sum_exec_times"]
    metrics["Weighted_Speedup"] = (p["sum_exec_times"] / cycles) if (p["sum_exec_times"] and cycles) else None

    # bank stats
    if p["bank_accesses"]:
        arr = np.array(p["bank_accesses"], dtype=float)
        metrics["Bank_Access_Mean"] = float(arr.mean())
        metrics["Bank_Access_Variance"] = float(arr.var(ddof=0))  # population variance
    else:
        metrics["Bank_Access_Mean"] = None
        metrics["Bank_Access_Variance"] = None

    return metrics

def main():
    print("It is working")
    print("cwd:",os.path.isdir(INPUT_DOMAINS_DIR))
    if not os.path.isdir(INPUT_DOMAINS_DIR):
        raise SystemExit(f"Missing {INPUT_DOMAINS_DIR}")

    benchmarks = [d for d in os.listdir(INPUT_DOMAINS_DIR)
    if os.path.isdir(os.path.join(INPUT_DOMAINS_DIR, d))]

    rows = []
    for bm in sorted(benchmarks):
        filename = os.path.join(RWOPT_OUTPUT_DIR, f"rwopt-{bm}")
        row = {"benchmark": bm, "file_found": os.path.exists(filename)}
        if not os.path.exists(filename):
        # leave metrics as None but mark missing file
            rows.append(row)
            print(f"[WARN] missing: {filename}")
            continue
        with open(filename, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        parsed = parse_log_text(text)
        metrics = compute_metrics(parsed)
        row.update(metrics)
        rows.append(row)
        print(f"[OK] parsed {bm}: cycles={metrics.get('Total_Simulation_Cycles')}")

    df = pd.DataFrame(rows)
    df=df.set_index("benchmark")
    os.makedirs(os.path.dirname(OUT_XLSX),exist_ok=True)
    try:
        df.to_excel(OUT_XLSX,index=True)
        print(f"Saved DataFrame to {OUT_XLSX}")
    except Exception as e:
        print("[Error] failed")
    print(f"Saved metrics for {len(rows)} benchmarks to {OUT_XLSX}")

if __name__ == "__main__":
        main()
