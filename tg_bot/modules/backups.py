import json
from io import BytesIO
from typing import Optional

from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async

from tg_bot import dispatcher, LOGGER
from tg_bot.__main__ import DATA_IMPORT
from tg_bot.modules.helper_funcs.chat_status import user_admin


@run_async
@user_admin
def import_data(bot: Bot, update):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    # TODO: allow uploading doc with command, not just as reply
    # only work with a doc
    if msg.reply_to_message and msg.reply_to_message.document:
        try:
            file_info = bot.get_file(msg.reply_to_message.document.file_id)
        except BadRequest:
            msg.reply_text("İçe aktarmadan önce dosyayı kendiniz indirip yeniden yüklemeyi deneyin"
                           "bu havalı!😎 ")
            return

        with BytesIO() as file:
            file_info.download(out=file)
            file.seek(0)
            data = json.load(file)

        # only import one group
        if len(data) > 1 and str(chat.id) not in data:
            msg.reply_text("Bu dosyada birden fazla grup var ve hiçbiri bu grupla aynı sohbet kimliğine sahip değil"
                           "- neyi içe aktaracağımı nasıl seçebilirim?")
            return

        # Select data source
        if str(chat.id) in data:
            data = data[str(chat.id)]['hashes']
        else:
            data = data[list(data.keys())[0]]['hashes']

        try:
            for mod in DATA_IMPORT:
                mod.__import_data__(str(chat.id), data)
        except Exception:
            msg.reply_text("Verileriniz geri yüklenirken bir hata oluştu. İşlem tamamlanmamış olabilir. Eğer"
                           "bununla ilgili sorun yaşıyorsanız, @SherlockSupport 'a yedek dosyanızla birlikte yazın."
                           "Sorun çözülebilir. Sahibim yardımcı olmaktan mutluluk duyar ve her hata"
                           "raporu beni daha iyi yapar! Teşekkürler! :)")
            LOGGER.exception("Import for chatid %s with name %s failed.", str(chat.id), str(chat.title))
            return

        # TODO: some of that link logic
        # NOTE: consider default permissions stuff?
        msg.reply_text("Yedek tamamen içe aktarıldı. Tekrar *Merhaba*! :D")


@run_async
@user_admin
def export_data(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    msg.reply_text("")


__mod_name__ = "Backups"

__help__ = """
*Admin only:*
 - /import: Grup yedeğini içe aktarmak için kullanılır.
 - /export: !!! Bu henüz bir komut değil, ama yakında gelecek!
"""
IMPORT_HANDLER = CommandHandler("import", import_data)
EXPORT_HANDLER = CommandHandler("export", export_data)

dispatcher.add_handler(IMPORT_HANDLER)
# dispatcher.add_handler(EXPORT_HANDLER)
