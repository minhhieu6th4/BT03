import asyncio
import time
import statistics
import json
import httpx
from typing import List, Dict, Any

AZURE_BASE_URL = "http://40.83.92.33:5000"
PASSWORD = "PerfPassword123!"

class PerformanceHarness:
    def __init__(self, base_url: str = AZURE_BASE_URL):
        self.base_url = base_url
        self.host_token = None
        self.user_tokens: List[Dict[str, Any]] = []

    async def setup_accounts(self, num_users: int = 20):
        print(f"\n[SETUP] Khoi tao {num_users} tai khoan kiem thu tren Azure ({self.base_url})...")
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0) as client:
            # 1. Host Account
            host_username = "perf_host_master"
            host_email = "perf_host_master@example.com"
            reg_host = await client.post("/api/auth/register", json={
                "username": host_username,
                "email": host_email,
                "password": PASSWORD
            })
            login_host = await client.post("/api/auth/login", data={
                "username": host_username,
                "password": PASSWORD
            })
            if login_host.status_code == 200:
                self.host_token = login_host.json()["access_token"]
                print(f"  -> Host account: {host_username} OK (Token: {self.host_token[:15]}...)")
            else:
                raise RuntimeError(f"Khong the dang nhap Host account: {login_host.status_code} - {login_host.text}")

            # 2. 20 Test Users
            self.user_tokens = []
            for i in range(1, num_users + 1):
                u_name = f"perf_user_{i:02d}"
                u_email = f"perf_user_{i:02d}@example.com"
                await client.post("/api/auth/register", json={
                    "username": u_name,
                    "email": u_email,
                    "password": PASSWORD
                })
                login_res = await client.post("/api/auth/login", data={
                    "username": u_name,
                    "password": PASSWORD
                })
                if login_res.status_code == 200:
                    token = login_res.json()["access_token"]
                    self.user_tokens.append({
                        "id": i,
                        "username": u_name,
                        "token": token
                    })
                else:
                    print(f"  [CANH BAO] Khong the dang nhap {u_name}: {login_res.status_code}")

            print(f"  -> Da chuan bi xong {len(self.user_tokens)} tai khoan test co JWT token hop le.")

    async def run_stage_single_room(self, num_users: int, stage_name: str) -> Dict[str, Any]:
        """
        Kich ban A (Contention/Race Condition):
        Host tao 1 phong. num_users nguoi dong thoi gui POST /api/rooms/{id}/join vao cung 1 phong do.
        """
        print(f"\n=======================================================")
        print(f"  CHAY {stage_name}: {num_users} USERS DONG THOI -> 1 PHONG DUY NHAT")
        print(f"=======================================================")

        async with httpx.AsyncClient(base_url=self.base_url, timeout=20.0) as client:
            # 1. Host tao phong
            host_headers = {"Authorization": f"Bearer {self.host_token}"}
            create_res = await client.post("/api/rooms/", json={
                "name": f"Perf_Contention_{num_users}U",
                "board_size": 9
            }, headers=host_headers)
            if create_res.status_code != 200:
                raise RuntimeError(f"Host khong tao duoc phong: {create_res.status_code} - {create_res.text}")

            room_id = create_res.json()["id"]
            print(f"  [ROOM CREATED] Room ID: {room_id} (Host: perf_host_master)")

            # 2. Chuan bi barrier release de dong thoi ban request
            start_event = asyncio.Event()
            results = []

            async def worker(user_info):
                headers = {"Authorization": f"Bearer {user_info['token']}"}
                await start_event.wait() # Doi tin hieu xuat phat dong thoi
                t0 = time.perf_counter()
                try:
                    res = await client.post(f"/api/rooms/{room_id}/join", headers=headers)
                    t1 = time.perf_counter()
                    latency_ms = (t1 - t0) * 1000
                    return {
                        "username": user_info["username"],
                        "status_code": res.status_code,
                        "latency_ms": latency_ms,
                        "body": res.text[:200],
                        "error": None
                    }
                except Exception as ex:
                    t1 = time.perf_counter()
                    latency_ms = (t1 - t0) * 1000
                    return {
                        "username": user_info["username"],
                        "status_code": 0,
                        "latency_ms": latency_ms,
                        "body": "",
                        "error": str(ex)
                    }

            tasks = [asyncio.create_task(worker(self.user_tokens[i])) for i in range(num_users)]
            
            # Cho cac tasks san sang roi kich hoat dong loat
            await asyncio.sleep(0.5)
            burst_start_time = time.perf_counter()
            start_event.set()
            results = await asyncio.gather(*tasks)
            burst_end_time = time.perf_counter()

            total_duration = burst_end_time - burst_start_time

            # 3. Kiem tra tinh nhat quan cua Room tren Azure sau khi burst
            check_res = await client.get(f"/api/rooms/{room_id}", headers=host_headers)
            room_detail = check_res.json() if check_res.status_code == 200 else {}

            # 4. Cleanup phong test
            await client.post(f"/api/rooms/{room_id}/cancel", headers=host_headers)

            stats = self._calc_stats(results, total_duration)
            stats["room_status"] = room_detail.get("status")
            stats["player1_id"] = room_detail.get("player1_id")
            stats["player2_id"] = room_detail.get("player2_id")
            stats["stage_name"] = stage_name
            stats["num_users"] = num_users

            self._print_stage_report(stats)
            return stats

    async def run_stage_multi_rooms(self, num_users: int, stage_name: str) -> Dict[str, Any]:
        """
        Kich ban B (Distributed Throughput):
        Host tao num_users phong rieng biet. num_users nguoi dong thoi gui POST /api/rooms/{id}/join vao phong cua minh.
        """
        print(f"\n=======================================================")
        print(f"  CHAY {stage_name}: {num_users} USERS DONG THOI -> {num_users} PHONG RIENG BIET")
        print(f"=======================================================")

        async with httpx.AsyncClient(base_url=self.base_url, timeout=20.0) as client:
            host_headers = {"Authorization": f"Bearer {self.host_token}"}
            created_rooms = []
            for i in range(num_users):
                c_res = await client.post("/api/rooms/", json={
                    "name": f"Perf_Multi_{num_users}U_{i+1}",
                    "board_size": 9
                }, headers=host_headers)
                if c_res.status_code == 200:
                    created_rooms.append(c_res.json()["id"])
                else:
                    print(f"  [LOI TAO PHONG {i+1}]: {c_res.status_code}")

            print(f"  [ROOMS CREATED] Da tao {len(created_rooms)} phong doc lap.")

            start_event = asyncio.Event()

            async def worker(idx, room_id, user_info):
                headers = {"Authorization": f"Bearer {user_info['token']}"}
                await start_event.wait()
                t0 = time.perf_counter()
                try:
                    res = await client.post(f"/api/rooms/{room_id}/join", headers=headers)
                    t1 = time.perf_counter()
                    latency_ms = (t1 - t0) * 1000
                    return {
                        "username": user_info["username"],
                        "status_code": res.status_code,
                        "latency_ms": latency_ms,
                        "body": res.text[:200],
                        "error": None
                    }
                except Exception as ex:
                    t1 = time.perf_counter()
                    latency_ms = (t1 - t0) * 1000
                    return {
                        "username": user_info["username"],
                        "status_code": 0,
                        "latency_ms": latency_ms,
                        "body": "",
                        "error": str(ex)
                    }

            tasks = [asyncio.create_task(worker(i, created_rooms[i], self.user_tokens[i])) for i in range(len(created_rooms))]

            await asyncio.sleep(0.5)
            burst_start_time = time.perf_counter()
            start_event.set()
            results = await asyncio.gather(*tasks)
            burst_end_time = time.perf_counter()
            total_duration = burst_end_time - burst_start_time

            # Cleanup
            for r_id in created_rooms:
                try:
                    await client.post(f"/api/rooms/{r_id}/cancel", headers=host_headers)
                except Exception:
                    pass

            stats = self._calc_stats(results, total_duration)
            stats["stage_name"] = stage_name
            stats["num_users"] = num_users
            self._print_stage_report(stats)
            return stats

    def _calc_stats(self, results: List[Dict[str, Any]], total_duration: float) -> Dict[str, Any]:
        latencies = [r["latency_ms"] for r in results]
        latencies.sort()
        status_counts = {}
        for r in results:
            code = r["status_code"]
            status_counts[code] = status_counts.get(code, 0) + 1

        success_count = status_counts.get(200, 0)
        total_requests = len(results)
        fail_count = total_requests - success_count
        rps = total_requests / total_duration if total_duration > 0 else 0

        p50 = statistics.median(latencies) if latencies else 0
        p90 = latencies[int(len(latencies) * 0.90)] if latencies else 0
        p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
        p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0
        avg_lat = statistics.mean(latencies) if latencies else 0
        min_lat = min(latencies) if latencies else 0
        max_lat = max(latencies) if latencies else 0

        return {
            "total_requests": total_requests,
            "success_count": success_count,
            "fail_count": fail_count,
            "status_counts": status_counts,
            "duration_sec": total_duration,
            "rps": rps,
            "min_ms": min_lat,
            "max_ms": max_lat,
            "avg_ms": avg_lat,
            "p50_ms": p50,
            "p90_ms": p90,
            "p95_ms": p95,
            "p99_ms": p99,
            "details": results
        }

    def _print_stage_report(self, s: Dict[str, Any]):
        print(f"  [KET QUA] Tong so requests: {s['total_requests']}")
        print(f"    - Thanh cong (HTTP 200): {s['success_count']} ({s['success_count']/s['total_requests']*100:.1f}%)")
        print(f"    - That bai (Non-200/Err): {s['fail_count']}")
        print(f"    - Phan bo Status Code: {s['status_counts']}")
        print(f"    - Throughput (RPS): {s['rps']:.2f} req/s (Tong thoi gian: {s['duration_sec']:.3f}s)")
        print(f"    - Do tre (Latency):")
        print(f"        Min: {s['min_ms']:.1f} ms | Avg: {s['avg_ms']:.1f} ms | Max: {s['max_ms']:.1f} ms")
        print(f"        p50 (Median): {s['p50_ms']:.1f} ms")
        print(f"        p90: {s['p90_ms']:.1f} ms | p95: {s['p95_ms']:.1f} ms | p99: {s['p99_ms']:.1f} ms")
        if "room_status" in s:
            print(f"    - Tinh trang phong sau burst: Status={s['room_status']}, P1={s['player1_id']}, P2={s['player2_id']}")

