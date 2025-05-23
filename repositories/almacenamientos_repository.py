from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from repositories.base_repository import IRepository
from schemas.almacenamientos_schema import AlmacenamientoResponse, AlmacenamientoCreate, AlmacenamientoUpdate
from database.models import Almacenamientos

class AlmacenamientosRepository(IRepository[Almacenamientos, AlmacenamientoResponse]):
    db: AsyncSession

    def __init__(self, model: type[Almacenamientos], schema: type[AlmacenamientoResponse], db: AsyncSession) -> None:
        self.db = db
        super().__init__(model, schema, db)

    async def get_alm_id_by_name(self, alm_name: str) -> Optional[int]:
        """
                        Find a Almacenamiento by 'name'

                        Args:
                            alm_name: The almacenamiento name param to filter.

                        Returns:
                            An integer of the almacenamiento id column.
                        """
        result = await self.db.execute(
            select(Almacenamientos.id).where(Almacenamientos.nombre == alm_name)
        )
        alm_id = result.scalar_one_or_none()
        return alm_id