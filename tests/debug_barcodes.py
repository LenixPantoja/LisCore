"""
Debug script: Diagnose why printer-barcodes fails for a given order_id.

Run with:
    cd d:/Mis Proyectos/CoreLab/Backend/Backend/LisCore
    py -m tests.debug_barcodes [order_id]
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings


async def debug_order(order_id: int):
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with sf() as db:
        print(f"\n{'='*80}")
        print(f"🔍 DIAGNÓSTICO PARA ORDER ID: {order_id}")
        print(f"{'='*80}\n")

        # 1. Check Order exists
        print("─── 1. ORDEN ───")
        row = await db.execute(text("SELECT o_id, o_number, o_his_id, o_enterprise_id, o_order_state FROM \"Orders\" WHERE o_id = :oid"), {"oid": order_id})
        order = row.fetchone()
        if not order:
            print(f"❌ Orden con ID {order_id} NO encontrada")
            return
        print(f"✅ Orden #{order[1]} (ID: {order[0]}) | Paciente ID: {order[2]} | Empresa ID: {order[3]} | Estado: {order[4]}")

        # 2. Check tubes
        print(f"\n─── 2. TUBOS / MUESTRAS (SamplesOrder) ───")
        row = await db.execute(text("SELECT so_id, so_sample_type_id, so_barcode FROM \"SamplesOrder\" WHERE so_order_id = :oid"), {"oid": order_id})
        tubes = row.fetchall()
        print(f"   Total: {len(tubes)}")
        for t in tubes:
            st_row = await db.execute(text("SELECT st_name, st_sufix FROM \"SampleTypes\" WHERE st_id = :sid"), {"sid": t[1]})
            st = st_row.fetchone()
            st_name = f"'{st[0]}' (suffix={st[1]})" if st else "⚠️ NO ENCONTRADO"
            print(f"   📍 Tubo ID {t[0]} -> sample_type_id={t[1]} -> {st_name}, barcode={t[2]}")
        if not tubes:
            print("❌ No hay tubos")
            return

        # 3. Studies in the order
        print(f"\n─── 3. ESTUDIOS EN LA ORDEN (OrdersDetail) ───")
        row = await db.execute(text("SELECT od_id, od_study_id, od_state, od_cancelled FROM \"OrdersDetails\" WHERE od_order_id = :oid"), {"oid": order_id})
        details = row.fetchall()
        print(f"   Total: {len(details)}")
        study_ids = [d[1] for d in details]
        for d in details:
            print(f"   📚 OrdersDetail ID {d[0]}: study_id={d[1]}, state={d[2]}, cancelled={d[3]}")

        if not study_ids:
            print("❌ No hay estudios")
            return

        # 4. Load StudiesLab with all their test details  
        print(f"\n─── 4. ESTUDIOS (StudiesLab) + PRUEBAS ───")
        for sid in study_ids:
            s = await db.execute(text("""
                SELECT sl.id, sl.code, sl.name, sl.work_groups_id, wg.wg_name
                FROM "StudiesLab" sl
                LEFT JOIN "Work_groups" wg ON wg.wg_id = sl.work_groups_id
                WHERE sl.id = :sid
            """), {"sid": sid})
            study = s.fetchone()
            if not study:
                print(f"   ⚠️ Study ID {sid}: NO ENCONTRADO")
                continue
            
            wg_info = f"✅ WG={study[3]} ('{study[4]}')" if study[3] else "❌ SIN WORK GROUP"
            print(f"\n   📚 Estudio ID {study[0]}: code='{study[1]}', name='{study[2]}'")
            print(f"      {wg_info}")

            tds = await db.execute(text("""
                SELECT tl.id, tl.code, tl.name, tl.print_barcode, tl.samples_type_id
                FROM "StudiesTestDetail" std
                JOIN "TestsLab" tl ON tl.id = std.tests_id
                WHERE std.studies_id = :sid
                ORDER BY std.order_print, std.id
            """), {"sid": sid})
            test_details = tds.fetchall()
            for td in test_details:
                flags = []
                if not td[3]:
                    flags.append("print_barcode=False ❌")
                if not td[4]:
                    flags.append("samples_type_id=NULL ❌")
                if not flags:
                    flags.append("✅ OK")
                
                st_info = ""
                if td[4]:
                    st = await db.execute(text("SELECT st_name, st_sufix FROM \"SampleTypes\" WHERE st_id = :sid"), {"sid": td[4]})
                    st_r = st.fetchone()
                    st_info = f" -> SampleType: '{st_r[0]}' (suffix={st_r[1]})" if st_r else f" -> ⚠️ SampleType ID {td[4]} NOT FOUND"
                
                print(f"      Test ID {td[0]}: code='{td[1]}' name='{td[2]}' | {' | '.join(flags)}{st_info}")

        # 5. Sample suffix matching simulation
        print(f"\n─── 5. MATCHING DE TIPOS DE MUESTRA ───")
        tube_st_ids = {t[1] for t in tubes if t[1]}
        study_st_ids = set()
        for sid in study_ids:
            rows = await db.execute(text("""
                SELECT DISTINCT tl.samples_type_id FROM "StudiesTestDetail" std
                JOIN "TestsLab" tl ON tl.id = std.tests_id
                WHERE std.studies_id = :sid AND tl.print_barcode = TRUE AND tl.samples_type_id IS NOT NULL
            """), {"sid": sid})
            study_st_ids.update(r[0] for r in rows.fetchall())

        print(f"   SampleType IDs en tubos:     {tube_st_ids}")
        print(f"   SampleType IDs en estudios:  {study_st_ids}")

        # 6. Sticker simulation
        print(f"\n─── 6. SIMULACIÓN FINAL DEL USECASE ───")
        from collections import defaultdict
        
        # Build sample_wg_studies
        sample_wg_studies = defaultdict(lambda: defaultdict(list))
        for sid in study_ids:
            s = await db.execute(text("SELECT id, code, name, work_groups_id FROM \"StudiesLab\" WHERE id = :sid"), {"sid": sid})
            study = s.fetchone()
            if not study or not study[3]:
                continue
            code = (study[1] or study[2] or "").strip()
            if not code:
                continue
            covered = set()
            tds = await db.execute(text("""
                SELECT tl.samples_type_id FROM "StudiesTestDetail" std
                JOIN "TestsLab" tl ON tl.id = std.tests_id
                WHERE std.studies_id = :sid AND tl.print_barcode = TRUE AND tl.samples_type_id IS NOT NULL
            """), {"sid": sid})
            for td in tds.fetchall():
                covered.add(td[0])
            for st_id in covered:
                sample_wg_studies[st_id][study[3]].append(code)

        print(f"   sample_wg_studies: {dict(sample_wg_studies)}")

        stickers_count = 0
        for t in tubes:
            if not t[1]:
                continue
            st = (await db.execute(text("SELECT st_id, st_name, st_sufix FROM \"SampleTypes\" WHERE st_id = :sid"), {"sid": t[1]})).fetchone()
            if not st:
                continue
            sufix = st[2] if st[2] is not None else st[0]
            related = (await db.execute(text("SELECT st_id FROM \"SampleTypes\" WHERE st_sufix = :sfx"), {"sfx": sufix})).fetchall()
            related_ids = [r[0] for r in related]
            
            combined = defaultdict(list)
            for st_id in related_ids:
                for wg_id, codes in sample_wg_studies.get(st_id, {}).items():
                    for c in codes:
                        if c not in combined[wg_id]:
                            combined[wg_id].append(c)
            
            n = len(combined)
            if n == 0:
                print(f"   ❌ Tubo ID {t[0]}: NO se genera sticker (sin estudios para sample_type suffix={sufix})")
            else:
                stickers_count += n
                print(f"   ✅ Tubo ID {t[0]}: se generarían {n} sticker(s) - {dict(combined)}")

        print(f"\n{'='*80}")
        if stickers_count == 0:
            print("🔴 DIAGNÓSTICO: NO se generarían stickers")
            print("   Causas posibles:")
            print("   1. Ningún estudio tiene work_groups_id asignado")
            print("   2. Ninguna prueba tiene print_barcode=True y samples_type_id configurado")
            print("   3. Los tipos de muestra de tubos no coinciden con los de los estudios")
            print("\n   🔧 Acción requerida: Verifica los flags ❌ en la sección 4")
        else:
            print(f"🟢 DIAGNÓSTICO: Se generarían {stickers_count} sticker(s) correctamente")
        print(f"{'='*80}")

        await engine.dispose()


if __name__ == "__main__":
    oid = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    asyncio.run(debug_order(oid))