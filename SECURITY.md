# Política de seguridad

VasakOS es un sistema operativo y escribe **código privilegiado propio**: un
llavero que guarda las contraseñas de la sesión, un agente de PolicyKit que pide
la de administrador, un servicio que corre como root y escribe perfiles de
AppArmor, y un instalador que particiona discos. Si encontraste un problema en
alguno, esto es lo que hacemos con tu reporte.

## Cómo reportar

**Usá el reporte privado de GitHub**, no un issue público. En el repositorio que
corresponda: pestaña **Security** → **Report a vulnerability**.

Está habilitado en **todos** los repositorios activos de la organización, así
que el que te interese lo va a tener. La única excepción es `vue-libvasak`, que
está archivado y GitHub no deja habilitarlo en un repositorio de sólo lectura.

Si no sabés cuál es el repositorio, mandalo a
[vasak-permissions](https://github.com/Vasak-OS/vasak-permissions/security) y lo
derivamos: nos llega igual.

Un issue público es lo único que te pedimos que **no** hagas: deja el problema a
la vista de cualquiera mientras todavía no hay arreglo.

Ayuda mucho que el reporte traiga la versión del paquete (`pacman -Q <paquete>`),
qué pasa, y cómo reproducirlo. Un exploit no hace falta.

## Qué hacemos, y cuándo

| | |
|---|---|
| Acuse de recibo | **72 horas hábiles** |
| Primer diagnóstico —si es, qué alcanza, qué gravedad— | **7 días** |
| Plazo antes de que publiques | **90 días**, o antes si el arreglo sale antes |

Los 90 días son el pedido, no una imposición: si pasan y no resolvimos, publicá.
Un plazo que se estira indefinidamente es cómo se pierde la confianza de quien
reporta.

Si querés crédito, lo damos con el nombre que nos digas; si preferís que no
figures, tampoco figurás. En los dos casos publicamos un aviso con qué pasaba y
desde qué versión está arreglado.

## Qué versiones sostenemos

**Sólo la última.** VasakOS es rolling: no hay ramas viejas mantenidas, y el
arreglo llega actualizando. Un equipo que hace meses no actualiza no está en una
versión anterior sostenida — está en una sin sostener.

## Qué entra y qué no

**Entra** el código de esta organización, y sobre todo lo que corre con
privilegios o toca secretos:

- `vasak-keyring` — el llavero. AES-256-GCM con derivación Argon2id.
- `vasak-permissions` — servicio de sistema; lee el registro del kernel y
  escribe perfiles de AppArmor.
- `polkit-vasak` — el agente que pide la contraseña de administrador.
- `vasak-installer` — corre como root y particiona discos.
- `vasak-connect` — expone el teléfono al escritorio; entrada desde la red.
- `vasak-wayfire-plugins` — corre **dentro del compositor** y decide qué
  protocolos de Wayland ve cada cliente.
- Los perfiles de AppArmor y la configuración del sistema en
  `vasak-desktop-settings`, y las recetas de `PKGBUILDS`.

**No entra** el software que empaquetamos sin escribir —el kernel, systemd,
wayfire, los paquetes de Arch—. Eso va a su proyecto de origen; si nos llega,
te decimos a dónde. Sí entra **cómo lo configuramos nosotros**: una opción
nuestra que debilita un componente ajeno es problema nuestro.

## Contra qué protege VasakOS, y contra qué todavía no

Esto es lo que hay hoy, sin adornos. Está acá porque una política de seguridad
que sólo enumera lo que funciona no le sirve a quien tiene que decidir si
confiar. El detalle —qué hay para proteger, de dónde puede venir el problema y
qué queda explícitamente afuera— está en el
[modelo de amenazas](THREAT-MODEL.md).

**Lo que sí hace cumplir.** El confinamiento real lo pone AppArmor, que es
independiente de cómo se lance el programa. Un AppImage no puede leer tus claves
de SSH ni de GPG, ni el llavero, ni los tokens guardados, ni hablar con los
agentes que firman por vos. Todo lo que se bloquea se puede desbloquear, desde el
aviso o desde Configuración.

**Lo que todavía tiene puerta de al lado.** Hay tres, y están abiertas y
numeradas:

- **Capturar la pantalla sin pasar por el portal.** El diálogo pregunta, pero un
  cliente de Wayland no está obligado a usarlo.
  ([vasak-permissions#27](https://github.com/Vasak-OS/vasak-permissions/issues/27))
- **Cámara y micrófono por PipeWire.** El permiso se pregunta y se anota, y un
  programa puede pedirle el nodo a PipeWire igual.
  ([vasak-desktop-settings#3](https://github.com/Vasak-OS/vasak-desktop-settings/issues/3))
- **La mayoría de los perfiles del sistema están en modo aviso**, no bloqueando.
  Anotan lo que habrían impedido.
  ([vasak-desktop-settings#2](https://github.com/Vasak-OS/vasak-desktop-settings/issues/2))

Y una que no es un agujero pero cambia la superficie: **VasakOS todavía no firma
su arranque**, así que hoy se instala con Secure Boot desactivado
([archiso#6](https://github.com/Vasak-OS/archiso/issues/6)).

El seguimiento de todo esto está en
[vasak-permissions#34](https://github.com/Vasak-OS/vasak-permissions/issues/34).

## Qué pasa después de que reportás

El detalle está en el [proceso de aviso](AVISOS.md): cuándo pedimos un CVE y
cuándo no, quién lo pide, qué dice un aviso y cómo se entera quien ya instaló.

En resumen: el arreglo sale como una actualización normal, el aviso se publica
**después** de que el paquete está en el repositorio, y `vasak-update` lo
comprueba una vez por día y al iniciar sesión, así que llega dentro de las
veinticuatro horas a un equipo encendido.

Con un límite que conviene saber: **el aviso no distingue todavía una
actualización de seguridad de una cualquiera.** La base de paquetes de pacman no
tiene ningún campo de seguridad, así que quien pospone las actualizaciones
pospone también éstas sin enterarse de que son distintas. El proceso explica qué
lo cierra.

## Lo que falta de esta política

Queda decidir si va a haber **auditoría externa** del llavero y del agente de
PolicyKit. Está en [website#5](https://github.com/Vasak-OS/website/issues/5).

El fuzzing de los analizadores privilegiados sí está. Los tres que leen entrada
que eligió otro tienen pruebas de propiedad corriendo en cada push: el registro
del kernel que lee el servicio de permisos, el sondeo de discos del instalador
—que monta particiones ajenas— y el protocolo del teléfono, que es el único que
llega desde la red.
