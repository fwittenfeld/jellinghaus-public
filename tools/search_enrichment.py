"""Modern search spellings and conservative topic hints; never edit the source CSV."""
import hashlib
import json
import re

VERSION = 3
TOPICS = {
    "tiere": "Tiere", "pflanzen": "Pflanzen", "essen": "Essen & Trinken",
    "landwirtschaft": "Landwirtschaft", "haus": "Haus & Alltag",
    "koerper": "Körper & Gesundheit", "kleidung": "Kleidung",
    "natur": "Natur & Wetter", "menschen": "Menschen, Familie & Gesellschaft",
    "arbeit": "Arbeit & Handwerk", "bewegung": "Bewegung",
    "gefuehle": "Gefühle & Verhalten",
    "eigenschaften": "Eigenschaften & Zustände", "handlungen": "Tätigkeiten & Vorgänge",
    "sprache": "Sprache & Wissen", "raum": "Raum & Lage", "zeit": "Zeit",
    "mengen": "Zahlen, Mengen & Maße", "handel": "Geld & Handel",
    "material": "Materialien & Stoffe", "religion": "Religion & Glaubenswelt",
    "spiel": "Spiel, Musik & Brauchtum", "namen": "Namen & Orte",
    "grundwoerter": "Sprachliche Grundwörter",
}

# Only used for German meanings. No blanket th -> t replacement (e.g. Thymian).
# Longer compounds take precedence; inflected forms retain their endings.
SPELLINGS = {
    "Theil": "Teil", "Athem": "Atem", "wüthig": "wütig", "thöricht": "töricht",
    "Noth": "Not", "hochmüthig": "hochmütig", "Muscatnuss": "Muskatnuss",
    "Bischen": "Bisschen", "Thau": "Tau", "kräftich": "kräftig",
    "aufthauen": "auftauen", "Kampthür": "Kamptür", "todt": "tot",
    "Todte": "Tote", "thauen": "tauen", "thun": "tun", "Thor": "Tor",
    "Thal": "Tal", "Thier": "Tier", "Unthier": "Untier", "Oel": "Öl",
    "Schaar": "Schar", "Thür": "Tür", "theuer": "teuer", "Theuerung": "Teuerung",
    "Epheu": "Efeu", "Mehlthau": "Mehltau", "vermuthete": "vermutete",
    "that": "tat", "Ruthen": "Ruten", "Fluth": "Flut", "Heerd": "Herd",
    "Vogelschaar": "Vogelschar", "Brod": "Brot", "muthmaßen": "mutmaßen",
    "roth": "rot", "demüthig": "demütig", "Buttermilchssuppe": "Buttermilchsuppe",
    "geräth": "gerät", "athmen": "atmen", "Flachsstengel": "Flachsstängel",
    "Großmuth": "Großmut", "Hofthür": "Hoftür", "Thürangel": "Türangel",
    "verheirathen": "verheiraten", "miethen": "mieten", "aichen": "eichen",
    "Thürhaken": "Türhaken", "Faß": "Fass", "Zwölftelthalerstück": "Zwölfteltalerstück",
    "Butterbrod": "Butterbrot", "Käthner": "Kätner", "Excrement": "Exkrement",
    "Kellerthür": "Kellertür", "muthwilligen": "mutwilligen", "Lection": "Lektion",
    "Leinewand": "Leinwand", "muthlos": "mutlos", "Muth": "Mut", "Meth": "Met",
    "Abendbrod": "Abendbrot", "nöthigen": "nötigen", "Nothnachbar": "Notnachbar",
    "Neuntödter": "Neuntöter", "theilnehmend": "teilnehmend", "Thieren": "Tieren",
    "Roßhufe": "Rosshufe", "daß": "dass", "Hintertheil": "Hinterteil",
    "irrthüml": "irrtüml", "tödtliche": "tödliche", "prakticiren": "praktizieren",
    "gemüthlich": "gemütlich", "probiren": "probieren", "Emporien": "Emporen",
    "Spectakel": "Spektakel", "Kuckuk": "Kuckuck", "Rath": "Rat", "rathen": "raten",
    "Emporie": "Empore", "Graubrod": "Graubrot", "rauh": "rau",
    "Todtenuhr": "Totenuhr", "Scheere": "Schere", "geniren": "genieren",
    "des Schoß": "der Schoß", "theilen": "teilen", "Brodschieber": "Brotschieber",
    "kokettiren": "kokettieren", "Hofthor": "Hoftor", "Barrière": "Barriere",
    "leichtmüthiges": "leichtmütiges", "schnabeliren": "schnabulieren",
    "Verwechselung": "Verwechslung", "punctiren": "punktieren", "Krautstengel": "Krautstängel",
    "Thalsenkung": "Talsenkung", "Sanct": "Sankt", "Räthsel": "Rätsel",
    "Thurm": "Turm", "Thätigkeit": "Tätigkeit", "Theer": "Teer", "theeren": "teeren",
    "Punct": "Punkt", "Bifurcation": "Bifurkation", "zweitheilen": "zweiteilen",
    "Werth": "Wert", "Wirth": "Wirt", "wüthend": "wütend", "Wurstbrod": "Wurstbrot",
    "Wachsthum": "Wachstum", "muthwillig": "mutwillig", "Muthwille": "Mutwille",
    "Übermuth": "Übermut", "Wermuth": "Wermut", "flistern": "flüstern",
}
_SPELLING_RE = re.compile("|".join(re.escape(k) for k in sorted(SPELLINGS, key=len, reverse=True)), re.I)
_SPELLINGS_LOWER = {k.lower(): v for k, v in SPELLINGS.items()}


