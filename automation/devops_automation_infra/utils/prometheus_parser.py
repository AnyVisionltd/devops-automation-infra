from prometheus_client import parser
import re
import math


class Parser(object):
    PROMETHEUS_HISTOGRAM_STATS_CLASSIFIER = re.compile("(.*)_bucket$")
    PROMETHEUS_HISTOGRAM_SUM_COUNT = re.compile("(.*)_(sum|count)$")

    def __init__(self, content):
        self.content = content
        self.buckets = {}
        self.histograms = {}
        self.stats = []
        self.BUCKETS_SUM_HANDLERS = {"count" : self._handle_bucket_count,
                                     "sum": self._handle_bucket_sum}

    def _find_series_label(self, series, labels):
        for label_series in series:
            if labels == label_series['labels']:
                return label_series
        return None

    def _create_bucket_stats(self, name):
        return self.buckets.setdefault(name, [])

    def _handle_bucket_sample(self, name, sample):
        series = self._create_bucket_stats(name)
        le = sample.labels.pop('le')
        value = sample.value
        metric = self._find_series_label(series, sample.labels)
        if metric is None:
            metric = {"labels" : sample.labels, "values" : {}}
            series.append(metric)
        metric["values"][float(le)] = float(value)

    def _handle_bucket_sum(self, bucket, sample):
        metric = self._find_series_label(bucket, sample.labels)
        metric['sum'] = sample.value

    def _handle_bucket_count(self, bucket, sample):
        metric = self._find_series_label(bucket, sample.labels)
        metric['count'] = sample.value

    def _bucket_match(self, sample):
        return self.PROMETHEUS_HISTOGRAM_STATS_CLASSIFIER.match(sample.name)

    def _sum_count_match(self, sample):
        return self.PROMETHEUS_HISTOGRAM_SUM_COUNT.match(sample.name)

    def _histogram_stat(self, sample):
        return "quantile" in sample.labels

    def _handle_histogram_stat(self, sample):
        metric = self.histograms.setdefault(sample.name, {"quantile" : {}, "sum" : 0, "count" : 0})
        metric['quantile'][float(sample.labels['quantile'])] = float(sample.value)

    def _pre_parse_stats(self, stats):
        for family in stats:
            remaninig_samples = []
            # First pass identify buckets stats
            for sample in family.samples:
                matches = self._bucket_match(sample)
                if matches is not None:
                    self._handle_bucket_sample(matches[1], sample)
                elif self._histogram_stat(sample):
                    self._handle_histogram_stat(sample)
                else:
                    remaninig_samples.append(sample)

            # second pass go over stats and find histograms/buckets count/sum or other stats
            for sample in remaninig_samples:
                matches = self._sum_count_match(sample)
                if matches is not None:
                    bucket = self.buckets.get(matches[1])
                    if bucket is not None:
                        self.BUCKETS_SUM_HANDLERS[matches[2]](bucket, sample)
                        continue
                    histogram = self.histograms.get(matches[1])
                    if histogram is not None:
                        histogram[matches[2]] = sample.value
                        continue
                    else:
                        self.stats.append(sample)
                else:
                    self.stats.append(sample)

    def parse(self):
        stats = parser.text_string_to_metric_families(self.content)
        self._pre_parse_stats(stats)

        for bucket in self.buckets.values():
            calculate_percentiles(bucket, 0.5, 0.9, 0.99)

        return {'buckets' : self.buckets,
                'histograms' : self.histograms,
                'stats' : self.stats}


def percentiles_on_sample(sample, percentiles):
    total_samples = sample['count']
    search_samples = [math.ceil(percentile * total_samples) for percentile in percentiles]
    percentile_index = 0
    result = {percentile : 0 for percentile in percentiles}
    for key, value in sample['values'].items():
        if percentile_index == len(percentiles):
            break
        while percentile_index < len(percentiles):
            if search_samples[percentile_index] > value:
                break
            percentile = percentiles[percentile_index]
            result[percentile] = key
            percentile_index = percentile_index + 1
    return result


def calculate_percentiles(samples, *percentiles):
    for bucket in samples:
        bucket['percentile'] = percentiles_on_sample(bucket, percentiles)

