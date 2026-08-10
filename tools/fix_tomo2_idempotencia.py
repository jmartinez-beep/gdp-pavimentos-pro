from pathlib import Path

app = Path("app.py")
text = app.read_text(encoding="utf-8")
needle = "from gdp_tomo2_adapter import alternatives_for_app, selected_trace\n"
while text.count(needle) > 1:
    first = text.find(needle)
    second = text.find(needle, first + len(needle))
    text = text[:second] + text[second + len(needle):]
app.write_text(text, encoding="utf-8")

patcher = Path("tools/integrate_tomo2_app.py")
p = patcher.read_text(encoding="utf-8")
old = '''replace_once(\n    "from web_storage import (authenticate, create_user, delete_project, list_projects, load_project, save_project)\\n",\n    "from web_storage import (authenticate, create_user, delete_project, list_projects, load_project, save_project)\\nfrom gdp_tomo2_adapter import alternatives_for_app, selected_trace\\n",\n    "import adapter",\n)\n'''
new = '''if "from gdp_tomo2_adapter import alternatives_for_app, selected_trace\\n" not in text:\n    replace_once(\n        "from web_storage import (authenticate, create_user, delete_project, list_projects, load_project, save_project)\\n",\n        "from web_storage import (authenticate, create_user, delete_project, list_projects, load_project, save_project)\\nfrom gdp_tomo2_adapter import alternatives_for_app, selected_trace\\n",\n        "import adapter",\n    )\nelse:\n    print("import adapter: already applied")\n'''
if old in p:
    p = p.replace(old, new, 1)
elif new not in p:
    raise SystemExit("Could not patch import idempotence")
patcher.write_text(p, encoding="utf-8")
print("Tomo II idempotence cleanup complete")
