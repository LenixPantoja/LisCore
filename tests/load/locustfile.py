"""
Prueba de carga del LIS (CoreLab) con Locust.

Simula usuarios de laboratorio usando el sistema al mismo tiempo. Todas las
operaciones son de SOLO LECTURA: no crean órdenes, no cargan ni validan
resultados (la única escritura es la traza de "Inicio de sesión" de cada login).

Uso rápido (ver README.md en esta carpeta):
    set LOAD_USERS=usuario1:clave1,usuario2:clave2
    locust -f tests/load/locustfile.py --host http://SERVIDOR:8000

Variables de entorno:
    LOAD_USERS          Lista "login:clave,login:clave". Se reparte entre los usuarios
                        simulados (se recomienda 1 usuario real por cada pocos simulados).
    LOAD_USER / LOAD_PASSWORD  Alternativa con un solo usuario.
    LOAD_DAYS           Días hacia atrás para el Plan de Trabajo (por defecto 30).
    LOAD_WORK_GROUP_ID  Área fija para el Plan de Trabajo (si no, se elige al azar).
    LOAD_PDF            "1" para incluir la generación del PDF de resultados (pesada:
                        usa el servicio externo de renderizado).
    LOAD_PARALLEL       Peticiones simultáneas por usuario en el Plan de Trabajo
                        (por defecto 6, lo que permite un navegador por servidor).
"""
import itertools
import os
import random
import threading
from datetime import date, timedelta

from gevent.pool import Pool
from locust import HttpUser, between, events, task

API = "/api"


def _load_credentials() -> list[tuple[str, str]]:
    raw = os.getenv("LOAD_USERS", "").strip()
    creds = []
    for item in filter(None, (p.strip() for p in raw.split(","))):
        login, _, password = item.partition(":")
        if login and password:
            creds.append((login, password))
    if not creds and os.getenv("LOAD_USER") and os.getenv("LOAD_PASSWORD"):
        creds.append((os.environ["LOAD_USER"], os.environ["LOAD_PASSWORD"]))
    return creds


CREDENTIALS = _load_credentials()
_cred_cycle = itertools.cycle(CREDENTIALS) if CREDENTIALS else None
_cred_lock = threading.Lock()

DAYS = int(os.getenv("LOAD_DAYS", "30"))
FIXED_WORK_GROUP = os.getenv("LOAD_WORK_GROUP_ID")
INCLUDE_PDF = os.getenv("LOAD_PDF", "0") == "1"
PARALLEL = max(1, int(os.getenv("LOAD_PARALLEL", "6")))

STUDY_TERMS = ["hemo", "glu", "cre", "uro", "tsh", "pt", "col", "trig", "orina", "cultivo"]


@events.test_start.add_listener
def _check_config(environment, **_):
    if not CREDENTIALS:
        raise SystemExit(
            "Configure LOAD_USERS=login:clave[,login:clave] (o LOAD_USER y LOAD_PASSWORD) antes de iniciar."
        )