async def main():
    harness = PerformanceHarness(AZURE_BASE_URL)
    await harness.setup_accounts(num_users=20)

    all_reports = []

    # ========================================================
    # KICH BAN 1: Contention Test (Cung tranh 1 phong)
    # ========================================================
    print("\n\n###############################################################")
    print("### KICH BAN 1: CONTENTION TEST (CUNG TRANH 1 PHONG DUY NHAT)")
    print("###############################################################")

    r1 = await harness.run_stage_single_room(1, "Stage 1: Smoke Baseline (1 User)")
    all_reports.append(r1)
    await asyncio.sleep(2)

    r2 = await harness.run_stage_single_room(5, "Stage 2: Light Concurrency (5 Users)")
    all_reports.append(r2)
    await asyncio.sleep(2)

    r3 = await harness.run_stage_single_room(10, "Stage 3: Medium Concurrency (10 Users)")
    all_reports.append(r3)
    await asyncio.sleep(2)

    r4 = await harness.run_stage_single_room(20, "Stage 4: Peak Target Concurrency (20 Users)")
    all_reports.append(r4)
    await asyncio.sleep(3)

    # ========================================================
    # KICH BAN 2: Distributed Throughput (Moi user 1 phong)
    # ========================================================
    print("\n\n###############################################################")
    print("### KICH BAN 2: DISTRIBUTED THROUGHPUT TEST (20 PHONG SONG SONG)")
    print("###############################################################")

    r5 = await harness.run_stage_multi_rooms(1, "Multi-Room Stage 1 (1 User)")
    all_reports.append(r5)
    await asyncio.sleep(2)

    r6 = await harness.run_stage_multi_rooms(5, "Multi-Room Stage 2 (5 Users)")
    all_reports.append(r6)
    await asyncio.sleep(2)

    r7 = await harness.run_stage_multi_rooms(10, "Multi-Room Stage 3 (10 Users)")
    all_reports.append(r7)
    await asyncio.sleep(2)

    r8 = await harness.run_stage_multi_rooms(20, "Multi-Room Stage 4 (20 Users)")
    all_reports.append(r8)

    # Ghi file ket qua JSON de bao cao chi tiet
    with open("perf_results.json", "w", encoding="utf-8") as f:
        json.dump(all_reports, f, indent=2, ensure_ascii=False)
    print("\n[DONE] Da hoan tat toan bo cac dot kiem thu. Du lieu luu tai perf_results.json")

if __name__ == "__main__":
    asyncio.run(main())
