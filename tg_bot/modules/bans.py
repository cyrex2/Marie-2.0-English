import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import run_async, CommandHandler, Filters
from telegram.utils.helpers import mention_html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery

from tg_bot import dispatcher, BAN_STICKER, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_ban_protected, can_restrict, \
    is_user_admin, is_user_in_chat, is_bot_admin
from tg_bot.modules.helper_funcs.extraction import extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.helper_funcs.filters import CustomFilters

RBAN_ERRORS = {
    "Bir yöneticin banlanmasında rol almamayı tercih ederim 😳 ",
    "Sohbet bulunamadı",
    "Sohbet üyelerini kısıtlamak/kısıtlamayı kaldırmak için yeterli yetki yok",
    "Kullanıcı_bir_katılımcı_değil",
    "Peer_id_invalid",
    "Grup sohbeti devre dışı bırakıldı",
    "Basit bir gruptan banlamak için kullanıcının davetli olması gerekir",
    "Chat_admin_required",
    "Yalnızca grubun kurucusu grup yöneticilerini atabilir",
    "Channel_private",
    "Sohbette değil"
}

RUNBAN_ERRORS = {
    "Bir yöneticin banlanmasında rol almamayı tercih ederim 😳 ",
    "Sohbet bulunamadı",
    "Sohbet üyelerini kısıtlamak/kısıtlamayı kaldırmak için yeterli yetki yok",
    "Kullanıcı_bir_katılımcı_değil",
    "Peer_id_invalid",
    "Grup sohbeti devre dışı bırakıldı",
    "Basit bir gruptan banlamak için kullanıcının davetli olması gerekir",
    "Chat_admin_required",
    "Yalnızca grubun kurucusu grup yöneticilerini atabilir",
    "Channel_private",
    "Sohbette değil"
}



@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Bu kullanıcıyı bulamıyorum")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Bir yöneticin banlanmasında rol almamayı tercih ederim 😳")
        return ""

    if user_id == bot.id:
        message.reply_text("Düşene bir tekme de sen vurma🙏")
        return ""

    log = "<b>{}:</b>" \
          "\n#Banlandı" \
          "\n<b>Admin:</b> {}" \
          "\n<b>Kullanıcı:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name))
    if reason:
        log += "\n<b>Sebep:</b> {}".format(reason)

    try:
        chat.kick_member(user_id)
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        keyboard = []
        reply = "{} kullanıcısı yönetici tarafından tekmelendi".format(mention_html(member.user.id, member.user.first_name))
        message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text('Banlandı!', quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Kahretsin, bu kullanıcıyı yasaklayamam")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Bu kullanıcıyı bulamıyorum.")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Bir yöneticin banlanmasında rol almamayı tercih ederim 😳")
        return ""

    if user_id == bot.id:
        message.reply_text("Düşene bir tekme de sen vurma🙏")
        return ""

    if not reason:
        message.reply_text("Bu kullanıcıyı banlamak için bir süre belirtmediniz!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    bantime = extract_time(message, time_val)

    if not bantime:
        return ""

    log = "<b>{}:</b>" \
          "\n#TEMP BANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>Kullanıcı:</b> {}" \
          "\n<b>Süre:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name), time_val)
    if reason:
        log += "\n<b>Sebep:</b> {}".format(reason)

    try:
        chat.kick_member(user_id, until_date=bantime)
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        message.reply_text("Banned! User will be banned for {}.".format(time_val))
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text("Kullanıcı şu kadar süre banlandı:{}.".format(time_val), quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Kahretsin, bu kullanıcıyı yasaklayamam.")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def kick(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Bu kullanıcıyı bulamıyorum")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id):
        message.reply_text("Bir yöneticin banlanmasında rol almamayı tercih ederim 😳")
        return ""

    if user_id == bot.id:
        message.reply_text("Bunu yapmak zorunda mıyım?")
        return ""

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        message.reply_text("Atıldı!")
        log = "<b>{}:</b>" \
              "\n#Atıldı" \
              "\n<b>Admin:</b> {}" \
              "\n<b>Kullanıcı:</b> {}".format(html.escape(chat.title),
                                         mention_html(user.id, user.first_name),
                                         mention_html(member.user.id, member.user.first_name))
        if reason:
            log += "\n<b>Sebep:</b> {}".format(reason)

        return log

    else:
        message.reply_text("Kahretsin, bu kullanıcıyı yasaklayamam")

    return ""


