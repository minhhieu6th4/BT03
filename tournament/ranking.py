from typing import List, Dict, Any

class RankingManager:
    @staticmethod
    def calculate_standings(teams: list, matches: list) -> list:
        """
        Tính bảng xếp hạng từ danh sách đội và các trận đấu đã hoàn thành.
        Win: 3 points, Draw: 1 point, Loss: 0 point.
        """
        table = {}
        for t in teams:
            tid = t.get("id") if isinstance(t, dict) else t
            tname = t.get("name", str(t)) if isinstance(t, dict) else str(t)
            table[tid] = {
                "id": tid,
                "name": tname,
                "played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "points": 0,
                "score_for": 0,
                "score_against": 0
            }

        for m in matches:
            if m.get("status") != "COMPLETED":
                continue
            r_id = m["red_team"]["id"] if isinstance(m.get("red_team"), dict) else m.get("red_team")
            b_id = m["blue_team"]["id"] if isinstance(m.get("blue_team"), dict) else m.get("blue_team")
            if r_id not in table or b_id not in table:
                continue

            r_score = m.get("score", {}).get("red", 0)
            b_score = m.get("score", {}).get("blue", 0)

            table[r_id]["played"] += 1
            table[b_id]["played"] += 1
            table[r_id]["score_for"] += r_score
            table[r_id]["score_against"] += b_score
            table[b_id]["score_for"] += b_score
            table[b_id]["score_against"] += r_score

            winner = m.get("winner")
            if winner == "RED":
                table[r_id]["wins"] += 1
                table[r_id]["points"] += 3
                table[b_id]["losses"] += 1
            elif winner == "BLUE":
                table[b_id]["wins"] += 1
                table[b_id]["points"] += 3
                table[r_id]["losses"] += 1
            else:
                table[r_id]["draws"] += 1
                table[r_id]["points"] += 1
                table[b_id]["draws"] += 1
                table[b_id]["points"] += 1

        standings = list(table.values())
        standings.sort(key=lambda x: (x["points"], x["score_for"] - x["score_against"], x["wins"]), reverse=True)
        return standings
