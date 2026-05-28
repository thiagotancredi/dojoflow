from pydantic import BaseModel, Field


class TelegramUser(BaseModel):
    id: int
    first_name: str | None = None
    username: str | None = None


class TelegramChat(BaseModel):
    id: int


class TelegramMessage(BaseModel):
    from_user: TelegramUser = Field(alias='from')
    chat: TelegramChat
    text: str | None = None


class TelegramCallbackMessage(BaseModel):
    chat: TelegramChat


class TelegramCallbackQuery(BaseModel):
    id: str
    from_user: TelegramUser = Field(alias='from')
    message: TelegramCallbackMessage | None = None
    data: str | None = None


class TelegramUpdate(BaseModel):
    update_id: int | None = None
    message: TelegramMessage | None = None
    callback_query: TelegramCallbackQuery | None = None
