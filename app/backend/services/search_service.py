"""
Servicio de búsqueda web inteligente
Permite a Ecko buscar información en tiempo real de Internet
"""

import os
import aiohttp
import json
from typing import Optional, Dict, List
from urllib.parse import quote

# Importar configuración
try:
    from config import SEARCH_API_KEY, SEARCH_PROVIDER
except ImportError:
    SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "")
    SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "duckduckgo")  # duckduckgo o tavily


class SearchService:
    """
    Servicio para búsquedas web inteligentes
    Soporta múltiples proveedores: Tavily (recomendado), DuckDuckGo (fallback)
    """
    
    def __init__(self):
        self.api_key = SEARCH_API_KEY
        self.provider = SEARCH_PROVIDER.lower()
        
        # Configuración de proveedores
        self.providers = {
            "tavily": {
                "url": "https://api.tavily.com/search",
                "requires_key": True
            },
            "duckduckgo": {
                "url": None,  # Se usa la biblioteca duckduckgo-search
                "requires_key": False
            }
        }
    
    async def search(self, query: str, max_results: int = 5) -> Dict:
        """
        Buscar información en la web
        
        Args:
            query: Consulta de búsqueda
            max_results: Número máximo de resultados
            
        Returns:
            Dict con resultados de búsqueda o error
        """
        query = query.strip()
        if not query:
            return {"error": "Consulta de búsqueda vacía", "results": []}
        
        print(f"🔍 [Búsqueda] Buscando: '{query}' (proveedor: {self.provider})")
        
        try:
            if self.provider == "tavily" and self.api_key:
                return await self._search_tavily(query, max_results)
            elif self.provider == "duckduckgo" or not self.api_key:
                return await self._search_duckduckgo(query, max_results)
            else:
                # Fallback a DuckDuckGo si Tavily no está configurado
                print("⚠️ [Búsqueda] Tavily no configurado, usando DuckDuckGo")
                return await self._search_duckduckgo(query, max_results)
                
        except Exception as e:
            print(f"❌ [Búsqueda] Error en búsqueda: {e}")
            return {"error": str(e), "results": []}
    
    async def _search_tavily(self, query: str, max_results: int) -> Dict:
        """
        Búsqueda usando Tavily API (recomendado para IA)
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "api_key": self.api_key,
                    "query": query,
                    "search_depth": "basic",
                    "include_answer": True,
                    "max_results": max_results
                }
                
                async with session.post(
                    "https://api.tavily.com/search",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Tavily API error {response.status}: {error_text}")
                    
                    data = await response.json()
                    
                    # Formatear resultados
                    results = []
                    if data.get("results"):
                        for result in data["results"][:max_results]:
                            results.append({
                                "title": result.get("title", ""),
                                "url": result.get("url", ""),
                                "content": result.get("content", "")[:500],  # Limitar contenido
                            })
                    
                    answer = data.get("answer", "")
                    
                    return {
                        "query": query,
                        "provider": "tavily",
                        "answer": answer,
                        "results": results,
                        "count": len(results)
                    }
                    
        except Exception as e:
            print(f"❌ [Tavily] Error: {e}")
            raise
    
    async def _search_duckduckgo(self, query: str, max_results: int) -> Dict:
        """
        Búsqueda usando DuckDuckGo (sin API key, más limitado)
        """
        try:
            # DuckDuckGo no tiene API oficial, usamos búsqueda HTML scraping
            # Nota: Esto es más simple pero menos confiable que Tavily
            
            search_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                
                async with session.get(
                    search_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        raise Exception(f"DuckDuckGo error {response.status}")
                    
                    html = await response.text()
                    
                    # Parsear resultados básicos (implementación simple)
                    # En producción, usar una biblioteca como duckduckgo-search sería mejor
                    results = []
                    
                    # Extraer títulos y URLs básicas (parsing simple)
                    import re
                    title_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
                    matches = re.findall(title_pattern, html)
                    
                    for match in matches[:max_results]:
                        url = match[0]
                        title = re.sub(r'<[^>]+>', '', match[1]).strip()
                        if title and url:
                            results.append({
                                "title": title,
                                "url": url,
                                "content": ""  # DuckDuckGo HTML no incluye snippets fácilmente
                            })
                    
                    return {
                        "query": query,
                        "provider": "duckduckgo",
                        "answer": f"Encontré {len(results)} resultados para '{query}'",
                        "results": results,
                        "count": len(results)
                    }
                    
        except Exception as e:
            print(f"❌ [DuckDuckGo] Error: {e}")
            # Fallback: retornar resultado genérico
            return {
                "query": query,
                "provider": "duckduckgo",
                "answer": f"Busca información sobre '{query}' en tu navegador para más detalles.",
                "results": [],
                "count": 0,
                "error": "Búsqueda no disponible temporalmente"
            }
    
    def format_results_for_ai(self, search_result: Dict) -> str:
        """
        Formatear resultados de búsqueda para que la IA los use
        """
        if "error" in search_result:
            return f"Error en búsqueda: {search_result['error']}"
        
        formatted = f"Resultados de búsqueda para: {search_result['query']}\n\n"
        
        if search_result.get("answer"):
            formatted += f"Respuesta resumida: {search_result['answer']}\n\n"
        
        if search_result.get("results"):
            formatted += "Fuentes encontradas:\n"
            for i, result in enumerate(search_result["results"], 1):
                formatted += f"{i}. {result.get('title', 'Sin título')}\n"
                if result.get("content"):
                    formatted += f"   {result['content'][:200]}...\n"
                if result.get("url"):
                    formatted += f"   URL: {result['url']}\n"
                formatted += "\n"
        
        return formatted

