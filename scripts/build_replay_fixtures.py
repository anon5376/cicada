#!/usr/bin/env python3
"""Extract replay fixtures from the captured wiki how-solved page."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIKI = Path(
    "/Users/anon5376/.cursor/projects/Users-anon5376-Projects-cicada/agent-tools/1a4a9a57-d5cc-4ba0-a0b6-e89e747cfc97.txt"
)
OUT = ROOT / "tests" / "liber_primus" / "replay_fixtures.json"
HEAD = ROOT / "tests" / "liber_primus" / "lp2_unsolved_head.txt"


def extract_section(text: str, heading: str) -> str:
    idx = text.find(f"## {heading}")
    if idx < 0:
        raise SystemExit(f"missing heading {heading}")
    rest = text[idx + 3 :]
    nxt = re.search(r"\n## ", rest)
    return rest[: nxt.start()] if nxt else rest


def fenced_blocks(section: str) -> list[str]:
    return re.findall(r"```\n(.*?)```", section, flags=re.S)


def first_rune_block(blocks: list[str]) -> str:
    for b in blocks:
        if any(0x16A0 <= ord(ch) <= 0x16FF for ch in b):
            return b.strip()
    raise SystemExit("no rune block")


def main() -> None:
    text = WIKI.read_text(encoding="utf-8")
    fixtures = []

    warn = extract_section(text, "A warning")
    wblocks = fenced_blocks(warn)
    fixtures.append(
        {
            "stage_id": "lp1.warning",
            "aliases": ["LP1 01.jpg", "A warning"],
            "collection": "LP1_early_2014",
            "ciphertext": first_rune_block(wblocks),
            "method": "atbash",
            "key": None,
            "expected_latin_normalized": "AWARNNGBELIEVENOTHNGFROMTHISBOOCEXCEPTWHATYOVCNOWTOBETRVETESTTHECNOWLEDGEFINDYOVRTRVTHEXPERIENCEYOVRDEATHDONOTEDITORCHANGETHISBOOCORTHEMESSAGECONTAINEDWITHINEITHERTHEWORDSORTHEIRNVMBERSFORALLISSACRED",
            "claim_source": "uncovering-cicada-wiki-how-solved-2026-09-07",
        }
    )

    wisdom = extract_section(text, "Some wisdom")
    sblocks = fenced_blocks(wisdom)
    fixtures.append(
        {
            "stage_id": "lp1.wisdom",
            "aliases": ["LP1 05.jpg", "Some wisdom"],
            "collection": "LP1_early_2014",
            "ciphertext": first_rune_block(sblocks),
            "method": "direct",
            "key": None,
            "expected_contains": [
                "SOMEWISDOM",
                "THEPRIMESARESACRED",
                "THETOTIENTFVNCTIANISSACRED",
                "ALLTHNGSSHOVLDBEENCRYPTED",
            ],
            "claim_source": "uncovering-cicada-wiki-how-solved-2026-09-07",
        }
    )

    p57 = extract_section(text, "Parable (57.jpg)")
    fixtures.append(
        {
            "stage_id": "lp2.page57_parable",
            "aliases": ["LP2 57.jpg", "PAGE 57"],
            "collection": "LP2_onion_0_57",
            "ciphertext": first_rune_block(fenced_blocks(p57)),
            "method": "direct",
            "key": None,
            "expected_latin_normalized": "PARABLELICETHEINSTARTVNNELNGTOTHESVRFACEWEMVSTSHEDOVROWNCIRCVMFERENCESFINDTHEDIVINITYWITHINANDEMERGE",
            "claim_source": "uncovering-cicada-wiki-how-solved-2026-09-07",
        }
    )

    p56 = extract_section(text, "An end (56.jpg)")
    fixtures.append(
        {
            "stage_id": "lp2.page56_an_end",
            "aliases": ["LP2 56.jpg", "An end"],
            "collection": "LP2_onion_0_57",
            "ciphertext": first_rune_block(fenced_blocks(p56)),
            "method": "totient_prime",
            "key": None,
            "expected_contains": [
                "ANEND",
                "WITHINTHEDEEPWEB",
                "THEREEXISTSAPAGETHATHASHESTO",
            ],
            "notes": "Paragraph 1 (45 runes) reproduces under totient-prime. Paragraph 2 does not match the wiki second sentence under a continuous or reset totient stream on this transcription.",
            "claim_source": "uncovering-cicada-wiki-how-solved-2026-09-07",
        }
    )

    unsolved = extract_section(text, "0.jpg to 55.jpg (UNSOLVED)")
    ct = first_rune_block(fenced_blocks(unsolved))
    # first ~800 runes as a head target (page-0-ish region of the concatenated dump)
    runes = [ch for ch in ct if 0x16A0 <= ord(ch) <= 0x16FF]
    HEAD.write_text("".join(runes[:400]), encoding="utf-8")

    OUT.write_text(json.dumps(fixtures, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", OUT, "fixtures", len(fixtures), "head_runes", 400)


if __name__ == "__main__":
    main()
