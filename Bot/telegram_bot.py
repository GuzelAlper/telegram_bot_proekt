import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import config, json
import random, time
import threading
from datetime import datetime

# Bot token is specified here
bot = Bot(token="7913606906:AAEKq30JoHEI9MvUSSxVekYw5CIcUDrzLg0")

# Start the Dispatcher
dp = Dispatcher()

user_steps = {}
user_last_task = {}
user_last_task_time = {}
user_names = {}
user_lastnames = {}

# Define your MySQL database information here
host = r"localhost"  # or the IP address of your server
user = r"root"
password = ""
database = "telegram_bot"

# Create a connection
conn = config.create_connection(host, user, password, database)

async def check_dates():
    while True:
        print("Checking done")
        data = config.fetch_query(conn, f"SELECT * FROM users")
        for user in data:
            tasks = user["tasks"]
            
            if tasks == "":
                continue
            else:
                task_json = json.loads(tasks)
                task_list = task_json["tasks"]

                for task in task_list:
                    print("Checking task date")
                    task_time = task["time"]
                    datetime_object = datetime.strptime(task_time, '%m/%d/%y %H:%M')
                    now = datetime.now()
                    

                    if(now >= datetime_object):
                        user_message = f"Task Reminder!\n{task['task']}"
                        print("Query message created")
                        await bot.send_message(chat_id=user["tg_id"], text=user_message)

        time.sleep(60)

x = threading.Thread(target=check_dates)
x.start()

# Listens for the /delete command and takes an id parameter
@dp.message(Command("delete"))
async def delete_item(message: types.Message):
    # Let's get the arguments from the command (id)
    try:
        # Parse the command and the parameter
        args = message.text.split()[1:]

        # If an id parameter is given
        if args:
            # You can use the id to perform an operation
            data = config.fetch_query(conn, f"SELECT * FROM users WHERE tg_id={message.from_user.id}")
            data = data[0]
            tasks = data["tasks"]
            if tasks == "":
                await message.reply("There are no tasks!")
            else:
                task_json = json.loads(tasks)
                task_list = task_json["tasks"]

                a = 0
                for task in task_list:
                    if task["id"] == str(args[0]):
                        break
                    a += 1
                task_list.pop(a)
            config.execute_query(conn, f"UPDATE users SET tasks = '{json.dumps(task_json)}' WHERE tg_id='{message.from_user.id}'")
            await message.answer(f"Task deleted!")
            await user_main_menu(message)

        else:
            await message.reply("Please specify an ID. Example: /delete 12345")

    except Exception as e:
        await message.reply(f"Error: {e}")

# Handler for the /start command
@dp.message(Command("start"))
async def start(message: types.Message):
    # If the user is not registered, ask for their information in the database
    data = config.fetch_query(conn, f"SELECT * FROM users WHERE tg_id='{message.from_user.id}'")
    if len(data) > 0:
        # If registered, proceed to the main menu
        await user_main_menu(message)
    else:
        await user_register(message)

async def user_main_menu(message: types.Message):
    buttons = [
        [InlineKeyboardButton(text="Create New Task", callback_data="new_task")],
        [InlineKeyboardButton(text="List Tasks", callback_data="list_tasks")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer("Hello👋 Choose one of the buttons (Only English):", reply_markup=keyboard)

async def user_register(message: types.Message):
    step = get_user_step(message.from_user.id)
    if step == "name":
        set_user_step(message.from_user.id, "surname")
        await message.answer("Please enter your last name:")
    else:
        set_user_step(message.from_user.id, "name")
        await message.answer("Please enter your first name(Only English):")

# CREATE NEW TASK
@dp.callback_query(lambda callback_query: callback_query.data in ["new_task"])
async def handle_button_click(callback_query: types.CallbackQuery):
    set_user_step(callback_query.from_user.id, "new_task")
    await callback_query.message.answer("Please specify the task📝:")

# LIST TASKS
@dp.callback_query(lambda callback_query: callback_query.data in ["list_tasks"])
async def handle_button_click(callback_query: types.CallbackQuery):
    print(callback_query.from_user.id)
    data = config.fetch_query(conn, f"SELECT * FROM users WHERE tg_id={callback_query.from_user.id}")
    data = data[0]
    tasks = data["tasks"]
    if tasks == "":
        await callback_query.message.answer("No tasks found!")
        await user_main_menu(callback_query.message)
    else:
        task_json = json.loads(tasks)
        task_list = task_json["tasks"]

        for task in task_list:
            await callback_query.message.answer(f"Task ID: {task['id']}\nTask Name: {task['task']}\nTask Time:{task['time']}")
        
        await callback_query.message.answer("To delete a task 🗑️ :\n/delete [task id]")
        await user_main_menu(callback_query.message)

@dp.message()
async def handle_message(message: types.Message):
    user_step = get_user_step(message.from_user.id)

    if user_step == "new_task":
        user_last_task[message.from_user.id] = message.text
        await get_task_time_from_user(message)
    elif user_step == "new_task_time":
        #'09/19/22 13:55'
        datetime_str = message.text
        try:
            datetime_object = datetime.strptime(datetime_str, '%m/%d/%y %H:%M')
        except:
            await message.answer(f"Invalid date format🕙 Correct format: 09/19/22 13:55 (month/day/year hour)")
            await get_task_time_from_user(message)
            return

        user_last_task_time[message.from_user.id] = message.text
        data = config.fetch_query(conn, f"SELECT * FROM users WHERE tg_id={message.from_user.id}")
        print(data)
        tasks = data[0]["tasks"]

        task_data = {
            "id": str(random.randint(10000, 1000000)),
            "task": user_last_task[message.from_user.id],
            "time": user_last_task_time[message.from_user.id]
        }

        task_json = None

        if tasks == "":
            task_json = {
                "tasks": [task_data]
            }
        else:
            task_json = json.loads(tasks)
            task_json["tasks"].append(task_data)

        config.execute_query(conn, f"UPDATE users SET tasks = '{json.dumps(task_json)}' WHERE tg_id='{message.from_user.id}'")
        await message.answer(f"Task added✔️")
        await user_main_menu(message)
    elif user_step == "name":
        user_names[message.from_user.id] = message.text
        await user_register(message)
    elif user_step == "surname":
        user_lastnames[message.from_user.id] = message.text
        config.execute_query(conn, f"INSERT INTO users (name, surname, tg_id) VALUES ('{user_names[message.from_user.id]}', '{user_lastnames[message.from_user.id]}', '{message.from_user.id}')")
        await user_main_menu(message)

def set_user_step(id, step):
    user_steps[id] = step
    print(get_user_step(id))

def get_user_step(id):
    if id in user_steps:
        return user_steps[id]
    
    return ""

# New task time step
async def get_task_time_from_user(message: types.Message):
    set_user_step(message.from_user.id, "new_task_time")
    await message.answer("Please enter the task time 🕙 (Correct format: 09/19/22 13:55 (month/day/year hour):")

# Main function
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

# Run the main function with asyncio
if __name__ == "__main__":
    asyncio.run(main())
