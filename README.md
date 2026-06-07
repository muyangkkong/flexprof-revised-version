# Predicting Optimal Read/Write Ratios in Memory Subsystems Using Machine Learning

This repository provides a machine learning framework designed to predict the optimal Read/Write ratio for various computing workloads using USIMM 1.3 (the Utah SImulated Memory Module). By analyzing hardware performance counters from a single profiling run, this framework eliminates the need for expensive, iterative, cycle-accurate simulation sweeps to find optimal configuration points.

---

## Key Features

* **Data Leakage Mitigation:** Identifies and eliminates post-simulation throughput artifacts (`Total_Reads/Writes_Serviced`), forcing the model to learn true hardware causality rather than trivial arithmetic shortcuts.
* **Pure Architectural Learning:** Leverages internal hardware bottleneck indicators such as page policy dynamics (`NUM_AGGRESSIVE_PRECHARGES`) and structural contention metrics (`BANK_ACCESS_VARIANCE`).
* **High-Precision Regression:** Built on an optimized XGBoost architecture validated across 12 SPEC CPU2006 benchmarks (`mcf`, `lbm`, `omnetpp`, etc.).

---

## Performance Evaluation

### 1. Prediction Accuracy (5-Fold Cross-Validation)

The framework achieves robust convergence across all folds after excluding throughput-leaking features.

* **Fold 1 Validation MSE:** 0.000534
* **Fold 2 Validation MSE:** 0.000208
* **Fold 3 Validation MSE:** 0.000201
* **Fold 4 Validation MSE:** 0.000152
* **Fold 5 Validation MSE:** 0.000434
* **Average MSE Error:** 0.000306 (RMSE ~0.017 / 1.7% Error Margin)

### 2. Feature Importance Analysis

The model accurately maps hardware characteristics to the target distribution. The top contributors represent structural bottlenecks inside the memory controller:

| Feature Name | Importance Score | Architectural Implication |
| --- | --- | --- |
| `NUM_AGGRESSIVE_PRECHARGES` | **0.3303** | Reflects page closure policy aggressiveness under varied R/W streams. |
| `BANK_ACCESS_VARIANCE` | **0.1591** | Indicates structural bank conflicts and request distribution skewness. |
| `MLP` | **0.1156** | Represents Memory-Level Parallelism changes across read/write phases. |
| `QUEUE_LATENCY` | **0.1102** | Captures request buffering delays inside the controller queue. |
| `WEIGHTED_SPEEDUP` | **0.0956** | Normalized throughput metric across co-running workloads. |
| `IPC` | **0.0743** | Instructions Per Cycle; reflects CPU-side demand on memory subsystem. |
| `TOTAL_SIMULATION_CYCLES` | **0.0528** | Total cycles elapsed; proxy for workload length and memory pressure. |
| `SUM_COMMITTED` | **0.0425** | Total committed instructions; indicates workload intensity. |
| `READ_WRITE_LATENCY_RATIO` | **0.0170** | Derived ratio of queue latency to MLP; captures asymmetric R/W timing. |
| `SUM_OF_EXECUTION_TIMES` | **0.0027** | Aggregate execution time; correlates with memory access duration. |
| `BANK_ACCESS_MEAN` | **0.0000** | Average bank access count; baseline for access distribution analysis. |
| `CYCLES_PER_REQUEST` | **0.0000** | Derived cycles per memory request; measures per-request memory cost. |

---

## File Structure

```text
├── metrics_by_*.xlsx         # Input training datasets derived from USIMM simulation sweeps
├── isoutput_*.txt.stdout     # Raw USIMM 1.3 standard output files used for live testing
├── XGBoost.py                # Main training, validation, and automated log parsing script
└── cleaned_total_dataset.csv # Final aggregated, cleaned dataset used for ML execution

```

---

## Getting Started

### Prerequisites

```bash
pip install numpy pandas xgboost scikit-learn

```

### Training and Live Testing

The script automates data compilation across multiple sheets, processes log transformations for high-variance metrics, handles zero-padding for hardware-omitted counters, trains the XGBoost regression model, and executes a test parser on a raw `.stdout` file.

```bash
python XGBoost.py

```

### Inference Pipeline

1. **Profile:** Run the target benchmark once on USIMM with a default configuration to generate a raw log (`.stdout`).
2. **Parse:** The script uses regular expressions to isolate hardware counters (e.g., `Cycles`, `Number of aggressive precharges`).
3. **Predict:** The framework outputs the targeted optimal Read/Write ratio directly to the console.
