"""Find regexp_like calls and other regex constructs in SQL text.

The scanner skips string literals ('...', with '' escapes; E'...' with backslash escapes),
quoted identifiers ("...") and comments (-- and /* */). For each regexp_like( ... ) call it
splits the arguments at top-level commas and reports, for each argument, whether it is a
literal (string, number, NULL, TRUE, FALSE) and the string value of string literals.
"""
import re

OTHER_FUNCS = ["regexp_match", "regexp_replace", "regexp_count", "regexp_instr", "regexp_substr"]
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
NUMBER = re.compile(r"[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?")


def _skip_string(sql, i):
    """sql[i] is a quote start ('), possibly after an E prefix handled by caller. Return end+1."""
    j = i + 1
    while j < len(sql):
        if sql[j] == "'":
            if j + 1 < len(sql) and sql[j + 1] == "'":
                j += 2
                continue
            return j + 1
        j += 1
    return len(sql)


def _skip_estring(sql, i):
    j = i + 1
    while j < len(sql):
        if sql[j] == "\\":
            j += 2
            continue
        if sql[j] == "'":
            if j + 1 < len(sql) and sql[j + 1] == "'":
                j += 2
                continue
            return j + 1
        j += 1
    return len(sql)


def tokens(sql):
    """Yield (kind, start, end) with kind in str, estr, qident, ident, punct, other."""
    i, n = 0, len(sql)
    while i < n:
        c = sql[i]
        if sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j < 0 else j + 1
            continue
        if sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "eE" and i + 1 < n and sql[i + 1] == "'" and (i == 0 or not (sql[i - 1].isalnum() or sql[i - 1] == "_")):
            j = _skip_estring(sql, i + 1)
            yield ("estr", i, j)
            i = j
            continue
        if c == "'":
            j = _skip_string(sql, i)
            yield ("str", i, j)
            i = j
            continue
        if c == '"':
            j = sql.find('"', i + 1)
            j = n if j < 0 else j + 1
            yield ("qident", i, j)
            i = j
            continue
        m = IDENT.match(sql, i)
        if m:
            yield ("ident", i, m.end())
            i = m.end()
            continue
        if c.isspace():
            i += 1
            continue
        yield ("punct", i, i + 1)
        i += 1


def _str_value(sql, kind, s, e):
    body = sql[s + (2 if kind == "estr" else 1):e - 1]
    if kind == "str":
        return body.replace("''", "'")
    out, k = [], 0
    while k < len(body):
        if body[k] == "\\" and k + 1 < len(body):
            out.append({"n": "\n", "t": "\t", "r": "\r"}.get(body[k + 1], body[k + 1]))
            k += 2
        elif body[k] == "'" and k + 1 < len(body) and body[k + 1] == "'":
            out.append("'")
            k += 2
        else:
            out.append(body[k])
            k += 1
    return "".join(out)


def _arg_info(sql, toks):
    text = sql[toks[0][1]:toks[-1][2]] if toks else ""
    info = {"text": text, "literal": False, "string": None}
    if len(toks) == 1 and toks[0][0] in ("str", "estr"):
        info.update(literal=True, string=_str_value(sql, *toks[0]))
    elif len(toks) == 1 and toks[0][0] == "ident" and text.upper() in ("NULL", "TRUE", "FALSE"):
        info["literal"] = True
    elif NUMBER.fullmatch(text.replace(" ", "")):
        info["literal"] = True
    return info


def scan(sql):
    toks = list(tokens(sql))
    calls, other = [], {f: 0 for f in OTHER_FUNCS}
    other.update({"~ operators": 0, "SIMILAR TO": 0})
    for k, (kind, s, e) in enumerate(toks):
        word = sql[s:e].lower() if kind == "ident" else None
        if kind == "punct" and sql[s] == "~":
            prev = toks[k - 1] if k else None
            if not (prev and prev[0] == "punct" and sql[prev[1]] == "~" and prev[2] == s):
                other["~ operators"] += 1
        if word == "similar" and k + 1 < len(toks) and sql[toks[k + 1][1]:toks[k + 1][2]].lower() == "to":
            other["SIMILAR TO"] += 1
        if word in OTHER_FUNCS and k + 1 < len(toks) and sql[toks[k + 1][1]] == "(":
            other[word] += 1
        if word == "regexp_like" and k + 1 < len(toks) and toks[k + 1][0] == "punct" and sql[toks[k + 1][1]] == "(":
            depth, args, cur, j = 0, [], [], k + 1
            while j < len(toks):
                t = toks[j]
                ch = sql[t[1]] if t[0] == "punct" else None
                if ch == "(":
                    depth += 1
                    if depth == 1:
                        j += 1
                        continue
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        args.append(cur)
                        break
                elif ch == "," and depth == 1:
                    args.append(cur)
                    cur = []
                    j += 1
                    continue
                cur.append(t)
                j += 1
            infos = [_arg_info(sql, a) for a in args]
            calls.append({
                "nargs": len(infos),
                "args": [i["text"] for i in infos],
                "all_literal": bool(infos) and all(i["literal"] for i in infos),
                "pattern": infos[1]["string"] if len(infos) > 1 else None,
                "flags": infos[2]["string"] if len(infos) > 2 else None,
                "pattern_is_literal": len(infos) > 1 and infos[1]["string"] is not None,
            })
    return {"regexp_like_calls": calls, "other_regex": other}


if __name__ == "__main__":
    import json, sys
    print(json.dumps(scan(sys.stdin.read()), indent=1))
