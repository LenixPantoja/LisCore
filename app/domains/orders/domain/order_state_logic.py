"""
Lógica de negocio (pura, sin acceso a BD) para calcular el o_order_state
de una Orden a partir del estado de sus Laboratorios, respetando la
configuración is_required de StudiesTestDetail.

Usada tanto por orders.application.use_cases (cálculo dinámico para
listados/consultas) como por laboratories.application.use_cases
(persistencia del estado tras operaciones sobre resultados), para evitar
que ambas copias de la lógica diverjan.
"""
from app.domains.laboratories.domain.constants import (
    LABORATORY_STATE_CON_RESULTADOS,
    LABORATORY_STATE_VALIDADA,
    LABORATORY_STATE_IMPRESO,
    LABORATORY_STATE_DESCARTADO,
)
from app.domains.orders.domain.constants import (
    ORDER_STATE_PENDIENTE,
    ORDER_STATE_CON_RESULTADOS,
    ORDER_STATE_VALIDADA,
)

# Un lab "tiene resultado" si está Con Resultados, Validada o Impreso.
# Un lab Descartado también cuenta como "resuelto": no se espera un resultado
# para él, así que no debe impedir que la orden avance a Con Resultados/Validada.
LAB_STATES_WITH_RESULTS = {
    LABORATORY_STATE_CON_RESULTADOS,
    LABORATORY_STATE_VALIDADA,
    LABORATORY_STATE_IMPRESO,
    LABORATORY_STATE_DESCARTADO,
}

# Un lab está "validado" (o superior) si está Validada o Impreso.
# Descartado también cuenta como resuelto por la misma razón que arriba.
LAB_STATES_VALIDATED_OR_BEYOND = {
    LABORATORY_STATE_VALIDADA,
    LABORATORY_STATE_IMPRESO,
    LABORATORY_STATE_DESCARTADO,
}


def compute_order_state_from_studies(
    study_labs: dict[int, dict[int, int]],
    required_tests_by_study: dict[int, set[int]],
) -> int:
    """
    Calcula el o_order_state de una orden a partir de sus laboratorios.

    Args:
        study_labs: {study_id: {test_id: l_state}} con todos los laboratorios
            de la orden, agrupados por estudio.
        required_tests_by_study: {study_id: {tests_id, ...}} solo con las
            pruebas marcadas is_required=True para ese estudio. Si un estudio
            no tiene entrada (o el set es vacío), se usa el comportamiento
            legacy: todas las pruebas del estudio determinan su estado.

    Reglas (de mayor a menor prioridad):
        - ORDER_STATE_VALIDADA (4): TODOS los estudios tienen sus pruebas
          relevantes (requeridas, o todas si no hay requeridas) en estado
          Validada o Impreso.
        - ORDER_STATE_CON_RESULTADOS (3): TODOS los estudios tienen sus
          pruebas relevantes con resultado (Con Resultados, Validada o
          Impreso), aunque no todas estén validadas.
        - ORDER_STATE_PENDIENTE (2): cualquier otro caso.
    """
    if not study_labs:
        return ORDER_STATE_PENDIENTE

    all_validated = True
    all_with_results = True

    for study_id, tests_map in study_labs.items():
        # Solo cuentan las pruebas requeridas que existen en la orden: una prueba
        # marcada como requerida después de crear la orden no tiene laboratorio
        # y no debe bloquear el estado.
        required_ids = (required_tests_by_study.get(study_id, set()) & tests_map.keys()) or set(tests_map.keys())

        if not all(tests_map.get(tid, 0) in LAB_STATES_VALIDATED_OR_BEYOND for tid in required_ids):
            all_validated = False
        if not all(tests_map.get(tid, 0) in LAB_STATES_WITH_RESULTS for tid in required_ids):
            all_with_results = False

        if not all_validated and not all_with_results:
            break

    if all_validated:
        return ORDER_STATE_VALIDADA
    if all_with_results:
        return ORDER_STATE_CON_RESULTADOS
    return ORDER_STATE_PENDIENTE


# Estados de un estudio (etiquetas que consume el frontend)
STUDY_STATE_SIN_RESULTADOS = "Sin Resultados"
STUDY_STATE_PENDIENTE = "Pendiente"
STUDY_STATE_CON_RESULTADOS = "Con Resultados"
STUDY_STATE_VALIDADO = "Validado"


def compute_study_state(tests_map: dict[int, int], required_test_ids: set[int]) -> str:
    """
    Estado de un estudio a partir de sus pruebas ({test_id: l_state}).

    Pruebas relevantes = las requeridas del estudio que existen en la orden; si
    el estudio no tiene requeridas, todas sus pruebas.

    - Validado: todas las requeridas están validadas (o impresas/descartadas)
      y las NO requeridas están validadas o sin resultado (una no requerida
      vacía no impide validar el estudio).
    - Con Resultados: todas las requeridas tienen resultado, pero falta
      validar alguna (o una no requerida tiene resultado sin validar).
    - Pendiente: alguna requerida aún no tiene resultado.
    - Sin Resultados: el estudio no tiene pruebas en la orden.
    """
    if not tests_map:
        return STUDY_STATE_SIN_RESULTADOS

    required_ids = (required_test_ids & tests_map.keys()) or set(tests_map.keys())
    optional_ids = tests_map.keys() - required_ids

    if not all(tests_map[tid] in LAB_STATES_WITH_RESULTS for tid in required_ids):
        return STUDY_STATE_PENDIENTE

    required_validated = all(tests_map[tid] in LAB_STATES_VALIDATED_OR_BEYOND for tid in required_ids)
    optional_ok = all(
        tests_map[tid] in LAB_STATES_VALIDATED_OR_BEYOND
        or tests_map[tid] not in LAB_STATES_WITH_RESULTS  # no requerida sin resultado
        for tid in optional_ids
    )
    if required_validated and optional_ok:
        return STUDY_STATE_VALIDADO
    return STUDY_STATE_CON_RESULTADOS
