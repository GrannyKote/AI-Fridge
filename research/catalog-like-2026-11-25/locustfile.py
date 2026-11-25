"""Deterministic traffic over the same fixed query mix in every arm."""
import csv
import itertools
import os
from random import Random

from locust import HttpUser, constant, events, task

from bench import records, RESULTS

mode = os.environ["CATALOG_MODE"]
size = int(os.environ["CATALOG_SIZE"])
trial = int(os.environ["CATALOG_TRIAL"])
queries = records("queries.csv")
Random(71 + trial).shuffle(queries)
cycle = itertools.cycle(queries)
samples = []


class AutocompleteUser(HttpUser):
    wait_time = constant(.05)

    @task
    def request_suggestion(self):
        query = next(cycle)
        self.client.get(f"/suggest/{mode}", params={"q": query["query"]},
                        context={"noise": query["noise"]}, name=mode, timeout=5)


@events.request.add_listener
def capture(response_time, response, context, exception, **kwargs):
    server = response.headers.get("Server-Timing", "").removeprefix("search;dur=") if response is not None else ""
    samples.append((context.get("noise"), response_time, server, bool(exception)))


@events.quitting.add_listener
def export(environment, **kwargs):
    destination = RESULTS / f"latency-{size}-{mode}-{trial}.csv"
    with destination.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["noise", "http_ms", "server_ms", "failed"])
        writer.writerows(samples)
