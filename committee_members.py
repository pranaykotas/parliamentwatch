"""Fetch and resolve committee membership data from sansad.in APIs."""

import json
import os
import re
from datetime import datetime, timezone

import requests

from config import BASE_URL, CURRENT_LOK_SABHA, DRSC_COMMITTEES, DATA_DIR

# API endpoints
COMMITTEE_MEMBERS_API = f"{BASE_URL}/api_ls/committee/committeeMembers"
LS_MEMBERS_API = f"{BASE_URL}/api_ls/member"
RS_MEMBERS_API = f"{BASE_URL}/api_rs/member/sitting-members"

# Cache file
COMMITTEE_MEMBERS_JSON = os.path.join(DATA_DIR, "committee_members.json")

# Request headers (mimic browser)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def _normalize_name(name):
    """Collapse whitespace and strip for consistent name matching."""
    if not name:
        return ""
    return re.sub(r"\s+", " ", name.strip())


def format_display_name(name):
    """
    Convert 'Last, Title First' to 'Title First Last' for human-readable display.

    Examples:
        'Singh, Shri Radha Mohan' -> 'Shri Radha Mohan Singh'
        'Dubey, Dr. Nishikant'    -> 'Dr. Nishikant Dubey'
        ', Smt. Shambhavi'        -> 'Smt. Shambhavi'
        'Gandhi, Shri Rahul'      -> 'Shri Rahul Gandhi'
    """
    if not name:
        return ""
    if "," not in name:
        return name.strip()
    last, _, first = name.partition(",")
    last = last.strip()
    first = first.strip()
    if not last:
        return first
    if not first:
        return last
    return f"{first} {last}"


def fetch_committee_roster(committee_key, lok_sabha=None):
    """
    Fetch the membership roster for a single committee.

    Returns list of dicts with keys: name, name_hindi, role, house.
    """
    if lok_sabha is None:
        lok_sabha = CURRENT_LOK_SABHA

    committee = DRSC_COMMITTEES[committee_key]
    params = {"committeeCode": committee["api_code"], "lsNo": lok_sabha}

    try:
        resp = requests.get(
            COMMITTEE_MEMBERS_API, params=params, headers=HEADERS, timeout=30
        )
        resp.raise_for_status()
        records = resp.json()
    except Exception as e:
        print(f"  Error fetching roster for {committee['name']}: {e}")
        return []

    members = []
    for rec in records:
        members.append(
            {
                "name": _normalize_name(rec.get("memberName", "")),
                "name_hindi": (rec.get("memberNameH") or "").strip(),
                "role": (rec.get("memberOrChairperson") or "").strip(),
                "house": (rec.get("memberHouse") or "").strip(),
            }
        )
    return members


