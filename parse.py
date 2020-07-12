# -*- coding:utf-8 -*-

import sys
import math

class Info:
    def __init__(self):
        self.raw = []

    def add(self, thread, qps):
        self.raw.append(qps)

    def merge(self, info):
        if len(self.raw) == 0:
            for it in info.raw:
                self.raw.append(it)
            return
        if len(self.raw) > len(info.raw):
            self.raw = self.raw[:len(info.raw)]
        for i in range(0, len(self.raw)):
            self.raw[i] += info.raw[i]

    def result(self):
        if len(self.raw) == 0:
            return 0
        if len(self.raw) >= 10:
            raw = self.raw[5:]
        else:
            raw = self.raw

        sum = 0
        count = len(raw)
        for q in raw:
            sum += q

        avg = sum / count
        sqs = 0
        max = 0
        for q in raw:
            sub = q - avg
            abs_sub = abs(q - avg)
            if abs_sub > max:
                max = abs_sub
            sqs += math.pow(abs_sub, 2)
            #print('qps:%.0f - avg:%.0f = jitter:%.0f (%.1f%%)' % (q, avg, sub, abs_sub * 100 / avg))
        return avg, max, math.sqrt(sqs / count)

class Qps:
    def __init__(self):
        self.threads = {}

    def add(self, thread, qps):
        if not self.threads.has_key(thread):
            self.threads[thread] = Info()
        info = self.threads[thread]
        info.add(thread, qps)

    def result(self):
        all = Info()
        for _, thread in self.threads.iteritems():
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
        thread, qps = int(fields[3].strip(':')), float(fields[7].strip('()').split(',')[0])
        res.add(thread, qps)

    avg, max, sd = res.result()
    #print('---')
    print('QPS avg: %.0f, jitter-max: %.1f%%, jitter-sd: %.1f%%' % (avg, max * 100 / avg, sd * 100 / avg))

if __name__ == '__main__':
    run()
