# VasakOS

Un sistema operativo libre construido sobre **Arch Linux**, con escritorio y
aplicaciones propias. Nace en el entorno de [Vasak Group](https://vasak.net.ar)
y crece con la comunidad.

La diferencia con otras distribuciones es dónde ponemos el trabajo. No armamos
una selección de aplicaciones de otros entornos: el panel, el gestor de
archivos, la terminal, los ajustes, la galería, el reproductor, el llavero de
claves y el gestor de sesión están escritos para este sistema, en Rust con Tauri
y Vue, compartiendo una misma biblioteca de componentes. Por eso todo se ve y se
comporta igual, y por eso la interfaz se puede personalizar con CSS sin
recompilar nada.

Abajo sigue siendo Arch: `pacman`, la wiki y el ecosistema que ya conocés.

| | |
|---|---|
| Base | Arch Linux |
| Modelo | Rolling release |
| Sesión gráfica | Wayland (Wayfire) |
| Escritorio y aplicaciones | Rust + Tauri + Vue |
| Arquitectura | x86_64 |
| Licencia | GPL-3.0 |

**[Probalo](https://os.vasak.net.ar/downloads)** ·
[Documentación](https://os.vasak.net.ar/docs) ·
[Estado del proyecto](https://os.vasak.net.ar/state)

## Qué hay acá

**El escritorio**
[`vasak-desktop`](https://github.com/Vasak-OS/vasak-desktop) es el núcleo: panel,
menú y centro de notificaciones.
[`vasak-desktop-settings`](https://github.com/Vasak-OS/vasak-desktop-settings)
trae la configuración del sistema y los perfiles de seguridad, y
[`vasak-session-manager`](https://github.com/Vasak-OS/vasak-session-manager) el
inicio de sesión y el bloqueo de pantalla. Las notificaciones las sirve
[`vasak-flare-daemon`](https://github.com/Vasak-OS/vasak-flare-daemon).

**Las aplicaciones**
[archivos](https://github.com/Vasak-OS/vasak-file-manager) ·
[terminal](https://github.com/Vasak-OS/vasak-terminal) ·
[configuración](https://github.com/Vasak-OS/vasak-settings) ·
[galería](https://github.com/Vasak-OS/vasak-gallery) ·
[música](https://github.com/Vasak-OS/vasak-resonance) ·
[capturas](https://github.com/Vasak-OS/vasak-shot) ·
[monitor](https://github.com/Vasak-OS/vasak-monitor) ·
[cuentas](https://github.com/Vasak-OS/vasak-accounts)

**Lo que corre con privilegios**
[`vasak-keyring`](https://github.com/Vasak-OS/vasak-keyring) guarda las
contraseñas de la sesión con AES-256-GCM y derivación Argon2id.
[`vasak-permissions`](https://github.com/Vasak-OS/vasak-permissions) decide qué
puede usar la cámara, el micrófono, la pantalla y tus credenciales, y lo hace
cumplir con AppArmor.
[`polkit-vasak`](https://github.com/Vasak-OS/polkit-vasak) es el agente que pide
la contraseña de administrador.
[`vasak-installer`](https://github.com/Vasak-OS/vasak-installer) instala el
sistema.

**El sistema**
[`archiso`](https://github.com/Vasak-OS/archiso) arma la imagen,
[`PKGBUILDS`](https://github.com/Vasak-OS/PKGBUILDS) tiene las recetas de todos
los paquetes, y
[`vasak-connect`](https://github.com/Vasak-OS/vasak-connect) integra el teléfono
Android.

**Para reusar en tus propios proyectos**
Los plugins de Tauri que escribimos se publican por separado y no dependen de
VasakOS:
[red](https://github.com/Vasak-OS/tauri-plugin-network-manager) ·
[bluetooth](https://github.com/Vasak-OS/tauri-plugin-bluetooth-manager) ·
[iconos del sistema](https://github.com/Vasak-OS/tauri-plugin-vicons) ·
[traducciones](https://github.com/Vasak-OS/tauri-plugin-i18n) ·
[arrastrar y soltar en Wayland](https://github.com/Vasak-OS/tauri-plugin-drag-and-drop-wayland) ·
[menú contextual](https://github.com/Vasak-OS/tauri-plugin-vsk-contextual-menu) ·
[diario](https://github.com/Vasak-OS/tauri-plugin-vsk-journal) ·
[configuración](https://github.com/Vasak-OS/tauri-plugin-config-manager) ·
[datos de usuario](https://github.com/Vasak-OS/tauri-plugin-user-data)

Y [`vapp`](https://github.com/Vasak-OS/vapp) es la plantilla con la que
arrancamos cada aplicación nueva.

## En qué anda

La última imagen publicada es la **Alpha 5**, del 19 de agosto de 2026. Lo que
cambió desde entonces está en el
[registro de cambios](https://os.vasak.net.ar/changelogs),
y el trabajo en curso en el proyecto
[VasakOS Roadmap](https://github.com/orgs/Vasak-OS/projects).

Es un sistema en desarrollo activo y lo decimos en serio: úsalo sabiendo que
todavía hay cosas a medio hacer, y contanos las que encuentres.

## Cómo colaborar

Los issues abiertos de cada repositorio son el mejor lugar para empezar; muchos
tienen escrito qué falta y por dónde. Si vas a mandar un cambio, una rama y un
pull request al repositorio que corresponda.

Traducir también cuenta, y hace falta: las aplicaciones están preparadas para
más idiomas de los que hoy tienen.

## Seguridad

Si encontrás una vulnerabilidad, **no abras un issue público**: usá el reporte
privado de GitHub —pestaña **Security** → **Report a vulnerability**— en el
repositorio que corresponda.

Los plazos, el alcance y **contra qué todavía no protege VasakOS** están en la
[política de seguridad](https://github.com/Vasak-OS/.github/blob/main/SECURITY.md).
Esa última parte está ahí a propósito: una política que sólo enumera lo que
funciona no le sirve a quien tiene que decidir si confiar.
