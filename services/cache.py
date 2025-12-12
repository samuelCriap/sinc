"""
Sistema de Cache em Memória com TTL
"""
import time
from typing import Any, Optional, Dict, Callable
from threading import Lock


class Cache:
    """Cache em memória com TTL (Time To Live)."""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Obtém valor do cache se existir e não estiver expirado.
        
        Args:
            key: Chave do cache
            
        Returns:
            Valor cacheado ou None se expirado/inexistente
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if entry['expires_at'] and time.time() > entry['expires_at']:
                del self._cache[key]
                return None
            
            return entry['value']
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """
        Armazena valor no cache com TTL.
        
        Args:
            key: Chave do cache
            value: Valor a armazenar
            ttl_seconds: Tempo de vida em segundos (padrão: 5 min)
        """
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expires_at': time.time() + ttl_seconds if ttl_seconds > 0 else None,
                'created_at': time.time()
            }
    
    def invalidate(self, key: str) -> bool:
        """
        Invalida (remove) uma entrada do cache.
        
        Args:
            key: Chave a remover
            
        Returns:
            True se existia, False caso contrário
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalida todas as chaves que começam com o padrão.
        
        Args:
            pattern: Prefixo das chaves a remover
            
        Returns:
            Número de entradas removidas
        """
        with self._lock:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(pattern)]
            for key in keys_to_remove:
                del self._cache[key]
            return len(keys_to_remove)
    
    def clear(self) -> None:
        """Limpa todo o cache."""
        with self._lock:
            self._cache.clear()
    
    def get_or_set(self, key: str, func: Callable, ttl_seconds: int = 300) -> Any:
        """
        Obtém do cache ou executa função e cacheia resultado.
        
        Args:
            key: Chave do cache
            func: Função a executar se cache miss
            ttl_seconds: TTL para o novo valor
            
        Returns:
            Valor do cache ou resultado da função
        """
        value = self.get(key)
        if value is not None:
            return value
        
        result = func()
        self.set(key, result, ttl_seconds)
        return result
    
    def stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        with self._lock:
            now = time.time()
            valid = sum(1 for e in self._cache.values() if not e['expires_at'] or now <= e['expires_at'])
            return {
                'total_entries': len(self._cache),
                'valid_entries': valid,
                'expired_entries': len(self._cache) - valid,
            }


# Instância global do cache
cache = Cache()


# ═══════════════════════════════════════════════════════════════
# FUNÇÕES DE CONVENIÊNCIA
# ═══════════════════════════════════════════════════════════════

# Chaves padronizadas
CACHE_KEYS = {
    'PRODUTOS': 'produtos_lista',
    'PRODUTOS_BLOQUEADOS': 'produtos_bloqueados',
    'CANAIS': 'canais_lista',
    'USUARIOS': 'usuarios_lista',
    'CHAMADOS': 'chamados_ativos',
    'DASHBOARD': 'dashboard_stats',
}

# TTLs em segundos
TTL = {
    'CURTO': 60,       # 1 minuto
    'MEDIO': 300,      # 5 minutos
    'LONGO': 600,      # 10 minutos
    'MUITO_LONGO': 3600,  # 1 hora
}


def get_cached(key: str) -> Optional[Any]:
    """Obtém valor do cache global."""
    return cache.get(key)


def set_cached(key: str, value: Any, ttl: int = TTL['MEDIO']) -> None:
    """Armazena valor no cache global."""
    cache.set(key, value, ttl)


def invalidate_cached(key: str) -> bool:
    """Invalida chave do cache global."""
    return cache.invalidate(key)


def clear_cache() -> None:
    """Limpa todo o cache."""
    cache.clear()
