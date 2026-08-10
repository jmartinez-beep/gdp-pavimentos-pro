# Persistencia de proyectos con PostgreSQL / Supabase

GDP Pavimentos Pro usa `web_storage.py` como capa única de persistencia.

## Selección automática del backend

- Si existe `DATABASE_URL` o `GDP_DATABASE_URL`, la aplicación usa PostgreSQL.
- Si no existe ninguna de esas variables, usa SQLite local para desarrollo y pruebas.

No es necesario modificar `app.py` para cambiar de backend.

## Configuración recomendada en Streamlit Community Cloud

1. Cree un proyecto en Supabase.
2. En Supabase, abra **Project Settings > Database** y copie una cadena de conexión PostgreSQL válida. Para una aplicación desplegada, use una cadena compatible con conexiones externas y SSL.
3. En Streamlit Community Cloud, abra la aplicación GDP Pavimentos Pro y entre a **Settings > Secrets**.
4. Agregue la cadena como secreto raíz:

```toml
DATABASE_URL = "postgresql://USUARIO:CONTRASENA@HOST:PUERTO/BASE?sslmode=require"
```

5. Guarde los secretos y reinicie/reboot la aplicación.

Al iniciar, `web_storage.py` crea automáticamente las tablas e índices requeridos si no existen.

## Esquema administrado por la aplicación

### users

- `id`
- `username`
- `password_hash`
- `display_name`
- `created_at`

El nombre de usuario es único sin distinguir mayúsculas/minúsculas.

### projects

- `id`
- `user_id`
- `name`
- `payload_json`
- `created_at`
- `updated_at`

Cada usuario puede guardar varios proyectos. Guardar nuevamente con el mismo nombre actualiza el proyecto existente.

## Seguridad

- Las contraseñas se almacenan como hashes PBKDF2-SHA256 con sal aleatoria; nunca se guarda la contraseña en texto plano.
- `DATABASE_URL` no debe agregarse al repositorio GitHub. Debe permanecer exclusivamente en los secretos del entorno de despliegue.
- No publique capturas de pantalla que muestren la cadena de conexión completa.

## Migración de datos SQLite existentes

Esta etapa habilita PostgreSQL para proyectos nuevos. Los datos que ya existan en un archivo SQLite local no se copian automáticamente a Supabase. Si hubiera proyectos SQLite que deban conservarse, deben exportarse/importarse mediante una migración controlada antes de retirar ese archivo.

## Verificación

Después de configurar `DATABASE_URL`:

1. Cree un usuario de prueba.
2. Inicie sesión.
3. Guarde un proyecto desde **Mis proyectos**.
4. Cierre sesión y vuelva a entrar.
5. Abra el proyecto guardado.
6. Reinicie la aplicación desde Streamlit Cloud y confirme que el proyecto sigue disponible.

Si el proyecto persiste tras el reinicio, la aplicación ya está trabajando contra PostgreSQL/Supabase y no contra el disco efímero del contenedor.
