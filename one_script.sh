#!/bin/bash


configs=("input/7domains_8banks_8ranks_addressmapping2.cfg")
output=("output/7domains_8banks_8ranks_addressmapping2")

benchmarks=(lbm namd cam4  deepsjeng fotonik3d mcf gcc roms omnetpp bt dc ep ft perl lu mg sp ua cg)
i=0
for config in "${configs[@]}"
do
  for core in {0..6}; do
    for bm in "${benchmarks[@]}";do
      python3 ratio_profiler.py input/domains/${bm}/core_${core}-2 4 "$bm" "$config"
      python3 run.py "$config" "${output[$i]}" "$core" "$bm"
    done
    #echo "starting Excel conversion for Core $core.."
    #for exclude in {0..6}; do
    #  remaining=""
    #  for r in {0..6}; do
    #    if [ $r -ne $exclude ]; then
    #      if [ -z "$remaining"]; then remaining="$r";else remaining="$remaining,$r"; fi
    #    fi
    #  done
    #  python3 convertexcel.py "$core" "$remaining" "Sheet_$exclude"
    #done
    #python3 convertexcel.py "$core" "0,1,2,3,4,5,6" "Sheet_All"
  done
  i=$((i+1))
done

    #python3 ratio_profiler.py input/domains/namd/core_2-2 4 namd "$config"
    #python3 ratio_profiler.py input/domains/perl/core_2-2 4 perl "$config"
    #python3 ratio_profiler.py input/domains/xalanc/core_2-2 4 xalanc "$config"
    #python3 ratio_profiler.py input/domains/bwaves/core_2-2 4 bwaves "$config"
    #python3 ratio_profiler.py input/domains/cactuBSSN/core_2-2 4 cactuBSSN "$config"

    #python3 ratio_profiler.py input/domains/cam4/core_2-2 4 cam4 "$config"
    #python3 ratio_profiler.py input/domains/deepsjeng/core_2-2 4 deepsjeng "$config"

    #python3 ratio_profiler.py input/domains/fotonik3d/core_2-2 4 fotonik3d "$config"
    #python3 ratio_profiler.py input/domains/mcf/core_2-2 4 mcf "$config"
    #python3 ratio_profiler.py input/domains/gcc/core_2-2 4 gcc "$config"
    #python3 ratio_profiler.py input/domains/roms/core_2-2 4 roms "$config"

    #python3 ratio_profiler.py input/domains/omnetpp/core_2-2 4 omnetpp "$config"

    # NPB
    #python3 ratio_profiler.py input/domains/bt/core_2-2 4 bt "$config"
    #python3 ratio_profiler.py input/domains/dc/core_2-2 4 dc "$config"
    #python3 ratio_profiler.py input/domains/ep/core_2-2 4 ep "$config"
    #python3 ratio_profiler.py input/domains/ft/core_2-2 4 ft "$config"
    #python3 ratio_profiler.py input/domains/is/core_2-2 4 is "$config"

    #python3 ratio_profiler.py input/domains/lu/core_2-2 4 lu "$config"

    #python3 ratio_profiler.py input/domains/mg/core_2-2 4 mg "$config"
    #python3 ratio_profiler.py input/domains/sp/core_2-2 4 sp "$config"
    #python3 ratio_profiler.py input/domains/ua/core_2-2 4 ua "$config"
    #python3 ratio_profiler.py input/domains/cg/core_2-2 4 cg "$config"
    #python3 convertexcel.py
    #python3 stats.py > fig7.stats
    #python3 graphs.py fig7.stats #fig 7
    #python3 util_graph.py #fig 2
    #python3 whats_sent_graph.py #fig 3
    #python3 true_ratio_best_ratio_graph.py #fig 5
    #python3 response_graph.py #fig 8
