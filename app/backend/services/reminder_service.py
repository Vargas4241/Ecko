"""
Servicio de recordatorios y alarmas proactivas
Permite crear recordatorios, alarmas programadas y notificaciones
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
import re
import threading
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
import dateparser

# Importar almacenamiento persistente si está disponible
try:
    from services.persistent_storage import get_storage
    PERSISTENT_STORAGE_AVAILABLE = True
except ImportError:
    PERSISTENT_STORAGE_AVAILABLE = False
    print("[WARN] Almacenamiento persistente no disponible para recordatorios")

class ReminderService:
    """
    Gestiona recordatorios, alarmas y notificaciones proactivas
    Usa APScheduler para tareas programadas
    """
    
    def __init__(self, timezone_str: str = "America/Argentina/Buenos_Aires", use_persistence: bool = True):
        # Configurar zona horaria
        self.timezone = pytz.timezone(timezone_str)
        
        # Almacenamiento en memoria (cache/fallback)
        self.reminders: Dict[str, Dict[str, Dict]] = {}  # {session_id: {reminder_id: reminder_data}}
        
        # Almacenamiento persistente
        self.use_persistence = use_persistence and PERSISTENT_STORAGE_AVAILABLE
        if self.use_persistence:
            try:
                self.storage = get_storage()
                print("[OK] ReminderService usando almacenamiento persistente")
                # Cargar recordatorios activos desde la base de datos
                self._load_active_reminders_from_storage()
            except Exception as e:
                print(f"[WARN] Error inicializando persistencia, usando solo memoria: {e}")
                self.use_persistence = False
        else:
            print("[OK] ReminderService usando solo almacenamiento en memoria")
        
        # Configurar scheduler con timezone y executor
        executor = ThreadPoolExecutor(max_workers=10)
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        
        self.scheduler = BackgroundScheduler(
            timezone=self.timezone,
            executors={'default': executor},
            job_defaults=job_defaults
        )
        self.scheduler.start()
        
        self.notification_callbacks: Dict[str, List[Callable]] = {}  # {session_id: [callbacks]}
        # Almacenamiento de notificaciones pendientes (para polling desde frontend)
        self.pending_notifications: Dict[str, List[Dict]] = {}  # {session_id: [{id, message, timestamp, reminder_id}]}
        
        # Log de hora actual del sistema
        now_local = datetime.now(self.timezone)
        now_utc = datetime.now(pytz.UTC)
        print(f"[OK] ReminderService inicializado - Sistema de alarmas activo")
        print(f"[TIME] Hora local (scheduler): {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"[TIME] Hora UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"[TIME] Zona horaria configurada: {timezone_str}")
    
    def get_current_time(self):
        """Obtener hora actual en la zona horaria configurada"""
        return datetime.now(self.timezone)
    
    def register_notification_callback(self, session_id: str, callback: Callable):
        """
        Registrar callback para recibir notificaciones de recordatorios
        callback debe recibir: (reminder_id, message, session_id)
        """
        if session_id not in self.notification_callbacks:
            self.notification_callbacks[session_id] = []
        self.notification_callbacks[session_id].append(callback)
    
    def _trigger_notification(self, session_id: str, reminder_id: str, message: str):
        """
        Disparar notificaciones a todos los callbacks registrados
        Y guardar en lista de notificaciones pendientes para polling
        También envía push notification si está disponible
        """
        # Guardar notificación para polling desde frontend
        if session_id not in self.pending_notifications:
            self.pending_notifications[session_id] = []
        
        notification = {
            "id": str(uuid.uuid4()),
            "reminder_id": reminder_id,
            "message": message,
            "timestamp": self.get_current_time().isoformat(),
            "type": "reminder"
        }
        self.pending_notifications[session_id].append(notification)
        
        # Limitar a últimas 50 notificaciones por sesión (memoria)
        if len(self.pending_notifications[session_id]) > 50:
            self.pending_notifications[session_id] = self.pending_notifications[session_id][-50:]
        
        # Guardar en almacenamiento persistente
        if self.use_persistence:
            try:
                self.storage.save_notification({
                    "id": notification["id"],
                    "session_id": session_id,
                    "reminder_id": reminder_id,
                    "message": message,
                    "timestamp": notification["timestamp"]
                })
            except Exception as e:
                print(f"[WARN] Error guardando notificación en storage: {e}")
        
        print(f"[NOTIFICACION] Guardada para sesion {session_id}: {message}")
        
        # Enviar push notification si está disponible
        try:
            from services.push_service import _push_service_instance
            if _push_service_instance:
                _push_service_instance.send_notification_to_user(
                    session_id,
                    message,
                    title="🔔 Ecko",
                    options={
                        "tag": f"reminder-{reminder_id}",
                        "requireInteraction": True,
                        "data": {"reminder_id": reminder_id, "type": "reminder"}
                    }
                )
                print(f"[PUSH] Notificación push enviada a {session_id}")
        except Exception as e:
            # No es crítico si falla, solo loguear
            print(f"[DEBUG] Push notification no disponible: {e}")
        
        # Ejecutar callbacks si hay registrados
        if session_id in self.notification_callbacks:
            for callback in self.notification_callbacks[session_id]:
                try:
                    callback(reminder_id, message, session_id)
                except Exception as e:
                    print(f"[ERROR] Error en callback de notificacion: {e}")
    
    def _parse_datetime(self, text: str) -> Optional[datetime]:
        """
        Parsear fecha/hora desde texto natural en español
        Ejemplos: "mañana a las 9am", "en 2 horas", "lunes a las 7pm", "hoy 14:38", "ahora en 2 minutos", "14:45"
        """
        try:
            # Limpiar el texto
            text_lower = text.lower().strip()
            now = self.get_current_time()  # Usar hora con timezone
            
            # Caso especial: "ahora en X minutos/horas"
            minutes_match = re.search(r'(?:en|dentro de|ahora en|ahora)\s+(\d+)\s+minutos?', text_lower)
            if minutes_match:
                minutes = int(minutes_match.group(1))
                result = now + timedelta(minutes=minutes)
                print(f"[DEBUG] Parseado 'en {minutes} minutos' -> {result} ({result.strftime('%H:%M:%S %Z')})")
                return result
            
            # Caso: "en un minuto" o "en 1 minuto"
            un_minuto_match = re.search(r'(?:en|dentro de|ahora en|ahora)\s+un\s+minuto', text_lower)
            if un_minuto_match:
                result = now + timedelta(minutes=1)
                print(f"[DEBUG] Parseado 'en un minuto' -> {result} ({result.strftime('%H:%M:%S %Z')})")
                return result
            
            hours_match = re.search(r'(?:en|dentro de|ahora en)\s+(\d+)\s+horas?', text_lower)
            if hours_match:
                hours = int(hours_match.group(1))
                result = now + timedelta(hours=hours)
                print(f"[DEBUG] Parseado 'en {hours} horas' -> {result} ({result.strftime('%H:%M:%S %Z')})")
                return result
            
            # Caso especial: formato "HHMM" sin separador (ej: "1445", "1459")
            hhmm_match = re.search(r'\b(\d{3,4})\b', text)
            if hhmm_match:
                time_str = hhmm_match.group(1)
                if len(time_str) == 4 and time_str.isdigit():
                    hour = int(time_str[:2])
                    minute = int(time_str[2:])
                    if 0 <= hour < 24 and 0 <= minute < 60:
                        # Si dice "hoy" o no especifica, usar hoy
                        if "hoy" in text_lower or "ahora" not in text_lower:
                            # Crear datetime naive y luego localizar
                            target_naive = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                            if target_naive <= now:
                                target_naive = target_naive + timedelta(days=1)
                            # Si el datetime naive fue creado a partir de uno con timezone, mantener timezone
                            if target_naive.tzinfo:
                                target = target_naive
                            else:
                                target = self.timezone.localize(target_naive)
                            print(f"[DEBUG] Parseado '{time_str}' (hoy) -> {target} ({target.strftime('%H:%M:%S %Z')})")
                            return target
            
            # Caso especial: "hoy HH:MM" o "hoy a las HH:MM" o solo "HH:MM" o "HH:MM minutos"
            today_match = re.search(r'(?:hoy\s+(?:a las\s+)?|(?:a las\s+)?)(\d{1,2}):(\d{2})(?:\s+minutos?)?', text_lower)
            if today_match:
                hour = int(today_match.group(1))
                minute = int(today_match.group(2))
                target_naive = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                # Si la hora ya pasó hoy, ponerla para mañana (a menos que diga "mañana")
                if target_naive <= now and "mañana" not in text_lower:
                    target_naive = target_naive + timedelta(days=1)
                # Asegurar timezone
                if target_naive.tzinfo:
                    target = target_naive
                else:
                    target = self.timezone.localize(target_naive)
                print(f"[DEBUG] Parseado 'hoy {hour}:{minute}' -> {target} ({target.strftime('%H:%M:%S %Z')})")
                return target
            
            # Caso especial: solo hora sin contexto (ej: "14:59" al final de frase)
            time_only_match = re.search(r'(\d{1,2}):(\d{2})(?:\s|$)', text)
            if time_only_match and ("hoy" in text_lower or "ahora" not in text_lower):
                hour = int(time_only_match.group(1))
                minute = int(time_only_match.group(2))
                if 0 <= hour < 24 and 0 <= minute < 60:
                    target_naive = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if target_naive <= now:
                        target_naive = target_naive + timedelta(days=1)
                    # Asegurar timezone
                    if target_naive.tzinfo:
                        target = target_naive
                    else:
                        target = self.timezone.localize(target_naive)
                    print(f"[DEBUG] Parseado hora sola '{hour}:{minute}' -> {target} ({target.strftime('%H:%M:%S %Z')})")
                    return target
            
            # Caso especial: "mañana HH:MM" o "mañana a las HH:MM"
            tomorrow_match = re.search(r'mañana\s+(?:a las\s+)?(\d{1,2}):(\d{2})', text_lower)
            if tomorrow_match:
                hour = int(tomorrow_match.group(1))
                minute = int(tomorrow_match.group(2))
                tomorrow = now + timedelta(days=1)
                result_naive = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
                # Asegurar timezone
                if result_naive.tzinfo:
                    result = result_naive
                else:
                    result = self.timezone.localize(result_naive)
                print(f"[DEBUG] Parseado 'mañana {hour}:{minute}' -> {result} ({result.strftime('%H:%M:%S %Z')})")
                return result
            
            # Reemplazar expresiones comunes en español
            replacements = {
                "mañana": "tomorrow",
                "pasado mañana": "in 2 days",
                "hoy": "today",
                "ahora": "now",
                "en una hora": "in 1 hour",
                "en dos horas": "in 2 hours",
                "en media hora": "in 30 minutes",
            }
            
            text_clean = text_lower
            for es, en in replacements.items():
                text_clean = text_clean.replace(es, en)
            
            # Intentar parsear con dateparser
            parsed = dateparser.parse(text_clean, languages=['es', 'en'], settings={
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': now,
                'TIMEZONE': 'America/Argentina/Buenos_Aires'  # Ajustar según tu zona horaria
            })
            
            if parsed:
                print(f"[DEBUG] Parseado con dateparser '{text_clean}' -> {parsed}")
            
            return parsed
        except Exception as e:
            print(f"[WARN] Error parseando fecha '{text}': {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_recurrence(self, text: str) -> Optional[Dict]:
        """
        Parsear patrones de recurrencia
        Ejemplos: "cada lunes", "todos los días", "cada semana"
        """
        text_lower = text.lower()
        
        # Días de la semana
        days_map = {
            "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2,
            "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5,
            "domingo": 6
        }
        
        # Buscar patrones de recurrencia
        if "cada día" in text_lower or "todos los días" in text_lower or "diario" in text_lower:
            return {"type": "daily"}
        
        if "cada semana" in text_lower or "semanal" in text_lower:
            return {"type": "weekly"}
        
        if "cada mes" in text_lower or "mensual" in text_lower:
            return {"type": "monthly"}
        
        # Buscar días específicos de la semana
        for day_name, day_num in days_map.items():
            if f"cada {day_name}" in text_lower or f"todos los {day_name}" in text_lower:
                return {"type": "weekly", "day_of_week": day_num}
        
        return None
    
    def _extract_time(self, text: str) -> Optional[str]:
        """
        Extraer hora del texto (formato 24h)
        Ejemplos: "9am" -> "09:00", "7pm" -> "19:00", "14:30" -> "14:30"
        """
        # Buscar patrones de hora
        patterns = [
            r'(\d{1,2})\s*:\s*(\d{2})',  # "14:30" o "9:30"
            r'(\d{1,2})\s*(am|pm)',      # "9am" o "7pm"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                if ':' in text:
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    if 0 <= hour < 24 and 0 <= minute < 60:
                        return f"{hour:02d}:{minute:02d}"
                else:
                    hour = int(match.group(1))
                    am_pm = match.group(2)
                    if am_pm == 'pm' and hour != 12:
                        hour += 12
                    elif am_pm == 'am' and hour == 12:
                        hour = 0
                    if 0 <= hour < 24:
                        return f"{hour:02d}:00"
        
        return None
    
    def create_reminder(self, session_id: str, message: str, reminder_text: str) -> Dict:
        """
        Crear un recordatorio desde texto natural
        Ejemplos:
        - "recuérdame estudiar Docker mañana a las 9am"
        - "recuérdame hacer ejercicio cada lunes a las 7am"
        - "recuérdame llamar a mamá en 2 horas"
        """
        reminder_id = str(uuid.uuid4())
        
        # Intentar extraer fecha/hora
        reminder_lower = reminder_text.lower()
        target_datetime = None
        recurrence = None
        time_str = None
        
        # Buscar recurrencia primero
        recurrence = self._parse_recurrence(reminder_text)
        
        # Buscar hora específica
        time_str = self._extract_time(reminder_text)
        
        # Buscar fecha/hora completa
        if not recurrence:
            target_datetime = self._parse_datetime(reminder_text)
        
        # Extraer el texto del recordatorio (eliminar comandos de tiempo de forma inteligente)
        reminder_message = reminder_text
        
        # Primero, intentar extraer solo la parte después de "que diga" o "que"
        que_diga_match = re.search(r'que\s+(?:diga\s+)?(.+)', reminder_text, re.IGNORECASE)
        if que_diga_match:
            reminder_message = que_diga_match.group(1).strip()
        
        # Lista de patrones de tiempo a remover (más específicos)
        time_patterns_to_remove = [
            r'^(?:ahora\s+)?(?:a las\s+)?\d{1,2}(?::\d{2})?\s+(?:minutos?\s+)?',  # "a las 15:14" o "15:14" al inicio
            r'^(?:hoy|mañana)\s+(?:a las\s+)?\d{1,2}(?::\d{2})?\s+(?:minutos?\s+)?',  # "hoy a las 15:14"
            r'^por favor\s+',  # "por favor" al inicio
            r'^\d{1,2}:\d{2}\s+',  # Solo hora al inicio
            r'\b(?:hoy|mañana)\s+(?:a las\s+)?',  # "hoy a las" o "mañana a las"
            r'\ba las\s+\d{1,2}(?::\d{2})?\s*',  # "a las 15:14"
            r'\ben\s+\d+\s+(?:hora|horas|minuto|minutos)\s+',  # "en 2 horas"
            r'\bde hoy\s+',  # "de hoy"
        ]
        
        # Remover patrones de tiempo
        original_message = reminder_message
        for pattern in time_patterns_to_remove:
            reminder_message = re.sub(pattern, '', reminder_message, flags=re.IGNORECASE)
        
        reminder_message = reminder_message.strip()
        
        # Limpiar "que" al inicio si quedó solo
        if reminder_message.lower().startswith("que "):
            reminder_message = reminder_message[4:].strip()
        
        # Si después de limpiar queda muy poco o nada, usar estrategia alternativa
        if len(reminder_message) < 3 or not reminder_message:
            # Intentar buscar el verbo principal y lo que sigue
            verb_patterns = [
                r'(?:tengo|tiene|debo|debes|necesito|necesita|quiero|quiere)\s+(?:que\s+)?(.+)',
                r'(?:estudiar|tomar|hacer|llamar|ir|volar|comprar|pagar)\s+(.+)',
            ]
            for pattern in verb_patterns:
                match = re.search(pattern, reminder_text, re.IGNORECASE)
                if match:
                    reminder_message = match.group(1).strip()
                    break
            
            # Si aún no hay nada, usar el texto original pero limpiado mínimamente
            if not reminder_message or len(reminder_message) < 3:
                # Remover solo horas muy obvias
                reminder_message = re.sub(r'\b\d{1,2}:\d{2}\b', '', reminder_text, flags=re.IGNORECASE).strip()
                reminder_message = re.sub(r'\ba las\s+\d+\b', '', reminder_message, flags=re.IGNORECASE).strip()
                reminder_message = re.sub(r'\s+', ' ', reminder_message)  # Normalizar espacios
                
                if not reminder_message:
                    reminder_message = reminder_text  # Último recurso: usar original
        
        # Crear estructura del recordatorio
        # Asegurar que target_datetime tenga timezone si existe
        if target_datetime and target_datetime.tzinfo is None:
            target_datetime = self.timezone.localize(target_datetime)
        
        reminder_data = {
            "id": reminder_id,
            "session_id": session_id,
            "message": reminder_message,
            "created_at": self.get_current_time().isoformat(),
            "target_datetime": target_datetime.isoformat() if target_datetime else None,
            "time_str": time_str,
            "recurrence": recurrence,
            "active": True,
        }
        
        # Guardar recordatorio
        if session_id not in self.reminders:
            self.reminders[session_id] = {}
        self.reminders[session_id][reminder_id] = reminder_data
        
        # Programar la alarma
        if recurrence:
            print(f"[DEBUG] Programando recordatorio recurrente...")
            self._schedule_recurring_reminder(reminder_data)
        elif target_datetime:
            print(f"[DEBUG] Programando recordatorio único para {target_datetime}...")
            self._schedule_one_time_reminder(reminder_data)
        else:
            # Si no se pudo parsear, crear recordatorio sin alarma programada
            print(f"[WARN] No se pudo parsear fecha/hora del recordatorio: {reminder_text}")
            print(f"[DEBUG] reminder_lower: {reminder_lower}, target_datetime: {target_datetime}, recurrence: {recurrence}, time_str: {time_str}")
        
        return reminder_data
    
    def _schedule_one_time_reminder(self, reminder: Dict):
        """
        Programar un recordatorio único
        """
        if not reminder.get("target_datetime"):
            print(f"[ERROR] No hay target_datetime en el recordatorio: {reminder}")
            return
        
        # Parsear datetime - puede venir con o sin timezone
        target_dt_str = reminder["target_datetime"]
        if isinstance(target_dt_str, str):
            target_dt = datetime.fromisoformat(target_dt_str)
            # Si no tiene timezone, asumir que es en nuestra zona horaria
            if target_dt.tzinfo is None:
                target_dt = self.timezone.localize(target_dt)
        else:
            target_dt = target_dt_str
        
        now = self.get_current_time()
        
        # Asegurar que ambos tengan timezone para comparar
        if target_dt.tzinfo is None:
            target_dt = self.timezone.localize(target_dt)
        
        diff_seconds = (target_dt - now).total_seconds()
        
        print(f"[DEBUG] Programando recordatorio:")
        print(f"  Ahora (local): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"  Target: {target_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"  Diferencia: {diff_seconds:.0f} segundos ({diff_seconds/60:.1f} minutos)")
        
        # No programar si ya pasó
        if target_dt <= now:
            print(f"[WARN] No se programa recordatorio porque la fecha ya pasó: {target_dt}")
            print(f"[WARN] Ahora: {now}, Target: {target_dt}, Diferencia: {diff_seconds:.0f}s")
            return
        
        def trigger():
            trigger_time = self.get_current_time()
            print(f"[TRIGGER] Disparando recordatorio {reminder['id']} a las {trigger_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            self._trigger_notification(
                reminder["session_id"],
                reminder["id"],
                f"🔔 Recordatorio: {reminder['message']}"
            )
            # Marcar como completado - IMPORTANTE: actualizar en el dict también
            reminder["active"] = False
            # Asegurar que se actualice en el almacenamiento en memoria
            if reminder["session_id"] in self.reminders:
                if reminder["id"] in self.reminders[reminder["session_id"]]:
                    self.reminders[reminder["session_id"]][reminder["id"]]["active"] = False
            
            # Actualizar en almacenamiento persistente
            if self.use_persistence:
                try:
                    self.storage.update_reminder_active(reminder["id"], False)
                except Exception as e:
                    print(f"[WARN] Error actualizando recordatorio en storage: {e}")
            
            print(f"[DEBUG] Recordatorio {reminder['id']} marcado como inactivo")
        
        try:
            self.scheduler.add_job(
                trigger,
                DateTrigger(run_date=target_dt),
                id=reminder["id"],
                replace_existing=True
            )
            
            print(f"[OK] Recordatorio programado para {target_dt.strftime('%Y-%m-%d %H:%M:%S')} (en {(target_dt-now).total_seconds():.0f} segundos)")
            
            # Verificar que el job se agregó correctamente
            jobs = self.scheduler.get_jobs()
            print(f"[DEBUG] Jobs activos en scheduler: {len(jobs)}")
            for job in jobs:
                if job.id == reminder["id"]:
                    print(f"[DEBUG] Job encontrado: {job.id}, próxima ejecución: {job.next_run_time}")
        except Exception as e:
            print(f"[ERROR] Error al programar recordatorio: {e}")
            import traceback
            traceback.print_exc()
    
    def _schedule_recurring_reminder(self, reminder: Dict):
        """
        Programar un recordatorio recurrente
        """
        recurrence = reminder.get("recurrence")
        if not recurrence:
            return
        
        time_str = reminder.get("time_str", "09:00")
        hour, minute = map(int, time_str.split(":"))
        
        def trigger():
            self._trigger_notification(
                reminder["session_id"],
                reminder["id"],
                f"⏰ Recordatorio: {reminder['message']}"
            )
        
        if recurrence["type"] == "daily":
            # Cada día a la hora especificada
            self.scheduler.add_job(
                trigger,
                CronTrigger(hour=hour, minute=minute),
                id=reminder["id"],
                replace_existing=True
            )
        elif recurrence["type"] == "weekly":
            # Cada semana, en el día especificado (o lunes si no se especifica)
            day_of_week = recurrence.get("day_of_week", 0)
            self.scheduler.add_job(
                trigger,
                CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute),
                id=reminder["id"],
                replace_existing=True
            )
        elif recurrence["type"] == "monthly":
            # Primer día de cada mes
            self.scheduler.add_job(
                trigger,
                CronTrigger(day=1, hour=hour, minute=minute),
                id=reminder["id"],
                replace_existing=True
            )
        
        print(f"[OK] Recordatorio recurrente programado: {recurrence['type']} a las {time_str}")
    
    def get_reminders(self, session_id: str, active_only: bool = True) -> List[Dict]:
        """
        Obtener todos los recordatorios de una sesión (desde persistencia si está disponible)
        """
        # Si hay persistencia, cargar desde ahí
        if self.use_persistence:
            try:
                reminders = self.storage.get_reminders(session_id, active_only)
                # Actualizar cache en memoria
                if session_id not in self.reminders:
                    self.reminders[session_id] = {}
                for reminder in reminders:
                    self.reminders[session_id][reminder["id"]] = reminder
                return reminders
            except Exception as e:
                print(f"[WARN] Error cargando recordatorios desde storage: {e}")
        
        # Fallback a memoria
        if session_id not in self.reminders:
            return []
        
        reminders = list(self.reminders[session_id].values())
        
        if active_only:
            reminders = [r for r in reminders if r.get("active", True)]
        
        # Ordenar por fecha objetivo
        reminders.sort(key=lambda x: x.get("target_datetime") or "9999-12-31")
        
        return reminders
    
    def delete_reminder(self, session_id: str, reminder_id: str) -> bool:
        """
        Eliminar un recordatorio
        """
        # Verificar si existe (en memoria o persistencia)
        exists = False
        if session_id in self.reminders and reminder_id in self.reminders[session_id]:
            exists = True
        elif self.use_persistence:
            try:
                reminders = self.storage.get_reminders(session_id, active_only=False)
                exists = any(r["id"] == reminder_id for r in reminders)
            except:
                pass
        
        if not exists:
            return False
        
        # Cancelar job en scheduler si existe
        try:
            self.scheduler.remove_job(reminder_id)
        except:
            pass
        
        # Eliminar de memoria
        if session_id in self.reminders and reminder_id in self.reminders[session_id]:
            del self.reminders[session_id][reminder_id]
        
        # Eliminar de almacenamiento persistente
        if self.use_persistence:
            try:
                self.storage.delete_reminder(reminder_id)
            except Exception as e:
                print(f"[WARN] Error eliminando recordatorio de storage: {e}")
        
        return True
    
    def get_pending_notifications(self, session_id: str, clear_after: bool = True) -> List[Dict]:
        """
        Obtener notificaciones pendientes (para polling desde el frontend)
        Retorna las notificaciones y opcionalmente las limpia después de leerlas
        """
        # Si hay persistencia, cargar desde ahí
        if self.use_persistence:
            try:
                notifications = self.storage.get_pending_notifications(session_id, read=False)
                # Convertir a formato esperado
                result = [{
                    "id": n["id"],
                    "reminder_id": n.get("reminder_id"),
                    "message": n["message"],
                    "timestamp": n["timestamp"],
                    "type": "reminder"
                } for n in notifications]
                
                # Marcar como leídas si se solicita
                if clear_after:
                    self.storage.mark_notifications_read(session_id)
                
                return result
            except Exception as e:
                print(f"[WARN] Error cargando notificaciones desde storage: {e}")
        
        # Fallback a memoria
        if session_id not in self.pending_notifications:
            return []
        
        notifications = self.pending_notifications[session_id].copy()
        
        # Limpiar después de leer si se solicita
        if clear_after:
            self.pending_notifications[session_id] = []
        
        return notifications
    
    def _load_active_reminders_from_storage(self):
        """Cargar recordatorios activos desde almacenamiento persistente al iniciar"""
        if not self.use_persistence:
            return
        
        try:
            all_reminders = self.storage.get_all_active_reminders()
            print(f"[OK] Cargando {len(all_reminders)} recordatorios activos desde almacenamiento...")
            
            for reminder in all_reminders:
                session_id = reminder["session_id"]
                
                # Cachear en memoria
                if session_id not in self.reminders:
                    self.reminders[session_id] = {}
                self.reminders[session_id][reminder["id"]] = reminder
                
                # Reprogramar alarmas
                if reminder.get("recurrence"):
                    self._schedule_recurring_reminder(reminder)
                elif reminder.get("target_datetime"):
                    # Verificar que la fecha no haya pasado
                    target_dt = datetime.fromisoformat(reminder["target_datetime"])
                    if target_dt.tzinfo is None:
                        target_dt = self.timezone.localize(target_dt)
                    
                    now = self.get_current_time()
                    if target_dt > now:
                        self._schedule_one_time_reminder(reminder)
                    else:
                        # Marcar como inactivo si ya pasó
                        self.storage.update_reminder_active(reminder["id"], False)
                        reminder["active"] = False
            
            print(f"[OK] Recordatorios cargados y programados correctamente")
        except Exception as e:
            print(f"[ERROR] Error cargando recordatorios desde storage: {e}")
            import traceback
            traceback.print_exc()
    
    def shutdown(self):
        """
        Detener el scheduler al cerrar
        """
        self.scheduler.shutdown()