class LisUser(HttpUser):
    # Tiempo que "piensa" el usuario entre acciones (lee la pantalla, escribe, etc.)
    wait_time = between(3, 10)

    def on_start(self):
        with _cred_lock:
            self.login_name, self.password = next(_cred_cycle)
        self.headers = {}
        self.orders: list[dict] = []
        self.work_groups: list[int] = []
        self.study_ids: list[int] = []
        self._login()
        self._warm_up()

    # ── Sesión ──────────────────────────────────────────────

    def _login(self) -> bool:
        with self.client.post(
            f"{API}/users/login",
            json={"usr_login": self.login_name, "usr_password": self.password},
            name="POST /users/login",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"login {self.login_name}: HTTP {r.status_code}")
                return False
            self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
            return True

    def _request(self, method: str, url: str, name: str, **kwargs):
        """Petición autenticada; si el token venció (401) vuelve a iniciar sesión y reintenta una vez."""
        for attempt in range(2):
            with self.client.request(method, url, headers=self.headers, name=name,
                                     catch_response=True, **kwargs) as r:
                if r.status_code == 401 and attempt == 0:
                    r.success()  # no cuenta como error: es la renovación normal del token
                    if not self._login():
                        return None
                    continue
                if r.status_code >= 400:
                    r.failure(f"HTTP {r.status_code}")
                    return None
                try:
                    return r.json()
                except ValueError:
                    snippet = (r.text or "")[:120].replace("\n", " ")
                    r.failure(f"respuesta no es JSON (HTTP {r.status_code}, {r.headers.get('content-type')}): {snippet}")
                    return None
        return None

    def _warm_up(self):
        """Carga datos reales (órdenes, áreas, estudios) para usarlos en las tareas."""
        for page in range(3):
            data = self._request("GET", f"{API}/orders/?skip={page * 50}&limit=50", "GET /orders/ [lista]")
            if data:
                self.orders.extend(data.get("items", []))
        groups = self._request("GET", f"{API}/masters/work-groups", "GET /masters/work-groups")
        if isinstance(groups, list):
            self.work_groups = [g["wg_id"] for g in groups if g.get("wg_id")]
        studies = self._request("GET", f"{API}/studies-lab/?limit=100", "GET /studies-lab/ [búsqueda]")
        if studies:
            self.study_ids = [s["id"] for s in studies.get("items", [])]

    def _random_order(self) -> dict | None:
        return random.choice(self.orders) if self.orders else None

    # ── Tareas (el número es el peso: qué tan seguido ocurre) ──

    @task(5)
    def orders_list(self):
        """Pantalla de Órdenes: primera(s) página(s) del historial."""
        skip = random.choice([0, 0, 0, 6, 12, 18])
        self._request("GET", f"{API}/orders/?skip={skip}&limit=6", "GET /orders/ [lista]")

    @task(2)
    def orders_search(self):
        """Búsqueda de órdenes por documento del paciente."""
        order = self._random_order()
        doc = (order or {}).get("patient_document")
        if doc:
            self._request("GET", f"{API}/orders/?skip=0&limit=6&search={doc}", "GET /orders/ [búsqueda]")

    @task(5)
    def order_details(self):
        """Abrir una orden en Laboratorio / Resultados (analitos y pruebas)."""
        order = self._random_order()
        if order:
            self._request(
                "GET",
                f"{API}/orders/by-number/{order['o_number']}/details?limit_labs=500&limit_tests=500",
                "GET /orders/by-number/[n]/details",
            )

    @task(2)
    def patient_by_document(self):
        """Admisión: buscar paciente por documento."""
        order = self._random_order()
        doc = (order or {}).get("patient_document")
        if doc:
            self._request("GET", f"{API}/patients/document/{doc}", "GET /patients/document/[doc]")

    @task(2)
    def studies_search(self):
        """Buscador de estudios (admisión, plan de trabajo)."""
        term = random.choice(STUDY_TERMS)
        self._request("GET", f"{API}/studies-lab/?limit=100&search={term}", "GET /studies-lab/ [búsqueda]")

    @task(1)
    def order_traces(self):
        """Trazabilidad de una orden."""
        order = self._random_order()
        if order:
            self._request("GET", f"{API}/traces/order/{order['o_id']}?skip=0&limit=10", "GET /traces/order/[id]")

    @task(1)
    def work_plan(self):
        """
        Plan de Trabajo: filtra las órdenes de un área/estudio y pide el detalle de cada una
        (30 por página), igual que el navegador: varias peticiones en paralelo.
        """
        today = date.today()
        body = {
            "start_date": (today - timedelta(days=DAYS)).isoformat(),
            "end_date": today.isoformat(),
            "sort_by_headquarter": True,
            "skip": 0,
            "limit": 30,
        }
        work_group = FIXED_WORK_GROUP or (random.choice(self.work_groups) if self.work_groups else None)
        if work_group:
            body["work_group_ids"] = [int(work_group)]
        elif self.study_ids:
            body["study_ids"] = [random.choice(self.study_ids)]
        else:
            return

        data = self._request("POST", f"{API}/orders/filter", "POST /orders/filter [plan de trabajo]", json=body)
        items = (data or {}).get("items", [])
        if not items:
            return
        params = "limit_labs=500&limit_tests=500" + (f"&work_group_id={work_group}" if work_group else "")
        pool = Pool(PARALLEL)
        for item in items:
            pool.spawn(
                self._request, "GET",
                f"{API}/orders/by-number/{item['o_number']}/details?{params}",
                "GET /orders/by-number/[n]/details [plan de trabajo]",
            )
        pool.join()

    @task(1)
    def result_pdf(self):
        """Generar el PDF de resultados (solo si LOAD_PDF=1)."""
        if not INCLUDE_PDF:
            return
        order = self._random_order()
        if order:
            self._request("POST", f"{API}/v2/reports/laboratory-results",
                          "POST /v2/reports/laboratory-results [PDF]",
                          json={"order_id": order["o_id"]})
