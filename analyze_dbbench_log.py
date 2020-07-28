# -*- coding:utf-8 -*-
# python >= 3.6
# used with perf_level=3 and show_table_properties is on

import sys
import math

skip_thread=[]
# for jitter
# now we monitor block_read_time/count jitter
skip_start=60

def parse_perf_context(line):
    metrics = {}
    fields = line.replace(',', '').replace('=', '').split()[2:]
    noun = ""
    for i in range(len(fields)):
        if fields[i].isdigit() and i > 0:
            metrics[fields[i-1]] = int(fields[i])
        elif fields[i].find('@') > 0:
            idx = fields[i].find('@')
            metrics[noun + "_" + fields[i][idx + 1:]] = int(fields[i][:idx])
        else:
            noun = fields[i]
    return metrics

class Jitter:
    def __init__(self):
        self.raw = []
        self.cursor = 0.0
    def add(self, val):
        self.cursor += val
    def finish_epoch(self):
        self.raw.append(self.cursor)
        self.cursor = 0.0
    def summarize(self, name):
        if len(self.raw) == 0:
            return 0
        if len(self.raw) >= skip_start * 2:
            raw = self.raw[skip_start:]
        else:
            raw = self.raw
        sum = 0
        count = len(raw)
        for q in raw:
            sum += q
        avg = sum / count
        sqs = 0
        sqs_10 = 0
        i = 0
        sub_accum = 0
        max = 0
        exp_avg = 0
        max_exp = 0
        for q in raw:
            if exp_avg == 0:
                exp_avg = q
                continue

            sub = q - avg
            abs_sub = abs(q - avg)
            if abs_sub > max:
                max = abs_sub
            if abs(q - exp_avg) > max_exp:
                max_exp = abs(q - exp_avg)
            exp_avg = (exp_avg + q) / 2
            sqs += math.pow(abs_sub, 2)
            sub_accum += abs_sub
            if i % 10 == 9:
                sqs_10 += math.pow(sub_accum / 10, 2)
                sub_accum = 0
            i += 1
        if avg <= 0:
            print(f"[{name}] average is non-positive")
        else:
            print(f"[{name}] Sample: {count}, avg: {avg:.0f}, j-max: {(max*100/avg):.1f}, j-expmax: {(max_exp*100/avg):.1f}, j-sd: {(math.sqrt(sqs / count)*100/avg):.1f}, j-sd-10: {(math.sqrt(sqs_10 / int((count + 1)/10))*100/avg):.1f}")

