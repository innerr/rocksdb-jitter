#!/bin/bash

function run()
{
        local filter="${1}"
        local rounds="${2}"
        local path="${3}"

        if [ -z "${rounds}" ]; then
                local rounds='2'
        fi

        local date=`date +%Y%m%d_%H%M%S`
        local output="${path}/log/${date}"
        mkdir -p "${output}"

        local flags="-stats_interval_seconds=1 -report_bg_io_stats=true -statistics --db=${path}/db"
        local warmup="--benchmarks=readrandomwriterandom,stats,levelstats -readwritepercent=10 -num=10000000 -key_size=16 -value_size=16 -batch_size=10 -threads=1"

        for file in ${path}/workloads/*; do
                local workload=`basename "${file}"`
                local filtered=`echo "${workload}" | grep "${filter}"`
                if [ -z "${filtered}" ]; then
                        continue
                fi
                echo "=> ${workload}"
                local job=`cat ${file}`
                echo "[${workload}] ${job}" >> "${output}/report"
                for (( i = 0; i < ${rounds}; i++)); do
                        db_bench ${flags} ${warmup} 2>&1 | awk '{print "['${workload}' warmup] "$0}'
                        db_bench ${flags} ${job} --use_existing_db=true 2>&1 | \
                                tee "${output}/${workload}.${i}.log" | awk '{print "['${workload}'] "$0}'
                        cat "${output}/${workload}.${i}.log" | python parse.py | \
                                awk '{print "['${workload}'] "$0}' | tee -a "${output}/report"
                done
        done
}

function print_help()
{
        echo "usage: <bin> work_dir [filter_string=''] [run_times_for_each_workload=2]" >&2
}

work_dir="${1}"
filter="${2}"
rounds="${3}"

if [ -z "${work_dir}" ]; then
        print_help
        exit 1
fi
if [ ! -d "${work_dir}" ]; then
        print_help
        echo "error: the work_dir '${work_dir}' not exists (or not a dir)" >&2
        exit 1
fi
if [ ! -d "${work_dir}/workloads" ]; then
        print_help
        echo "error: the workload dir '${work_dir}/workloads' not exists" >&2
        exit 1
fi

db_bench_exists=`db_bench --help 2>&1 | grep max_background_compactions`
if [ -z "${db_bench_exists}" ]; then
        echo "error: db_bench not found (build rocksdb and add db_bench to \$PATH)" >&2
        exit 1
fi

set -euo pipefail
run "${filter}" "${rounds}" "${work_dir}"
