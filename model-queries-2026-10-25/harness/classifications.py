"""Validate classification records before reuse or analysis."""
import json


class ClassificationError(ValueError):
    pass


def load_classifications(path, items):
    """Require one well-formed record for each loaded item, with no other ids."""
    expected = {it["query_id"] for it in items}
    prefix = f"classification completeness error in {path}"
    if len(expected) != len(items):
        raise ClassificationError(f"{prefix}: duplicate loaded item ids")
    records = {}
    try:
        with path.open(encoding="utf-8") as fh:
            for number, line in enumerate(fh, 1):
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict) or not isinstance(record.get("query_id"), str):
                        raise ValueError("expected an object with a string query_id")
                    calls = record.get("regexp_like_calls")
                    if not isinstance(calls, list) or not isinstance(record.get("other_regex"), dict):
                        raise ValueError("expected regexp_like_calls list and other_regex object")
                    for call in calls:
                        if (not isinstance(call, dict)
                                or not isinstance(call.get("pattern_is_literal"), bool)
                                or not isinstance(call.get("all_literal"), bool)):
                            raise ValueError("invalid regexp_like call")
                        if call["pattern_is_literal"] and (
                                not isinstance(call.get("pattern"), str)
                                or not isinstance(call.get("classification"), dict)):
                            raise ValueError("literal pattern requires a string and classification object")
                except ValueError as error:
                    raise ClassificationError(f"{prefix}: malformed line {number}: {error}") from error
                item_id = record["query_id"]
                if item_id in records:
                    raise ClassificationError(f"{prefix}: duplicate id {item_id} at line {number}")
                records[item_id] = record
    except (OSError, UnicodeError) as error:
        raise ClassificationError(f"{prefix}: {error}") from error
    missing, extra = expected - records.keys(), records.keys() - expected
    if missing or extra:
        raise ClassificationError(
            f"{prefix}: expected exactly {len(expected)} ids; found {len(records)}; "
            f"missing {len(missing)} {sorted(missing)[:5]}; unexpected {len(extra)} {sorted(extra)[:5]}")
    return records
