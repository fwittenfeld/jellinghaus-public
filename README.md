# Wallenbrücker Wörterbuch

Eine statische, durchsuchbare Ausgabe des Wörterbuchteils aus Hermann Friedrich
Jellinghaus' *Westfälischer Grammatik. Die Laute und Flexionen der
Ravensbergischen Mundart, mit einem Wörterbuche* (Norden, 1885).

Die Einträge wurden von Gerhard Heining aufgearbeitet und eingesprochen. Das
Projekt wurde fachlich von Dr. Robert Damme unterstützt; die technische
Betreuung übernimmt Felix Wittenfeld.

Die Daten in diesem Repository werden automatisch aus dem redaktionellen
Quellprojekt erzeugt. Bitte bearbeite `web/data/dictionary.json` nicht von Hand.

## Lokal ansehen

Da die Seite ihre Daten mit `fetch()` lädt, sollte sie über einen lokalen
Webserver geöffnet werden:

```bash
python -m http.server 8000 --directory web
```

Danach ist sie unter <http://localhost:8000> erreichbar.

## Quelle

Das digitalisierte Original ist beim Internet Archive verfügbar:

<https://archive.org/details/westflischegra00jelluoft/page/116/mode/2up>

Weitere Angaben zu Herkunft und Lizenzen stehen in [NOTICE.md](NOTICE.md).
