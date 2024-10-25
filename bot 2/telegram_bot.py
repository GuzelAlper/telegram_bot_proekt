import asyncio
import firebase_admin
from firebase_admin import credentials, firestore
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import json
import random
import threading
from datetime import datetime

# Инициализация Firebase
cred = credentials.Certificate(
    "C:/Users/Артур/Desktop/ToDoList/tgbot-7bacf-firebase-adminsdk-xo9jd-0548057ff1.json"
)
firebase_admin.initialize_app(cred)
db = firestore.client()

# Bot token is specified here
bot = Bot(token="7914931445:AAHv6XAdrREpjoo9Yam6sm7sDjAJyMSUMqI")
dp = Dispatcher()
user_steps = {}
user_last_task = {}
user_last_task_time = {}
user_last_task_category = {}
user_names = {}
user_lastnames = {}


async def check_dates():
    while True:
        print("Checking done")
        users_ref = db.collection("users").stream()
        for user in users_ref:
            user_data = user.to_dict()
            tasks = user_data.get("tasks", [])
            if not tasks:
                continue

            for task in tasks:
                task_time = task["time"]
                datetime_object = datetime.strptime(task_time, "%m/%d/%y %H:%M")
                now = datetime.now()

                if now >= datetime_object:
                    user_message = (
                        f"Task Reminder!\n{task['task']} (Category: {task['category']})"
                    )
                    print("Query message created")
                    await bot.send_message(
                        chat_id=user_data["tg_id"], text=user_message
                    )

        await asyncio.sleep(60)


x = threading.Thread(target=lambda: asyncio.run(check_dates()))
x.start()


@dp.message(Command("delete"))
async def delete_item(message: types.Message):
    await message.answer("Чтобы удалить задачу, используйте кнопки в списке задач.")


@dp.message(Command("start"))
async def start(message: types.Message):
    user_ref = db.collection("users").document(str(message.from_user.id))
    user_data = user_ref.get()
    if user_data.exists:
        await user_main_menu(message)
    else:
        await user_register(message)


async def user_main_menu(message: types.Message):
    buttons = [
        [InlineKeyboardButton(text="Создать новую задачу", callback_data="new_task")],
        [InlineKeyboardButton(text="Список задач", callback_data="list_tasks")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Привет👋 Выберите одну из кнопок:", reply_markup=keyboard)


async def user_register(message: types.Message):
    step = get_user_step(message.from_user.id)
    if step == "name":
        set_user_step(message.from_user.id, "surname")
        await message.answer("Пожалуйста, введите вашу фамилию:")
    else:
        set_user_step(message.from_user.id, "name")
        await message.answer("Пожалуйста, введите ваше имя:")


@dp.callback_query(lambda callback_query: callback_query.data in ["new_task"])
async def handle_button_click(callback_query: types.CallbackQuery):
    set_user_step(callback_query.from_user.id, "new_task")
    await callback_query.message.answer("Пожалуйста, укажите задачу📝:")


@dp.callback_query(lambda callback_query: callback_query.data in ["list_tasks"])
async def handle_button_click(callback_query: types.CallbackQuery):
    user_ref = db.collection("users").document(str(callback_query.from_user.id))
    user_data = user_ref.get()
    if user_data.exists:
        tasks = user_data.to_dict().get("tasks", [])
        if not tasks:
            await callback_query.message.answer("Задач не найдено!")
        else:
            for task in tasks:
                delete_button = InlineKeyboardButton(
                    text="Удалить", callback_data=f"delete_task_{task['id']}"
                )
                task_keyboard = InlineKeyboardMarkup(inline_keyboard=[[delete_button]])
                await callback_query.message.answer(
                    f"ID задачи: {task['id']}\nНазвание задачи: {task['task']}\nВремя задачи: {task['time']}\nОписание: {task['category']}",
                    reply_markup=task_keyboard,
                )
            await callback_query.message.answer(
                "Чтобы удалить задачу, нажмите на кнопку 'Удалить'."
            )
    else:
        await callback_query.message.answer("Пользователь не найден.")
    await user_main_menu(callback_query.message)


@dp.callback_query(
    lambda callback_query: callback_query.data.startswith("delete_task_")
)
async def delete_task(callback_query: types.CallbackQuery):
    task_id = callback_query.data.split("_")[2]
    user_ref = db.collection("users").document(str(callback_query.from_user.id))
    user_data = user_ref.get()

    if user_data.exists:
        tasks = user_data.to_dict().get("tasks", [])
        task_to_delete = next((task for task in tasks if task["id"] == task_id), None)
        if task_to_delete:
            tasks.remove(task_to_delete)
            user_ref.update({"tasks": tasks})
            await callback_query.answer("Задача удалена!", show_alert=True)
        else:
            await callback_query.answer("Задача не найдена!", show_alert=True)
    else:
        await callback_query.answer("Пользователь не найден!", show_alert=True)


@dp.message()
async def handle_message(message: types.Message):
    user_step = get_user_step(message.from_user.id)

    if user_step == "new_task":
        user_last_task[message.from_user.id] = message.text
        await get_task_time_from_user(message)
    elif user_step == "new_task_time":
        datetime_str = message.text
        try:
            datetime_object = datetime.strptime(datetime_str, "%m/%d/%y %H:%M")
        except:
            await message.answer(
                "Неверный формат даты🕙 Правильный формат: 09/19/22 13:55 (месяц/день/год час)"
            )
            await get_task_time_from_user(message)
            return

        user_last_task_time[message.from_user.id] = message.text
        await get_task_category_from_user(message)
    elif user_step == "new_task_category":
        user_last_task_category[message.from_user.id] = message.text
        user_ref = db.collection("users").document(str(message.from_user.id))
        user_data = user_ref.get()

        if user_data.exists:
            tasks = user_data.to_dict().get("tasks", [])
            task_data = {
                "id": str(random.randint(10000, 1000000)),
                "task": user_last_task[message.from_user.id],
                "time": user_last_task_time[message.from_user.id],
                "category": user_last_task_category[message.from_user.id],
            }
            tasks.append(task_data)
            user_ref.update({"tasks": tasks})
            await message.answer("Задача добавлена✔️")
        else:
            await message.answer("Пользователь не найден.")

        await user_main_menu(message)
    elif user_step == "name":
        user_names[message.from_user.id] = message.text
        await user_register(message)
    elif user_step == "surname":
        user_lastnames[message.from_user.id] = message.text
        add_user(
            user_names[message.from_user.id],
            user_lastnames[message.from_user.id],
            message.from_user.id,
        )
        await user_main_menu(message)


def add_user(name, surname, tg_id):
    user_ref = db.collection("users").document(str(tg_id))
    user_ref.set({"name": name, "surname": surname, "tg_id": tg_id, "tasks": []})


def set_user_step(id, step):
    user_steps[id] = step
    print(get_user_step(id))


def get_user_step(id):
    return user_steps.get(id, "")


async def get_task_time_from_user(message: types.Message):
    set_user_step(message.from_user.id, "new_task_time")
    await message.answer(
        "Пожалуйста, введите время задачи 🕙 (Правильный формат: 09/19/22 13:55 (месяц/день/год час)): "
    )


async def get_task_category_from_user(message: types.Message):
    set_user_step(message.from_user.id, "new_task_category")
    await message.answer("Пожалуйста, введите описание задачи:")


# Основная функция
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


# Запуск основной функции с использованием asyncio
if __name__ == "__main__":
    asyncio.run(main())
