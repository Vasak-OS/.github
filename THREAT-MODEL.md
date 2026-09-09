# Contra qué protege VasakOS

Este documento dice qué defiende el sistema, con qué, y **qué no defiende
todavía**. Lo segundo importa tanto como lo primero: una política que sólo
enumera lo que funciona no le sirve a quien tiene que decidir si confiar.

Va junto a la [política de seguridad](SECURITY.md), que explica cómo reportar.

## Qué hay para proteger

| | dónde vive |
|---|---|
| Las contraseñas de la sesión | `vasak-keyring`, AES-256-GCM con derivación Argon2id |
| Las claves de SSH y de GPG | `~/.ssh`, `~/.gnupg`, y los agentes que firman con ellas |
| Los tokens que abren una cuenta sin segundo factor | `~/.netrc`, `~/.git-credentials`, `~/.npmrc`, `~/.aws`, `~/.kube`, `~/.config/gh` |
| La cámara, el micrófono y la pantalla | los dispositivos, PipeWire y el compositor |
| El disco, durante la instalación | `vasak-installer`, que corre como root |
| El teléfono conectado | `vasak-connect`, que lo expone al escritorio |

## De dónde puede venir el problema

Cinco entradas, en orden de cuánto se usan:

**Una aplicación que la persona instala.** Sobre todo un AppImage: se baja de
cualquier lado, no pasa por `pacman`, y corre con la cuenta de quien lo abre.

**Un cliente de Wayland.** Cualquier programa con acceso al compositor, esté
empaquetado o no.

**Un aparato que se enchufa.** Un teléfono por USB o por red: el número de
serie, el nombre del modelo y los nombres de paquete los elige él.

**Un disco ajeno.** Al instalar, `os-prober` **monta** las particiones que
encuentra para mirar qué hay adentro. Un pendrive preparado a mano es entrada
elegida por otro, leída por un proceso que corre como root.

**Una dependencia.** Cada aplicación del escritorio arrastra un árbol de
paquetes de Rust y de JavaScript que nadie de este proyecto escribió.

## Qué hace cumplir hoy

**AppArmor, y es lo único que de verdad bloquea.** Es independiente de cómo se
lance el programa: no hay forma de saltearlo abriendo la aplicación de otra
manera. El perfil de los AppImage niega **14 rutas** de credenciales —las claves,
el llavero, los tokens y los sockets de los agentes—, con `rwkl` y no `rwk`: sin
la `l` se puede crear un enlace duro desde afuera del directorio negado y leer
por ahí, y la valla queda en decorado.

Eso vino de una medición, no de una sospecha: con `file,` y `network,` —que el
perfil necesita— un AppImage podía leer `~/.ssh/id_ed25519` y mandarlo a donde
quisiera, y esa clave normalmente no tiene frase de paso.

**Todo lo que se bloquea se puede desbloquear**, desde el aviso o desde
Configuración. Es una regla del proyecto y no un detalle: un bloqueo sin salida
termina en alguien desactivando el mecanismo entero.

**Y el aviso llega.** Las denegaciones se leen del socket de auditoría del
kernel además del registro, porque el registro tiene cupo y descartaba el 96% —
medido: 42410 registros tirados contra 1672 que pasaban, en dos horas.

**Las decisiones se guardan contra el programa**, no contra la ventana que
preguntó, y quien pregunta se identifica por el ejecutable detrás de su pid.

## Contra qué **no** protege todavía

Cuatro cosas, abiertas y numeradas.

**Capturar la pantalla sin pasar por el portal.** El diálogo pregunta, pero un
cliente de Wayland no está obligado a usar el portal: puede hablarle al
compositor directo. Medido: un cliente supuestamente aislado sacó 313899 bytes
con `grim` y leyó 84822 bytes del portapapeles.
([vasak-permissions#27](https://github.com/Vasak-OS/vasak-permissions/issues/27))

**Cámara y micrófono por PipeWire.** El permiso se pregunta y se anota, y un
programa puede pedirle el nodo a PipeWire igual.
([vasak-desktop-settings#3](https://github.com/Vasak-OS/vasak-desktop-settings/issues/3))

**La mayoría de los perfiles del sistema están en modo aviso.** De los ~1048
instalados, sólo tres bloquean de verdad; el resto anota lo que habría impedido.
Son perfiles escritos afuera que nunca corrieron en VasakOS, y uno mal ajustado
no se ve como seguridad sino como un programa que dejó de andar. Ampliar la
tanda necesita una semana de diario primero.
([vasak-desktop-settings#2](https://github.com/Vasak-OS/vasak-desktop-settings/issues/2))

**El arranque no está firmado.** Hoy se instala con Secure Boot desactivado, lo
que deja fuera del alcance las manipulaciones previas al arranque.
([archiso#6](https://github.com/Vasak-OS/archiso/issues/6))

## Lo que este modelo deja explícitamente afuera

**Un atacante con root.** Nada de esto sobrevive a eso, y no pretende.

**El hardware y el firmware.** Sin Secure Boot no hay nada que decir sobre el
arranque; con él, tampoco cubriríamos el firmware.

**La persona que decide mal.** Si alguien le concede las credenciales a un
programa hostil desde el diálogo, el sistema hizo su trabajo: preguntó. Lo que
sí es responsabilidad nuestra es que la pregunta diga la verdad sobre **qué**
programa está pidiendo.

**El software que empaquetamos sin escribir** —el kernel, systemd, wayfire, los
paquetes de Arch—. Sus fallas van a su proyecto de origen. Sí es nuestra
responsabilidad **cómo lo configuramos**: una opción que debilita un componente
ajeno es problema de VasakOS.

## Cómo se sostiene

**Los analizadores que leen entrada elegida por otro tienen pruebas de
propiedad**, corriendo en cada push: el registro del kernel, el sondeo de discos
del instalador y el protocolo del teléfono.

**Las dependencias están fijadas.** Todo paquete se compila con `--locked`, así
que dos compilaciones del mismo commit dan el mismo binario — que es lo que hay
que poder afirmar cuando aparece una vulnerabilidad en una dependencia.

**Y hay comprobación automática en los 29 repositorios con código**, que hasta
hace poco no existía en ninguno.

## Qué falta de este documento

El proceso de CVE, que depende de tener por dónde avisar: hoy un arreglo de
seguridad llega cuando la persona se acuerda de actualizar. Está en
[website#5](https://github.com/Vasak-OS/website/issues/5) junto con el
notificador.
