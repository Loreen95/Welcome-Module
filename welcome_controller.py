from core.alts.alts_service import AltsService
from core.decorators import instance, command, setting, event
from core.command_param_types import Any
from core.db import DB
from core.chat_blob import ChatBlob
from core.setting_service import SettingService
from core.text import Text
from core.access_service import AccessService
from core.logger import Logger
from core.lookup.character_service import CharacterService
from core.private_channel_service import PrivateChannelService
import time
from core.tyrbot import Tyrbot
from core.util import Util


@instance()
class welcomeController:
    JOINED_PRIVATE_CHANNEL_EVENT = "private_channel_joined"

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.bot: Tyrbot = registry.get_instance("bot")
        self.access_service: AccessService = registry.get_instance("access_service")
        self.buddy_service = registry.get_instance ("buddy_service")
        self.buddy_service = registry.get_instance("buddy_service")
        self.news_controller = registry.get_instance("news_controller")
        self.private_channel_service = registry.get_instance("private_channel_service")
        self.points_controller = registry.get_instance("points_controller")
        self.timer_controller = registry.get_instance("timer_controller")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.event_service = registry.get_instance("event_service")
        self.alts_service: AltsService = registry.get_instance("alts_service")  
        self.util: Util = registry.get_instance("util")  
        self.alts_service: AltsService = registry.get_instance("alts_service")
        self.util: Util = registry.get_instance("util")
    
    def pre_start(self):
        self.event_service.register_event_type(self.JOINED_PRIVATE_CHANNEL_EVENT)
        
    @command(command="welcome", params=[], access_level="all",
             description="Shows the welcome news-feed")
    def welcome_command(self, request):
        welcome = self.get_welcome_window(request.sender.char_id)
        self.bot.send_private_message(request.sender.char_id, ChatBlob("Welcome", welcome))

    def get_welcome_window(self, char_id):
        sql = "SELECT n.*, p.name AS author FROM news n LEFT JOIN player p ON n.char_id = p.char_id WHERE n.deleted_at = 0 AND n.sticky = 0 ORDER BY n.created_at DESC LIMIT 1"
        news = self.db.query(sql)
        blob = ""
        blob += "\n<header>::Newsfeed::<end>\n"
        for item in news:
            timestamp = self.util.format_datetime(item.created_at)

        blob += "\n<white>on %s <end><highlight>%s<end> <white>wrote article: <end><highlight>%d<end>\n" % (timestamp, item.author, item.id)
        blob += "<highlight%s<end>\n" % (item.news)

        blob += "\n\n<header>:: Raid Timers ::<end>\n"
        t = int(time.time())
        data = self.db.query("SELECT t.*, p.name AS char_name FROM timer t LEFT JOIN player p ON t.char_id = p.char_id ORDER BY t.finished_at ASC")
        blob = ""
        for timer in data:
            blob += "\n<highlight>%s<end>" % timer.name
            blob += " <white>has <highlight>%s<end> <white>left.<end>" % (self.util.time_to_readable(timer.created_at + timer.duration - t, max_levels=None))

        blob += "\n\n"

        blob += "\n<header>:: Personal Info & Preferences ::<end>\n"
        main_id = self.alts_service.get_main(char_id)
        main_name = self.character_service.resolve_char_to_name(main_id.char_id)
        points = self.db.query_single("SELECT points, disabled FROM points WHERE char_id = ?", [main_id.char_id])
        alts_link = self.text.make_chatcmd("Alts", "/tell <myname> alts %s" % main_name)
        acct_link = self.text.make_chatcmd("Account", "/tell <myname> account")
        autoinv_link = self.text.make_chatcmd("ON", "/tell <myname> autoinvite on")
        autoin_link = self.text.make_chatcmd("OFF", "/tell <myname> autoinvite off")
      
        blob += "\n<white>Your main is:<end> <highlight>%s [%s]<end>" % (main_name, alts_link)
        blob += "\n<white>You have<end> <highlight>%d<end> <white>points.<end> %s" % (points.points, acct_link)
        blob += "\n<white>Your account is currently:<end> %s" % ("<green>Open<end>" if points.disabled == 0 else "<red>Disabled<end>")
        
        sql = "SELECT COALESCE(p.name, m.char_id) AS name, m.char_id, m.auto_invite FROM members m LEFT JOIN player p ON m.char_id = p.char_id ORDER BY p.name ASC"
        pref = self.db.query(sql)
        blob += "\n<white>Your autoinvite is currently:<end> %s [%s|%s]" % ("<red>Off<end>" if pref == 1 else "<green>On<end>", autoinv_link, autoin_link)
        
        return blob
    
    @event(event_type=PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, description="Send newsfeed when someone joins private channel")
    def priv_logon_event(self, event_type, event_data):
        welcome = self.get_welcome_window(False, event_data.char_id)
        self.bot.send_private_message(event_data.char_id, ChatBlob("Welcome", welcome))