def fetch_ls_directory(lok_sabha=None):
    """
    Fetch all sitting Lok Sabha members.

    Returns dict mapping normalized name -> member record.
    """
    if lok_sabha is None:
        lok_sabha = CURRENT_LOK_SABHA

    params = {
        "loksabha": lok_sabha,
        "size": 600,
        "page": 1,
        "sitting": 1,
        "locale": "en",
    }

    try:
        resp = requests.get(LS_MEMBERS_API, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  Error fetching LS member directory: {e}")
        return {}

    directory = {}
    for m in data.get("membersDtoList", []):
        name = _normalize_name(m.get("mpLastFirstName", ""))
        if name:
            directory[name] = {
                "mpsno": m.get("mpsno"),
                "party": (m.get("partyFname") or "").strip(),
                "party_short": (m.get("partySname") or "").strip(),
                "state": (m.get("stateName") or "").strip(),
                "constituency": (m.get("constName") or "").strip(),
                "photo_url": (m.get("imageUrl") or "").strip(),
            }
    return directory


def fetch_rs_directory():
    """
    Fetch all sitting Rajya Sabha members.

    Returns dict mapping normalized name -> member record.
    """
    params = {
        "page": 1,
        "size": 300,
        "mpFlag": 1,
        "locale": "en",
        "state": "",
        "party": "",
        "search": "",
    }

    try:
        resp = requests.get(RS_MEMBERS_API, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  Error fetching RS member directory: {e}")
        return {}

    directory = {}
    for m in data.get("records", []):
        name = _normalize_name(m.get("name", ""))
        if name:
            directory[name] = {
                "mpsno": m.get("mpsno"),
                "party": (m.get("party") or "").strip(),
                "party_short": (m.get("partyCode") or "").strip(),
                "state": (m.get("state") or "").strip(),
                "constituency": "",  # RS members don't have constituencies
                "photo_url": (m.get("imageUrl") or "").strip(),
            }
    return directory


def _build_profile_url(mpsno, house):
    """Construct the sansad.in biography URL for a member."""
    if not mpsno:
        return ""
    if "lok" in house.lower():
        return f"{BASE_URL}/ls/members/biographyM/{mpsno}?from=members"
    else:
        return f"{BASE_URL}/rs/members/biographyM/{mpsno}"


def _match_member(name, house, ls_dir, rs_dir):
    """
    Try to match a committee member name against LS/RS directories.

    Returns the matching directory entry or None.
    """
    is_ls = "lok" in house.lower()
    primary = ls_dir if is_ls else rs_dir
    fallback = rs_dir if is_ls else ls_dir

    # Exact match (after normalization)
    if name in primary:
        return primary[name]

    # Case-insensitive match
    name_lower = name.lower()
    for dir_name, entry in primary.items():
        if dir_name.lower() == name_lower:
            return entry

    # Surname-only match: extract text before the first comma
    surname = name.split(",")[0].strip().lower() if "," in name else ""
    if surname:
        candidates = [
            (n, e) for n, e in primary.items() if n.lower().startswith(surname + ",")
        ]
        if len(candidates) == 1:
            return candidates[0][1]

    # Try the other house as last resort
    if name in fallback:
        return fallback[name]
    for dir_name, entry in fallback.items():
        if dir_name.lower() == name_lower:
            return entry

    return None


def resolve_committee_members(roster, ls_dir, rs_dir):
    """
    Enrich committee roster entries with profile data from member directories.

    Returns list of fully resolved member dicts.
    """
    resolved = []
    for member in roster:
        match = _match_member(member["name"], member["house"], ls_dir, rs_dir)

        entry = {
            "name": member["name"],
            "display_name": format_display_name(member["name"]),
            "name_hindi": member.get("name_hindi", ""),
            "role": member["role"],
            "house": member["house"],
        }

        if match:
            entry["mpsno"] = match["mpsno"]
            entry["party"] = match["party"]
            entry["party_short"] = match["party_short"]
            entry["state"] = match["state"]
            entry["constituency"] = match["constituency"]
            entry["photo_url"] = match["photo_url"]
            entry["profile_url"] = _build_profile_url(match["mpsno"], member["house"])
        else:
            entry["mpsno"] = None
            entry["party"] = ""
            entry["party_short"] = ""
            entry["state"] = ""
            entry["constituency"] = ""
            entry["photo_url"] = ""
            entry["profile_url"] = ""

        resolved.append(entry)

    # Sort: Chairperson first, then alphabetically by name
    resolved.sort(key=lambda m: (0 if "chair" in m["role"].lower() else 1, m["name"]))
    return resolved


def fetch_all_committee_members(lok_sabha=None):
    """
    Fetch and resolve members for all 16 DRSCs.

    Makes 18 API calls total (16 committees + 1 LS dir + 1 RS dir).
    Saves result to COMMITTEE_MEMBERS_JSON.
    """
    if lok_sabha is None:
        lok_sabha = CURRENT_LOK_SABHA

    print("Fetching MP directories...")
    print("  Lok Sabha members...")
    ls_dir = fetch_ls_directory(lok_sabha)
    print(f"  Found {len(ls_dir)} LS members")

    print("  Rajya Sabha members...")
    rs_dir = fetch_rs_directory()
    print(f"  Found {len(rs_dir)} RS members")

    committees = {}
    unmatched_total = 0

    for key in sorted(DRSC_COMMITTEES.keys()):
        committee = DRSC_COMMITTEES[key]
        print(f"  Fetching roster for {committee['name']}...")

        roster = fetch_committee_roster(key, lok_sabha)
        if not roster:
            print(f"    No members found")
            continue

        resolved = resolve_committee_members(roster, ls_dir, rs_dir)

        # Count unmatched
        unmatched = [m for m in resolved if m["mpsno"] is None]
        if unmatched:
            unmatched_total += len(unmatched)
            for m in unmatched:
                print(f"    Could not match: {m['name']} ({m['house']})")

        committees[key] = {
            "committee_name": committee["name"],
            "member_count": len(resolved),
            "members": resolved,
        }

        print(
            f"    {len(resolved)} members ({len(resolved) - len(unmatched)} matched)"
        )

    result = {
        "metadata": {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "lok_sabha": lok_sabha,
            "total_committees": len(committees),
            "ls_directory_size": len(ls_dir),
            "rs_directory_size": len(rs_dir),
            "unmatched_members": unmatched_total,
        },
        "committees": committees,
    }

    save_committee_members(result)
    total_members = sum(c["member_count"] for c in committees.values())
    print(f"\nDone. {total_members} members across {len(committees)} committees.")
    if unmatched_total:
        print(f"  {unmatched_total} member(s) could not be matched to a profile.")
    print(f"  Saved to {COMMITTEE_MEMBERS_JSON}")

    return result


def load_committee_members():
    """Load cached committee members from JSON file."""
    if os.path.exists(COMMITTEE_MEMBERS_JSON):
        with open(COMMITTEE_MEMBERS_JSON, "r") as f:
            return json.load(f)
    return {}


def save_committee_members(data):
    """Save committee members to JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(COMMITTEE_MEMBERS_JSON, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