def run(parse_read):
    op = 0
    last_level_block_count = [0] * 10 # except for bottommost
    current_level_block_count = [0] * 10
    in_reading_levels = False
    jitters = {}
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        if len(line) == 0:
            continue
        line = line[:-1]
        if line.find('Level[') == 0:
            fields = line.split()
            level = int(fields[0][6:-2]) # Level[n]:
            count = int(fields[3][7:-1]) # blocks=152126;
            if level < 10:
                current_level_block_count[level] = count
            in_reading_levels = True
        elif in_reading_levels:
            for i in range(len(current_level_block_count)):
                if last_level_block_count[i] == current_level_block_count[i]:
                    continue
                if last_level_block_count[i] == 0:
                    print(f"event: Level {i} appears last epoch")
                elif current_level_block_count[i] == 0:
                    print(f"event: Level {i} disappears last epoch")
                elif current_level_block_count[i] > last_level_block_count[i]:
                    print(f"event: Level {i} bigger last epoch")
                else:
                    print(f"event: Level {i} smaller last epoch")
            last_level_block_count = current_level_block_count
            current_level_block_count = [0] * 10
            in_reading_levels = False
        if line.find('ops and') > 0:
            fields = line.split()
            thread, op, qps = int(fields[3].strip(':')), float(fields[4].strip('()').split(',')[0]), float(fields[7].strip('()').split(',')[0])
            if thread == 0:
                # next epoch
                for (_, j) in jitters.items():
                    j.finish_epoch()
            if thread in skip_thread:
                continue
            print(f'{fields[0]} thread {thread} {op} ops and {qps} ops/second, latency {(1000000000.0 / qps):.2f} ns')
        elif line.find('perf context') >= 0:
            metrics = parse_perf_context(line)
            if 'get_from_memtable_time' in metrics:
                # parse read related metrics
                print(f"user_key_comp/op = {(metrics['user_key_comparison_count'] / op):.2f}", end = ', ')
                block_read_total = 0
                for (name, val) in metrics.items():
                    if name.startswith("block_read_count"):
                        time_name = name.replace('count', 'time')
                        if time_name in metrics:
                            print(f"{time_name}/count = {(metrics[time_name] / val):.2f}", end = ', ')
                            if not name in jitters:
                                jitters[name] = Jitter()
                            jitters[name].add(metrics[time_name] / val)
                        else:
                            print(f"missing {time_name}", end = ', ')
                        print(f"{name}/op = {(val / op):.2f}", end = ', ')
                        block_read_total += val
                print(f"read_filter_block_time/op = {(metrics['read_filter_block_nanos'] / op):.2f}", end = ', ')
                print(f"read_index_block_time/op = {(metrics['read_index_block_nanos'] / op):.2f}", end = ', ')
                print(f"block_seek_time/op = {(metrics['block_seek_nanos'] / op):.2f}", end = ', ')
                print(f"new_block_iter_time/op = {(metrics['new_table_block_iter_nanos'] / op):.2f}", end = ', ')
                if "new_table_block_iter_nocached_nanos" in metrics:
                    print(f"new_block_iter_nocached_time/op = {(metrics['new_table_block_iter_nocached_nanos'] / op):.2f}", end = ', ')
                if "new_index_block_iter_nanos" in metrics:
                    print(f"new_index_block_iter_time/op = {(metrics['new_index_block_iter_nanos'] / op):.2f}", end = ', ')
                print(f"block_decompress_time/op = {(metrics['block_decompress_time'] / op):.2f}", end = ', ')
                print(f"block_read_byte/count = {(metrics['block_read_byte'] / block_read_total):.2f}", end = ', ')
                print(f"block_decompress_time/bytes = {(metrics['block_decompress_time'] / metrics['block_read_byte']):.2f}", end = ', ')
                print(f"get_from_files_time/count = {(metrics['get_from_output_files_time'] / metrics['get_from_output_files_count']):.2f}", end = ', ')
                print(f"get_from_files/op = {(metrics['get_from_output_files_count'] / op * 100):.2f}%", end = ', ')
                print(f"get_byte/op = {(metrics['get_read_bytes'] / op):.2f}", end = ', ')
                print(f"get_from_mem_time/count = {(metrics['get_from_memtable_time'] / metrics['get_from_memtable_count']):.2f}", end = ', ')
                print(f"get_from_mem/op = {(metrics['get_from_memtable_count'] / op):.2f}", end = ', ')
                print(f"bloom_sst_hit_rate = {(metrics['bloom_sst_hit_count'] / (metrics['bloom_sst_miss_count'] + metrics['bloom_sst_hit_count']) * 100):.2f}", end = ', ')
                print("block_cache_hit_rate = [", end = '')
                for (name, val) in metrics.items():
                    if name.startswith("block_cache_miss_count"):
                        # it's possible to have zero hit
                        level = name[23:]
                        hit = 0 if not ("block_cache_hit_count_" + level) in metrics else metrics["block_cache_hit_count_" + level]
                        print(f"{(hit / (val + hit) * 100):.2f}@{level}", end = ', ')
                    if name.startswith("block_cache_hit_count_") and not ("block_cache_miss_count_" + name[22:]) in metrics:
                        print(f"{100}@{name[22:]}", end = ', ')
                print(']', end = '')
                print("") # newline
            # TODO: write related perf context parsing
        elif line.find('event:') >= 0:
            print(line)
    for (k, j) in jitters.items():
        j.summarize(k)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        run(True if sys.argv[1] == 'read' else False)
    else:
        run(True)

