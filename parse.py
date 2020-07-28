# -*- coding:utf-8 -*-

import sys
import math

skip_start=60
skip_thread=[]
sd_smooth_window=10

class Info:
    def __init__(self):
        self.raw = []

    def add(self, time, thread, qps):
        self.raw.append(qps)

    def merge(self, info):
        if len(self.raw) == 0:
            for it in info.raw:
                self.raw.append(it)
            return
        if len(self.raw) > len(info.raw):
            self.raw = self.raw[:len(info.raw)]
        for i in range(0, len(self.raw)):
            # use timestamp of first sample
            self.raw[i] += info.raw[i]

    def result(self):
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
        # use average diff inside sd_smooth_window
        sqs_smooth = 0
        i = 0
        sub_accum = 0
        max = 0
        exp_avg = 0
        max_exp = 0
        for q in raw:
            if exp_avg == 0:
                exp_avg = q
                continue
            abs_sub = abs(q - avg)
            if abs_sub > max:
                max = abs_sub
            if abs(q - exp_avg) > max_exp:
                max_exp = abs(q - exp_avg)
            exp_avg = (exp_avg + q) / 2
            sqs += math.pow(abs_sub, 2)
            sub_accum += abs_sub
            if i % sd_smooth_window == sd_smooth_window - 1:
                sqs_smooth += math.pow(sub_accum / sd_smooth_window, 2)
                sub_accum = 0
            i += 1
        return count, avg, max, max_exp, math.sqrt(sqs / count), math.sqrt(sqs_smooth / int(count / sd_smooth_window))

class Qps:
    def __init__(self):
        self.threads = {}

    def add(self, time, thread, qps):
        if not self.threads.has_key(thread):
            self.threads[thread] = Info()
        info = self.threads[thread]
        info.add(time, thread, qps)

    def result(self):
        all = Info()
        for idx, thread in self.threads.iteritems():
            if idx in skip_thread:
                continue
            all.merge(thread)
        return all.result()

def run():
    res = Qps()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        if len(line) == 0:
            continue
        line = line[:-1]
        if line.find('ops and') < 0:
            continue
        fields = line.split()
        time, thread, qps = fields[0], int(fields[3].strip(':')), float(fields[7].strip('()').split(',')[0])
        res.add(time, thread, qps)

    count, avg, max, max_exp, sd, sd_smooth = res.result()
    #print('---')
    print('Samples: %d, QPS avg: %.0f, j-max: %.1f%%, j-expmax: %.1f%% j-sd: %.1f%%, j-sd-%d: %.1f%%' % (count, avg, max * 100 / avg, max_exp * 100 / avg, sd * 100 / avg, sd_smooth_window, sd_smooth * 100 / avg))

if __name__ == '__main__':
    run()
