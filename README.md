# SHADOW

## Descripción

**SHADOW** es un juego 2D de plataformas y puzzles desarrollado en Python 3 utilizando Pygame.

La mecánica principal del juego consiste en que el jugador tiene una sombra que **reproduce los movimientos que el jugador realizó unos segundos antes**.

La sombra no es un enemigo y no persigue ni elimina al jugador. Es una parte fundamental de los puzzles y debe utilizarse para avanzar por los niveles.

> **Tu sombra es parte de la solución.**

---

## Mecánica principal

El jugador controla al personaje normalmente.

Todos sus movimientos se van registrando y, aproximadamente **3 segundos después**, la sombra reproduce esos mismos movimientos.

Esto permite crear situaciones en las que:

- El jugador activa un interruptor.
- La sombra repite el recorrido anterior.
- La sombra puede activar otro interruptor.
- Se pueden abrir puertas.
- Se pueden activar plataformas.
- Se pueden utilizar caminos alternativos.
- El jugador debe pensar sus movimientos antes de realizarlos.

La sombra no tiene inteligencia artificial para perseguir al jugador.

No puede:

- Cambiar de dirección por su cuenta.
- Teletransportarse.
- Acelerar artificialmente.
- Elegir caminos.
- Atacar.
- Matar al jugador.

Simplemente reproduce los movimientos registrados del jugador.

---

## Objetivo de los niveles

Cada nivel contiene:

- Jugador.
- Sombra.
- 3 estrellas obligatorias.
- Plataformas.
- Obstáculos.
- Interruptores o palancas.
- Puertas.
- Plataformas móviles.
- Caminos alternativos.
- Una puerta de salida.

El jugador debe conseguir las **3 estrellas** del nivel.

Cuando consigue una estrella:

- La estrella desaparece.
- Se muestra una pequeña animación.
- El contador del HUD aumenta.

La sombra no puede recoger estrellas.

---

## Puerta final

La puerta final comienza bloqueada.

Cuando el jugador consigue las 3 estrellas:

**3/3**

la puerta se desbloquea mediante una pequeña animación.

Después de desbloquearla, el jugador debe llegar hasta la puerta para completar el nivel.

---

## Interruptores y mecanismos

Los interruptores pueden ser activados tanto por:

- El jugador.
- La sombra.

Dependiendo del nivel, un interruptor puede:

- Abrir una puerta.
- Activar una plataforma.
- Desactivar un obstáculo.
- Cambiar el recorrido disponible.

Los mecanismos deben estar relacionados con el diseño del nivel y tener una función clara.

---

## Dificultad

La dificultad aumenta progresivamente mediante el diseño de los niveles.

Los primeros niveles deben enseñar la mecánica de la sombra de manera sencilla.

Los niveles posteriores pueden incluir:

- Más interruptores.
- Caminos alternativos.
- Plataformas móviles.
- Mayor precisión.
- Secuencias de movimientos.
- Situaciones donde sea necesario planificar varios segundos antes.

La dificultad no debe aumentar haciendo que la sombra se mueva más rápido.

---

## Estilo visual

El juego utiliza un estilo:

- Oscuro.
- Minimalista.
- Limpio.
- Fácil de entender.

El jugador y la sombra deben diferenciarse claramente.

Se pueden utilizar:

- Partículas.
- Pequeñas animaciones.
- Efectos al recoger estrellas.
- Efectos al activar interruptores.
- Animaciones para las puertas.
- Transiciones entre pantallas.

No es obligatorio utilizar recursos externos. El juego puede utilizar formas básicas de Pygame.

---

## Controles

| Tecla | Acción |
|---|---|
| WASD / Flechas | Mover al jugador |
| R | Reiniciar nivel |
| ESC | Pausar |

---

## Pantallas

El juego debe contar con:

### Menú principal

Opciones:

- Jugar.
- Seleccionar nivel.
- Salir.

### Selección de nivel

Permite seleccionar los niveles desbloqueados.

### Juego

Muestra:

- Jugador.
- Sombra.
- Nivel.
- Estrellas conseguidas.
- Objetivo.
- Elementos interactivos.

### Pausa

Opciones:

- Continuar.
- Reiniciar.
- Volver al menú.

### Victoria

Se muestra cuando el jugador completa un nivel.

Debe permitir:

- Pasar al siguiente nivel.
- Repetir el nivel.
- Volver al menú.

---

## Estructura del proyecto

```text
SHADOW/
│
├── main.py
├── game.py
├── player.py
├── shadow.py
├── level.py
├── objects.py
│
├── levels/
│   ├── level1.py
│   ├── level2.py
│   └── ...
│
└── assets/
    ├── images/
    └── sounds/
```

La estructura puede modificarse si es necesario, siempre manteniendo el proyecto organizado.

---

## Tecnologías

- Python 3
- Pygame

No se requieren motores externos.

---

## Instalación

Instalar Pygame:

```bash
pip install pygame
```

Ejecutar el juego:

```bash
python main.py
```

---

## Diseño de los niveles

Los niveles deben estar diseñados de forma lógica.

Cada objeto debe tener una función.

No se deben colocar objetos simplemente para llenar espacio.

Los elementos tampoco deben superponerse sin una razón.

La posición de:

- Estrellas.
- Interruptores.
- Puertas.
- Plataformas.
- Obstáculos.
- Caminos.

debe formar parte del puzzle.

El jugador debe poder entender progresivamente qué debe hacer sin que el nivel sea completamente obvio.

---

## Progresión

La progresión recomendada es:

**Nivel 1**
- Presentación de la sombra.
- Movimiento básico.
- Una estrella.
- Un interruptor sencillo.

**Nivel 2**
- 3 estrellas.
- Primer uso real de la sombra para activar mecanismos.

**Nivel 3**
- Dos interruptores.
- Puertas.
- Caminos alternativos.

**Nivel 4 en adelante**
- Plataformas móviles.
- Secuencias de movimientos.
- Puzzles más complejos.
- Mayor necesidad de planificación.

---

## Guardado

El juego puede utilizar un archivo JSON para guardar el progreso del jugador.

Por ejemplo:

```json
{
    "nivel_actual": 1,
    "niveles_desbloqueados": 1,
    "estrellas": {}
}
```

El sistema de guardado puede almacenar:

- Nivel actual.
- Niveles desbloqueados.
- Estrellas conseguidas.
- Configuraciones necesarias.

---

## Objetivo del proyecto

El objetivo es crear un juego sencillo de entender, pero que utilice una mecánica diferente a un plataformas tradicional.

La sombra no debe ser simplemente una copia visual del personaje.

Debe ser una herramienta que el jugador necesite utilizar para resolver los puzzles y completar los niveles.
