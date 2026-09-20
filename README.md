# Exportar Chat de Servidor de Discord

Exporta todos los mensajes de un canal en orden cronológico a **JSON** y a una **vista previa HTML** estilo Discord. Sin dependencias (solo Python 3.8+).

## Uso

1. Crea un bot en https://discord.com/developers/applications, copia su token y actívale **Message Content Intent**.
2. Invita el bot al servidor con permisos *View Channel* y *Read Message History*.
3. Activa el modo desarrollador en Discord y copia el ID del servidor y del canal (clic derecho → Copiar ID).
4. Ejecuta:

```powershell
$env:DISCORD_TOKEN = "TU_TOKEN"
python export_discord.py --server ID_SERVIDOR --channel ID_CANAL
```

Si no defines `DISCORD_TOKEN`, el script lo pedirá de forma oculta. Abre `export/<canal>.html` en el navegador para ver la vista previa.

## Seguridad

- El token nunca se guarda ni se sube al repositorio. No lo pegues en issues ni commits.
- Usar un token de **usuario** (`--user-token`) infringe los Términos de Servicio de Discord y puede suspender tu cuenta. Usa un bot.
- La carpeta `export/` está en `.gitignore` porque contiene conversaciones privadas.
