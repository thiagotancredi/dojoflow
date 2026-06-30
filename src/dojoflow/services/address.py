from dojoflow.repositories.address import AddressRepository
from dojoflow.schemas.address import AddressCreate, AddressRead


class AddressService:
    def __init__(
        self,
        address_repository: AddressRepository,
    ) -> None:
        self.address_repository = address_repository

    async def create(
        self,
        address_create: AddressCreate,
    ) -> AddressRead:
        address_id = await self.address_repository.create(address_create)
        address = await self.address_repository.get_by_id_or_fail(address_id)

        return AddressRead(**address)
