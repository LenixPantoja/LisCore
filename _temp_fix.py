import pathlib

f = pathlib.Path(r'd:\Mis Proyectos\CoreLab\Backend\Backend\LisCore\app\domains\reports\infrastructure\pdf_generator.py')
content = f.read_text(encoding='utf-8')

# Remove the duplicate l_result check that was left after the edit
# Handle both \r\n and \n line endings
nl = '\r\n' if '\r\n' in content else '\n'

old = f"        return str(lab.l_result_num){nl}    if lab.l_result:{nl}        return lab.l_result{nl}    # l_result_comp se muestra debajo del examen como fila compuesta, no en esta columna"

new = f"        return str(lab.l_result_num){nl}    # l_result_comp se muestra debajo del examen como fila compuesta, no en esta columna"

if old in content:
    content = content.replace(old, new)
    f.write_text(content, encoding='utf-8')
    print("FIXED: Removed duplicate l_result check.")
else:
    print("NOT FOUND: The duplicate text was not found.")
    lines = content.splitlines()
    for i in range(658, 670):
        if i < len(lines):
            print(f"L{i+1}: {repr(lines[i])}")

