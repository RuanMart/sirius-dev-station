"""Agentic OS / Sirius Dev Station — Persistent Memory with SQLite FTS5

Full-text search across Sirius .context files, BMAD skills, journal, and prompts.
Auto-indexes text content on startup and provides search + knowledge graph extraction.
"""
import json
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.resolve()
load_dotenv(BASE_DIR.parent / ".env")

SIRIUS_ROOT_ENV = os.environ.get("SIRIUS_ROOT")
if SIRIUS_ROOT_ENV:
    SIRIUS_ROOT = Path(SIRIUS_ROOT_ENV).resolve()
else:
    sibling = (BASE_DIR.parent.parent / "sirius").resolve()
    SIRIUS_ROOT = sibling if sibling.exists() else BASE_DIR.parent

SIRIUS_CONTEXT = SIRIUS_ROOT / ".context"
SIRIUS_SKILLS = SIRIUS_ROOT / ".agents" / "skills"

DB_PATH = BASE_DIR.parent / "data" / "memory.db"

_local = threading.local()

def _get_db():
    if not hasattr(_local, "conn") or _local.conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _local.conn = sqlite3.connect(str(DB_PATH))
        _local.conn.row_factory = sqlite3.Row
    return _local.conn

def init_db():
    conn = _get_db()
    conn.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
            id, source, path, title, content, category,
            tokenize='porter unicode61'
        );
        CREATE TABLE IF NOT EXISTS memory_meta (
            id TEXT PRIMARY KEY,
            source TEXT,
            path TEXT,
            title TEXT,
            category TEXT,
            created TEXT,
            updated TEXT
        );
        CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY,
            name TEXT,
            type TEXT,
            context TEXT,
            source TEXT,
            created TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_meta_source ON memory_meta(source);
        CREATE INDEX IF NOT EXISTS idx_meta_category ON memory_meta(category);
        CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
    """)
    conn.commit()

def index_text(source: str, path: str, title: str, content: str, category: str = "general"):
    conn = _get_db()
    doc_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO memory_meta (id, source, path, title, category, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (doc_id, source, path, title, category, now, now)
    )
    conn.execute(
        "INSERT INTO memory_fts (id, source, path, title, content, category) VALUES (?, ?, ?, ?, ?, ?)",
        (doc_id, source, path, title, content, category)
    )
    conn.commit()
    return doc_id

def search(query: str, limit: int = 20) -> list:
    conn = _get_db()
    if not query.strip():
        return []
    try:
        rows = conn.execute(
            "SELECT m.id, m.source, m.path, m.title, m.category, m.created, "
            "snippet(memory_fts, 4, '<mark>', '</mark>', '...', 32) as snippet "
            "FROM memory_fts JOIN memory_meta m ON memory_fts.id = m.id "
            "WHERE memory_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit)
        ).fetchall()
    except Exception:
        return []
    return [dict(r) for r in rows]

def build_graph() -> dict:
    """Build a knowledge graph from the FTS5 index + entity table.

    Nodes: Sirius .context documents, BMAD skills, journal entries, extracted entities.
    Edges: document->entity co-occurrence, cross-references.
    """
    conn = _get_db()
    nodes, edges = [], []
    node_ids, edge_keys = set(), set()

    # Document nodes (from memory_meta)
    rows = conn.execute(
        "SELECT id, source, path, title, category FROM memory_meta"
    ).fetchall()
    doc_by_id = {}
    for r in rows:
        node = {
            "id": r["id"],
            "label": r["title"] or r["path"],
            "type": r["category"] or r["source"],
            "path": r["path"],
            "source": r["source"],
        }
        nodes.append(node)
        node_ids.add(r["id"])
        doc_by_id[r["id"]] = r["path"]

    # Entity nodes
    ents = conn.execute(
        "SELECT DISTINCT name, type, source FROM entities LIMIT 200"
    ).fetchall()
    entity_ids = set()
    for e in ents:
        nid = f"ent:{e['name']}:{e['type']}"
        if nid in entity_ids:
            continue
        entity_ids.add(nid)
        nodes.append({
            "id": nid,
            "label": e["name"],
            "type": f"entity:{e['type']}",
            "path": "",
            "source": e["source"] or "auto",
        })

    # Edges: document <-> entity co-occurrence
    edge_rows = conn.execute(
        "SELECT source, name, type FROM entities LIMIT 500"
    ).fetchall()
    for e in edge_rows:
        target_id = f"ent:{e['name']}:{e['type']}"
        for doc_id, path in doc_by_id.items():
            if e["source"] and (e["source"] in path or path in e["source"]):
                edge_key = f"{doc_id}->{target_id}"
                if edge_key not in edge_keys:
                    edge_keys.add(edge_key)
                    edges.append({
                        "source": doc_id,
                        "target": target_id,
                        "type": "mentions",
                        "weight": 1,
                    })

    # Category clustering edges (connect documents in same category, e.g. architecture)
    cat_docs = {}
    for r in rows:
        cat_docs.setdefault(r["category"], []).append(r["id"])
    for cat, ids in cat_docs.items():
        if len(ids) > 1 and cat in ("architecture", "business-rule", "decision", "feature"):
            for i in range(len(ids) - 1):
                edge_key = f"{ids[i]}<->{ids[i+1]}"
                if edge_key not in edge_keys:
                    edge_keys.add(edge_key)
                    edges.append({
                        "source": ids[i],
                        "target": ids[i+1],
                        "type": "same_category",
                        "weight": 0.5,
                    })

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "nodes": len(nodes),
            "edges": len(edges),
            "documents": len(rows),
            "entities": len(entity_ids),
        },
    }

def index_brain_files():
    # 1. Index Sirius .context documents
    if SIRIUS_CONTEXT.exists():
        for cat in ["architecture", "business-rule", "decision", "feature", "component"]:
            cat_dir = SIRIUS_CONTEXT / cat
            if cat_dir.exists():
                for f in sorted(cat_dir.glob("*.md")):
                    content = f.read_text(encoding="utf-8", errors="replace")
                    title = f.stem.replace("-", " ").replace("_", " ").title()
                    for line in content.splitlines():
                        if line.startswith("title:"):
                            title = line.split("title:", 1)[1].strip().strip('"\'')
                            break
                        elif line.startswith("# "):
                            title = line[2:].strip()
                            break
                    rel_path = f".context/{cat}/{f.name}"
                    index_text("sirius-context", rel_path, title, content, cat)
    
    # 2. Local brain documents
    brain_dir = BASE_DIR
    for f in sorted(brain_dir.glob("*.md")):
        content = f.read_text(encoding="utf-8", errors="replace")
        title = f.stem.replace("-", " ").replace("_", " ").title()
        index_text("brain", f"brain/{f.name}", title, content, "brain")

def index_skills():
    # Index Sirius BMAD skills
    if SIRIUS_SKILLS.exists():
        for d in sorted(SIRIUS_SKILLS.iterdir()):
            if d.is_dir() and not d.name.startswith(("_", ".")):
                skill_md = d / "SKILL.md"
                if skill_md.exists():
                    content = skill_md.read_text(encoding="utf-8", errors="replace")
                    rel_path = f".agents/skills/{d.name}/SKILL.md"
                    index_text("sirius-skill", rel_path, f"Skill: {d.name}", content, "skill")
    else:
        # Fallback to local skills
        skills_dir = BASE_DIR.parent / "skills"
        if skills_dir.exists():
            for d in sorted(skills_dir.iterdir()):
                if d.is_dir() and not d.name.startswith(("_", ".")):
                    for f in d.glob("*.md"):
                        content = f.read_text(encoding="utf-8", errors="replace")
                        index_text("skill", str(f.relative_to(BASE_DIR.parent)), f"{d.name}/{f.stem}", content, "skill")

def index_journal():
    journal_dir = BASE_DIR / "journal"
    if journal_dir.exists():
        for f in sorted(journal_dir.glob("*.md")):
            content = f.read_text(encoding="utf-8", errors="replace")
            index_text("journal", str(f.relative_to(BASE_DIR.parent)), f"Journal {f.stem}", content, "journal")

def reindex_all():
    conn = _get_db()
    conn.executescript("DELETE FROM memory_fts; DELETE FROM memory_meta;")
    conn.commit()
    index_brain_files()
    index_skills()
    index_journal()

def extract_entities(text: str) -> list:
    entities = []
    patterns = [
        (r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', 'person'),
        (r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b', 'email'),
        (r'\bhttps?://[^\s<>"]+\b', 'url'),
        (r'\b[A-Z]{2,}\b', 'acronym'),
        (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', 'ip'),
    ]
    seen = set()
    for pattern, etype in patterns:
        for match in re.finditer(pattern, text):
            value = match.group()
            if value not in seen:
                seen.add(value)
                entities.append({"value": value, "type": etype})
    return entities

def save_entities(entities: list, source: str = "auto"):
    conn = _get_db()
    now = datetime.now(timezone.utc).isoformat()
    for ent in entities:
        eid = str(uuid.uuid4())[:8]
        conn.execute(
            "INSERT OR IGNORE INTO entities (id, name, type, context, source, created) VALUES (?, ?, ?, ?, ?, ?)",
            (eid, ent["value"], ent["type"], ent.get("context", ""), source, now)
        )
    conn.commit()

def get_entities(entity_type: str = "", limit: int = 50) -> list:
    conn = _get_db()
    if entity_type:
        rows = conn.execute(
            "SELECT DISTINCT name, type, COUNT(*) as count FROM entities WHERE type = ? GROUP BY name ORDER BY count DESC LIMIT ?",
            (entity_type, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT DISTINCT name, type, COUNT(*) as count FROM entities GROUP BY name ORDER BY count DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]

# Initialize and reindex if empty
init_db()
conn = _get_db()
row_count = conn.execute("SELECT COUNT(*) FROM memory_meta").fetchone()[0]
if row_count == 0:
    reindex_all()
