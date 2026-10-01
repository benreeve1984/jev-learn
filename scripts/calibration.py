"""Measure Jev's calibration on public human-labelled datasets -> docs/calibration.js.

Run: .venv/bin/python scripts/calibration.py
"""
import asyncio, json, os, random, urllib.request
from datetime import date
from pathlib import Path

from dotenv import dotenv_values

if "TYPESAFE_API_KEY" not in os.environ:
    os.environ["TYPESAFE_API_KEY"] = dotenv_values(Path.home() / "Developer/candor/.env")["TYPESAFE_API_KEY"]

from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul

OUT = Path(__file__).resolve().parent.parent / "docs" / "calibration.js"
N = 500
random.seed(0)


def rows(dataset, split, n_total):
    out = []
    for off in range(0, n_total, 100):
        url = (f"https://datasets-server.huggingface.co/rows?dataset={dataset}&config=default"
               f"&split={split}&offset={off}&length=100")
        out += [r["row"] for r in json.load(urllib.request.urlopen(url))["rows"]]
    return out


def ece(ps, ys, bins=10):
    """Expected calibration error over equal-width bins; also returns the bins for plotting."""
    b = [[] for _ in range(bins)]
    for p, y in zip(ps, ys):
        b[min(int(p * bins), bins - 1)].append((p, y))
    tbl = [{"n": len(x), "mean_p": sum(p for p, _ in x) / len(x), "frac": sum(y for _, y in x) / len(x)}
           for x in b if x]
    return sum(t["n"] * abs(t["mean_p"] - t["frac"]) for t in tbl) / len(ps), tbl


async def run(items, make):
    sem = asyncio.Semaphore(12)
    async with AsyncTypeSafeClient() as c:
        async def one(it):
            async with sem:
                state, qs = make(it)
                return (await c.system_one(state=state, questions=qs)).model_dump(mode="json")["answers"]["q"]
        return await asyncio.gather(*(one(it) for it in items))


def binary_report(name, ps, ys):
    e, tbl = ece(ps, ys)
    return {"name": name, "n": len(ys),
            "accuracy": sum((p > .5) == bool(y) for p, y in zip(ps, ys)) / len(ys),
            "brier": sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(ys),
            "ece": e, "bins": tbl}


async def main():
    res = {"captured": date.today().isoformat()}

    sst = random.sample(rows("stanfordnlp/sst2", "validation", 872), N)
    a = await run(sst, lambda r: (r["sentence"], {"q": Noul(instructions="Is this movie review positive?")}))
    res["sst2"] = binary_report("SST-2 sentiment (Noul)", [x["noul"] for x in a], [r["label"] for r in sst])

    bq = random.sample(rows("google/boolq", "validation", 1000), N)
    a = await run(bq, lambda r: ({"passage": r["passage"]},
                                 {"q": Noul(instructions=f"According to the passage: {r['question']}?")}))
    res["boolq"] = binary_report("BoolQ reading comprehension (Noul)", [x["noul"] for x in a],
                                 [int(r["answer"]) for r in bq])

    names = ["World", "Sports", "Business", "Sci/Tech"]
    ag = random.sample(rows("fancyzhx/ag_news", "test", 1000), N)
    a = await run(ag, lambda r: (r["text"], {"q": Choice(instructions="What is the topic of this news article?",
                                                         criteria={k: None for k in names})}))
    top = [max(x["probabilities"].values()) for x in a]
    hit = [int(x["choice"] == names[r["label"]]) for x, r in zip(a, ag)]
    e, tbl = ece(top, hit)
    res["agnews"] = {"name": "AG News topic, 4 classes (Choice)", "n": N, "accuracy": sum(hit) / N,
                     "brier": sum(sum((x["probabilities"].get(k, 0) - (k == names[r["label"]])) ** 2 for k in names)
                                  for x, r in zip(a, ag)) / N,
                     "ece": e, "bins": tbl,
                     "acc_by_conf": {f">={t}": (lambda s: {"n": len(s), "acc": sum(s) / len(s) if s else None})(
                         [h for x, h in zip(a, hit) if x["confidence"] >= t]) for t in (0.5, 0.8, 0.9)}}

    OUT.write_text("window.CALIBRATION = " + json.dumps(res, indent=1) + ";\n")
    for k in ("sst2", "boolq", "agnews"):
        r = res[k]
        print(f"{r['name']:40s} n={r['n']} acc={r['accuracy']:.3f} brier={r['brier']:.3f} ece={r['ece']:.3f}")
        for t in r["bins"]:
            print(f"   p~{t['mean_p']:.2f} actual={t['frac']:.2f} n={t['n']}")
    print(res["agnews"]["acc_by_conf"])


asyncio.run(main())
