import telebot as tb
from telebot import formatting
import phonenumbers

# Read token from file
with open("./.token", "r") as file:
    token = file.read().rstrip("\n")

bot = tb.TeleBot(token)
userdb = dict()
menudb = dict()
categories = {
    "Напитки": "drinks",
    "Комбо": "combo",
    "Десерты": "desserts",
    "Сеты": "sets",
    "Роллы": "rolls",
    "Онигири": "onigiri",
    "Супы": "soups",
    "Салаты": "salads",
}

notify_cids = [-1002574327978]


class Food:
    id = "bytes"
    category = "bits"
    pretty_name = "Программистские Биты"

    def __init__(self, new_id, new_category, new_name):
        self.id = new_id
        self.category = new_category
        self.pretty_name = new_name


class User:
    uid = 0
    uname = str()
    phone = phonenumbers.PhoneNumber()
    sel = None
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
        return phonenumbers.format_number(
            self.phone, phonenumbers.PhoneNumberFormat.NATIONAL
        )

    def add2cart(self, food):
        for i_item in range(len(self.cart)):
            if self.cart[i_item][0].id == food.id:
                self.cart[i_item][1] += 1
                return True
        self.cart.append([food, 1])

        return True

    def rm_cart(self, food):
        for i_item in range(len(self.cart)):
            if self.cart[i_item][0].id == food.id:
                self.cart[i_item][1] -= 1
            if self.cart[i_item][1] <= 0:
                self.cart.pop(i_item)
                return True

        return False

    def print_cart(self):
        ret = ["У Вас в корзине:"]
        for item in self.cart:
            ret.append(f"{formatting.hbold(str(item[1]))}x {item[0].pretty_name}")

        return "\n".join(ret)

    def __repr__(self):
        return f"Пользователь {self.uname}/{self.uid} | тел {self.print_phone()}"


menu_list = (Food("chuka", "salads", "Салат Чука"),)

for food in menu_list:
    if food.category not in menudb.keys():
        menudb[food.category] = list()
    menudb[food.category].append(food)

menu_category_items = list()
menu_category_kbd = tb.types.InlineKeyboardMarkup(row_width=2)

for key in categories.keys():
    menu_category_items.append(
        tb.types.InlineKeyboardButton(text=key, callback_data="m_" + categories[key])
    )

menu_category_items.append(
    tb.types.InlineKeyboardButton(text="🛒 Корзина", callback_data="m_cart")
)
menu_category_kbd.add(*menu_category_items)

# Commands definition
c_start = tb.types.BotCommand(command="start", description="Начало работы с ботом")
c_phone = tb.types.BotCommand(command="phone", description="Наcтройка номера телефона")
c_menu = tb.types.BotCommand(command="menu", description="Выбрать еду из меню")
c_cart = tb.types.BotCommand(command="cart", description="Редактировать корзину")
c_out = tb.types.BotCommand(command="checkout", description="Оформить заказ")
bot.set_my_commands([c_start, c_phone, c_menu, c_cart, c_out])


@bot.message_handler(commands=["start"])
def on_start(message):
    if message.from_user.id not in userdb.keys():
        userdb[message.from_user.id] = User(
            message.from_user.id, message.from_user.username
        )

    bot.set_chat_menu_button(message.chat.id, tb.types.MenuButtonCommands("commands"))

    bot.send_message(message.chat.id, f"Добрый день, @{message.from_user.username}")

    if not userdb[message.from_user.id].phone.national_number:
        prompt_phone(message)
    else:
        verify_phone(message)


def verify_phone(message):
    bot.send_message(
        message.chat.id,
        f"""Ваш номер телефона зарегистрирован как {userdb[message.from_user.id].print_phone()}
Вы всегда можете изменить его командой /phone""",
    )


@bot.message_handler(commands=["phone"])
def prompt_phone(message):
    bot.send_message(
        message.chat.id, f"Пожалуйста укажите номер телефона для оформления заказа"
    )
    bot.register_next_step_handler(message, get_phone)


def get_phone(message):
    if not userdb[message.from_user.id].set_phone(message.text):
        bot.send_message(
            message.chat.id, f"Я не понимаю такой формат телефонного номера"
        )
        prompt_phone(message)
    else:
        verify_phone(message)
        menu(message)


@bot.message_handler(commands=["menu"])
def menu(message):
    global menu_category_kbd

    with open("./assets/menu.png", "rb") as pic:
        bot.send_photo(
            message.chat.id,
            pic,
            caption="Здесь должно быть меню, но его съел зайчик >;3",
            reply_markup=menu_category_kbd,
        )


@bot.callback_query_handler(func=lambda a: "m_" in a.data)
# m_ are global menu categories
def menu_category(callback):
    global menu_category_kbd

    cb = callback.data.split("_")[1]

    if cb == "menu":
        bot.edit_message_caption(
            caption="Здесь должно быть меню, но его съел зайчик >;3",
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            reply_markup=menu_category_kbd,
        )
    elif cb == "cart":
        cart(callback.message)
    elif cb not in menudb.keys():
        bot.send_message(
            callback.message.chat.id,
            "К сожалению, наши зайчики пока не готовят эту категорию :<",
        )
    else:
        kbd = tb.types.InlineKeyboardMarkup(row_width=2)
        buttons = list()
        for food in menudb[cb]:
            buttons.append(
                tb.types.InlineKeyboardButton(
                    text=food.pretty_name, callback_data=f"f_{food.id}"
                )
            )
        buttons.append(
            tb.types.InlineKeyboardButton(text="⏎ Назад", callback_data="m_menu")
        )

        kbd.add(*buttons)
        bot.edit_message_caption(
            caption=callback.message.caption,
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            reply_markup=kbd,
        )


@bot.callback_query_handler(func=lambda a: "f_" in a.data)
# f_ are individual food items
def menu_order(callback):
    cb = callback.data.split("_")[1]
    food = None

    for key in menudb.keys():
        for try_food in menudb[key]:
            if cb == try_food.id:
                food = try_food

    if not food:
        raise KeyError

    print(
        f"Menu order {food.pretty_name} chat.id {callback.message.chat.id} user.id {callback.message.from_user.id}"
    )

    userdb[callback.message.chat.id].add2cart(food)

    bot.send_message(
        callback.message.chat.id,
        f"{formatting.hitalic(food.pretty_name)} добавлен в корзину",
        parse_mode="HTML",
    )


@bot.message_handler(commands=["cart"])
def cart(message):
    bot.send_message(
        message.chat.id, userdb[message.chat.id].print_cart(), parse_mode="HTML"
    )
    print(userdb)


@bot.message_handler(commands=["id"])
def id(message):
    bot.send_message(
        message.chat.id,
        f"DEBUG|\nUID: {formatting.hpre(str(message.from_user.id))} CID: {formatting.hpre(str(message.chat.id))}",
        parse_mode="HTML",
    )


@bot.message_handler(commands=["checkout"])
def checkout(message):
    order_str = f"{userdb[message.from_user.id].__repr__()}\nЗаказал(а) биты да байты."
    bot.send_message(message.chat.id, "ВНИМАНИЕ: функционал в разработке")
    for cid in notify_cids:
        bot.send_message(cid, order_str)


bot.infinity_polling()
