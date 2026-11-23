"""FastAPI server for isolated HTTP benchmarks."""
from contextlib import asynccontextmanager
from queue import Queue
from time import perf_counter

from fastapi import FastAPI, Query, Response

from bench import connect
from search import MODES, suggest

pools = {mode: Queue() for mode in MODES}


@asynccontextmanager
async def lifespan(app):
    connections = []
    try:
        for mode, pool in pools.items():
            for _ in range(8):
                conn = connect()
                connections.append(conn)
                if mode == "pgvector":
                    conn.execute("SET enable_seqscan = off")
                pool.put(conn)
        yield
    finally:
        for conn in connections:
            conn.close()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/suggest/{mode}")
def autocomplete(mode: str, response: Response, q: str = Query(min_length=1, max_length=500)):
    if mode not in MODES:
        response.status_code = 404
        return []
    start = perf_counter()
    pool = pools[mode]
    conn = pool.get()
    try:
        rows = suggest(conn, mode, q)
    finally:
        pool.put(conn)
    response.headers["Server-Timing"] = f"search;dur={(perf_counter() - start) * 1000:.3f}"
    return [{"id": row[0], "name": row[1]} for row in rows]
