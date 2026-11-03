"""
Crea datos de PRUEBA para la prueba de carga: pacientes y órdenes marcados para poder
identificarlos y eliminarlos después. Mide además el tiempo de creación de órdenes
(la operación de escritura más pesada del sistema).

    python tests/load/seed_test_orders.py --host http://SERVIDOR:8080 --user PRUEBAS --password "..." --orders 200

Marcas:
    - Pacientes: documento 99000000NN, apellido "CARGA LIS".
    - Órdenes:   o_note = "PRUEBA DE CARGA - ELIMINAR".
Los IDs creados quedan en tests/load/resultados/seed_creados.json.
"""
import argparse
import json
import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import requests

NOTE = "PRUEBA DE CARGA - ELIMINAR"
# Estudios comunes (ids de producción) agrupados para armar órdenes realistas
COMMON_STUDIES = [61, 61, 61, 59, 59, 13, 12, 1, 1, 16, 33, 19, 29, 89, 111, 102, 67, 69, 77, 260]
HEADQUARTERS = [1, 2, 3, 4]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--patients", type=int, default=20)
    ap.add_argument("--orders", type=int, default=200)
    ap.add_argument("--parallel", type=int, default=4)
    args = ap.parse_args()

    api = args.host.rstrip("/") + "/api"
    s = requests.Session()
    r = s.post(f"{api}/users/login", json={"usr_login": args.user, "usr_password": args.password}, timeout=30)
    r.raise_for_status()
    login = r.json()
    s.headers["Authorization"] = f"Bearer {login['access_token']}"
    usr_id = login["usr_id"]

    out_dir = Path(__file__).parent / "resultados"
    out_dir.mkdir(exist_ok=True)
    created = {"patients": [], "orders": []}

    # 1. Pacientes de prueba (se reutilizan si ya existen)
    patients = []
    for i in range(1, args.patients + 1):
        doc = f"99000000{i:02d}"
        r = s.get(f"{api}/patients/document/{doc}", timeout=30)
        if r.status_code == 200:
            patients.append(r.json()["pt_id"])
            continue
        r = s.post(f"{api}/patients/", json={
            "pt_Number_document": doc,
            "pt_firts_name": "PRUEBA",
            "pt_last_name": "CARGA LIS",
            "pt_second_last_name": f"{i:02d}",
            "pt_date_of_birth": f"{random.randint(1950, 2015)}-0{random.randint(1, 9)}-1{random.randint(0, 9)}",
            "pt_authorize_habeas_data": False,
            "pt_authorize_send_digital": False,
        }, timeout=30)
        if r.status_code >= 400:
            raise SystemExit(f"No se pudo crear el paciente {doc}: {r.status_code} {r.text[:300]}")
        pt = r.json()
        patients.append(pt["pt_id"])
        created["patients"].append({"pt_id": pt["pt_id"], "document": doc})
    print(f"Pacientes de prueba listos: {len(patients)} ({len(created['patients'])} nuevos)")

    # 2. Órdenes de prueba
    def create_order(n: int):
        studies = sorted(set(random.sample(COMMON_STUDIES, random.randint(2, 5))))
        body = {
            "o_number": "AUTO",
            "o_date": date.today().isoformat(),
            "o_his_id": random.choice(patients),
            "o_priority": 1 if random.random() < 0.15 else 0,
            "o_headquarter_id": random.choice(HEADQUARTERS),
            "o_AppUser_id": usr_id,
            "o_order_state": 1,
            "o_note": NOTE,
            "studies": studies,
        }
        t0 = time.perf_counter()
        r = s.post(f"{api}/orders/", json=body, timeout=120)
        elapsed = time.perf_counter() - t0
        return n, r.status_code, elapsed, (r.json() if r.status_code < 400 else r.text[:300])

    times, errors = [], []
    t_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = [pool.submit(create_order, n) for n in range(args.orders)]
        for f in as_completed(futures):
            n, code, elapsed, data = f.result()
            if code >= 400:
                errors.append((code, data))
                continue
            times.append(elapsed)
            created["orders"].append({k: data.get(k) for k in ("o_id", "o_number", "o_hq_consecutive", "o_headquarter_id")}
                                     if isinstance(data, dict) else data)
            if len(times) % 25 == 0:
                print(f"  {len(times)} órdenes creadas...")
    total = time.perf_counter() - t_start

    (out_dir / "seed_creados.json").write_text(json.dumps(created, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nÓrdenes creadas: {len(times)} / {args.orders}  en {total:.1f}s  ({args.parallel} en paralelo)")
    if times:
        times.sort()
        p95 = times[int(len(times) * 0.95) - 1]
        print(f"Tiempo por orden: mediana {statistics.median(times):.2f}s · p95 {p95:.2f}s · máx {times[-1]:.2f}s")
    if errors:
        print(f"ERRORES: {len(errors)}")
        for code, detail in errors[:10]:
            print(f"  HTTP {code}: {detail}")


if __name__ == "__main__":
    main()
