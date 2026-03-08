# PyGPT Enhanced

> **Avatar Ready Player Me** + **MCP Memory Cloud (Firebase)**  
> Plugin suite for [PyGPT](https://github.com/szczyglis-dev/py-gpt) desktop AI assistant.

---

## Features

### 🎭 Avatar Ready Player Me
- 3D interactive avatar with **Ready Player Me** free tier
- **Lip-sync** reactive to audio output
- **Emotion detection** based on text sentiment (ES + EN)
- Idle animations (breathing, subtle rotation)
- Floating window, always-on-top, configurable size
- Uses PyGPT's built-in WebEngine (no extra overhead)

### 🧠 MCP Memory Cloud
- Persistent memory via **Firebase Firestore** (free tier)
- Semantic search with local embeddings (`all-MiniLM-L6-v2`)
- Tools: `remember_fact`, `semantic_recall`, `summarize_context`, `sync_devices`
- Multi-device sync
- Auto-remembers conversations in realtime

---

## Requirements

- PyGPT >= 2.7.0
- Python >= 3.10
- Firebase project (free tier is enough)

---

## Quick Install

```bash
git clone https://github.com/Phoenixai36/py-gpt
cd py-gpt
git checkout feature/avatar-rpm-mcp-memory
bash install.sh
```

---

## Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Create a new project (free Spark plan)
3. Enable **Firestore Database**
4. Go to Project Settings > Service Accounts > Generate new private key
5. Save the JSON file
6. Edit `mcp-memory-server/config.json`:

```json
{
  "firebase": {
    "project_id": "your-project-id",
    "credentials_path": "/path/to/serviceAccountKey.json"
  }
}
```

---

## Avatar Setup

1. Go to [Ready Player Me](https://demo.readyplayer.me/avatar)
2. Create your avatar
3. Copy the `.glb` URL
4. In PyGPT: **Plugins > Avatar RPM > Avatar URL**

---

## Plugin Configuration

### Avatar RPM
| Option | Description | Default |
|--------|-------------|------|
| `enabled` | Show avatar window | `false` |
| `avatar_url` | Ready Player Me .glb URL | `` |
| `window_width` | Window width in px | `300` |
| `window_height` | Window height in px | `450` |
| `always_on_top` | Keep above other windows | `true` |
| `lip_sync` | Sync mouth with audio | `true` |
| `emotion_detection` | Change expression by sentiment | `true` |

### MCP Memory Cloud
| Option | Description | Default |
|--------|-------------|------|
| `firebase_project_id` | Firebase project ID | `` |
| `firebase_credentials_path` | Path to service account JSON | `` |
| `user_id` | Memory namespace | `default` |
| `auto_remember` | Auto-save conversations | `true` |
| `semantic_search` | Use embeddings for recall | `true` |
| `embedding_model` | `local` / `openai` / `gemini` | `local` |
| `sync_mode` | `realtime` / `manual` / `on_exit` | `realtime` |

---

## Firestore Schema

```
/users/{user_id}/
  /memory/
    - content: string
    - category: preference|fact|skill|project|conversation
    - importance: float 0-1
    - tags: string[]
    - embedding: float[] (optional)
    - created_at: timestamp
  /conversations/
    - title: string
    - content: string
    - tags: string[]
    - timestamp: timestamp
  /devices/
    - hostname: string
    - platform: string
    - last_seen: timestamp
```

---

## MCP Tools Reference

### `remember_fact`
Save a fact or preference to long-term memory.
```json
{
  "content": "User prefers Ableton Live for music production",
  "category": "preference",
  "importance": 0.9,
  "tags": ["daw", "music", "production"]
}
```

### `semantic_recall`
Search memory using semantic similarity.
```json
{ "query": "what DAW does the user prefer?", "limit": 3 }
```

### `summarize_context`
Summarize recent conversations on a topic.
```json
{ "topic": "music production", "days_back": 7 }
```

### `sync_devices`
Sync state across devices.
```json
{ "device_id": "my-laptop", "push": true }
```

---

## Overhead

| Component | RAM | CPU idle | CPU active |
|-----------|-----|----------|------------|
| Avatar RPM | ~15 MB | <1% | ~4% |
| MCP Memory Server | ~50 MB (with embeddings) | <1% | ~2% |
| Firebase SDK | ~5 MB | <1% | <1% |

---

## License

MIT - Same as PyGPT core.
