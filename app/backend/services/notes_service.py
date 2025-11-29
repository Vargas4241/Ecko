"""
Servicio de gestión de notas
Permite crear, leer, actualizar y eliminar notas por voz
"""

import uuid
import re
from datetime import datetime
from typing import Dict, List, Optional

try:
    from services.persistent_storage import get_storage
    PERSISTENT_STORAGE_AVAILABLE = True
except ImportError:
    PERSISTENT_STORAGE_AVAILABLE = False
    print("[WARN] Almacenamiento persistente no disponible para NotesService")

class NotesService:
    """
    Gestiona las notas del usuario
    Permite operaciones tipo Jarvis: crear, leer, actualizar, eliminar
    """
    
    def __init__(self):
        self.use_persistence = PERSISTENT_STORAGE_AVAILABLE
        if self.use_persistence:
            try:
                self.storage = get_storage()
                print("[OK] NotesService usando almacenamiento persistente")
            except Exception as e:
                print(f"[WARN] Error inicializando persistencia: {e}")
                self.use_persistence = False
        else:
            print("[WARN] NotesService usando solo memoria (no persistente)")
            self.notes_cache: Dict[str, Dict[str, Dict]] = {}  # session_id -> {note_id -> note}
    
    def create_note(self, session_id: str, title: str, content: str = "") -> Dict:
        """Crear una nueva nota"""
        note_id = str(uuid.uuid4())
        note = {
            "id": note_id,
            "session_id": session_id,
            "title": title,
            "content": content,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        if self.use_persistence:
            self.storage.save_note(note)
        else:
            if session_id not in self.notes_cache:
                self.notes_cache[session_id] = {}
            self.notes_cache[session_id][note_id] = note
        
        return note
    
    def get_note(self, session_id: str, note_id: str) -> Optional[Dict]:
        """Obtener una nota por ID"""
        if self.use_persistence:
            return self.storage.get_note(session_id, note_id)
        else:
            return self.notes_cache.get(session_id, {}).get(note_id)
    
    def get_note_by_title(self, session_id: str, title: str) -> Optional[Dict]:
        """Obtener una nota por título"""
        if self.use_persistence:
            return self.storage.get_note_by_title(session_id, title)
        else:
            # Buscar en cache
            notes = self.notes_cache.get(session_id, {})
            for note in notes.values():
                if note["title"].lower() == title.lower():
                    return note
            return None
    
    def update_note(self, session_id: str, note_id: str, content: str = None, title: str = None) -> Optional[Dict]:
        """Actualizar una nota existente"""
        note = self.get_note(session_id, note_id)
        if not note:
            return None
        
        if content is not None:
            note["content"] = content
        if title is not None:
            note["title"] = title
        
        note["updated_at"] = datetime.now().isoformat()
        
        if self.use_persistence:
            self.storage.save_note(note)
        else:
            self.notes_cache[session_id][note_id] = note
        
        return note
    
    def append_to_note(self, session_id: str, note_id: str, text: str) -> Optional[Dict]:
        """Agregar texto al final de una nota"""
        note = self.get_note(session_id, note_id)
        if not note:
            return None
        
        current_content = note.get("content", "")
        separator = "\n" if current_content else ""
        note["content"] = current_content + separator + text
        note["updated_at"] = datetime.now().isoformat()
        
        if self.use_persistence:
            self.storage.save_note(note)
        else:
            self.notes_cache[session_id][note_id] = note
        
        return note
    
    def overwrite_note(self, session_id: str, note_id: str, content: str) -> Optional[Dict]:
        """Sobrescribir completamente el contenido de una nota"""
        return self.update_note(session_id, note_id, content=content)
    
    def delete_note(self, session_id: str, note_id: str) -> bool:
        """Eliminar una nota"""
        if self.use_persistence:
            return self.storage.delete_note(session_id, note_id)
        else:
            if session_id in self.notes_cache and note_id in self.notes_cache[session_id]:
                del self.notes_cache[session_id][note_id]
                return True
            return False
    
    def list_notes(self, session_id: str) -> List[Dict]:
        """Listar todas las notas de una sesión"""
        if self.use_persistence:
            return self.storage.get_all_notes(session_id)
        else:
            return list(self.notes_cache.get(session_id, {}).values())
    
    def parse_note_command(self, message: str) -> Dict:
        """
        Parsear comandos de notas desde el mensaje del usuario
        Retorna un dict con la acción y parámetros
        IMPORTANTE: El orden de evaluación importa - comandos más específicos primero
        """
        message_lower = message.lower().strip()
        
        # PRIORIDAD 1: Leer nota (antes de listar para evitar falsos positivos)
        read_patterns = [
            r"(?:dime|lee|muestra|muéstrame|qué\s+dice|que\s+dice|qué\s+hay\s+en|que\s+hay\s+en)\s+(?:la\s+)?nota\s+['\"]?([^'\"]+?)(?:['\"]|\s|$)",
            r"(?:la\s+)?nota\s+['\"]?([^'\"]+?)(?:['\"]|\s|$)(?:\s|$)(?!.*(?:agrega|sobrescribe|elimina|borra))",  # "la nota jarvis" (sin verbos de acción después)
            r"qué\s+dice\s+(?:la\s+)?nota\s+['\"]?([^'\"]+?)(?:['\"]|\s|$)",
            r"me\s+podés\s+decir\s+lo\s+que\s+dice\s+(?:adentro\s+)?(?:la\s+)?nota\s+['\"]?([^'\"]+?)(?:['\"]|\s|$)",
        ]
        
        for pattern in read_patterns:
            match = re.search(pattern, message_lower)
            if match:
                title = match.group(1).strip()
                # Verificar que no sea un comando de lista
                if "qué notas" not in message_lower and "que notas" not in message_lower:
                    return {"action": "read", "title": title}
        
        # PRIORIDAD 2: Sobrescribir nota (antes de crear para evitar conflictos)
        overwrite_patterns = [
            r"sobrescribe?\s+(?:la\s+)?nota\s+['\"]?([^'\"]+?)(?:['\"]|\s+)(?:con|que\s+diga|que\s+dice|pone|poner)?\s*(.+)",
            r"(?:reemplaza?|cambia?)\s+(?:la\s+)?nota\s+['\"]?([^'\"]+?)(?:['\"]|\s+)(?:por|con)?\s*(.+)",
        ]
        
        for pattern in overwrite_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Extraer todo después del título como contenido
                if len(match.groups()) >= 2:
                    content = match.group(2).strip()
                else:
                    # Si no capturó contenido, buscar después del match
                    match_end = message_lower.find(match.group(0)) + len(match.group(0))
                    content = message[match_end:].strip()
                return {"action": "overwrite", "title": title, "content": content}
        
        # PRIORIDAD 3: Crear nota (patrones más flexibles)
        create_keywords = ["crea", "crear", "creame", "inicia", "inició", "nueva", "abre", "abrir"]
        if any(keyword in message_lower for keyword in create_keywords) and "nota" in message_lower:
            # Buscar el nombre de la nota después de "nota" o "llame" o "llama" o "nombre"
            # Patrones flexibles para encontrar el nombre
            name_patterns = [
                r"nota\s+(?:que\s+se\s+llame|que\s+se\s+llama|nombre|llamada|llamado)\s+['\"]?([^'\"]+?)(?:['\"]|$|\s+y|\s+con|\s+que|\s+para)",
                r"nota\s+(?:nueva\s+)?(?:que\s+se\s+va\s+a\s+llamar|que\s+se\s+llama)\s+['\"]?([^'\"]+?)(?:['\"]|$|\s+y|\s+con|\s+que|\s+para)",
                r"nota\s+['\"]?([^'\"]+?)(?:['\"]|$)(?!.*(?:agrega|agregar|agregue|lee|leer|dime|muestra))",  # Si dice "nota X" sin verbos después
                r"(?:crea|crear|creame|nueva|abre|abrir)\s+(?:una\s+)?nota\s+(?:que\s+se\s+llame|nombre|llamada)\s+['\"]?([^'\"]+?)(?:['\"]|$|\s+y|\s+con|\s+que)",
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    title = match.group(1).strip()
                    # Limpiar palabras comunes del título
                    title = re.sub(r'\s*(y|con|que|para|diga|dice|agrega|agregar)\s*.*$', '', title, flags=re.IGNORECASE).strip()
                    
                    # Extraer contenido si hay algo después del título
                    match_end_pos = message_lower.find(match.group(0)) + len(match.group(0))
                    remaining = message[match_end_pos:].strip()
                    
                    # Si hay "y" o "con" después, puede ser contenido
                    content = ""
                    if " y " in remaining or " con " in remaining or " que " in remaining:
                        # Extraer después de estas palabras
                        content_match = re.search(r'(?:y|con|que|para)\s+(?:agrega|agregar|pon|poner)?\s*(.+)', remaining, re.IGNORECASE)
                        if content_match:
                            content = content_match.group(1).strip()
                    
                    # Limpiar palabras comunes
                    content = re.sub(r'^(?:que\s+)?(?:diga|dice|escriba|escribe|poner|pon)\s*', '', content, flags=re.IGNORECASE).strip()
                    
                    if title:
                        return {"action": "create", "title": title, "content": content}
        
        # PRIORIDAD 4: Agregar a nota (más flexible)
        append_keywords = ["agrega", "agregar", "agregue", "agregame", "añade", "añadir", "pon", "poner", "escribe", "escribir"]
        if any(keyword in message_lower for keyword in append_keywords) and "nota" in message_lower:
            # Patrones para encontrar la nota y el contenido
            append_patterns = [
                r"(?:agrega|agregar|agregue|pon|poner|escribe|escribir)\s+(?:a\s+)?(?:la\s+)?nota\s+['\"]?([^'\"]+?)(?:['\"]|\s+)(?:que\s+)?(?:diga|dice|escriba|escribe|poner|pon)?\s*(.+)",
                r"(?:agrega|agregar|pon|poner|escribe)\s+(.+?)\s+(?:a\s+)?(?:la\s+)?nota\s+['\"]?([^'\"]+?)(?:['\"]|\s|$)",
                r"nota\s+['\"]?([^'\"]+?)(?:['\"]|\s+)(?:y\s+)?(?:agrega|agregar|pon|poner)\s+(.+)",
            ]
            
            for pattern in append_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    if len(match.groups()) == 2:
                        group1, group2 = match.groups()
                        # Determinar cuál es el título y cuál el contenido
                        if "nota" in group1.lower() or (len(group1.split()) <= 2 and len(group2.split()) > 2):
                            title = group2.strip()
                            content = group1.strip()
                        else:
                            title = group1.strip()
                            content = group2.strip()
                        
                        # Limpiar contenido
                        content = re.sub(r'^(?:que\s+)?(?:diga|dice|escriba|escribe|poner|pon)\s*', '', content, flags=re.IGNORECASE).strip()
                        
                        if title:
                            return {"action": "append", "title": title, "content": content}
        
        # PRIORIDAD 5: Eliminar nota
        delete_patterns = [
            r"(?:elimina?|borra?|quita?)\s+(?:la\s+)?nota\s+['\"]?([^'\"]+?)(?:['\"]|\s|$)",
            r"nota\s+['\"]?([^'\"]+?)(?:['\"]|\s+)(?:elimina?|borra?|quita?)",
        ]
        
        for pattern in delete_patterns:
            match = re.search(pattern, message_lower)
            if match:
                title = match.group(1).strip()
                return {"action": "delete", "title": title}
        
        # PRIORIDAD 6: Listar notas (último para evitar falsos positivos)
        list_patterns = [
            r"(?:lista?|muestra?|dime)\s+(?:las\s+)?notas?$",
            r"qué\s+notas?\s+tengo",
            r"^(?:las\s+)?notas?$",  # Solo si es solo "notas" o "las notas"
        ]
        
        for pattern in list_patterns:
            if re.search(pattern, message_lower):
                # Verificar que no sea parte de otro comando
                if "nota " in message_lower and len(re.findall(r'\bnota\b', message_lower)) == 1:
                    # Si hay "nota" seguido de algo, probablemente no es listar
                    continue
                return {"action": "list"}
        
        return {"action": None}

