"""
Servicio para exportar conversaciones a archivos por día
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict

class ChatExportService:
    """
    Exporta conversaciones a archivos de texto por día
    Los archivos se guardan en app/backend/data/chats/ por defecto
    """
    
    def __init__(self, export_dir: str = None):
        # Directorio donde se guardan los chats
        if export_dir is None:
            # Por defecto: app/backend/data/chats/
            base_path = Path(__file__).parent.parent
            export_dir = base_path / "data" / "chats"
        else:
            export_dir = Path(export_dir)
        
        self.export_dir = export_dir
        # Crear directorio si no existe
        self.export_dir.mkdir(parents=True, exist_ok=True)
        print(f"[OK] ChatExportService inicializado - Directorio: {self.export_dir}")
    
    def export_conversation(self, session_id: str, messages: List[Dict], date: datetime = None):
        """
        Exporta una conversación a un archivo por día
        
        Args:
            session_id: ID de la sesión
            messages: Lista de mensajes [{role, content, timestamp}, ...]
            date: Fecha para el nombre del archivo (default: hoy)
        """
        if date is None:
            date = datetime.now()
        
        # Nombre del archivo: YYYY-MM-DD.txt
        filename = date.strftime("%Y-%m-%d") + ".txt"
        filepath = self.export_dir / filename
        
        # Formatear mensajes
        formatted_lines = []
        formatted_lines.append(f"=" * 80)
        formatted_lines.append(f"CONVERSACIÓN - {date.strftime('%d/%m/%Y %H:%M:%S')}")
        formatted_lines.append(f"Sesión: {session_id}")
        formatted_lines.append(f"=" * 80)
        formatted_lines.append("")
        
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp")
            
            # Formatear timestamp si está disponible
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = timestamp
            else:
                time_str = datetime.now().strftime("%H:%M:%S")
            
            # Formatear según el rol
            if role == "user":
                formatted_lines.append(f"[{time_str}] USUARIO:")
                formatted_lines.append(f"  {content}")
            elif role == "assistant":
                formatted_lines.append(f"[{time_str}] ECKO:")
                formatted_lines.append(f"  {content}")
            else:
                formatted_lines.append(f"[{time_str}] {role.upper()}:")
                formatted_lines.append(f"  {content}")
            
            formatted_lines.append("")
        
        formatted_lines.append("=" * 80)
        formatted_lines.append("")
        
        # Escribir o append al archivo
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write("\n".join(formatted_lines))
            print(f"[OK] Conversación exportada a: {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"[ERROR] Error exportando conversación: {e}")
            return None
    
    def export_daily_summary(self, date: datetime = None):
        """
        Exporta un resumen de todas las conversaciones del día
        """
        if date is None:
            date = datetime.now()
        
        filename = date.strftime("%Y-%m-%d") + "_resumen.txt"
        filepath = self.export_dir / filename
        
        # Por ahora, solo crear el archivo vacío con fecha
        # Se puede expandir para incluir estadísticas
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"RESUMEN DE CONVERSACIONES - {date.strftime('%d/%m/%Y')}\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Fecha: {date.strftime('%d/%m/%Y')}\n")
                f.write(f"Archivo generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            print(f"[OK] Resumen diario creado: {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"[ERROR] Error creando resumen: {e}")
            return None

