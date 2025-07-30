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

    def __repr__(self):
        return f"Блюдо {self.pretty_name} ({self.id})"


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
        self.prune()

        return True

    def set_in_cart(self, food, n):
        for i_item in range(len(self.cart)):
            if self.cart[i_item][0].id == food.id:
                self.cart[i_item][1] = n
                self.prune()

    def rm_cart(self, food):
        for i_item in range(len(self.cart)):
            if self.cart[i_item][0].id == food.id:
                self.cart[i_item][1] -= 1
            if self.cart[i_item][1] <= 0:
                self.cart.pop(i_item)
                self.prune()
                return True

        return False

    def prune(self):
        kill_list = list()
        for i_item in range(len(self.cart)):
            if not self.cart[i_item][1]:
                kill_list.append(i_item)

        for i in kill_list:
            print(f"Pruned {self.cart[i]}")
            self.cart.pop(i)

    def print_cart(self):
        ret = ["У Вас в корзине:"]
        for food, n in self.cart:
            ret.append(f"{formatting.hbold(str(n))}x {food.pretty_name}")

        return "\n".join(ret)

    def __repr__(self):
        return f"Пользователь {self.uname}/{self.uid} | тел {self.print_phone()}"


menu_list = (Food("chuka", "salads", "Салат Чука"),)


def food_by_id(id):
    food = None

    for key in menudb.keys():
        for try_food in menudb[key]:
            if id == try_food.id:
                food = try_food

    if not food:
        raise KeyError

    return food


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
            caption="Вот, что мы можем предложить:",
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            reply_markup=menu_category_kbd,
        )
    elif cb == "cart":
        cart(callback.message)
    elif cb == "order":
        checkout(callback.message)
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

    food = food_by_id(cb)

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
    user = userdb[message.chat.id]
    kbd = tb.types.InlineKeyboardMarkup(row_width=2)
    items = []

    for food, q in user.cart:
        items.append(
            tb.types.InlineKeyboardButton(
                text=food.pretty_name, callback_data="c_" + food.id
            )
        )

    items.append(
        tb.types.InlineKeyboardButton(text="📦🚀 Заказать", callback_data="m_order")
    )

    kbd.add(*items)

    bot.send_message(
        message.chat.id,
        user.print_cart()
        + "\n\n"
        + "Чтобы отредактировать количество, выберите товар из корзины",
        parse_mode="HTML",
        reply_markup=kbd,
    )
    print(userdb)


@bot.callback_query_handler(func=lambda a: "c_" in a.data)
def cart_edit_callback(callback):
    cb = callback.data.split("_")[1]
    cart_edit(callback.message, cb)

    # Кнопочный интерфейс редактирования корзины
    # kbd = tb.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    # items = [
    #     tb.types.KeyboardButton(text="➕"),
    #     tb.types.KeyboardButton(text="➖"),
    #     tb.types.KeyboardButton(text="🗑️"),
    #     tb.types.KeyboardButton(text="⏎ Назад")
    # ]
    # kbd.add(*items)


def cart_edit(message, food_id):
    user = userdb[message.chat.id]
    user.sel = food_by_id(food_id)

    kbd = tb.types.ReplyKeyboardMarkup(
        row_width=5,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Количество для заказа числом",
    )
    items = [
        tb.types.KeyboardButton(text="0"),
        tb.types.KeyboardButton(text="1"),
        tb.types.KeyboardButton(text="2"),
        tb.types.KeyboardButton(text="4"),
        tb.types.KeyboardButton(text="8"),
    ]

    kbd.add(*items)

    bot.send_message(
        message.chat.id,
        text=f"{user.sel.pretty_name}: введите количество для заказа числом",
        reply_markup=kbd,
    )
    bot.register_next_step_handler(message, cart_edit_n)


def cart_edit_n(message):
    user = userdb[message.chat.id]
    try:
        i = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "Извините, не понимаю такое количество.")
        print(f"Trying to edit {user.sel}")
        cart_edit(message, user.sel)
    else:
        user.set_in_cart(user.sel, i)
        cart(message)


@bot.message_handler(commands=["id"])
def id(message):
    bot.send_message(
        message.chat.id,
        f"DEBUG|\nUID: {formatting.hpre(str(message.from_user.id))} CID: {formatting.hpre(str(message.chat.id))}",
        parse_mode="HTML",
    )


@bot.message_handler(commands=["checkout"])
def checkout(message):
    user = userdb[message.chat.id]

    order_str = f"{user.__repr__()} заказал(а):\n" + user.print_cart()
    bot.send_message(
        message.chat.id,
        "Заказ отправлен!\nВНИМАНИЕ: функционал в разработке",
    )
    for cid in notify_cids:
        bot.send_message(cid, order_str, parse_mode="HTML")

    user.cart.clear()


@bot.message_handler(content_types=["text"])
@bot.message_handler(commands=["/help"])
def help(message):
    bot.send_message(message.chat.id, "Бегите, глупцы")


bot.infinity_polling()
