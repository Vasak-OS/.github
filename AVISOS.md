# Proceso de aviso de seguridad

Qué pasa entre que un reporte se confirma y que la persona que ya instaló
VasakOS está a salvo. La [política de seguridad](SECURITY.md) dice cómo
reportar; esto dice qué hacemos después.

Es corto a propósito. Un proceso que nadie va a poder seguir bajo presión —que
es cuando se usa— no es un proceso.

## Los cinco pasos

**1. Confirmar y medir el alcance.** Qué versiones, qué hace falta para
explotarlo, y si es nuestro. Si el problema está en software que empaquetamos
sin escribir, va a su proyecto de origen y lo derivamos; lo que sí es nuestro es
**cómo lo configuramos**.

**2. Arreglar y publicar el paquete.** El arreglo sale como una actualización
normal, con el número de versión subido. VasakOS es rolling: no hay rama vieja
que parchear.

**3. Pedir el identificador, si corresponde.** Ver más abajo cuándo sí y cuándo
no.

**4. Publicar el aviso.** Con el paquete ya en el repositorio, nunca antes: un
aviso que describe el problema mientras el arreglo no llegó le da el mapa a
quien no lo tenía.

**5. Avisar.** `vasak-update` comprueba todos los días y al iniciar sesión, así
que un equipo encendido se entera dentro de las veinticuatro horas. Uno que
estuvo apagado, al encenderse: el temporizador es `Persistent=true`.

## Cuándo se pide un CVE, y cuándo no

**Sí**, cuando el problema está en código que escribimos nosotros y alguien lo
puede sufrir sin ser quien lo instaló. En la práctica: `vasak-keyring`,
`vasak-permissions`, `polkit-vasak`, `vasak-installer`, `vasak-connect`, los
perfiles de AppArmor y las recetas de `PKGBUILDS`.

**No**, en tres casos:

- **El problema es de un paquete de Arch o de un proyecto de origen.** Ese CVE
  lo pide quien lo mantiene. Nosotros publicamos, si hace falta, qué versión
  nuestra lo trae arreglado.
- **Es un endurecimiento y no una falla.** Cerrar una puerta que estaba abierta
  a la vista y documentada —las tres que la política enumera— no es un CVE.
  Pedir uno por cada mejora hace que los de verdad se pierdan entre el ruido.
- **No hay versión publicada afectada.** Si se encontró y se arregló antes de
  que el paquete saliera, no hay nadie a quien avisar.

## Quién lo pide, y cómo

Lo pide quien mantiene el repositorio, por **GitHub**, que es CNA y puede
asignar identificadores para repositorios que aloja.

En el repositorio afectado: pestaña **Security** → **Advisories** → **New draft
security advisory**. En el borrador está el botón **Request CVE**. GitHub lo
asigna y, al publicar, el aviso entra en su base de datos.

Se pide sobre el **borrador**, antes de publicar, no después: el identificador
tiene que estar en el aviso cuando el aviso sale.

Si GitHub no puede asignarlo —pasa cuando el problema no cae dentro de un
repositorio, por ejemplo algo que sólo existe en la imagen instalada—, se pide a
MITRE por su formulario. Es más lento y por eso es el segundo camino, no el
primero.

## Qué dice un aviso

Cinco cosas, y ninguna de más:

| | |
|---|---|
| Qué pasa | En una frase, sin eufemismos |
| A quién le pasa | Paquete y rango de versiones afectadas |
| Desde qué versión está arreglado | El `pkgver-pkgrel` exacto |
| Qué hacer si no se puede actualizar ya | Si hay algo; si no hay, se dice que no hay |
| Quién lo encontró | Con el nombre que pidió, o sin nombre si lo prefirió |

Lo que **no** lleva: un exploit, ni el detalle suficiente para escribir uno, en
los primeros siete días desde que el paquete salió. Después sí — el detalle
técnico es lo que permite que otros proyectos revisen si les pasa lo mismo.

## Cómo se entera quien ya instaló

Hoy, por `vasak-update`. Comprueba a los dos minutos de iniciar sesión y después
una vez por día, con hasta una hora de demora al azar para no pegarle todos los
equipos al mismo espejo en el mismo segundo. Si el equipo estuvo apagado cuando
tocaba, comprueba al encenderse.

O sea que el arreglo llega. Lo que **todavía no** pasa es que se distinga de una
actualización cualquiera.

### El agujero, dicho con todas las letras

`vasak-update` avisa «hay 14 actualizaciones». No puede decir «una de estas
tapa un agujero por el que alguien te lee el llavero», porque no tiene de dónde
saberlo: la base de paquetes de pacman no tiene ningún campo de seguridad, y
este programa no hace una sola llamada de red a propósito — pregunta con
`checkupdates`, que trabaja sobre una copia local.

Las consecuencias son dos, y conviene tenerlas escritas:

- Quien pospone las actualizaciones pospone también las de seguridad, sin saber
  que son distintas.
- Las reglas de insistencia del aviso no se pueden ajustar por gravedad. Hoy
  insiste cuando cambia el kernel o cuando pasaron siete días; un arreglo de
  seguridad merece insistir y no tiene cómo pedirlo.

**Lo que lo cierra**, cuando se haga: publicar en el repositorio de paquetes un
archivo de avisos firmado —paquete, versiones afectadas, versión que arregla,
identificador— y que lo lea la tienda, que es la que va a aplicar
actualizaciones. Ahí el dato ya está del lado del cliente y el notificador puede
marcar cuál es cuál.

No se hizo todavía porque meterle una descarga de red a `vasak-update` es
agrandar la superficie del programa que corre todos los días en cada equipo,
para resolver medio problema: seguiría sin poder aplicar nada. Va con la tienda,
que es donde el resto de la respuesta vive.

Seguimiento en
[website#5](https://github.com/Vasak-OS/website/issues/5) y
[vasak-settings#45](https://github.com/Vasak-OS/vasak-settings/issues/45).

## Qué NO promete este proceso

- **No hay canal de seguridad aparte.** No hay lista de correo ni feed de
  avisos: están en GitHub y llegan como una actualización más.
- **No hay parche para versiones viejas.** Rolling: el arreglo es actualizar.
- **No hay plazo de arreglo garantizado.** Hay plazo de respuesta —72 horas
  hábiles para el acuse, 7 días para el diagnóstico— y eso sí se sostiene.
  Prometer una fecha de arreglo sin saber qué es sería prometer lo que no se
  puede.
