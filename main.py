import telebot as tb
from telebot import formatting as fmt
from telebot.util import quick_markup
import phonenumbers

import csv
import json
import math

NBSP: str = chr(int("A0", 16))
roll_threshold = 2

# Read configuration from file
with open("./boba.json", "r") as file:
    cfg = json.load(file)

print(f"Current environment: {cfg['_comment']}")
notify_cids = cfg["notify_cids"]
bot = tb.TeleBot(cfg["telegram_token"])
userdb = dict()
menudb = dict()


class Food:
    """Представляет пункт меню кафе"""

    id = "bytes"
    category = "bits"
    pretty_name = "Программистские Биты"
    price = 256

    def __init__(self, new_id, new_category, new_name, new_price):
        self.id = new_id
        self.category = new_category
        self.pretty_name = new_name
        self.price = new_price

    def __repr__(self):
        return f"Блюдо {self.pretty_name} ({self.id})"


class User:
    """Представляет досье на пользователя бота"""

    uid = 0
    uname = str()
    phone: phonenumbers.PhoneNumber = phonenumbers.PhoneNumber()
    sel: Food = Food("bytes", "bits", "Программистские биты", math.pi)
    cart = list()

    payment_cash = False
    address = str()
    time = str()
    comment = str()

    order_message_id = 0
    cart_message_id = 0

    roll_order = 0
    roll_cart = 0

    def __init__(self, new_uid, new_uname):
        self.uid = new_uid
        self.uname = new_uname
        self.cart = list()
        self.add2cart(food_by_id("utensils"))

    def set_phone(self, new_phone):
        try:
            self.phone = phonenumbers.parse(new_phone, "RU")
            return True
        except phonenumbers.phonenumberutil.NumberParseException:
            return False

    def print_phone(self):
        return phonenumbers.format_number(
            self.phone, phonenumbers.PhoneNumberFormat.NATIONAL
        ).translate({ord(c): None for c in "( )-"})

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
        """Удаляет невещественные записи в корзине"""
        kill_list = list()
        for i_item in range(len(self.cart)):
            if self.cart[i_item][1] <= 0:
                kill_list.append(i_item)

        for i in kill_list:
            print(f"Pruned {self.cart[i]}")
            self.cart.pop(i)

    def print_cart(self):
        ret = list()
        total = 0
        for food, n in self.cart:
            total += food.price * n
            ret.append(f"{fmt.hbold(str(n))}x {food.pretty_name} [{food.price}₽]")

        ret.append(f"{fmt.hbold('Итого:')}\t{total}₽")

        return "\n".join(ret)

    def print_order_details(self):
        ret = list()
        ret.append("Детали заказа:")
        payment_string = fmt.hbold("Оплата:")
        geo_string = fmt.hbold("Адрес:")
        timeam_string = fmt.hbold("Время:")

        if self.payment_cash:
            ret.append(payment_string + " 💸 наличными")
        else:
            ret.append(payment_string + " 💳 картой")

        if not self.address:
            ret.append(geo_string + " 📍 не указан")
        else:
            ret.append(geo_string + f" {self.address}")

        if not self.time:
            ret.append(timeam_string + " 🚄 Как можно скорее")
        else:
            ret.append(timeam_string + f" начнём в {self.time}")

        ret.append("")
        if self.comment:
            ret.append(f"{fmt.hbold('Комментарий:')} " + self.comment)
        else:
            ret.append(f"🪪🛇 {fmt.hitalic('Без комментариев')}")

        return "\n".join(ret)

    def clear(self):
        self.cart.clear()
        self.add2cart(food_by_id("utensils"))

    def __repr__(self):
        return f"Пользователь @{self.uname}/{self.uid} | тел{NBSP}{self.print_phone()}"


# menu_list = (Food("chuka", "salads", "Салат Чука"),)
# Load menu items from disk

menu_list = []

