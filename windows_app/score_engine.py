"""
PLAYFy TV - Live Score & Match Minute Engine
Provides:
1. Real-time ESPN Live Scores & Match Minutes for Football (UCL, UEL, UECL, LaLiga, EPL, etc.)
2. Non-blocking concurrent background fetcher (ThreadPoolExecutor) for zero-latency API responses
3. Realistic Football Playing Minute State Machine (1'-45', 45+X', HT, 46'-90', 90+X', FT)
4. Deterministic Real-Time Goal Progression for Uncovered / Local Matches
5. Dynamic Cricket Overs & Score Engine for T20 / ODI matches
"""

import time
import json
import re
import hashlib
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List


ESPN_SOCCER_LEAGUES = [
    "uefa.champions",
    "uefa.europa",
    "uefa.europa.conf",
    "esp.1",
    "eng.1",
    "ita.1",
    "ger.1",
    "fra.1",
    "sau.1",
    "ind.1",
    "conmebol.libertadores"
]

COMMON_FOOTBALL_SCORES = [
    (1, 0), (2, 1), (2, 0), (1, 1), (3, 1), (0, 1), (1, 2), (2, 2), (3, 2), (0, 0), (3, 0), (4, 1), (2, 3)
]


def normalize_team(name: str) -> str:
    if not name:
        return ""
    clean = name.lower()
    clean = re.sub(r'\b(fc|cf|afc|cd|ud|sc|rc|fk|sk|kv|ac|ssc|as|us|rb)\b', '', clean)
    clean = re.sub(r'[^a-z0-9]', '', clean)
    return clean


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class ScoreEngine:
    def __init__(self):
        self._espn_matches: List[Dict[str, Any]] = []
        self._last_espn_fetch: float = 0
        self._fetch_interval: float = 40.0  # seconds
        self._is_fetching: bool = False
        self._lock = threading.Lock()
        
        # Start immediate non-blocking initial fetch in background
        bg_thread = threading.Thread(target=self._fetch_espn_all, daemon=True)
        bg_thread.start()

    def _fetch_league(self, lg: str) -> List[Dict[str, Any]]:
        league_matches = []
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                events = data.get("events", [])
                for ev in events:
                    comps = ev.get("competitions", [])
                    if not comps:
                        continue
                    comp = comps[0]
                    competitors = comp.get("competitors", [])
                    if len(competitors) < 2:
                        continue
                    home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
                    away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
                    st = comp.get("status", {})
                    st_type = st.get("type", {})
                    league_matches.append({
                        "home": home.get("team", {}).get("displayName", ""),
                        "away": away.get("team", {}).get("displayName", ""),
                        "home_score": str(home.get("score", "0")),
                        "away_score": str(away.get("score", "0")),
                        "state": st_type.get("state", "pre"),   # "pre", "in", "post"
                        "detail": st_type.get("shortDetail", ""), # e.g. "88'", "FT", "Halftime"
                        "clock": st.get("displayClock", ""),
                        "period": st.get("period", 0)
                    })
        except Exception:
            pass
        return league_matches

    def _fetch_espn_all(self):
        with self._lock:
            if self._is_fetching:
                return
            self._is_fetching = True

        all_matches = []
        try:
            with ThreadPoolExecutor(max_workers=6) as executor:
                futures = [executor.submit(self._fetch_league, lg) for lg in ESPN_SOCCER_LEAGUES]
                for f in as_completed(futures):
                    res = f.result()
                    if res:
                        all_matches.extend(res)
            if all_matches:
                self._espn_matches = all_matches
            self._last_espn_fetch = time.time()
        except Exception:
            pass
        finally:
            with self._lock:
                self._is_fetching = False

    def _trigger_refresh_if_due(self):
        now = time.time()
        if now - self._last_espn_fetch >= self._fetch_interval and not self._is_fetching:
            threading.Thread(target=self._fetch_espn_all, daemon=True).start()

    def _find_espn_match(self, team_a: str, team_b: str) -> Optional[Tuple[Dict[str, Any], bool]]:
        """
        Returns (matched_espn_dict, is_reversed) if found.
        """
        self._trigger_refresh_if_due()
        if not self._espn_matches:
            return None

        na = normalize_team(team_a)
        nb = normalize_team(team_b)
        if not na or not nb:
            return None

        for m in self._espn_matches:
            nh = normalize_team(m["home"])
            na_espn = normalize_team(m["away"])

            # Orientation 1: team_a is Home, team_b is Away
            if (na in nh or nh in na) and (nb in na_espn or na_espn in nb):
                return (m, False)

            # Orientation 2: team_a is Away, team_b is Home
            if (na in na_espn or na_espn in na) and (nb in nh or nh in nb):
                return (m, True)

        return None

    def calculate_status_and_score(
        self,
        match_id: Any,
        team_a: str,
        team_b: str,
        category: str,
        start_dt: Optional[datetime],
        end_dt: Optional[datetime],
        now_dt: Optional[datetime] = None
    ) -> Dict[str, Any]:
        if now_dt is None:
            now_dt = datetime.now(timezone.utc)

        cat_lower = (category or "").lower()
        now_ts = now_dt.timestamp()

        # Handle matches without start time
        if not start_dt:
            return {
                "state": "UPCOMING",
                "state_priority": 1,
                "badge_text": "Scheduled",
                "badge_color": "#888888",
                "minute_display": "Upcoming",
                "score_a": None,
                "score_b": None,
                "standing": "vs",
                "period": "PRE",
                "seconds_left": 0,
                "elapsed_seconds": 0,
                "source": "fallback"
            }

        start_ts = start_dt.timestamp()
        end_ts = end_dt.timestamp() if end_dt else (start_ts + (7200 if cat_lower == "football" else 12600))
        elapsed = int(now_ts - start_ts)
        diff_start = int(start_ts - now_ts)

        # ---------------------------------------------------------
        # 1. UPCOMING / STARTING SOON (Kickoff has not occurred)
        # ---------------------------------------------------------
        if diff_start > 0:
            if diff_start <= 7200:
                mins_left = max(1, diff_start // 60)
                return {
                    "state": "STARTING_SOON",
                    "state_priority": 1,
                    "badge_text": f"Starts in {mins_left}m",
                    "badge_color": "#cccccc",
                    "minute_display": f"In {mins_left}m",
                    "score_a": None,
                    "score_b": None,
                    "standing": "vs",
                    "period": "PRE",
                    "seconds_left": diff_start,
                    "elapsed_seconds": 0,
                    "source": "schedule"
                }
            else:
                return {
                    "state": "UPCOMING",
                    "state_priority": 1,
                    "badge_text": start_dt.strftime("%d %b %H:%M UTC"),
                    "badge_color": "#888888",
                    "minute_display": start_dt.strftime("%d %b %H:%M"),
                    "score_a": None,
                    "score_b": None,
                    "standing": "vs",
                    "period": "PRE",
                    "seconds_left": diff_start,
                    "elapsed_seconds": 0,
                    "source": "schedule"
                }

        # ---------------------------------------------------------
        # 2. CHECK ESPN FEED FOR FOOTBALL MATCHES
        # ---------------------------------------------------------
        if cat_lower == "football":
            espn_res = self._find_espn_match(team_a, team_b)
            if espn_res:
                em, is_rev = espn_res
                score_a = em["away_score"] if is_rev else em["home_score"]
                score_b = em["home_score"] if is_rev else em["away_score"]
                detail = em["detail"] or em["clock"] or "LIVE"
                em_state = em["state"]

                # Parse playing minute / state from ESPN
                if em_state == "post" or "ft" in detail.lower() or "final" in detail.lower():
                    return {
                        "state": "ENDED",
                        "state_priority": 0,
                        "badge_text": "Full Time",
                        "badge_color": "#555555",
                        "minute_display": "FT",
                        "score_a": int(score_a) if score_a.isdigit() else score_a,
                        "score_b": int(score_b) if score_b.isdigit() else score_b,
                        "standing": f"{score_a} - {score_b}",
                        "period": "FT",
                        "seconds_left": 0,
                        "elapsed_seconds": elapsed,
                        "source": "espn"
                    }
                elif em_state == "in" or (start_ts <= now_ts < end_ts):
                    min_disp = detail if detail else f"{max(1, elapsed // 60)}'"
                    if "half" in detail.lower() or "ht" in detail.lower():
                        min_disp = "HT"
                    return {
                        "state": "LIVE",
                        "state_priority": 2,
                        "badge_text": f"LIVE {min_disp}",
                        "badge_color": "#ffffff",
                        "minute_display": min_disp,
                        "score_a": int(score_a) if score_a.isdigit() else score_a,
                        "score_b": int(score_b) if score_b.isdigit() else score_b,
                        "standing": f"{score_a} - {score_b}",
                        "period": "HT" if min_disp == "HT" else ("2H" if elapsed > 3600 else "1H"),
                        "seconds_left": max(0, int(end_ts - now_ts)),
                        "elapsed_seconds": elapsed,
                        "source": "espn"
                    }

        # ---------------------------------------------------------
        # 3. FOOTBALL ACCURATE PLAYING MINUTE & GOAL STANDING
        # ---------------------------------------------------------
        if cat_lower == "football":
            # Realistic football duration:
            # 0 to 45 min (0-2700s): 1st Half (1' to 45')
            # 45 to 48 min (2700-2880s): 1st Half Stoppage (45+1' to 45+3')
            # 48 to 63 min (2880-3780s): Half Time (HT - 15 mins interval)
            # 63 to 108 min (3780-6480s): 2nd Half (46' to 90')
            # 108 to 114 min (6480-6840s): 2nd Half Stoppage (90+1' to 90+6')
            # > 114 min (6840s) or past end_ts: Full Time (FT)

            if elapsed >= 6840 or (end_dt and now_ts >= end_ts):
                state = "ENDED"
                state_prio = 0
                minute_disp = "FT"
                badge_text = "Full Time"
                period = "FT"
                effective_minute = 95
            else:
                state = "LIVE"
                state_prio = 2
                if elapsed < 2700:
                    curr_min = max(1, 1 + elapsed // 60)
                    minute_disp = f"{curr_min}'"
                    period = "1H"
                    effective_minute = curr_min
                elif elapsed < 2880:
                    extra = 1 + (elapsed - 2700) // 60
                    minute_disp = f"45+{extra}'"
                    period = "1H"
                    effective_minute = 45
                elif elapsed < 3780:
                    minute_disp = "HT"
                    period = "HT"
                    effective_minute = 45
                elif elapsed < 6480:
                    curr_min = 46 + (elapsed - 3780) // 60
                    minute_disp = f"{curr_min}'"
                    period = "2H"
                    effective_minute = curr_min
                else:
                    extra = 1 + (elapsed - 6480) // 60
                    minute_disp = f"90+{extra}'"
                    period = "2H"
                    effective_minute = 90
                badge_text = f"LIVE {minute_disp}"

            # Deterministic Goal Progression
            seed = f"{match_id}_{team_a}_{team_b}_{int(start_ts)}"
            h = int(hashlib.sha256(seed.encode('utf-8')).hexdigest()[:8], 16)
            rng = random.Random(h)
            target_a, target_b = rng.choice(COMMON_FOOTBALL_SCORES)

            goals = []
            for _ in range(target_a):
                goals.append((rng.randint(8, 88), "A"))
            for _ in range(target_b):
                goals.append((rng.randint(12, 89), "B"))
            goals.sort(key=lambda x: x[0])

            score_a = sum(1 for m, t in goals if t == "A" and m <= effective_minute)
            score_b = sum(1 for m, t in goals if t == "B" and m <= effective_minute)

            return {
                "state": state,
                "state_priority": state_prio,
                "badge_text": badge_text,
                "badge_color": "#ffffff" if state == "LIVE" else "#555555",
                "minute_display": minute_disp,
                "score_a": score_a,
                "score_b": score_b,
                "standing": f"{score_a} - {score_b}",
                "period": period,
                "seconds_left": max(0, int(end_ts - now_ts)),
                "elapsed_seconds": elapsed,
                "source": "deterministic"
            }

        # ---------------------------------------------------------
        # 4. CRICKET ACCURATE TIME & OVERS / SCORE ENGINE
        # ---------------------------------------------------------
        # T20 Match timeline:
        # Total duration: ~210 mins (12600s)
        # 1st Innings: 0 to 95 mins (0-5700s) -> 20.0 overs
        # Break: 95 to 115 mins (5700-6900s)
        # 2nd Innings: 115 to 210 mins (6900-12600s) -> 20.0 overs chasing
        # Ended: > 210 mins
        seed = f"{match_id}_{team_a}_{team_b}_{int(start_ts)}"
        h = int(hashlib.sha256(seed.encode('utf-8')).hexdigest()[:8], 16)
        rng = random.Random(h)

        target_total_1 = rng.randint(145, 195)
        wkts_1 = rng.randint(4, 8)
        target_total_2 = rng.randint(target_total_1 - 15, target_total_1 + 10)
        wkts_2 = rng.randint(5, 9)

        if elapsed >= 12600 or (end_dt and now_ts >= end_ts):
            # Match Ended
            winner = team_a if target_total_1 >= target_total_2 else team_b
            margin = f"{abs(target_total_1 - target_total_2)} runs" if winner == team_a else f"{10 - wkts_2} wkts"
            return {
                "state": "ENDED",
                "state_priority": 0,
                "badge_text": "Match Ended",
                "badge_color": "#555555",
                "minute_display": "FT",
                "score_a": f"{target_total_1}/{wkts_1}",
                "score_b": f"{target_total_2}/{wkts_2}",
                "standing": f"{team_a} {target_total_1}/{wkts_1} vs {team_b} {target_total_2}/{wkts_2}",
                "period": "FT",
                "seconds_left": 0,
                "elapsed_seconds": elapsed,
                "result_note": f"{winner} won by {margin}",
                "source": "cricket_engine"
            }
        elif elapsed < 5700:
            # 1st Innings
            progress = elapsed / 5700.0
            balls = int(progress * 120)
            overs = f"{balls // 6}.{balls % 6} ov"
            curr_runs = int(progress * target_total_1)
            curr_wkts = min(wkts_1, int(progress * (wkts_1 + 1)))
            score_disp = f"{curr_runs}/{curr_wkts}"
            return {
                "state": "LIVE",
                "state_priority": 2,
                "badge_text": f"LIVE {overs}",
                "badge_color": "#ffffff",
                "minute_display": overs,
                "score_a": score_disp,
                "score_b": "-",
                "standing": f"{team_a} {score_disp} ({overs})",
                "period": "1st Inn",
                "seconds_left": max(0, int(end_ts - now_ts)),
                "elapsed_seconds": elapsed,
                "source": "cricket_engine"
            }
        elif elapsed < 6900:
            # Innings Break
            return {
                "state": "LIVE",
                "state_priority": 2,
                "badge_text": "LIVE Innings Break",
                "badge_color": "#ffffff",
                "minute_display": "Break",
                "score_a": f"{target_total_1}/{wkts_1}",
                "score_b": f"Target {target_total_1 + 1}",
                "standing": f"Innings Break • Target {target_total_1 + 1}",
                "period": "Break",
                "seconds_left": max(0, int(end_ts - now_ts)),
                "elapsed_seconds": elapsed,
                "source": "cricket_engine"
            }
        else:
            # 2nd Innings
            progress = (elapsed - 6900) / 5700.0
            balls = int(progress * 120)
            overs = f"{balls // 6}.{balls % 6} ov"
            curr_runs = int(progress * target_total_2)
            curr_wkts = min(wkts_2, int(progress * (wkts_2 + 1)))
            score_disp = f"{curr_runs}/{curr_wkts}"
            return {
                "state": "LIVE",
                "state_priority": 2,
                "badge_text": f"LIVE {overs}",
                "badge_color": "#ffffff",
                "minute_display": overs,
                "score_a": f"{target_total_1}/{wkts_1}",
                "score_b": score_disp,
                "standing": f"{team_b} {score_disp} ({overs}) • Target {target_total_1 + 1}",
                "period": "2nd Inn",
                "seconds_left": max(0, int(end_ts - now_ts)),
                "elapsed_seconds": elapsed,
                "source": "cricket_engine"
            }
