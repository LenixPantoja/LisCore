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
)
from app.domains.orders.domain.constants import (
    ORDER_STATE_PENDIENTE,
    ORDER_STATE_CON_RESULTADOS,
    ORDER_STATE_VALIDADA,
)

# Un lab "tiene resultado" si está Con Resultados, Validada o Impreso
LAB_STATES_WITH_RESULTS = {
    LABORATORY_STATE_CON_RESULTADOS,
    LABORATORY_STATE_VALIDADA,
    LABORATORY_STATE_IMPRESO,
}

# Un lab está "validado" (o superior) si está Validada o Impreso
LAB_STATES_VALIDATED_OR_BEYOND = {
    LABORATORY_STATE_VALIDADA,
    LABORATORY_STATE_IMPRESO,
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
        required_ids = required_tests_by_study.get(study_id) or set(tests_map.keys())

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