def modern_meaning(value):
    def replace(match):
        old = match.group()
        new = _SPELLINGS_LOWER[old.lower()]
        return new[0].upper() + new[1:] if old[0].isupper() else new[0].lower() + new[1:]
    return _SPELLING_RE.sub(replace, value.replace("ſ", "s"))


def entry_input(row):
    return {
        "id": row["id"],
        "source": row.get("quelle_regularisiert") or row.get("quelle", ""),
        "meaning": modern_meaning(row.get("ziel_regularisiert") or row.get("ziel", "")),
    }


def fingerprint(row):
    payload = {"version": VERSION, "topics": TOPICS, "entry": entry_input(row)}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


# Small, explicit fallback lexicon for a usable preview without model inference.
# It is not presented as LLM output. Ambiguous/contextual matches are left alone.
HINTS = [
    ("tiere", r"^(?:der |die |das )?(?:Aal|Fisch|Hecht|Barsch|Karpfen)\b", ["Fisch", "Fische", "Wassertier"]),
    ("tiere", r"^(?:der |die |das )?(?:Kuh|Pferd|Hund|Katze|Schwein|Vogel|Rabe|Huhn|Gans|Ente|Wolf|Hase|Schnecke|Wespe|Biene|Spinne|Käfer)\b", ["Tier", "Tiere"]),
    ("essen", r"^(?:der |die |das )?(?:Kartoffel|Pellkartoffeln|Brot|Butterbrot|Milch|Buttermilch|Bier|Wein|Käse|Speck|Suppe|Apfel|Birne|Erdbeere|Brombeere|Heidelbeere|Zwiebel|Bohne|Gericht aus)\b", ["Essen", "Nahrung", "Lebensmittel"]),
    ("pflanzen", r"^(?:der |die |das )?(?:Eiche|Efeu|Birke|Fichte|Tanne|Holunderbusch|Klette|Blume|Gras|Salweide|Baum)\b", ["Pflanze", "Pflanzen"]),
    ("landwirtschaft", r"^(?:der |die |das )?(?:Pflug|Verbindungskette am Pfluge|Acker|Ernte|Garben|Flachs)\b", ["Ackerbau", "Landwirtschaft", "Bauernhof"]),
    ("koerper", r"^(?:der |die |das )?(?:Ader|Atem|Auge|Ohr|Nase|Zahn|Zunge|Knie|Daumen|Finger|Bauch|Blut|Kopf|Hand|Fuß|Gehirn)\b", ["Körper", "Körperteil"]),
    ("kleidung", r"^(?:der |die |das )?(?:Schuh|Holzschuh|Holzschuhe|Stiefel|Hut|Hose|Hemd|Rock|Pantoffel)\b", ["Kleidung", "Bekleidung"]),
    ("haus", r"^(?:der |die |das )?(?:Haus|Bett|Tür|Fenster|Tisch|Stuhl|Schublade|Besen|Keller|Herd|Backhaus)\b", ["Haus", "Haushalt", "Alltag"]),
    ("natur", r"^(?:der |die |das )?(?:Regen|Schnee|Wind|Tau|Nebel|Wetter|Sonne|Wald|Wiese|Bach|Fluss|Teich|Erde)\b", ["Natur", "Wetter"]),
]


def enrichment(row, cache):
    source = row.get("quelle_regularisiert") or row.get("quelle", "")
    target = row.get("ziel_regularisiert") or row.get("ziel", "")
    modern = modern_meaning(target)
    aliases = [modern] if modern != target else []
    # User-supplied long-s example applies to Plattdeutsch, not German spelling rules.
    if row["id"] == "lr_0129_004":
        aliases.append(source.replace("ſ", "s"))
    saved = cache.get(row["id"], {})
    if saved.get("fingerprint") == fingerprint(row) and saved.get("engine") in ("local-model-v2", "codex-review-v1"):
        return {"modernMeaning": modern, "searchAliases": aliases,
                "topics": saved["topics"], "semanticTerms": saved["terms"],
                "semanticOrigin": "ai-review" if saved.get("engine") == "codex-review-v1" else "local-model"}
    topics, terms = [], []
    for topic, pattern, keywords in HINTS:
        if re.search(pattern, modern, re.I):
            topics.append(topic)
            terms.extend(keywords)
    return {"modernMeaning": modern, "searchAliases": aliases, "topics": sorted(set(topics)),
            "semanticTerms": sorted(set(terms)), "semanticOrigin": "rules" if topics else "none"}
