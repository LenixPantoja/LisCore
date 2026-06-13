"""
⚠️ COPIA ESTE ARCHIVO A TU SERVIDOR Y EJECUTA:
    cd /ruta/del/proyecto
    python -m tests.debug_barcodes_v2 3

Te mostrará EXACTAMENTE qué falta para generar stickers.
"""
import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

async def debug(order_id: int):
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as db:
        # 1. Orden
        r = await db.execute(text("SELECT o_id, o_number FROM \"Orders\" WHERE o_id=:oid"), {"oid": order_id})
        o = r.fetchone()
        if not o: print(f"❌ Orden {order_id} no existe"); return
        print(f"✅ Orden #{o[1]}")

        # 2. Tubos
        r = await db.execute(text("""
            SELECT so_id, so_sample_type_id, st.st_name, st.st_sufix 
            FROM "SamplesOrder" so
            LEFT JOIN "SampleTypes" st ON st.st_id = so.so_sample_type_id
            WHERE so.so_order_id=:oid
        """), {"oid": order_id})
        tubes = r.fetchall()
        print(f"📦 Tubos: {len(tubes)}")
        for t in tubes:
            print(f"   ID {t[0]}: sample_type_id={t[1]} -> '{t[2]}' (suffix={t[3]})")

        if not tubes: print("❌ Sin tubos"); return

        # 3. Estudios + WorkGroups + TestDetails + TestsLab
        r = await db.execute(text("""
            SELECT DISTINCT od.od_study_id, sl.code, sl.work_groups_id, wg.wg_name
            FROM "OrdersDetails" od
            JOIN "StudiesLab" sl ON sl.id = od.od_study_id
            LEFT JOIN "Work_groups" wg ON wg.wg_id = sl.work_groups_id
            WHERE od.od_order_id = :oid
        """), {"oid": order_id})
        studies = r.fetchall()
        print(f"\n📚 Estudios: {len(studies)}")
        
        ALL_OK = True
        for s in studies:
            sid, code, wg_id, wg_name = s
            problems = []
            
            if not wg_id:
                problems.append("❌ SIN WORK_GROUP")
                ALL_OK = False
            
            # Tests
            r2 = await db.execute(text("""
                SELECT tl.id, tl.code, tl.print_barcode, tl.samples_type_id, st.st_name
                FROM "StudiesTestDetail" std
                JOIN "TestsLab" tl ON tl.id = std.tests_id
                LEFT JOIN "SampleTypes" st ON st.st_id = tl.samples_type_id
                WHERE std.studies_id = :sid
            """), {"sid": sid})
            tests = r2.fetchall()
            
            has_valid_test = False
            for t in tests:
                if t[2] and t[3]:  # print_barcode=True AND samples_type_id NOT NULL
                    has_valid_test = True
            
            if not tests:
                problems.append("❌ SIN PRUEBAS ASOCIADAS (StudiesTestDetail vacío)")
                ALL_OK = False
            elif not has_valid_test:
                problems.append("❌ NINGUNA PRUEBA CON print_barcode=True + samples_type_id")
                ALL_OK = False
                for t in tests:
                    issues = []
                    if not t[2]: issues.append("print_barcode=False")
                    if not t[3]: issues.append("samples_type_id=NULL")
                    print(f"      ⚠️  Test {t[0]} '{t[1]}': {', '.join(issues)} -> SampleType '{t[4]}'")
            
            wg_status = f"WG={wg_id} '{wg_name}'" if wg_id else "❌ SIN WG"
            status = " | ".join(problems) if problems else "✅ OK"
            print(f"   📚 Study {sid} '{code}' | {wg_status} | {len(tests)} tests | {status}")

        if ALL_OK:
            print(f"\n🎉 La orden {order_id} debería generar stickers correctamente")
        else:
            print(f"\n🔴 La orden {order_id} NO generará stickers. Revisa los ❌ arriba")
        
        await engine.dispose()

asyncio.run(debug(int(sys.argv[1]) if len(sys.argv) > 1 else 3))