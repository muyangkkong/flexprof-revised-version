import time
import os
import subprocess
from sys import argv
# Define the lists of fractions and benchmarks
fractions_list = []

benchmarks = [d for d in os.listdir("output/profile/") if os.path.isdir(os.path.join("input/domains", d))]
banks = [4]
domains =  7
try:
    input_file = argv[1]
    output_folder = argv[2]
    core_id=argv[3]
except IndexError:
    print("Usage: python3 run.py <input_file> <output_folder> <core_id>")
    exit(1)

#create the output folder if it does not exist
if not os.path.exists(output_folder):
    os.makedirs(output_folder)


for bm in benchmarks:
    performance = []
    std_outs = [file for file in os.listdir(f"output/profile/{bm}") if os.path.isfile(os.path.join(f"output/profile/{bm}", file))]
    std_outs = [f"output/profile/{bm}/{file}" for file in std_outs]
    for file in std_outs:
        with open(file, "r") as f:
            for line in f:
                if "Total Simulation Cycles" in line:
                    performance.append((file, int(line.split()[3])))
                    print(len(performance))
                    break
    performance.sort(key=lambda x: x[1])
    if not performance:
        print(f"[WARN] No performance entries found for benchmark '{bm}'. Skipping.")
        continue  
    best = performance[0]
    try:
        frac_part = best[0].split('_')[1].split('.')[0]
    except Exception as e:
        print(f"[WARN] Unexpected filename format: {best[0]} ({e}). Using fallback '0'")
        frac_part = "-1"
    fractions_list.append((bm, f"{frac_part}/100"))
output_txt=f"output/best_fractions{core_id}.txt"

with open(output_txt,"w") as f:

    for bm, fractions in fractions_list:
        f.write(f"{bm}: {fractions}\n")
print(f"Saved to {output_txt}")

max_processes = 20
def wait_for_available_slot(processes, max_processes):
    while len(processes) >= max_processes:
        for p in processes.copy():
            if p.poll() is not None:  # Process has finished
                processes.remove(p)
        time.sleep(1)  # Wait a bit before checking again
processes = []

with open(output_txt,"r") as f:
    #read the line
    for line in f:
        benchmark,fractions_str = line.split(':')
    benchmark= benchmark.strip()
    fractions_str =(fractions_str.strip()+" ")* domains
   #Start the first set of commands
    cmd1 = f"python3 pattern_finder.py {fractions_str} input/patterns/{benchmark}.8pattern {banks[0]}"
    processes.append(subprocess.Popen(cmd1, shell=True))
    print(benchmark)
    time.sleep(2)

    for exclude in nums:
        remaining = [n for n in nums if n!=exclude]
        core_paths=""
        for num in remaining:
            core_paths+=f" input/domains/{benchmark}/core_{num}-2"

        cmd2 = (f"bin/usimm-fsbta-rwopt {input_file} "
                f"{core_paths} "
                f"input/patterns/{benchmark}.8pattern > {output_folder}/rwopt-{benchmark}{exclude}")
        processes.append(subprocess.Popen(cmd2, shell=True))
        wait_for_available_slot(processes, max_processes)
        
        remaining_csv = ",".join(str(n) for n in remaining)
        cmd3 = [
            "python3", 
            "convertexcel.py", 
            core_id, 
            "--remaining", remaining_csv, 
        ]
        subprocess.run(cmd3)

    # Start the second set of commands
    cmd5 = (f"bin/usimm-rwopt {input_file} "
            f"input/domains/{benchmark}/core_0-2 input/domains/{benchmark}/core_1-2 "
            f"input/domains/{benchmark}/core_2-2 input/domains/{benchmark}/core_3-2 "
            f"input/domains/{benchmark}/core_4-2 input/domains/{benchmark}/core_5-2 "
            f"input/domains/{benchmark}/core_6-2 "
            f"input/patterns/{benchmark}.8pattern > {output_folder}/rwopt-{benchmark}")
    processes.append(subprocess.Popen(cmd5, shell=True))
    wait_for_available_slot(processes, max_processes)
    
    '''cmd6 = (f"bin/usimm-rta {input_file} "
            f"input/domains/{benchmark}/core_0-2 input/domains/{benchmark}/core_1-2 "
            f"input/domains/{benchmark}/core_2-2 input/domains/{benchmark}/core_3-2 "
            f"input/domains/{benchmark}/core_4-2 input/domains/{benchmark}/core_5-2 "
            f"input/domains/{benchmark}/core_6-2 "
            f"> {output_folder}/rta-{benchmark}")
    processes.append(subprocess.Popen(cmd6, shell=True))
    wait_for_available_slot(processes, max_processes)
    cmd7 = (f"bin/usimm {input_file} "
            f"input/domains/{benchmark}/core_0-2 input/domains/{benchmark}/core_1-2 "
            f"input/domains/{benchmark}/core_2-2 input/domains/{benchmark}/core_3-2 "
            f"input/domains/{benchmark}/core_4-2 input/domains/{benchmark}/core_5-2 "
            f"input/domains/{benchmark}/core_6-2 "
            f"> {output_folder}/base-{benchmark}")
    processes.append(subprocess.Popen(cmd7, shell=True))
    wait_for_available_slot(processes, max_processes)
'''
# Wait for all processes to complete
for p in processes:
    p.wait()
