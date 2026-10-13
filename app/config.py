from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    admin_token: str
    database_url: str = "sqlite:///./data.db"
    products_file: str = "produtos.json"
    stores_file: str = "lojas.json"
    # Chaves fixas, separadas por vírgula. Úteis em hospedagens onde o SQLite é apagado
    # a cada reinício (ex.: Render gratuito): a chave não depende do banco.
    api_keys: str = ""

    @property
    def static_api_keys(self) -> list[str]:
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