@run_async
@bot_admin
@can_restrict
def kickme(bot: Bot, update: Update):
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("Beni güldürme, sen bir yöneticisin.")
        return

    res = update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text("No problem.")
    else:
        update.effective_message.reply_text("Yapamam :/")


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def unban(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Bu kullanıcıyı bulamıyorum")
            return ""
        else:
            raise

    if user_id == bot.id:
        message.reply_text("Dostum...Bu espriye gülmeli miyim?")
        return ""

    if is_user_in_chat(chat, user_id):
        message.reply_text("Zaten yasaklı olmayan birinin yasağını nasıl kaldırabilirim ki?")
        return ""

    chat.unban_member(user_id)
    message.reply_text("Tamamdır. Tekrar teşrif edebilirler")

    log = "<b>{}:</b>" \
          "\n#YasakKaldırma" \
          "\n<b>Admin:</b> {}" \
          "\n<b>Kullanıcı:</b> {}".format(html.escape(chat.title),
                                     mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name))
    if reason:
        log += "\n<b>Sebep:</b> {}".format(reason)

    return log


@run_async
@bot_admin
def rban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    if not args:
        message.reply_text("Bir sohbete veya kişiye atıfta bulunmuyorsun.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir kişiye atıfta bulunmuyorsun.")
        return
    elif not chat_id:
        message.reply_text("Bir sohbete atıfta bulunmuyorsun.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Chat not found":
            message.reply_text("Sohbet bulunamadı! Geçerli bir sohbet kimliği girdiğinizden ve bu sohbetin bir parçası olduğumdan emin olun.")
            return
        else:
            raise

    if chat.type == 'private':
        message.reply_text("Üzgünüm, ama bu özel bir sohbet!")
        return

    if not is_bot_admin(chat, bot.id) or not chat.get_member(bot.id).can_restrict_members:
        message.reply_text("Oradaki insanları kısıtlayamıyorum! Yönetici olduğumdan ve kullanıcıları yasaklayabildiğimden emin olun.")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Bu kullanıcıyı bulamıyorum")
            return
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Bir yöneticin banlanmasında rol almamayı tercih ederim 😳")
        return

    if user_id == bot.id:
        message.reply_text("Bu espriye gülmeyeceğim")
        return

    try:
        chat.kick_member(user_id)
        message.reply_text("Banlandı!")
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text('Banned!', quote=False)
        elif excp.message in RBAN_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Kahretsin! Bu kullanıcıyı yasaklayamam")

@run_async
@bot_admin
def runban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    if not args:
        message.reply_text("Bir sohbete veya kişiye atıfta bulunmuyorsun.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir kişiye atıfta bulunmuyorsun.")
        return
    elif not chat_id:
        message.reply_text("Bir sohbete atıfta bulunmuyorsun.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Sohbet Bulunamadı":
            message.reply_text("Sohbet bulunamadı! Geçerli bir sohbet kimliği girdiğinizden ve bu sohbetin bir parçası olduğumdan emin olun.")
            return
        else:
            raise

    if chat.type == 'private':
        message.reply_text("Üzgünüm, ama bu özel bir sohbet!")
        return

    if not is_bot_admin(chat, bot.id) or not chat.get_member(bot.id).can_restrict_members:
        message.reply_text("Oradaki insanları sınırlayamıyorum! Yönetici olduğumdan ve kullanıcıların yasaklayabildiğimden emin olun.")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Bu kullanıcıyı orada bulamıyorum")
            return
        else:
            raise
            
    if is_user_in_chat(chat, user_id):
        message.reply_text("Neden o sohbette olan birinin uzaktan yasağını kaldırmaya çalışıyorsun?")
        return

    if user_id == bot.id:
        message.reply_text("Hayır")
        return

    try:
        chat.unban_member(user_id)
        message.reply_text("Tamamdır. Tekrar teşrif edebilirler")
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text('Unbanned!', quote=False)
        elif excp.message in RUNBAN_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR unbanning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Kahretsin, bu kullanıcıyı yasaklayamam.")


__help__ = """
 - /kickme: kicks the user who issued the command

*Admin only:*
 - /ban <userhandle>: bans a user. (via handle, or reply)
 - /tban <userhandle> x(m/h/d): bans a user for x time. (via handle, or reply). m = minutes, h = hours, d = days.
 - /unban <userhandle>: unbans a user. (via handle, or reply)
 - /kick <userhandle>: kicks a user, (via handle, or reply)
"""

__mod_name__ = "Bans"

BAN_HANDLER = CommandHandler("ban", ban, pass_args=True, filters=Filters.group)
TEMPBAN_HANDLER = CommandHandler(["tban", "tempban"], temp_ban, pass_args=True, filters=Filters.group)
KICK_HANDLER = CommandHandler("kick", kick, pass_args=True, filters=Filters.group)
UNBAN_HANDLER = CommandHandler("unban", unban, pass_args=True, filters=Filters.group)
KICKME_HANDLER = DisableAbleCommandHandler("kickme", kickme, filters=Filters.group)
RBAN_HANDLER = CommandHandler("rban", rban, pass_args=True, filters=CustomFilters.sudo_filter)
RUNBAN_HANDLER = CommandHandler("runban", runban, pass_args=True, filters=CustomFilters.sudo_filter)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(KICK_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(KICKME_HANDLER)
dispatcher.add_handler(RBAN_HANDLER)
dispatcher.add_handler(RUNBAN_HANDLER)
