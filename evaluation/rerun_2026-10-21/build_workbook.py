"""Build NFR3_v1_v2_rerun.xlsx from the re-run's score tables, copying the layout of the existing NFR3 sheet.

Template (read only): SelfDoneEval/Evaluation_Results (Version 2).xlsx, sheet
"NFR3 Lesson-plan accuracy (V3)". Fonts, fills, borders, column widths, row
positions, merged cells, frozen header, dropdowns and the "not there"
highlight are copied from it; the description line (empty in that sheet) is
taken from the same sheet in ThesisWriting/.../Evaluation_Results_Final_Clean.xlsx.
v3's figures for the comparison sheet are computed from the template's own
feature table (nothing is re-run).

Run with an interpreter that has openpyxl:  python build_workbook.py
"""

import copy
import csv
import re
import sys
from pathlib import Path

import openpyxl
from openpyxl.comments import Comment
from openpyxl.formatting.rule import Rule
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.formula import ArrayFormula

HERE = Path(__file__).resolve().parent
THESIS = HERE.parent.parent.parent
TEMPLATE = THESIS / "SelfDoneEval" / "Evaluation_Results (Version 2).xlsx"
TEMPLATE_SHEET = "NFR3 Lesson-plan accuracy (V3)"
DESCRIPTION_FROM = THESIS / "ThesisWriting" / "Referencing" / "Eval" / "Evaluation_Results_Final_Clean.xlsx"
REVIEWED = sys.argv[1:] == ["reviewed"]  # build from the *_reviewed tables (after the manual check)
SUFFIX = "_reviewed" if REVIEWED else ""
OUT = HERE / f"NFR3_v1_v2_rerun{SUFFIX}.xlsx"
DATE = "21 October 2026"

FEAT_FIRST, FEAT_LAST = 17, 258      # feature table rows in the template
QUOTE_TITLE, QUOTE_FIRST, QUOTE_LAST = 265, 267, 766
SETS = [("T01–T10", 1, 10), ("T11–T20", 11, 20), ("T21–T30", 21, 30), ("T31–T60", 31, 60), ("All 60", 1, 60)]

tpl_wb = openpyxl.load_workbook(TEMPLATE)
tpl = tpl_wb[TEMPLATE_SHEET]
description = openpyxl.load_workbook(DESCRIPTION_FROM)["NFR3 Lesson-plan accuracy"]["A2"].value


