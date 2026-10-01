#!/usr/bin/env python3
"""Bounded CPU classification with downloaded model weights; no inference API."""
import argparse
import csv
import json
from pathlib import Path

from search_enrichment import TOPICS, VERSION, enrichment, entry_input, fingerprint

MODEL = "MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli"
ENGINE = "local-model-v1"
# Fixed labels constrain the experiment: the model does not invent definitions.
LABELS = {
    "ein Tier": ("tiere", []),
    "eine Pflanze": ("pflanzen", []),
    "ein Lebensmittel oder Getränk": ("essen", ["Essen", "Lebensmittel"]),
    "etwas aus der Landwirtschaft": ("landwirtschaft", ["Ackerbau"]),
    "ein Haushaltsgegenstand oder Gebäudeteil": ("haus", ["Haushalt"]),
    "ein Körperteil oder eine Krankheit": ("koerper", ["Körper", "Gesundheit"]),
    "ein Kleidungsstück": ("kleidung", ["Bekleidung"]),
    "ein Naturphänomen oder eine Landschaft": ("natur", ["Natur"]),
    "eine Person oder soziale Beziehung": ("menschen", []),
    "einen Beruf oder eine handwerkliche Arbeit": ("arbeit", ["Handwerk"]),
    "eine Bewegung": ("bewegung", []),
    "ein Gefühl oder eine Charaktereigenschaft": ("gefuehle", []),
    "einen Fisch": ("tiere", ["Fisch", "Fische", "Wassertier"]),
    "einen Vogel": ("tiere", ["Vogel", "Vögel"]),
    "ein Insekt": ("tiere", ["Insekt", "Insekten"]),
    "ein Säugetier": ("tiere", ["Säugetier"]),
    "ein Gemüse": ("essen", ["Gemüse", "Essen"]),
    "eine essbare Frucht": ("essen", ["Obst", "Frucht", "Essen"]),
    "ein Brot oder Gebäck": ("essen", ["Brot", "Gebäck", "Essen"]),
    "ein Milchprodukt": ("essen", ["Milchprodukt", "Essen"]),
    "ein Getränk": ("essen", ["Getränk", "Trinken"]),
    "einen Baum": ("pflanzen", ["Baum", "Bäume"]),
    "eine Blume": ("pflanzen", ["Blume", "Blumen"]),
    "ein Werkzeug": ("arbeit", ["Werkzeug"]),
    "ein Möbelstück": ("haus", ["Möbel"]),
    "einen Schuh": ("kleidung", ["Schuh", "Schuhe"]),
    "ein Wetterphänomen": ("natur", ["Wetter"]),
}


def load_cache(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("entries", {})


def validate_results(value, batch):
    expected = {row["id"] for row in batch}
    result = value.get("entries")
    if not isinstance(result, list) or len(result) != len(expected):
        raise ValueError("Incomplete semantic batch")
    found = set()
    for item in result:
        if item["id"] not in expected or item["id"] in found:
            raise ValueError("Unknown or duplicate semantic ID")
        found.add(item["id"])
        if not isinstance(item["topics"], list) or not set(item["topics"]) <= TOPICS.keys():
            raise ValueError("Invalid topics")
        if not isinstance(item["terms"], list) or len(item["topics"]) > 4 or len(item["terms"]) > 12:
            raise ValueError("Too many semantic terms or topics")
        if any(not isinstance(term, str) or not term.strip() or len(term) > 80 for term in item["terms"]):
            raise ValueError("Invalid semantic term")
        item["topics"] = sorted(set(item["topics"]))
        item["terms"] = sorted(set(term.strip() for term in item["terms"]))
    return result


def select_labels(row, prediction, threshold=0.85):
    # Preserve explicit, unambiguous fallback hints even if the model abstains.
    baseline = enrichment(row, {})
    topics, terms = list(baseline["topics"]), list(baseline["semanticTerms"])
    for label, score in zip(prediction["labels"], prediction["scores"]):
        if score < threshold or label not in LABELS:
            continue
        topic, keywords = LABELS[label]
        if topic not in topics and len(topics) >= 4:
            continue
        if topic not in topics:
            topics.append(topic)
        terms.extend(term for term in keywords if term not in terms)
    return {"id": row["id"], "topics": topics, "terms": terms[:12]}


def classify_batch(batch, classifier):
    results = []
    for row in batch:
        meaning = entry_input(row)["meaning"].strip()
        if not meaning or meaning.lower().startswith(("s. ", "siehe ", "vgl. ")):
            prediction = {"labels": [], "scores": []}
        else:
            prediction = classifier(meaning, candidate_labels=list(LABELS),
                                    hypothesis_template="Die Wortbedeutung bezeichnet {}.",
                                    multi_label=True, batch_size=16)
        results.append(select_labels(row, prediction))
    return validate_results({"entries": results}, batch)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=Path("output/jellinghaus_extraction.csv"))
    parser.add_argument("--cache", type=Path, default=Path("output/semantic_cache.json"))
    parser.add_argument("--dictionary", type=Path, help="Enrich an existing public dictionary instead of the source CSV")
    parser.add_argument("--limit", type=int, default=150)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.limit <= 3000:
        parser.error("--limit must be between 1 and 3000")
    if args.dictionary:
        payload = json.loads(args.dictionary.read_text(encoding="utf-8"))
        rows = [{"id": entry["id"], "quelle": entry["source"], "ziel": entry["target"]}
                for entry in payload["entries"]]
    else:
        with args.csv.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter=";"))
    cache = load_cache(args.cache)
    pending = [row for row in rows if cache.get(row["id"], {}).get("fingerprint") != fingerprint(row)
               or cache.get(row["id"], {}).get("engine") != ENGINE]
    if len(pending) > args.limit:
        pending = [pending[i * len(pending) // args.limit] for i in range(args.limit)]
    print(f"Pending in this run: {len(pending)}; cached: {len(cache)}")
    if args.dry_run or not pending:
        return
    # Lazy imports keep builds, tests and dry-runs independent of ML packages.
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
    torch.set_num_threads(2)
    tokenizer = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL, use_safetensors=True, trust_remote_code=False)
    classifier = pipeline("zero-shot-classification", model=model, tokenizer=tokenizer, device=-1)
    for start in range(0, len(pending), 10):
        batch = pending[start:start + 10]
        result = classify_batch(batch, classifier)
        by_id = {row["id"]: row for row in batch}
        for item in result:
            cache[item["id"]] = {"fingerprint": fingerprint(by_id[item["id"]]),
                                 "engine": ENGINE, "model": MODEL,
                                 "topics": item["topics"], "terms": item["terms"]}
        args.cache.parent.mkdir(parents=True, exist_ok=True)
        temp = args.cache.with_suffix(".tmp")
        temp.write_text(json.dumps({"version": VERSION, "entries": cache}, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(args.cache)
        print(f"Processed {min(start + 10, len(pending))}/{len(pending)}", flush=True)
    if args.dictionary:
        by_id = {row["id"]: row for row in rows}
        for entry in payload["entries"]:
            entry.update(enrichment(by_id[entry["id"]], cache))
        payload["meta"]["semanticCount"] = sum(entry["semanticOrigin"] == "local-model" for entry in payload["entries"])
        temp = args.dictionary.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        temp.replace(args.dictionary)


if __name__ == "__main__":
    main()
