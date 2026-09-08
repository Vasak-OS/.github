<!--
Contá qué cambia y **por qué**, no qué archivos tocaste — eso ya está en el
diff. Si arregla algo, qué pasaba antes; si lo mediste, el número.
-->

## Qué cambia



<!--
Lo de abajo no es burocracia: cada línea está por una vez que faltó y costó.
Lo que no aplique, borralo.
-->

- [ ] **Versión subida**, si el paquete tiene que recompilarse. El script de
      publicación construye sólo lo que tiene versión distinta de la publicada,
      así que código mergeado sin subir la versión **no llega a nadie**. Son
      cuatro archivos: `package.json`, `Cargo.toml`, `tauri.conf.json` y el
      `pkgver` del PKGBUILD — y el `Cargo.lock`, que también anota la versión
      del propio paquete.
- [ ] **CHANGELOG actualizado**, en términos de qué gana o qué deja de sufrir
      quien usa el sistema.
- [ ] **Pruebas**. Si el repositorio tiene poca cobertura, sumá las vecinas.
- [ ] **Dependencias nuevas al PKGBUILD**, en el mismo momento. Una que falta no
      se nota compilando acá: se nota en un equipo limpio, ya instalado.
- [ ] **Textos traducidos**. Nada de cadenas escritas a mano en la interfaz.
- [ ] **Etiqueta y proyecto**: la etiqueta que corresponda y el proyecto
      «VasakOS Roadmap».

<!--
Si algo no pudiste probar —hace falta hardware, otra pantalla, un teléfono—,
decilo acá abajo en vez de dejarlo pasar. Se agradece más que un checkbox
marcado de más.
-->

## Sin probar

