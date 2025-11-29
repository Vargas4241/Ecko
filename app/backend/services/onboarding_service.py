"""
Servicio de Onboarding - Preguntas iniciales para personalizar la experiencia
Se ejecuta cuando es la primera vez que un usuario interactúa con Ecko
"""

from typing import Dict, List, Optional
from services.user_profile_service import UserProfileService

class OnboardingService:
    """
    Maneja el proceso de onboarding - preguntas iniciales para conocer al usuario
    """
    
    def __init__(self, user_profile_service: UserProfileService):
        self.user_profile_service = user_profile_service
        
        # Preguntas de onboarding (en orden)
        self.onboarding_questions = [
            {
                "step": 1,
                "question": "¡Hola! Soy Ecko, tu asistente virtual personal. Es un placer conocerte. Para personalizar mejor tu experiencia, ¿cuál es tu nombre?",
                "type": "name",
                "follow_up": "Perfecto, {name}. ¿Cómo te gustaría que te llame? ¿Prefieres que use tu nombre, 'Señor', u otro título?"
            },
            {
                "step": 2,
                "question": "¿Cuál es tu fecha de cumpleaños? (Por ejemplo: 15 de marzo, o 15/03)",
                "type": "birthday",
                "follow_up": "Gracias, {name}. Recordaré tu cumpleaños."
            },
            {
                "step": 3,
                "question": "Genial. ¿Hay algo específico en lo que te gustaría que te ayude? Puedo recordarte tareas, crear notas, buscar información, y mucho más.",
                "type": "preferences",
                "follow_up": "Perfecto, lo tendré en cuenta."
            }
        ]
    
    def is_onboarding_complete(self, session_id: str) -> bool:
        """Verificar si el onboarding ya está completo para esta sesión"""
        if not self.user_profile_service:
            return True  # Si no hay servicio, asumir completado
        
        profile = self.user_profile_service.get_or_create_profile(session_id)
        
        # El onboarding está completo si el usuario tiene nombre guardado
        # y ha completado al menos el primer paso
        if profile.get("name"):
            return True
        
        return False
    
    def get_current_step(self, session_id: str) -> int:
        """Obtener el paso actual del onboarding"""
        if self.is_onboarding_complete(session_id):
            return 0  # Completado
        
        profile = self.user_profile_service.get_or_create_profile(session_id)
        learned_info = profile.get("learned_info", {})
        
        # Verificar qué pasos se han completado
        completed_steps = learned_info.get("onboarding_steps", [])
        
        # Retornar el siguiente paso a completar
        return len(completed_steps) + 1
    
    def mark_step_complete(self, session_id: str, step: int):
        """Marcar un paso del onboarding como completado"""
        profile = self.user_profile_service.get_or_create_profile(session_id)
        learned_info = profile.get("learned_info", {})
        
        completed_steps = learned_info.get("onboarding_steps", [])
        if step not in completed_steps:
            completed_steps.append(step)
        
        learned_info["onboarding_steps"] = completed_steps
        profile["learned_info"] = learned_info
        
        # Guardar en almacenamiento persistente
        if hasattr(self.user_profile_service, 'storage'):
            self.user_profile_service.storage.save_user_profile(session_id, profile)
        else:
            # Fallback: actualizar en memoria
            pass
    
    def get_onboarding_question(self, session_id: str) -> Optional[str]:
        """Obtener la pregunta de onboarding actual"""
        current_step = self.get_current_step(session_id)
        
        if current_step == 0:
            return None  # Onboarding completado
        
        if current_step > len(self.onboarding_questions):
            return None  # Ya pasó todas las preguntas
        
        question_data = self.onboarding_questions[current_step - 1]
        return question_data["question"]
    
    def process_onboarding_response(self, session_id: str, user_response: str) -> Dict:
        """
        Procesar respuesta del usuario durante onboarding
        Retorna: {"completed": bool, "response": str, "next_question": Optional[str]}
        """
        current_step = self.get_current_step(session_id)
        
        if current_step == 0:
            return {
                "completed": True,
                "response": None,
                "next_question": None
            }
        
        question_data = self.onboarding_questions[current_step - 1]
        response_type = question_data["type"]
        
        # Procesar según el tipo de pregunta
        if response_type == "name":
            # Extraer nombre de la respuesta
            import re
            name_match = re.search(r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\b', user_response)
            if name_match:
                name = name_match.group(1)
                self.user_profile_service.update_name(session_id, name)
                self.mark_step_complete(session_id, current_step)
                
                # Obtener siguiente pregunta
                next_step = self.get_current_step(session_id)
                if next_step > 0:
                    next_question_data = self.onboarding_questions[next_step - 1]
                    # Personalizar con el nombre si tiene placeholder
                    next_question = next_question_data["question"].replace("{name}", name)
                else:
                    next_question = None
                
                return {
                    "completed": False,
                    "response": question_data["follow_up"].format(name=name),
                    "next_question": next_question
                }
            else:
                return {
                    "completed": False,
                    "response": "Por favor, dime tu nombre. Por ejemplo: 'Me llamo Franco' o 'Soy Franco'.",
                    "next_question": question_data["question"]
                }
        
        elif response_type == "birthday":
            # Intentar extraer fecha de cumpleaños
            if self.user_profile_service.update_birthday(session_id, user_response):
                profile = self.user_profile_service.get_or_create_profile(session_id)
                name = profile.get("name", "usuario")
                
                self.mark_step_complete(session_id, current_step)
                
                # Obtener siguiente pregunta
                next_step = self.get_current_step(session_id)
                if next_step > 0:
                    next_question = self.onboarding_questions[next_step - 1]["question"]
                else:
                    next_question = None
                
                return {
                    "completed": False,
                    "response": question_data["follow_up"].format(name=name),
                    "next_question": next_question
                }
            else:
                return {
                    "completed": False,
                    "response": "No pude entender la fecha. ¿Podrías decirme de otra forma? Por ejemplo: '15 de marzo' o '15/03/1990'",
                    "next_question": question_data["question"]
                }
        
        elif response_type == "preferences":
            # Guardar preferencias si hay alguna información útil
            self.mark_step_complete(session_id, current_step)
            
            profile = self.user_profile_service.get_or_create_profile(session_id)
            name = profile.get("name", "Señor")
            
            return {
                "completed": True,
                "response": f"Perfecto, {name}. Ya tengo toda la información que necesito. Estoy listo para ayudarte. ¿En qué puedo asistirte hoy?",
                "next_question": None
            }
        
        return {
            "completed": False,
            "response": None,
            "next_question": question_data["question"]
        }

