"""
Sistema de almacenamiento persistente usando SQLite
Guarda perfiles de usuario, recordatorios y conversaciones
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import os

class PersistentStorage:
    """
    Gestiona almacenamiento persistente en SQLite
    Permite que los datos sobrevivan reinicios del servidor
    """
    
    def __init__(self, db_path: str = "data/ecko.db"):
        """
        Inicializar base de datos
        db_path: Ruta al archivo de base de datos SQLite
        """
        # Crear directorio si no existe
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
        self._create_tables()
        
        print(f"[OK] Almacenamiento persistente inicializado: {db_path}")
    
    def _create_tables(self):
        """Crear tablas si no existen"""
        cursor = self.conn.cursor()
        
        # Tabla de perfiles de usuario
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                session_id TEXT PRIMARY KEY,
                name TEXT,
                preferred_title TEXT,
                birthday TEXT,
                preferences TEXT,  -- JSON string
                learned_info TEXT,  -- JSON string
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Tabla de recordatorios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                message TEXT NOT NULL,
                target_datetime TEXT,
                time_str TEXT,
                recurrence TEXT,  -- JSON string
                active INTEGER DEFAULT 1,
                created_at TEXT,
                FOREIGN KEY (session_id) REFERENCES user_profiles(session_id)
            )
        """)
        
        # Tabla de notificaciones pendientes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_notifications (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                reminder_id TEXT,
                message TEXT NOT NULL,
                timestamp TEXT,
                read INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES user_profiles(session_id),
                FOREIGN KEY (reminder_id) REFERENCES reminders(id)
            )
        """)
        
        # Tabla de conversaciones (para historial persistente)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT,
                FOREIGN KEY (session_id) REFERENCES user_profiles(session_id)
            )
        """)
        
        # Tabla de sesiones (para identificar sesiones activas)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT,
                last_activity TEXT,
                user_agent TEXT
            )
        """)
        
        # Tabla de notas (sistema de notas tipo Jarvis)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (session_id) REFERENCES user_profiles(session_id)
            )
        """)
        
        # Índices para mejor performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_session ON reminders(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_active ON reminders(active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_session ON pending_notifications(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_read ON pending_notifications(read)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_session ON notes(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title)")
        
        self.conn.commit()
        print("[OK] Tablas de base de datos creadas/verificadas")
    
    # ========== PERFILES DE USUARIO ==========
    
    def save_user_profile(self, session_id: str, profile_data: Dict):
        """Guardar o actualizar perfil de usuario"""
        cursor = self.conn.cursor()
        
        # Convertir dicts a JSON strings
        preferences = json.dumps(profile_data.get("preferences", {}))
        learned_info = json.dumps(profile_data.get("learned_info", {}))
        
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_profiles 
            (session_id, name, preferred_title, birthday, preferences, learned_info, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 
                    COALESCE((SELECT created_at FROM user_profiles WHERE session_id = ?), ?),
                    ?)
        """, (
            session_id,
            profile_data.get("name"),
            profile_data.get("preferred_title"),
            profile_data.get("birthday"),
            preferences,
            learned_info,
            session_id,
            now,
            now
        ))
        
        self.conn.commit()
    
    def get_user_profile(self, session_id: str) -> Optional[Dict]:
        """Obtener perfil de usuario"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM user_profiles WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        profile = dict(row)
        # Convertir JSON strings de vuelta a dicts
        profile["preferences"] = json.loads(profile["preferences"] or "{}")
        profile["learned_info"] = json.loads(profile["learned_info"] or "{}")
        return profile
    
    def update_user_preference(self, session_id: str, key: str, value):
        """Actualizar una preferencia específica del usuario"""
        profile = self.get_user_profile(session_id) or {}
        preferences = profile.get("preferences", {})
        preferences[key] = value
        
        if not profile.get("session_id"):
            profile["session_id"] = session_id
        
        profile["preferences"] = preferences
        self.save_user_profile(session_id, profile)
    
    # ========== RECORDATORIOS ==========
    
    def save_reminder(self, reminder_data: Dict):
        """Guardar recordatorio"""
        cursor = self.conn.cursor()
        
        recurrence = json.dumps(reminder_data.get("recurrence")) if reminder_data.get("recurrence") else None
        
        cursor.execute("""
            INSERT OR REPLACE INTO reminders 
            (id, session_id, message, target_datetime, time_str, recurrence, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reminder_data["id"],
            reminder_data["session_id"],
            reminder_data["message"],
            reminder_data.get("target_datetime"),
            reminder_data.get("time_str"),
            recurrence,
            1 if reminder_data.get("active", True) else 0,
            reminder_data.get("created_at", datetime.now().isoformat())
        ))
        
        self.conn.commit()
    
    def get_reminders(self, session_id: str, active_only: bool = True) -> List[Dict]:
        """Obtener recordatorios de una sesión"""
        cursor = self.conn.cursor()
        
        if active_only:
            cursor.execute("""
                SELECT * FROM reminders 
                WHERE session_id = ? AND active = 1
                ORDER BY target_datetime ASC
            """, (session_id,))
        else:
            cursor.execute("""
                SELECT * FROM reminders 
                WHERE session_id = ?
                ORDER BY target_datetime ASC
            """, (session_id,))
        
        rows = cursor.fetchall()
        reminders = []
        
        for row in rows:
            reminder = dict(row)
            reminder["active"] = bool(reminder["active"])
            if reminder.get("recurrence"):
                reminder["recurrence"] = json.loads(reminder["recurrence"])
            reminders.append(reminder)
        
        return reminders
    
    def update_reminder_active(self, reminder_id: str, active: bool):
        """Actualizar estado activo de un recordatorio"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE reminders SET active = ? WHERE id = ?", (1 if active else 0, reminder_id))
        self.conn.commit()
    
    def delete_reminder(self, reminder_id: str):
        """Eliminar recordatorio"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        self.conn.commit()
    
    def get_all_active_reminders(self) -> List[Dict]:
        """Obtener todos los recordatorios activos (para scheduler)"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM reminders WHERE active = 1")
        rows = cursor.fetchall()
        
        reminders = []
        for row in rows:
            reminder = dict(row)
            reminder["active"] = True
            if reminder.get("recurrence"):
                reminder["recurrence"] = json.loads(reminder["recurrence"])
            reminders.append(reminder)
        
        return reminders
    
    # ========== NOTIFICACIONES ==========
    
    def save_notification(self, notification_data: Dict):
        """Guardar notificación pendiente"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO pending_notifications 
            (id, session_id, reminder_id, message, timestamp, read)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (
            notification_data["id"],
            notification_data["session_id"],
            notification_data.get("reminder_id"),
            notification_data["message"],
            notification_data.get("timestamp", datetime.now().isoformat())
        ))
        
        self.conn.commit()
    
    def get_pending_notifications(self, session_id: str, read: bool = False) -> List[Dict]:
        """Obtener notificaciones pendientes"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM pending_notifications 
            WHERE session_id = ? AND read = ?
            ORDER BY timestamp ASC
        """, (session_id, 1 if read else 0))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def mark_notifications_read(self, session_id: str):
        """Marcar notificaciones como leídas"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE pending_notifications SET read = 1 WHERE session_id = ?", (session_id,))
        self.conn.commit()
    
    def delete_old_notifications(self, days: int = 7):
        """Eliminar notificaciones antiguas"""
        cursor = self.conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("DELETE FROM pending_notifications WHERE timestamp < ?", (cutoff_date,))
        self.conn.commit()
    
    # ========== SESIONES Y CONVERSACIONES ==========
    
    def create_session(self, session_id: str = None, user_agent: str = None) -> str:
        """Crear o registrar una sesión"""
        import uuid
        if not session_id:
            session_id = str(uuid.uuid4())
        
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO sessions (session_id, created_at, last_activity, user_agent)
            VALUES (?, 
                    COALESCE((SELECT created_at FROM sessions WHERE session_id = ?), ?),
                    ?, ?)
        """, (session_id, session_id, now, now, user_agent))
        
        self.conn.commit()
        return session_id
    
    def add_conversation_message(self, session_id: str, role: str, content: str):
        """Agregar mensaje a la conversación"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO conversations (session_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        """, (session_id, role, content, now))
        
        # Actualizar última actividad de la sesión
        cursor.execute("""
            UPDATE sessions SET last_activity = ? WHERE session_id = ?
        """, (now, session_id))
        
        self.conn.commit()
    
    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Obtener historial de conversación"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT role, content, timestamp 
            FROM conversations 
            WHERE session_id = ? 
            ORDER BY timestamp ASC
            LIMIT ?
        """, (session_id, limit))
        
        rows = cursor.fetchall()
        return [
            {
                "role": row[0],
                "content": row[1],
                "timestamp": row[2]
            }
            for row in rows
        ]
    
    def clear_conversation(self, session_id: str):
        """Limpiar historial de conversación de una sesión"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        self.conn.commit()
    
    def session_exists(self, session_id: str) -> bool:
        """Verificar si una sesión existe"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,))
        return cursor.fetchone() is not None
    
    # ========== NOTAS ==========
    
    def save_note(self, note_data: Dict):
        """Guardar o actualizar una nota"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO notes 
            (id, session_id, title, content, created_at, updated_at)
            VALUES (?, ?, ?, ?, 
                    COALESCE((SELECT created_at FROM notes WHERE id = ?), ?),
                    ?)
        """, (
            note_data["id"],
            note_data["session_id"],
            note_data["title"],
            note_data["content"],
            note_data["id"],
            now,
            now
        ))
        
        self.conn.commit()
    
    def get_note(self, session_id: str, note_id: str) -> Optional[Dict]:
        """Obtener una nota específica"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM notes 
            WHERE id = ? AND session_id = ?
        """, (note_id, session_id))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return dict(row)
    
    def get_note_by_title(self, session_id: str, title: str) -> Optional[Dict]:
        """Obtener una nota por título (case-insensitive)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM notes 
            WHERE session_id = ? AND LOWER(title) = LOWER(?)
            ORDER BY updated_at DESC
            LIMIT 1
        """, (session_id, title))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return dict(row)
    
    def get_all_notes(self, session_id: str) -> List[Dict]:
        """Obtener todas las notas de una sesión"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM notes 
            WHERE session_id = ?
            ORDER BY updated_at DESC
        """, (session_id,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def delete_note(self, session_id: str, note_id: str) -> bool:
        """Eliminar una nota"""
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM notes 
            WHERE id = ? AND session_id = ?
        """, (note_id, session_id))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def close(self):
        """Cerrar conexión a la base de datos"""
        if self.conn:
            self.conn.close()

# Singleton global
_storage_instance = None

def get_storage() -> PersistentStorage:
    """Obtener instancia singleton de almacenamiento"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = PersistentStorage()
    return _storage_instance

