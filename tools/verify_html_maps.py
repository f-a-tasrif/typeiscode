
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maps_data import MAPS

D = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}


def rules(blocks):
    at = {(r, c): t for r, c, t in blocks}
    R = {"Path": True, "Door": False, "Trap": True}
    for r, c, t in blocks:
        if t.endswith("."):
            g = lambda x, _r=r, _c=c: at.get((_r, _c + x))
            if g(2) == "=":
                v = g(3)
                n = False
                if v == "NOT":
                    n = True
                    v = g(4)
                if v == "True" or v == "False":
                    R[t[:-1]] = (v == "True") != n
    return R


def sim(m):
    p = list(m["start"])
    b = [list(x) for x in m["tokens"]]
    F = [{"p": list(p), "b": [list(x) for x in b], "bad": 0, "dead": 0}]
    for ch in "".join(s[0] for s in m["solution"]):
        R = rules(b)
        dr, dc = D[ch]

        def bl(r, c):
            k = m["rows"][r][c]
            return k == "#" or (k == "T" and R["Path"]) or (k == "D" and not R["Door"])

        def bi(r, c):
            for k, x in enumerate(b):
                if x[0] == r and x[1] == c:
                    return k
            return -1

        nr, nc = p[0] + dr, p[1] + dc
        bad = 0
        if bl(nr, nc):
            bad = 1
        else:
            i = bi(nr, nc)
            if i >= 0:
                r2, c2 = nr + dr, nc + dc
                if bl(r2, c2) or bi(r2, c2) >= 0:
                    bad = 1
                else:
                    b[i][0] = r2
                    b[i][1] = c2
        if not bad:
            p = [nr, nc]
        dead = 1 if (m["rows"][p[0]][p[1]] == "X" and rules(b)["Trap"]) else 0
        F.append({"p": list(p), "b": [list(x) for x in b], "bad": bad, "dead": dead})
    return F


def main():
    ok = True
    for mi, m in enumerate(MAPS):
        F = sim(m)
        last = F[-1]
        solved = m["rows"][last["p"][0]][last["p"][1]] == "F"
        rej = [i for i, f in enumerate(F) if f["bad"]]
        deaths = [i for i, f in enumerate(F) if f["dead"]]
        print(f"Map {mi + 1} ({m['name']}): "
              f"solved={solved} rejected={len(rej)} deaths={len(deaths)}")
        if rej or deaths or not solved:
            ok = False

            ends = []
            a = 0
            for moves, _note in m["solution"]:
                a += len(moves)
                ends.append(a)
            for i in rej:
                ph = next(j for j, e in enumerate(ends) if i <= e)
                print(f"  rejected move {i} in phase {ph}: "
                      f"{m['solution'][ph][1]}")
            for i in deaths:
                ph = next(j for j, e in enumerate(ends) if i <= e)
                print(f"  death at move {i} in phase {ph}: "
                      f"{m['solution'][ph][1]}")
            if not solved:
                print(f"  ends on {m['rows'][last['p'][0]][last['p'][1]]!r} "
                      f"at {last['p']}, not on F")
    if not ok:
        sys.exit(1)
    print("ALL MAPS VERIFIED")


if __name__ == "__main__":
    main()
