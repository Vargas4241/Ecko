"""
Servicio de resúmenes automáticos de conversaciones
Usa OpenAI para generar resúmenes concisos y útiles
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Importar configuración
try:
    from config import USE_AI, OPENAI_API_KEY, AI_PROVIDER
except ImportError:
    USE_AI = os.getenv("USE_AI", "false").lower() == "true"
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower()


class SummaryService:
    """
    Servicio para generar resúmenes automáticos de conversaciones
    """
    
    def __init__(self, memory_service=None):
        self.memory_service = memory_service
        self.use_ai = USE_AI
        self.openai_api_key = OPENAI_API_KEY
        self.ai_provider = AI_PROVIDER
    
    async def generate_summary(
        self, 
        session_id: str, 
        history: List[Dict],
        period: str = "today",
        custom_context: Optional[str] = None
    ) -> str:
        """
        Genera un resumen de la conversación usando OpenAI
        
        Args:
            session_id: ID de la sesión
            history: Historial de mensajes
            period: Período del resumen ("today", "week", "all", "custom")
            custom_context: Contexto adicional personalizado
            
        Returns:
            Resumen generado por la IA
        """
        
        if not self.use_ai or not self.openai_api_key:
            return "⚠️ Los resúmenes requieren IA activada. Configura OpenAI en tu .env"
        
        if not history or len(history) == 0:
            return "📝 No hay conversaciones para resumir en este período."
        
        # Filtrar mensajes según el período
        filtered_history = self._filter_history_by_period(history, period)
        
        if not filtered_history:
            return f"📝 No hay conversaciones en el período seleccionado ({period})."
        
        # Preparar el prompt para OpenAI
        summary_prompt = self._build_summary_prompt(filtered_history, period, custom_context)
        
        try:
            # Generar resumen usando OpenAI
            summary = await self._call_openai_for_summary(summary_prompt, filtered_history)
            return summary
        except Exception as e:
            print(f"[ERROR] [Summary] Error generando resumen: {e}")
            return f"⚠️ Error al generar el resumen: {str(e)}"
    
    def _filter_history_by_period(self, history: List[Dict], period: str) -> List[Dict]:
        """
        Filtra el historial según el período seleccionado
        """
        now = datetime.now()
        
        if period == "today":
            # Mensajes de hoy
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            filtered = [
                msg for msg in history
                if self._parse_message_timestamp(msg) >= today_start
            ]
        elif period == "week":
            # Mensajes de la última semana
            week_start = now - timedelta(days=7)
            filtered = [
                msg for msg in history
                if self._parse_message_timestamp(msg) >= week_start
            ]
        elif period == "all":
            # Todo el historial
            filtered = history
        elif period == "custom":
            # Historial completo (el filtrado se hace fuera)
            filtered = history
        else:
            filtered = history
        
        return filtered
    
    def _parse_message_timestamp(self, message: Dict) -> datetime:
        """
        Extrae el timestamp de un mensaje
        """
        # Intentar diferentes formatos de timestamp
        timestamp = message.get("timestamp") or message.get("created_at")
        
        if isinstance(timestamp, str):
            try:
                # Formato ISO
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                try:
                    # Formato común
                    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                except:
                    pass
        
        # Si no se puede parsear, asumir que es reciente
        return datetime.now()
    
    def _build_summary_prompt(
        self, 
        history: List[Dict], 
        period: str, 
        custom_context: Optional[str]
    ) -> str:
        """
        Construye el prompt para OpenAI
        """
        # Formatear historial para el prompt
        conversation_text = self._format_history_for_prompt(history)
        
        period_descriptions = {
            "today": "de hoy",
            "week": "de la última semana",
            "all": "completas",
            "custom": ""
        }
        
        period_desc = period_descriptions.get(period, "")
        
        prompt = f"""Eres Ecko, un asistente virtual personal estilo Jarvis. 

Tu tarea es generar un resumen conciso y útil de la conversación {period_desc}.

INSTRUCCIONES:
- Sé conciso pero informativo (máximo 200 palabras)
- Destaca los puntos más importantes: tareas creadas, decisiones tomadas, información guardada
- Usa formato claro con viñetas cuando sea útil
- Si no hay información relevante, indícalo brevemente
- Mantén un tono profesional pero amigable

CONVERSACIÓN A RESUMIR:
{conversation_text}
"""
        
        if custom_context:
            prompt += f"\nCONTEXTO ADICIONAL:\n{custom_context}\n"
        
        prompt += "\nGenera el resumen ahora:"
        
        return prompt
    
    def _format_history_for_prompt(self, history: List[Dict]) -> str:
        """
        Formatea el historial para incluirlo en el prompt
        """
        formatted = []
        
        for msg in history[-50:]:  # Últimos 50 mensajes para no exceder tokens
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = self._parse_message_timestamp(msg)
            
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M")
            role_label = "Usuario" if role == "user" else "Ecko"
            
            formatted.append(f"[{timestamp_str}] {role_label}: {content}")
        
        return "\n".join(formatted)
    
    async def _call_openai_for_summary(self, prompt: str, history: List[Dict]) -> str:
        """
        Llama a OpenAI para generar el resumen
        """
        if self.ai_provider != "openai" or not self.openai_api_key:
            raise Exception("OpenAI no está configurado. Configura OPENAI_API_KEY en tu .env")
        
        import aiohttp
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        # Usar gpt-4o-mini para resúmenes (más barato y eficiente)
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "Eres Ecko, un asistente virtual personal estilo Jarvis. Generas resúmenes concisos y útiles de conversaciones."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.5,  # Más bajo para resúmenes más precisos
            "max_tokens": 400,   # Suficiente para un resumen conciso
            "top_p": 0.9,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API Error {response.status}: {error_text}")
                
                data = await response.json()
                summary = data["choices"][0]["message"]["content"].strip()
                
                print(f"[OK] [Summary] Resumen generado: {len(summary)} caracteres")
                return summary
    
    def get_summary_stats(self, history: List[Dict], period: str = "today") -> Dict:
        """
        Obtiene estadísticas básicas del período para mostrar antes del resumen
        """
        filtered = self._filter_history_by_period(history, period)
        
        user_messages = [msg for msg in filtered if msg.get("role") == "user"]
        assistant_messages = [msg for msg in filtered if msg.get("role") == "assistant"]
        
        return {
            "total_messages": len(filtered),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "period": period,
            "first_message": filtered[0] if filtered else None,
            "last_message": filtered[-1] if filtered else None,
        }