with open("menu.csv", "r") as menu_file:
    menu_reader = csv.reader(menu_file, delimiter=" ", quotechar="|")
    next(menu_reader)  # skip top row (menu header)

    for category, ID, pretty_name, price in menu_reader:
        menu_list.append(Food(ID, category, pretty_name, int(price)))

categories = []
for item in menu_list:
    if item.category not in categories:
        categories.append(item.category)

print(categories)
print(menu_list)


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

print(menudb)

menu_category_items = list()
menu_category_kbd = quick_markup(
    dict(
        [(key, {"callback_data": "m_" + key}) for key in categories]
        + [("🛒 Корзина", {"callback_data": "m_cart"})]
    ),
    row_width=2,
)

cart_edit_kbd = tb.types.ReplyKeyboardMarkup(
    row_width=5,
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Количество для заказа числом",
)

cart_edit_kbd.add("🗑️ Удалить", "1", "2", "4", "8")

rm_comment_kbd = tb.types.ReplyKeyboardMarkup(
    row_width=1,
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Ваш комментарий",
)
rm_comment_kbd.add("🛇 Удалить комментарий")

time_kbd = tb.types.ReplyKeyboardMarkup(
    row_width=1,
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Задержка заказа",
)
rm_comment_kbd.add("⏰ Как можно скорее")
# location_pick_kbd = tb.types.ReplyKeyboardMarkup(
#     row_width=1,
#     resize_keyboard=True,
#     one_time_keyboard=True,
#     input_field_placeholder="широ.та, долго.та",
# )
# location_pick_kbd.add(
#     tb.types.KeyboardButton(text="📍 Прислать локацию", request_location=True)
# )

# Commands definition
c_start = tb.types.BotCommand(command="start", description="Начало работы с ботом")
c_phone = tb.types.BotCommand(command="phone", description="Наcтройка номера телефона")
c_menu = tb.types.BotCommand(command="menu", description="Выбрать еду из меню")
c_cart = tb.types.BotCommand(command="cart", description="Редактировать корзину")
c_out = tb.types.BotCommand(command="checkout", description="Оформить заказ")
bot.set_my_commands([c_start, c_phone, c_menu, c_cart, c_out])


def get_user_or_bail(message):
    id = message.chat.id
    if id not in userdb.keys():
        print("Bailed — not good!")
        bot.send_message(
            chat_id=message.chat.id,
            reply_to_message_id=message.id,
            text=" ".join(
                [
                    "🛑 Мы потеряли вашу учётную запись из-за перезапуска бота.",
                    "Пожалуйста, используйте команду /start, чтобы продолжить.",
                    "Мы уже работаем над этой проблемой.",
                ]
            ),
        )
    else:
        return userdb[id]


@bot.message_handler(commands=["start"])
def on_start(message):
    id = message.chat.id
    guy = bot.get_chat_member(id, id).user
    if id not in userdb.keys():
        userdb[id] = User(id, guy.username)

    bot.set_chat_menu_button(message.chat.id, tb.types.MenuButtonCommands("commands"))

    if guy.username:
        bot.send_message(message.chat.id, f"Добрый день, @{guy.username}")
    else:
        bot.send_message(message.chat.id, "Добрый день!")

    if not userdb[id].phone.national_number:
        prompt_phone(message)
    else:
        verify_phone(message)


def verify_phone(message):
    user = get_user_or_bail(message)
    if not user:
        return None

    bot.send_message(
        chat_id=message.chat.id,
        text="\n".join(
            [
                f"Ваш номер телефона зарегистрирован как {user.print_phone()}",
                "Вы всегда можете изменить его командой /phone",
            ]
        ),
    )


@bot.message_handler(commands=["phone"])
def prompt_phone(message):
    bot.send_message(
        chat_id=message.chat.id,
        text="Пожалуйста укажите номер телефона для оформления заказа",
    )
    bot.register_next_step_handler_by_chat_id(message.chat.id, get_phone)


