from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = ''
    database_worker_url: str = ''
    supabase_url: str = ''
    supabase_publishable_key: str = ''
    supabase_storage_key: str = ''
    storage_bucket: str = 'broquer-privado'
    origenes_permitidos: list[str] = []
    sitio_url: str = ''
    proxy_secret: str = ''
    sesiones_claves: list[str] = []  # first encrypts; all decrypt, for rotation
    rate_limit_secret: str = ''
    registro_habilitado: bool = False
    google_habilitado: bool = False
    ia_modelo_default: str = 'claude-sonnet-4-6'
    anthropic_api_key: str = ''

    @property
    def disponible(self):
        return bool(self.database_url and self.supabase_url.startswith('https://')
                    and self.supabase_publishable_key and self.sesiones_claves
                    and len(self.proxy_secret) >= 32 and len(self.rate_limit_secret) >= 32
                    and self.sitio_url.startswith('https://')
                    and self.sitio_url in self.origenes_permitidos)

@lru_cache
def configuracion():
    return Configuracion()
