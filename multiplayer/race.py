"""race.py — "I'm faster than you" LAN race rules (no GUI, no sockets).

Format: every connected player races the full single-player roster
solo on their own machine.  Winner = most levels solved when the
15-minute timer expires.  Ties break on fewest restarts, then fewest
total steps.  Score mirrors that order so the panel can show one number
plus the breakdown.
"""
from __future__ import annotations

from dataclasses import dataclass

RACE_DURATION_S = 15 * 60  # 15 minutes
SCORE_PER_LEVEL = 10000
SCORE_PER_RESTART = -100
SCORE_PER_STEP = -1


def score_for(levels: int, restarts: int, steps: int) -> int:
    return (levels * SCORE_PER_LEVEL
            + restarts * SCORE_PER_RESTART
            + steps * SCORE_PER_STEP)


@dataclass
class RacerStats:
    name: str
    levels: int = 0
    moves: int = 0
    restarts: int = 0

    @property
    def score(self) -> int:
        return score_for(self.levels, self.restarts, self.moves)


@dataclass
class Standing:
    rank: int
    name: str
    levels: int
    moves: int
    restarts: int
    score: int


def compute_standings(stats: list[RacerStats] | dict[str, RacerStats]) -> list[Standing]:
    """Rank racers: most levels, then fewest restarts, then fewest steps."""
    racers = list(stats.values()) if isinstance(stats, dict) else list(stats)
    racers.sort(key=lambda r: (-r.levels, r.restarts, r.moves, r.name))
    out: list[Standing] = []
    for i, r in enumerate(racers):
        out.append(Standing(rank=i + 1, name=r.name, levels=r.levels,
                            moves=r.moves, restarts=r.restarts,
                            score=r.score))
    return out


def fmt_time(secs: float) -> str:
    secs = max(0, int(secs))
    return "%02d:%02d" % (secs // 60, secs % 60)


def board_lines(standings: list[Standing]) -> list[str]:
    lines = []
    for s in standings:
        lines.append(
            "#%d %s — Lv %d · %d steps · %d restarts · %d pts"
            % (s.rank, s.name, s.levels, s.moves, s.restarts, s.score))
    return lines