def get_phone(message):
    user = get_user_or_bail(message)
    if not user:
        return None

    if not user.set_phone(message.text):
        bot.send_message(
            message.chat.id, "Я не понимаю такой формат телефонного номера"
        )
        prompt_phone(message)
    else:
        verify_phone(message)
        menu(message)


@bot.message_handler(commands=["menu"])
def menu(message):
    with open("./assets/menu.png", "rb") as pic:
        bot.send_photo(
            chat_id=message.chat.id,
            photo=pic,
            caption="Вот, что мы можем предложить:",
            reply_markup=menu_category_kbd,
        )


@bot.callback_query_handler(func=lambda a: "m_" in a.data)
# m_ are global menu categories
def menu_category(callback):
    print(f"Callback: {callback.data}")

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
        checkout_begin(callback.message)
    elif cb not in menudb.keys():
        bot.send_message(
            chat_id=callback.message.chat.id,
            text="К сожалению, наши зайчики пока не готовят эту категорию :<",
        )
    else:
        kbd = tb.types.InlineKeyboardMarkup(row_width=2)
        buttons = list()
        for food in menudb[cb]:
            buttons.append(
                tb.types.InlineKeyboardButton(
                    text=f"{food.pretty_name}", callback_data=f"f_{food.id}"
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
    user = get_user_or_bail(callback.message)
    if not user:
        return None
    cb = callback.data.split("_")[1]

    food = food_by_id(cb)

    print(
        f"Menu order {food.pretty_name} chat.id {callback.message.chat.id} user.id {callback.message.from_user.id}"
    )

    user.add2cart(food)

    bot.send_message(
        chat_id=callback.message.chat.id,
        text=f"{fmt.hitalic(food.pretty_name)} добавлен в корзину",
        parse_mode="HTML",
    )


@bot.message_handler(commands=["cart"])
def cart(message):
    user = get_user_or_bail(message)
    if not user:
        return None

    user.cart_message_id = bot.send_message(
        chat_id=message.chat.id,
        text="У Вас в корзине:"
        + "\n"
        + user.print_cart()
        + "\n\n"
        + "Чтобы отредактировать количество, выберите товар из корзины",
        parse_mode="HTML",
        reply_markup=build_cart_keyboard(user),
    ).id


def update_cart(message):
    user = get_user_or_bail(message)
    if not user:
        return None
    id = message.chat.id

    if user.roll_cart >= roll_threshold:
        user.roll_cart = 0
        cart(message)
    else:
        user.roll_cart += 1
        bot.edit_message_text(
            chat_id=id,
            message_id=user.cart_message_id,
            text="У Вас в корзине:"
            + "\n"
            + user.print_cart()
            + "\n\n"
            + "Чтобы отредактировать количество, выберите товар из корзины",
            parse_mode="HTML",
            reply_markup=build_cart_keyboard(user),
        )


def build_cart_keyboard(user):
    kbd = tb.types.InlineKeyboardMarkup(row_width=2)
    items = []

    for food, q in user.cart:
        items.append(
            tb.types.InlineKeyboardButton(
                text=food.pretty_name, callback_data="c_" + food.id
            )
        )

    items.append(
        tb.types.InlineKeyboardButton(text="🪪 Оформить", callback_data="m_order")
    )

    kbd.add(*items)
    return kbd


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
    user = get_user_or_bail(message)
    if not user:
        return None
    user.sel = food_by_id(food_id)

    bot.send_message(
        chat_id=message.chat.id,
        text=f"{fmt.hbold(user.sel.pretty_name)}: введите количество для заказа числом",
        parse_mode="HTML",
        reply_markup=cart_edit_kbd,
    )
    bot.register_next_step_handler_by_chat_id(message.chat.id, cart_edit_n)


def cart_edit_n(message):
    user = get_user_or_bail(message)
    if not user:
        return None
    try:
        i = int(message.text.strip())
    except ValueError as err:
        if "🗑️" in message.text:
            bot.send_message(
                chat_id=message.chat.id,
                text=f"{fmt.hbold(user.sel.pretty_name)}: удалено из корзины",
                parse_mode="HTML",
                reply_markup=tb.types.ReplyKeyboardRemove(),
            )
            user.rm_cart(user.sel)
            cart(message)
        else:
            bot.send_message(
                chat_id=message.chat.id, text="Извините, не понимаю такое количество."
            )
            print(f"{err} trying to edit {user.sel}")
            cart_edit(message, user.sel)
    else:
        user.set_in_cart(user.sel, i)
        update_cart(message)
        bot.send_message(
            chat_id=message.chat.id,
            text=f"{fmt.hbold(user.sel.pretty_name)}: изменён",
            parse_mode="HTML",
            reply_markup=tb.types.ReplyKeyboardRemove(),
        )


@bot.message_handler(commands=["id"])
def id(message):
    bot.send_message(
        chat_id=message.chat.id,
        text=f"DEBUG|\nUID: {fmt.hpre(str(message.from_user.id))} CID: {fmt.hpre(str(message.chat.id))}",
        parse_mode="HTML",
    )


def build_checkout_keyboard(user):
    kbd = tb.types.InlineKeyboardMarkup(row_width=1)
    items = list()

    if user.payment_cash:
        items.append(
            tb.types.InlineKeyboardButton("💳 Оплата картой", callback_data="o_card")
        )
    else:
        items.append(
            tb.types.InlineKeyboardButton("💸 Оплата наличными", callback_data="o_cash")
        )

    items += [
        tb.types.InlineKeyboardButton(
            "📍 Установить адрес", callback_data="o_location"
        ),
        tb.types.InlineKeyboardButton("⏰ Установить время", callback_data="o_time"),
        tb.types.InlineKeyboardButton(
            "🪪 Изменить комментарий", callback_data="o_comment"
        ),
        tb.types.InlineKeyboardButton("📦🚀 Заказать", callback_data="o_checkout"),
    ]

    kbd.add(*items)
    return kbd


@bot.message_handler(commands=["checkout"])
def checkout_begin(message):
    user = get_user_or_bail(message)
    if not user:
        return None

    user.order_message_id = bot.send_message(
        message.chat.id,
        text=user.print_order_details(),
        parse_mode="HTML",
        reply_markup=build_checkout_keyboard(user),
    ).id


@bot.callback_query_handler(func=lambda a: "o_" in a.data)
def checkout_callback(callback):
    cb = callback.data.split("_")[1]
    user = get_user_or_bail(callback.message)
    if not user:
        return None
    print(f"Callback: {callback.data}")

    if cb == "card":
        user.payment_cash = False
        update_checkout(callback.message)
    elif cb == "cash":
        user.payment_cash = True
        update_checkout(callback.message)
    elif cb == "location":
        bot.send_message(
            chat_id=callback.message.chat.id,
            text=" ".join(
                [
                    "Пожалуйста, сообщите нам адрес для доставки в формате:",
                    "\nНаселённый пункт, улица, дом,",
                    "корпус/строение, подъезд, этаж, квартира, домофон.",
                    "\n\nЕсли ваш адрес не имеет чего-либо из перечисленного,",
                    "пропускайте этот пункт.",
                ]
            ),
        )
        bot.clear_step_handler_by_chat_id(callback.message.chat.id)
        bot.register_next_step_handler_by_chat_id(
            callback.message.chat.id, edit_location
        )
    elif cb == "time":
        bot.send_message(
            chat_id=callback.message.chat.id,
            text=" ".join(
                [
                    "Мы можем начать готовить с задержкой от времени получения заказа.",
                    "Введите время в любом удобном формате (5 минут; 12:21, через пол-часа)",
                ]
            ),
            reply_markup=time_kbd,
        )
        bot.clear_step_handler_by_chat_id(callback.message.chat.id)
        bot.register_next_step_handler_by_chat_id(callback.message.chat.id, edit_time)
    elif cb == "comment":
        bot.send_message(
            chat_id=callback.message.chat.id,
            text=" ".join(
                [
                    "Введите комментарий к заказу.",
                    "Наш персонал прочитает его, и перезвонит за подробностями,",
                    "если возникнет необходимость",
                ]
            ),
            reply_markup=rm_comment_kbd,
        )
        bot.clear_step_handler_by_chat_id(callback.message.chat.id)
        bot.register_next_step_handler_by_chat_id(
            callback.message.chat.id, edit_comment
        )
    elif cb == "checkout":
        checkout_end(callback.message)


def edit_location(message):
    user = get_user_or_bail(message)
    if not user:
        return None

    user.address = message.text
    bot.send_message(
        chat_id=message.chat.id,
        text="Адрес установлен",
        reply_markup=tb.types.ReplyKeyboardRemove(),
    )
    update_checkout(message)


def edit_time(message):
    user = get_user_or_bail(message)
    if not user:
        return None

    if "⏰" in message.text:
        user.comment = str()
        bot.send_message(
            chat_id=message.chat.id,
            text="Готовим как можно скорее",
            reply_markup=tb.types.ReplyKeyboardRemove(),
        )
    else:
        user.time = message.text
        bot.send_message(
            chat_id=message.chat.id,
            text="Время установлено",
            reply_markup=tb.types.ReplyKeyboardRemove(),
        )
    update_checkout(message)


def edit_comment(message):
    user = get_user_or_bail(message)
    if not user:
        return None

    if "🛇" in message.text:
        user.comment = str()
        bot.send_message(
            chat_id=message.chat.id,
            text="Комментарий успешно удалён",
            reply_markup=tb.types.ReplyKeyboardRemove(),
        )
    else:
        user.comment = message.text
        bot.send_message(
            chat_id=message.chat.id,
            text="Комментарий успешно отредактирован",
            reply_markup=tb.types.ReplyKeyboardRemove(),
        )
    update_checkout(message)


def update_checkout(message):
    user = get_user_or_bail(message)
    if not user:
        return None

    if user.roll_order >= roll_threshold:
        user.roll_order = 0
        checkout_begin(message)
    else:
        user.roll_order += 1
        try:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=user.order_message_id,
                text=user.print_order_details(),
                parse_mode="HTML",
                reply_markup=build_checkout_keyboard(user),
            )
        except tb.apihelper.ApiTelegramException as err:
            if "Bad Request: message is not modified" not in err.description:
                raise err


def checkout_end(message):
    user = get_user_or_bail(message)
    if not user:
        return None

    order_str = "\n".join(
        [
            f"{user.__repr__()} заказал(а):",
            user.print_cart(),
            "",
            user.print_order_details(),
        ]
    )
    bot.send_message(chat_id=message.chat.id, text="📦Заказ отправлен!🚀")
    for cid in notify_cids:
        bot.send_message(
            chat_id=cid,
            text=order_str,
            parse_mode="HTML",
            reply_markup=tb.types.ReplyKeyboardRemove(),
        )


@bot.message_handler(content_types=["text"])
@bot.message_handler(commands=["/help"])
def help(message):
    bot.send_message(
        chat_id=message.chat.id,
        text="""Здравствуйте, я бот Bunny Boba. Кажется вам нужна помощь. Для начала работы с ботом введите /start. 

/phone для настройки номера телефона.
/menu для вызова меню.
/cart для редактирования корзины. 
Чтобы оформить заказ введите /checkout

Если я не смог Вам помочь, обратиться в поддержку можно по номеру +79362822882)
""",
    )


if __name__ == "__main__":
    print("0x808A")
    bot.infinity_polling()
