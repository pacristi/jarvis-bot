# 🤖 JARVIS — Bot de Stats

Bot que trackea partidas de juegos + actividad de Discord, con personalidad tóxica estilo JARVIS de Iron Man.

## Personalidad

JARVIS británico, sarcástico, destructor de egos con datos. Elegante en la forma, brutal en el contenido.

> *"Sir, sus estadísticas en Pummel Party sugieren que debería considerar actividades que no requieran coordinación mano-ojo. Quizás la jardinería."*

---

## Arquitectura

```
┌─────────────────────────────────────────┐
│              Gateways                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │ Discord │  │WhatsApp │  │  ???    │ │
│  └────┬────┘  └────┬────┘  └────┬────┘ │
└───────┼────────────┼────────────┼──────┘
        │            │            │
        ▼            ▼            ▼
┌─────────────────────────────────────────┐
│            Core JARVIS                  │
│  ┌──────────────────────────────────────┐  │
│  │     Message Router / Handler      │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ Commands │ │  Stats   │ │ Roasts │  │
│  └──────────┘ └──────────┘ └────────┘  │
└─────────────────────────────────────────┘
        │            │
        ▼            ▼
┌──────────────┐ ┌─────────────────────┐
│   SQLite     │ │   LLM Provider      │
│              │ │  ┌───────┬───────┐  │
│              │ │  │OpenAI │Claude │  │
│              │ │  └───────┴───────┘  │
└──────────────┘ └─────────────────────┘
```

### Principios

- **Gateway agnóstico:** El core no sabe si es Discord, WhatsApp u otro
- **LLM agnóstico:** Soporta OpenAI y Anthropic via config
- **Type safety:** Pydantic + type hints en todo el código
- **Schema flexible:** Soporta cualquier juego sin hardcodear

---

## Stack

- **Runtime:** Python 3.11+
- **DB:** SQLite (aiosqlite)
- **LLM:** OpenAI / Anthropic (configurable)
- **Gateway inicial:** Discord (discord.py)
- **Type safety:** Pydantic

---

## Schema de Base de Datos

```sql
-- Jugadores del server
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    discord_id TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Nicknames que usa en juegos (para matching de screenshots)
CREATE TABLE player_nicknames (
    id INTEGER PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    nickname TEXT NOT NULL,
    UNIQUE(player_id, nickname)
);

-- Cuentas externas (Riot, Steam, etc.)
CREATE TABLE linked_accounts (
    id INTEGER PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    platform TEXT NOT NULL,  -- "riot", "steam", "epic"
    game_id TEXT NOT NULL,
    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, platform)
);

-- Partidas (cualquier juego)
CREATE TABLE matches (
    id INTEGER PRIMARY KEY,
    game_name TEXT NOT NULL,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    screenshot_url TEXT,
    recorded_by INTEGER REFERENCES players(id)
);

-- Resultados por partida
CREATE TABLE results (
    id INTEGER PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    player_id INTEGER REFERENCES players(id),
    position INTEGER NOT NULL,
    score INTEGER,
    extra_data TEXT,  -- JSON para stats específicos del juego
    UNIQUE(match_id, player_id)
);
```

---

## Configuración

```yaml
# config.yaml
llm:
  provider: "openai"  # o "anthropic"
  model: "gpt-4o-mini"  # o "claude-3-5-haiku-20241022"

gateways:
  discord:
    enabled: true

database:
  path: "jarvis.db"
```

Variables de entorno:
- `LLM_API_KEY` - API key de OpenAI o Anthropic
- `DISCORD_TOKEN` - Token del bot de Discord

---

## Interfaces Abstractas

```python
from abc import ABC, abstractmethod
from typing import Callable, Optional
from pydantic import BaseModel

class Message(BaseModel):
    channel_id: str
    author_id: str
    author_name: str
    content: str
    image_url: Optional[str] = None

class Gateway(ABC):
    @abstractmethod
    async def send(self, channel_id: str, message: str, buttons: Optional[list] = None) -> None:
        pass
    
    @abstractmethod
    async def on_message(self, handler: Callable) -> None:
        pass

class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict]) -> str:
        pass
    
    @abstractmethod
    async def vision(self, image_url: str, prompt: str) -> str:
        pass
```

---

## Fases de Desarrollo

### Fase 1 — Core (MVP) ✅
- [x] Estructura del proyecto + dependencias
- [x] Config loader (yaml + env vars)
- [x] SQLite schema + migrations
- [x] LLM provider abstraction (OpenAI + Anthropic)
- [x] Gateway abstraction + Discord implementation
- [x] `/partido` + screenshot → registra partida
- [x] `/ranking` → leaderboard
- [x] `/stats @user` → stats individuales
- [x] Comentario tóxico automático post-partida

### Fase 2 — Discord Tracking ✅
- [x] Track horas en voice
- [x] Stats de actividad del server
- [x] Combinar con stats de partidas para roasts

### Fase 3 — Integraciones Externas
- [ ] `/link riot [id]` — linkear cuenta
- [ ] Stats de LoL/Valorant via Riot API
- [ ] Roasts cross-plataforma

---

## Comandos

| Comando | Descripción |
|---------|-------------|
| `/partido` | Registrar partida (adjuntar screenshot) |
| `/ranking [juego]` | Leaderboard general o por juego |
| `/stats @usuario` | Stats individuales de un jugador |
| `/actividad [@usuario]` | Stats de mensajes en el servidor |
| `/voice [@usuario\|leaderboard]` | Stats de tiempo en voice channels |
| `/server` | Stats combinados del servidor completo |
| `/versus @uno @otro` | Head to head entre dos jugadores |
| `/racha` | Quién viene ganando/perdiendo |
| `/historial [n]` | Últimas n partidas |

---

## Ejemplo de Interacción

```
[Usuario sube screenshot de Pummel Party]

JARVIS: Procesando su... "rendimiento". 
        1° Juan, 2° Mati, 3° Piero. 
        ¿Correcto?
        
        ✅ Confirmar  ❌ Cancelar

[Usuario confirma]

JARVIS: Registrado. Piero, son 4 últimos lugares consecutivos. 
        Estadísticamente impresionante. La consistencia es una 
        virtud, aunque no en su caso.
```

---

## Estructura del Proyecto

```
jarvis-bot/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── repository.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── openai.py
│   │   └── anthropic.py
│   ├── gateways/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── discord.py
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── partido.py
│   │   ├── ranking.py
│   │   └── stats.py
│   └── services/
│       ├── __init__.py
│       ├── match_parser.py
│       └── roast_generator.py
├── tests/
├── config.yaml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Development Guidelines

- **Commits:** Conventional commits, un feature por commit
- **Types:** Pydantic models + type hints everywhere
- **Async:** Todo async (aiosqlite, aiohttp, etc.)
- **Tests:** Pytest para lógica core
