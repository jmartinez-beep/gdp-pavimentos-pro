from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

replacements = [
    ('from cr2010_asphalt import render_asphalt_cr2010_checklist', 'from cr2020_asphalt import render_asphalt_cr2020_checklist'),
    ('13. Control CR-2010', '13. Control CR-2020'),
    ('render_asphalt_cr2010_checklist(project_name)', 'render_asphalt_cr2020_checklist(project_name)'),
    ('asphalt_cr2010_result', 'asphalt_cr2020_result'),
    ('"asphalt_cr2010": st.session_state.get("asphalt_cr2010_checklist", {}),', '"asphalt_cr2020": st.session_state.get("asphalt_cr2020_checklist", st.session_state.get("asphalt_cr2010_checklist", {})),'),
    ('payload.get("asphalt_cr2010", {})', 'payload.get("asphalt_cr2020", payload.get("asphalt_cr2010", {}))'),
    ('sheet_name="Control_CR2010"', 'sheet_name="Control_CR2020"'),
    ('sheet_name="Checklist_CR2010"', 'sheet_name="Checklist_CR2020"'),
    ('Control CR-2010 asfaltos', 'Control CR-2020 asfaltos'),
    ('Cumplimiento CR-2010', 'Cumplimiento CR-2020'),
    ('Control asfáltico CR-2010 revisado', 'Control constructivo CR-2020 revisado'),
    ('asphalt_cr2010_checklist", {})', 'asphalt_cr2020_checklist", st.session_state.get("asphalt_cr2010_checklist", {}))'),
    ('qa_asphalt_cr2010', 'qa_asphalt_cr2020'),
]

changed = []
for old, new in replacements:
    if old in text:
        text = text.replace(old, new)
        changed.append(old)

required = [
    'from cr2020_asphalt import render_asphalt_cr2020_checklist',
    '13. Control CR-2020',
    'render_asphalt_cr2020_checklist(project_name)',
    'asphalt_cr2020',
    'Control_CR2020',
    'Checklist_CR2020',
]

missing = [item for item in required if item not in text]
if missing:
    raise SystemExit(f'No se pudo completar la migración; faltan: {missing}')

path.write_text(text, encoding='utf-8')
print('Migración CR-2020 aplicada. Reemplazos:', len(changed))
