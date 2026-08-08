# GDP Pavimentos Pro 2024 — v1.1.1 Piloto Cloud

Versión piloto para despliegue gratuito en Streamlit Community Cloud.

## Despliegue
1. Subir los archivos de esta carpeta a un repositorio de GitHub.
2. En Streamlit Community Cloud seleccionar **Create app**.
3. Elegir el repositorio, rama principal y `app.py` como archivo de entrada.
4. Desplegar.

## Notas del piloto
- Se permite crear usuarios o entrar como invitado.
- El modo invitado no guarda proyectos.
- La base SQLite del plan gratuito no debe considerarse almacenamiento permanente: un reinicio/redeploy puede eliminar datos.
- Para producción se recomienda PostgreSQL/Supabase u otra base de datos persistente.
