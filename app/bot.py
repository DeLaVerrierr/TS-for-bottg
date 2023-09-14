import httpx as httpx
from config import API_TOKEN
import asyncio
import sys
from aiogram.enums import ParseMode
from aiogram import Bot, Router
from aiogram import types
from aiogram.filters import CommandStart
from aiogram.dispatcher.dispatcher import Dispatcher
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging

bot = Bot(token=API_TOKEN)

router = Router()

logging.basicConfig(level=logging.INFO)


class UserStates(StatesGroup):
    waiting_end_currency = State()
    waiting_start_amount = State()
    waiting_start_currency = State()


@router.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext) -> None:
    start_text = "Здравствуйте, {user_name}!\n\n" \
                 "Вы можете использовать этого бота для конвертации валют.\n" \
                 "Пожалуйста, выберите вашу валюту:\n"

    currencies_start = [[types.KeyboardButton(text="RUB")],
                        [types.KeyboardButton(text="USD")],
                        [types.KeyboardButton(text="EUR")],
                        [types.KeyboardButton(text="GBP")],
                        [types.KeyboardButton(text="JPY")]
                        ]

    keyboard = types.ReplyKeyboardMarkup(keyboard=currencies_start)

    await message.answer(start_text.format(user_name=message.from_user.full_name), reply_markup=keyboard)

    await state.set_state(UserStates.waiting_start_currency)


@router.message(lambda message: message.text in ["RUB", "USD", "EUR", "GBP", "JPY"],
                UserStates.waiting_start_currency)
async def start_currency(message: types.Message, state: FSMContext):
    selected_start_currency = message.text

    await state.update_data(selected_start_currency=selected_start_currency)

    await message.answer(f'Вы выбрали {selected_start_currency}. Напишите сумму:')

    await state.set_state(UserStates.waiting_start_amount)


@router.message(lambda message: message.text.isdigit(), UserStates.waiting_start_amount)
async def start_amount(message: types.Message, state: FSMContext):
    selected_start_currency = (await state.get_data())["selected_start_currency"]
    amount_start_text = message.text

    await state.update_data(amount_start_text=amount_start_text)

    currencies_end = [[types.KeyboardButton(text="RUB")],
                      [types.KeyboardButton(text="USD")],
                      [types.KeyboardButton(text="EUR")],
                      [types.KeyboardButton(text="GBP")],
                      [types.KeyboardButton(text="JPY")]
                      ]

    keyboard = types.ReplyKeyboardMarkup(keyboard=currencies_end)

    await message.answer(f'Теперь выберите в какой валюте конвертировать:', reply_markup=keyboard)

    await state.set_state(UserStates.waiting_end_currency)


async def get_exchange_rate(start_currency, end_currency):
    async with httpx.AsyncClient() as client:
        url = f"https://api.coingate.com/v2/rates/merchant/{start_currency}/{end_currency}"
        response = await client.get(url)
        data = response.json()
        return data


@router.message(lambda message: message.text in ["RUB", "USD", "EUR", "GBP", "JPY"],
                UserStates.waiting_end_currency)
async def end_currency(message: types.Message, state: FSMContext):
    selected_start_currency = (await state.get_data())["selected_start_currency"]
    amount_start_text = (await state.get_data())["amount_start_text"]
    selected_end_currency = message.text

    exchange_rate = await get_exchange_rate(selected_start_currency, selected_end_currency)

    if exchange_rate > 0.0:
        amount_in_start_currency = float(amount_start_text)
        converted_amount = amount_in_start_currency * exchange_rate

        result_message = f'{amount_start_text} {selected_start_currency} = {converted_amount:.2f} {selected_end_currency}\n\n' \
                         'Если хотите еще раз конвертировать, напишите /start.'
        await message.answer(result_message)
    else:
        await message.answer("К сожалению, не удалось получить курс конвертации.")


async def main():
    bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
