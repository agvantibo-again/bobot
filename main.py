import telebot as tb
import phonenumbers

import enum

# Read token from file
with open("./.token", "r") as file:
    token = file.read().rstrip("\n")

bot = tb.TeleBot(token)
userdb = dict()
menudb = dict()

notify_cids = [-1002574327978]

# class FoodCategory(enum.Enum):

class Food:
    id = 'bytes'
    category = 'bits'
    pretty_name = "Программистские Биты"

    def __init__(self, new_id, new_category, new_name):
        self.id = new_id
        self.category = new_category
        self.pretty_name = new_name


class User:
    uid = 0
    uname = None
    phone = None
    cart = list()

    def __init__(self, new_uid, new_uname):
        self.uid = new_uid
        self.uname = new_uname
        self.cart = list()

    def set_phone(self, new_phone):
        try:
            self.phone = phonenumbers.parse(new_phone, "RU")
            return True
        except phonenumbers.phonenumberutil.NumberParseException:
            return False

    def print_phone(self):
        return phonenumbers.format_number(self.phone, phonenumbers.PhoneNumberFormat.NATIONAL)

    def __repr__(self):
        return f"Пользователь {self.uname}/{self.uid} | тел {self.print_phone()}"


menu_list = (
    Food("chuka", "salads", "Салат Чука"),
)

for food in menu_list:
    if food.category not in menudb.keys():
        menudb[food.category] = list()
    menudb[food.category].append(food)

# Commands definition
c_start = tb.types.BotCommand(command="start", description="Начало работы с ботом")
c_phone = tb.types.BotCommand(command="phone", description="Наcтройка номера телефона")
c_menu = tb.types.BotCommand(command="menu", description="Выбрать еду из меню")
c_out = tb.types.BotCommand(command="checkout", description="Оформить заказ")
bot.set_my_commands([c_start, c_phone, c_menu, c_out])


@bot.message_handler(commands=["start"])
def on_start(message):
    if message.from_user.id not in userdb.keys():
        userdb[message.from_user.id] = User(message.from_user.id, message.from_user.username)

    bot.set_chat_menu_button(message.chat.id, tb.types.MenuButtonCommands('commands'))

    bot.send_message(message.chat.id, f"Добрый день, @{message.from_user.username}")

    if not userdb[message.from_user.id].phone:
        prompt_phone(message)
    else:
        verify_phone(message)


def verify_phone(message):
    bot.send_message(
        message.chat.id,
        f'''Ваш номер телефона зарегистрирован как {userdb[message.from_user.id].print_phone()}
Вы всегда можете изменить его командой /phone'''
    )

@bot.message_handler(commands=["phone"])
def prompt_phone(message):
    bot.send_message(message.chat.id, f"Пожалуйста укажите номер телефона для оформления заказа")
    bot.register_next_step_handler(message, get_phone)


def get_phone(message):
    if not userdb[message.from_user.id].set_phone(message.text):
        bot.send_message(message.chat.id, f"Я не понимаю такой формат телефонного номера")
        prompt_phone(message)
    else:
        verify_phone(message)
        menu(message)


@bot.message_handler(commands=["menu"])
def menu(message):
    kbd = tb.types.InlineKeyboardMarkup(row_width=2)
    items = (
        tb.types.InlineKeyboardButton(text="Комбо", callback_data="m_combo"),
        tb.types.InlineKeyboardButton(text="Напитки", callback_data="m_drinks"),
        tb.types.InlineKeyboardButton(text="Десерты", callback_data="m_desserts"),
        tb.types.InlineKeyboardButton(text="Сеты", callback_data="m_sets"),
        tb.types.InlineKeyboardButton(text="Роллы", callback_data="m_rolls"),
        tb.types.InlineKeyboardButton(text="Онигири", callback_data="m_onigiri"),
        tb.types.InlineKeyboardButton(text="Супы", callback_data="m_soups"),
        tb.types.InlineKeyboardButton(text="Салаты", callback_data="m_salads"),
        tb.types.InlineKeyboardButton(text="Перейти в корзину", callback_data="m_cart"),
    )
    kbd.add(*items)

    with open("./assets/menu.png", "rb") as pic:
        bot.send_photo(message.chat.id, pic, caption=f"Здесь должно быть меню, но его съел зайчик >;3", show_caption_above_media=True, reply_markup=kbd)


@bot.callback_query_handler(func=lambda a: "m_" in a.data)
def menu_category(callback):
    cb = callback.data.split("_")[1]
    if cb == "menu":
        menu(callback.message)
    elif cb not in menudb.keys():
        bot.send_message(callback.message.chat.id, "К сожалению, наши зайчики пока не готовят эту категорию :<")
    else:
        kbd = tb.types.InlineKeyboardMarkup(row_width=2)
        buttons = list()
        for food in menudb[cb]:
            buttons.append(tb.types.InlineKeyboardButton(text=food.pretty_name, callback_data=f"f_{food.id}"))
        buttons.append(tb.types.InlineKeyboardButton(text="⏎ Назад", callback_data="m_menu"))

        kbd.add(*buttons)
        bot.send_message(callback.message.chat.id, "Вот, что мы можем предложить:", reply_markup=kbd)


@bot.message_handler(commands=["id"])
def id(message):
    bot.send_message(message.chat.id, f"DEBUG|\nUID: {tb.formatting.hpre(str(message.from_user.id))} CID: {tb.formatting.hpre(str(message.chat.id))}", parse_mode='HTML')


@bot.message_handler(commands=["checkout"])
def checkout(message):
    order_str = f"{userdb[message.from_user.id].__repr__()}\nЗаказал(а) биты да байты."
    bot.send_message(message.chat.id, "ВНИМАНИЕ: функционал в разработке")
    for cid in notify_cids:
        bot.send_message(cid, order_str)


bot.infinity_polling()
