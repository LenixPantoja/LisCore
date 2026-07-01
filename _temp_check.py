import pathlib
f = pathlib.Path(r'd:\Mis Proyectos\CoreLab\Backend\Backend\LisCore\app\domains\reports\infrastructure\pdf_generator.py')
lines = f.read_text(encoding='utf-8').splitlines()
# Remove duplicate l_result check at lines 662-663 (0-indexed: 661-662)
# Keep all lines except 662 and 663 (0-indexed: 661, 662)
new_lines = [line for i, line in enumerate(lines) if i not in (661, 662)]
f.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
print("Done. Removed duplicate lines.")