def read_tsv(name: str) -> list:
    # v1_scoring.tsv is hand-typed plain text; the other tables were written by csv with standard quoting.
    literal = name == "v1_scoring.tsv"
    with (HERE / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", **({"quoting": csv.QUOTE_NONE} if literal else {})))


def style_from(dst, src) -> None:
    dst.font, dst.fill, dst.border = copy.copy(src.font), copy.copy(src.fill), copy.copy(src.border)
    dst.alignment, dst.number_format, dst.protection = copy.copy(src.alignment), src.number_format, copy.copy(src.protection)


def text_height(text: str, chars_per_line: int = 115, line: float = 12.75) -> float:
    lines = sum(max(1, -(-len(part) // chars_per_line)) for part in text.split("\n"))
    return max(line * lines + 3, 14.25)


def manual_numbers() -> dict:
    """{(version, transcript_id, text): number in needs_manual_check.md}."""
    out, version = {}, None
    for line in (HERE / "needs_manual_check.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"## (v\d)", line)
        if m:
            version = m.group(1)
        m = re.match(r"(\d+)\. \*\*(T\d\d)\*\*", line)
        if m:
            number, tid = m.groups()
            out.setdefault((version, tid), []).append(int(number))
    return out


def build_version_sheet(wb, version: str, method: list, failed: list) -> None:
    ws = wb.create_sheet(f"NFR3 Version {version[1]}")
    # Layout copied from the template.
    for key, dim in tpl.column_dimensions.items():
        if dim.width:
            ws.column_dimensions[key].width = dim.width
    for r in range(1, 17):
        ws.row_dimensions[r].height = tpl.row_dimensions[r].height
        for col in "ABCDE":
            style_from(ws[f"{col}{r}"], tpl[f"{col}{r}"])
            v = tpl[f"{col}{r}"].value
            if v is not None and not isinstance(v, ArrayFormula):
                ws[f"{col}{r}"] = v
    for rng in ["A1:E1", "A2:E2", "A3:E3", "A4:E4", "A5:E5", "A6:E6", "A7:E7", "A8:E8", "A9:E9",
                "A11:C11", "A12:B12", "A13:B13", "A14:B14", "A15:B15"]:
        ws.merge_cells(rng)
    ws.freeze_panes = tpl.freeze_panes
    ws.sheet_properties.tabColor = copy.copy(tpl.sheet_properties.tabColor)
    ws.sheet_view.showGridLines = tpl.sheet_view.showGridLines
    ws.sheet_view.zoomScale = tpl.sheet_view.zoomScale

    ws["A1"] = f"NFR3 · Lesson-plan accuracy (Test 6) — Lesson planner {version}"
    ws["A2"] = description
    ws["A3"] = "Method"
    for r, text in zip(range(4, 10), method):
        ws[f"A{r}"] = text
        ws.row_dimensions[r].height = max(text_height(text), tpl.row_dimensions[r].height or 0)
    # Results formulas: the template's, except C13's range, which the template stops at row 228; here it covers
    # the whole feature table (17-258), as C12 and C15 already do, so no row is left out.
    ws["C12"] = f'=IF(COUNTIF($C${FEAT_FIRST}:$C${FEAT_LAST},"Y")=0,"",COUNTIF($E${FEAT_FIRST}:$E${FEAT_LAST},"hit")/COUNTIF($C${FEAT_FIRST}:$C${FEAT_LAST},"Y"))'
    a, e = f"$A${FEAT_FIRST}:$A${FEAT_LAST}", f"$E${FEAT_FIRST}:$E${FEAT_LAST}"
    ws["C13"] = ArrayFormula("C13", f'=IF(SUMPRODUCT(({a}<>"")/COUNTIF({a},{a}&""))=0,"",COUNTIF({e},"false alarm")/SUMPRODUCT(({a}<>"")/COUNTIF({a},{a}&"")))')
    q = f"$C${QUOTE_FIRST}:$C${QUOTE_LAST}"
    ws["C14"] = f'=IF(COUNTA({q})=0,"",COUNTIF({q},"not there")/COUNTA({q}))'
    ws["C15"] = f'=IF(COUNTIF({e},"hit")+COUNTIF({e},"false alarm")=0,"",COUNTIF({e},"hit")/(COUNTIF({e},"hit")+COUNTIF({e},"false alarm")))'

    # By-set table beside the results (G11:N16), so no template row moves.
    head = ["Set", "hits", "planted", "hit rate", "false alarms", "false alarms per transcript",
            "quotes checked", "quotes not there"]
    for i, (col, h) in enumerate(zip("GHIJKLMN", head)):
        cell = ws[f"{col}11"]
        cell.value = h
        style_from(cell, tpl["A16"])
        ws.column_dimensions[col].width = 12 if i else 11
    failed_ids = {f["transcript_id"] for f in failed}
    for r, (name, lo, hi) in zip(range(12, 17), SETS):
        n = sum(1 for i in range(lo, hi + 1) if f"T{i:02d}" not in failed_ids)
        ids = f'{a},">=T{lo:02d}",{a},"<=T{hi:02d}"'
        qa = f"$A${QUOTE_FIRST}:$A${QUOTE_LAST}"
        qids = f'{qa},">=T{lo:02d}",{qa},"<=T{hi:02d}"'
        values = [name, f'=COUNTIFS({ids},{e},"hit")', f'=COUNTIFS({ids},$C${FEAT_FIRST}:$C${FEAT_LAST},"Y")',
                  f'=IF(I{r}=0,"",H{r}/I{r})', f'=COUNTIFS({ids},{e},"false alarm")', f"=K{r}/{n}",
                  f"=COUNTIFS({qids})", f'=COUNTIFS({qids},{q},"not there")']
        for col, v in zip("GHIJKLMN", values):
            cell = ws[f"{col}{r}"]
            cell.value = v
            style_from(cell, tpl["C12"] if col != "G" else tpl["A12"])
            cell.number_format = {"J": "0.00", "L": "0.0"}.get(col, "General")

    numbers = manual_numbers()
    # Feature table.
    feats = [r for r in read_tsv(f"{version}_features{SUFFIX}.tsv") if r["result"] in ("hit", "miss", "false alarm")]
    assert len(feats) <= FEAT_LAST - FEAT_FIRST + 1, "feature table would overflow the template's rows"
    unsure = {}
    if version == "v1":
        for r in read_tsv(f"v1_scoring{SUFFIX}.tsv"):
            if r["confidence"] == "unsure":
                unsure.setdefault((r["transcript_id"], r["feature"]), r)
    for row, f in zip(range(FEAT_FIRST, FEAT_LAST + 1), feats):
        for col, v in zip("ABCDE", [f["transcript_id"], f["feature"], f["planted"], f["reported"], f["result"]]):
            cell = ws[f"{col}{row}"]
            cell.value = v
            style_from(cell, tpl[f"{col}{FEAT_FIRST}"])
        ws.row_dimensions[row].height = tpl.row_dimensions[FEAT_FIRST].height
        key = (f["transcript_id"], f["feature"])
        if key in unsure and REVIEWED:
            ws[f"E{row}"].comment = Comment(f"Checked by hand: {unsure[key]['reviewed']}", "rerun")
        elif key in unsure:
            ws[f"E{row}"].comment = Comment(f"Judgement call: see needs_manual_check.md ({f['transcript_id']}).", "rerun")

    # Quotes table.
    ws.merge_cells(f"A{QUOTE_TITLE}:E{QUOTE_TITLE}")
    for col in "ABCDE":
        style_from(ws[f"{col}{QUOTE_TITLE}"], tpl[f"{col}{QUOTE_TITLE}"])
        style_from(ws[f"{col}{QUOTE_TITLE + 1}"], tpl[f"{col}{QUOTE_TITLE + 1}"])
        ws[f"{col}{QUOTE_TITLE + 1}"].value = tpl[f"{col}{QUOTE_TITLE + 1}"].value
    ws[f"A{QUOTE_TITLE}"] = "Quotes: every example the analysis quotes as said in the session, checked against the transcript"
    ws.row_dimensions[QUOTE_TITLE + 1].height = tpl.row_dimensions[QUOTE_TITLE + 1].height
    quotes = [r for r in read_tsv(f"{version}_quotes{SUFFIX}.tsv") if r["found"] != "excluded"]
    assert len(quotes) <= QUOTE_LAST - QUOTE_FIRST + 1, "quotes table would overflow the template's rows"
    for row, qr in zip(range(QUOTE_FIRST, QUOTE_LAST + 1), quotes):
        for col, v in zip("ABC", [qr["transcript_id"], qr["quote"], qr["found"]]):
            cell = ws[f"{col}{row}"]
            cell.value = v
            style_from(cell, tpl[f"{col}{QUOTE_FIRST}"])
        ws.row_dimensions[row].height = text_height(qr["quote"], 55)
        if qr["how"] == "checked by hand":
            ws[f"C{row}"].comment = Comment(f"Checked by hand: {qr['reviewed']}", "rerun")
        elif qr["how"] == "PROVISIONAL":
            ws[f"C{row}"].comment = Comment(
                f"Provisional (automatic). Closest {qr['speaker']} turn: \"{qr['closest_turn'][:200]}\". "
                f"See needs_manual_check.md ({qr['transcript_id']}).", "rerun")

    # Failed runs, below the quotes table.
    r = QUOTE_LAST + 3
    ws.merge_cells(f"A{r}:E{r}")
    for col in "ABCDE":
        style_from(ws[f"{col}{r}"], tpl[f"{col}{QUOTE_TITLE}"])
    ws[f"A{r}"] = "Failed runs (crashed or timed out twice; not scored)"
    if not failed:
        ws[f"A{r + 1}"] = "None: all 60 transcripts produced a plan on the first attempt."
        style_from(ws[f"A{r + 1}"], tpl["A4"])
    for i, f in enumerate(failed, 1):
        ws[f"A{r + i}"], ws[f"B{r + i}"] = f["transcript_id"], f["reason"]
        style_from(ws[f"A{r + i}"], tpl[f"A{FEAT_FIRST}"])
        style_from(ws[f"B{r + i}"], tpl[f"B{FEAT_FIRST}"])

    # Dropdowns and the "not there" highlight, as in the template.
    for dv in tpl.data_validations.dataValidation:
        sqref = {"C17:D258": f"C{FEAT_FIRST}:D{FEAT_LAST}", "E17:E258": f"E{FEAT_FIRST}:E{FEAT_LAST}"}.get(
            str(dv.sqref), f"C{QUOTE_FIRST}:C{QUOTE_LAST}")
        new = DataValidation(type=dv.type, formula1=dv.formula1, allow_blank=dv.allow_blank,
                             showErrorMessage=dv.showErrorMessage, errorTitle=dv.errorTitle, error=dv.error)
        new.add(sqref)
        ws.add_data_validation(new)
    for cf in tpl.conditional_formatting:
        if str(cf.sqref) == f"C{QUOTE_FIRST}:C{QUOTE_LAST}":
            for rule in cf.rules:
                new = Rule(type=rule.type, operator=rule.operator, formula=list(rule.formula), dxf=copy.copy(rule.dxf))
                ws.conditional_formatting.add(f"C{QUOTE_FIRST}:C{QUOTE_LAST}", new)


def failed_runs(version: str) -> list:
    out = []
    for p in sorted((HERE / version).glob("T*_FAILED.txt")):
        last = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()][-1]
        out.append({"transcript_id": p.stem.split("_")[0], "reason": last})
    return out


def v3_by_set() -> dict:
    rows = [(tpl.cell(r, 1).value, tpl.cell(r, 3).value, tpl.cell(r, 5).value) for r in range(FEAT_FIRST, FEAT_LAST + 1)
            if tpl.cell(r, 1).value]
    out = {}
    for name, lo, hi in SETS:
        ids = {f"T{i:02d}" for i in range(lo, hi + 1)}
        sel = [r for r in rows if r[0] in ids]
        hits, planted = sum(r[2] == "hit" for r in sel), sum(r[1] == "Y" for r in sel)
        out[name] = (hits / planted, sum(r[2] == "false alarm" for r in sel) / len(ids), hits, planted)
    return out


common_5 = ("5. Every string the plan quotes as said in the session (sections 1–5; the Suggested Reachy Prompts are "
            "excluded) was checked against the labelled transcript and marked exact (word for word, ignoring case "
            "and punctuation), reworded (same meaning) or not there (not said, or meaning changed). Non-exact marks "
            "are provisional (cell comments) until checked by hand (needs_manual_check.md); proposed questions and "
            "suggestions not offered as the child's words are left out.")
common_1 = (f"1. Reproduction carried out on {DATE}, because the original per-feature records were not retained. "
            "Same 60 transcripts (T01–T60) and the same frozen truth sheets as the v3 run (SHA-256 verified); "
            "each transcript run once, in order T01→T60, with nothing else on the GPU.")
common_3 = ("3. 181 planted features: T01–T20 from features.json (story parts left out, use of 'because'/'so', "
            "emotion words); T21–T60 from the T21–T30 and T31–T60 truth sheets, scored by meaning (parts left out, "
            "feelings, reasons).")
methods = {
    "v1": [common_1,
           "2. Lesson planner v1 (lesson_planner.py, unchanged): qwen2.5:3b via Ollama, model defaults (the file sets "
           "no seed or temperature). Run on the labelled transcripts (\"Therapist.\" / \"Child.\" kept), as the "
           "original v1 run was. T11–T60 are new for v1 (originally only T01–T10 were run).",
           common_3,
           "4. v1 writes free text, which the v3 scorer (compare.py) cannot read, so each plan was scored by reading "
           "it against the same truth sheets with the same fixed rules: sections 1–4 only; a planted feature reported "
           "= hit, not reported = miss; a gap reported in a planted category that is not real = false alarm (one row "
           "each). Judgement calls carry a comment and are listed in needs_manual_check.md.",
           common_5,
           "Raw plans: evaluation/rerun_2026-10-21/v1/. Run log, hashes and model digests: run_log.md."],
    "v2": [common_1,
           "2. Lesson planner v2 (lesson_planner_v2.py, unchanged): qwen3:8b via Ollama, thinking off, temperature 0 "
           "for checks and 0.2 for writing, seed 0. Speaker labels were removed and re-added automatically by v2, "
           "exactly as in the v3 run.",
           common_3,
           "4. Scored automatically with the same scorer as v3 (compare.py's rules, unchanged), from each plan's "
           "saved analysis: sections 2–4; a planted feature reported = hit, not reported = miss; a gap reported in a "
           "planted category that is not real = false alarm (one row each).",
           common_5,
           "Raw plans and analysis JSON: evaluation/rerun_2026-10-21/v2/. Run log, hashes and model digests: "
           "run_log.md."],
}

if REVIEWED:
    checked_5 = ("5. Every string the plan quotes as said in the session (sections 1–5; the Suggested Reachy Prompts are "
                 "excluded) was checked against the labelled transcript and marked exact (word for word, ignoring case "
                 "and punctuation), reworded (same meaning) or not there (not said, said only by the therapist, or "
                 "meaning changed). Non-exact cases were checked by hand (cell comments; manual_review.tsv); proposed "
                 "questions, suggestions and verbatim dumps of the transcript are left out.")
    methods["v1"][3] = methods["v1"][3].replace(
        "Judgement calls carry a comment and are listed in needs_manual_check.md.",
        "Judgement calls were checked by hand (cell comments; manual_review.tsv): where a plan contradicts itself, a "
        "feature counts as credited if any section clearly credits it; a credited reason must be the child's own.")
    for v in ("v1", "v2"):
        methods[v][4] = checked_5

wb = openpyxl.Workbook()
wb.remove(wb.active)
for version in ("v1", "v2"):
    build_version_sheet(wb, version, methods[version], failed_runs(version))

# Comparison sheet.
ws = wb.create_sheet("NFR3 Version comparison")
style_from(ws["A1"], tpl["A1"])
ws["A1"] = "NFR3 · Lesson-plan accuracy (Test 6) — Version comparison"
ws.merge_cells("A1:G1")
ws.row_dimensions[1].height = tpl.row_dimensions[1].height
ws.sheet_properties.tabColor = copy.copy(tpl.sheet_properties.tabColor)
ws.sheet_view.showGridLines = tpl.sheet_view.showGridLines
heads = ["Transcript set", "v1 hit rate", "v1 false alarms per transcript", "v2 hit rate",
         "v2 false alarms per transcript", "v3 hit rate", "v3 false alarms per transcript"]
for col, h in zip("ABCDEFG", heads):
    style_from(ws[f"{col}3"], tpl["A16"])
    ws[f"{col}3"] = h
    ws.column_dimensions[col].width = 14 if col == "A" else 16
ws.row_dimensions[3].height = 30
v3 = v3_by_set()
for r, (name, _, _) in zip(range(4, 9), SETS):
    src = r + 8  # row of this set in the by-set table (G12:N16) of each version sheet
    values = [name, f"='NFR3 Version 1'!J{src}", f"='NFR3 Version 1'!L{src}", f"='NFR3 Version 2'!J{src}",
              f"='NFR3 Version 2'!L{src}", round(v3[name][0], 4), round(v3[name][1], 4)]
    for col, v in zip("ABCDEFG", values):
        cell = ws[f"{col}{r}"]
        cell.value = v
        style_from(cell, tpl["A17"] if col == "A" else tpl["C12"])
        cell.number_format = "General" if col == "A" else ("0.00" if col in "BDF" else "0.0")
notes = [
    "Notes",
    "v1 used the labelled transcripts; v2 and v3 used transcripts with the speaker labels removed and re-added "
    "automatically.",
    "T01–T10 were development transcripts for v2.",
    "v3's fixes were designed from v2's failures on T21–T60, so v3's figures on those sets are not held-out results.",
    f"v1 and v2: this re-run ({DATE}); the v1 and v2 cells are formulas on the version sheets. v3: computed from the "
    f"existing sheet '{TEMPLATE_SHEET}' in {TEMPLATE.name} (not re-run).",
    "v2 and v3 were scored by the same automatic scorer (compare.py); v1 writes free text and was scored by reading "
    "it, with the same truth sheets and rules.",
]
for i, text in enumerate(notes):
    r = 10 + i
    ws.merge_cells(f"A{r}:G{r}")
    style_from(ws[f"A{r}"], tpl["A11"] if i == 0 else tpl["A4"])
    ws[f"A{r}"] = text
    ws.row_dimensions[r].height = 14.25 if i == 0 else text_height(text, 105)

wb.save(OUT)
print("saved", OUT)
for name in SETS:
    print(name[0], "v3", f"{v3[name[0]][0]:.2f} ({v3[name[0]][2]}/{v3[name[0]][3]})", f"{v3[name[0]][1]:.1f}")
