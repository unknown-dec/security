import discord
from discord import app_commands
from discord.ext import commands
import datetime
import traceback
import re
import asyncio
import json
import os
from collections import defaultdict, deque

# Bot Intents Setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Bot Owner & Security Role IDs
WHITELISTED_USERS = {1494798963889410048}
ROLE_SECURITY = 1542221896848769046

def is_whitelisted():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.id in WHITELISTED_USERS:
            return True
        if any(role.id == ROLE_SECURITY for role in interaction.user.roles):
            return True
        await interaction.response.send_message("❌ Access Denied: This command is restricted to the Bot Owner or Security Role.", ephemeral=True)
        return False
    return app_commands.check(predicate)


# --- 1. Emergency Panel ---
class EmergencyPanelView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="LOCK ALL NUKE", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="persistent_lock_all_nuke")
    async def lock_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in WHITELISTED_USERS and not any(r.id == ROLE_SECURITY for r in interaction.user.roles):
            await interaction.response.send_message("❌ You are not allowed!", ephemeral=True)
            return
        
        for key in self.cog.ANTI_SETTINGS:
            self.cog.ANTI_SETTINGS[key] = False
            
        embed = self.cog.get_main_panel_embed()
        await interaction.response.edit_message(embed=embed, view=MainDashboardView(self.cog))
        await interaction.followup.send("🔒 Successfully locked and disabled **all** security systems!", ephemeral=True)

    @discord.ui.button(label="UNLOCK ALL NUKE", style=discord.ButtonStyle.success, emoji="🔓", custom_id="persistent_unlock_all_nuke")
    async def unlock_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in WHITELISTED_USERS and not any(r.id == ROLE_SECURITY for r in interaction.user.roles):
            await interaction.response.send_message("❌ You are not allowed!", ephemeral=True)
            return
        
        for key in self.cog.ANTI_SETTINGS:
            self.cog.ANTI_SETTINGS[key] = True
            
        embed = self.cog.get_main_panel_embed()
        await interaction.response.edit_message(embed=embed, view=MainDashboardView(self.cog))
        await interaction.followup.send("🔓 Successfully unlocked and enabled **all** security systems!", ephemeral=True)

    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=1, custom_id="persistent_back_home_emg")
    async def back_home(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.cog.get_main_panel_embed()
        await interaction.response.edit_message(embed=embed, view=MainDashboardView(self.cog))


# --- 2. Individual Systems Control ---
class AntiSystemSelect(discord.ui.Select):
    def __init__(self, cog):
        self.cog = cog
        options = []
        for key in self.cog.ANTI_SETTINGS.keys():
            status = self.cog.ANTI_SETTINGS[key]
            emoji = "🟢" if status else "🔴"
            desc = "Status: Enabled" if status else "Status: Disabled"
            options.append(discord.SelectOption(label=key, value=key, description=desc, emoji=emoji))

        super().__init__(placeholder="Select a system to toggle...", min_values=1, max_values=1, options=options, custom_id="persistent_anti_system_select")

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id not in WHITELISTED_USERS and not any(r.id == ROLE_SECURITY for r in interaction.user.roles):
            await interaction.response.send_message("❌ You are not allowed!", ephemeral=True)
            return

        selected_key = self.values[0]
        current_state = self.cog.ANTI_SETTINGS[selected_key]
        self.cog.ANTI_SETTINGS[selected_key] = not current_state

        new_status = "Enabled 🟢" if self.cog.ANTI_SETTINGS[selected_key] else "Disabled 🔴"
        view = IndividualControlView(self.cog)
        await interaction.response.edit_message(view=view)
        await interaction.followup.send(f"⚙️ Status of system `{selected_key}` changed to: **{new_status}**", ephemeral=True)


class IndividualControlView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        self.add_item(AntiSystemSelect(cog))

    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=1, custom_id="persistent_back_home_ind")
    async def back_home(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.cog.get_main_panel_embed()
        await interaction.response.edit_message(embed=embed, view=MainDashboardView(self.cog))


# --- 3. Main Dashboard ---
class MainDashboardView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="🚨 Emergency Panel", style=discord.ButtonStyle.danger, emoji="⚡", custom_id="persistent_btn_emergency", row=0)
    async def btn_emergency(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in WHITELISTED_USERS and not any(r.id == ROLE_SECURITY for r in interaction.user.roles):
            await interaction.response.send_message("❌ You are not allowed!", ephemeral=True)
            return
        embed = discord.Embed(
            title="🚨 Server Emergency Panel",
            description="From here you can lock or unlock all security systems at once.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=EmergencyPanelView(self.cog))

    @discord.ui.button(label="⚙️ Individual Control", style=discord.ButtonStyle.primary, emoji="🎛️", custom_id="persistent_btn_individual", row=0)
    async def btn_individual(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in WHITELISTED_USERS and not any(r.id == ROLE_SECURITY for r in interaction.user.roles):
            await interaction.response.send_message("❌ You are not allowed!", ephemeral=True)
            return
        embed = discord.Embed(
            title="🎛️ Individual Security Control",
            description="Select a system from the dropdown menu below to toggle its protection.",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=IndividualControlView(self.cog))

    @discord.ui.button(label="📊 Anti Settings Status", style=discord.ButtonStyle.success, emoji="📋", custom_id="persistent_btn_anti_settings", row=1)
    async def btn_anti_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in WHITELISTED_USERS and not any(r.id == ROLE_SECURITY for r in interaction.user.roles):
            await interaction.response.send_message("❌ You are not allowed!", ephemeral=True)
            return
        
        status_text = ""
        for key, state in self.cog.ANTI_SETTINGS.items():
            icon = "🟢 Enabled" if state else "🔴 Disabled"
            status_text += f"• **{key}**: {icon}\n"

        embed = discord.Embed(
            title="📊 Security Systems Status Report",
            description=status_text[:4000],
            color=discord.Color.green()
        )
        embed.set_footer(text="Current status list of all systems")
        
        back_view = discord.ui.View(timeout=None)
        back_btn = discord.ui.Button(label="🔙 Back", style=discord.ButtonStyle.secondary, custom_id="persistent_back_btn_status")
        async def back_callback(inter):
            await inter.response.edit_message(embed=self.cog.get_main_panel_embed(), view=MainDashboardView(self.cog))
        back_btn.callback = back_callback
        back_view.add_item(back_btn)

        await interaction.response.edit_message(embed=embed, view=back_view)


class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.words_file = "badwords.json"
        self.filtered_words = self.load_words()
        self.word_warning_counts = {}
        self.warnings_db = {}
        
        self.MESSAGE_TIMES = defaultdict(lambda: deque(maxlen=20))
        self.SPAM_LIMIT = 6
        self.SPAM_WINDOW = 6
        self.FLOOD_LIMIT = 4
        self.FLOOD_WINDOW = 2
        self.CAPS_PERCENT = 0.75
        self.MAX_MENTIONS = 5
        self.MAX_EMOJIS = 15
        self.MAX_FILE_SIZE_MB = 25

        self.ANTI_SETTINGS = {
            "antilink": True,
            "antispam": True,
            "antispamfiles": True,
            "antiflood": True,
            "anticaps": True,
            "antiinvite": True,
            "antibot": True,
            "antiwebhook": True,
            "antiintegration": True,
            "antirole": True,
            "antiroledelete": True,
            "antirolecreate": True,
            "antiroleupdate": True,
            "antipermissions": True,
            "antiadmin": True,
            "antidangerousrole": True,
            "antichannel": True,
            "antichanneldelete": True,
            "antichannelcreate": True,
            "antichannelupdate": True,
            "antiemoji": True,
            "antimention": True,
            "antiband": True,
            "antiping": True,
            "badwords": True
        }

    def load_words(self):
        if os.path.exists(self.words_file):
            try:
                with open(self.words_file, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception:
                return set()
        return set()

    def save_words(self):
        try:
            with open(self.words_file, "w", encoding="utf-8") as f:
                json.dump(list(self.filtered_words), f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[ANTI] Failed to save words: {e}")

    def get_main_panel_embed(self):
        active_count = sum(1 for k in self.ANTI_SETTINGS.values() if k)
        inactive_count = len(self.ANTI_SETTINGS) - active_count

        embed = discord.Embed(
            title="🛡️ Main Server Security Center",
            description=(
                f"Welcome Server Owner.\n"
                f"Choose what you want to control from the buttons below:\n\n"
                f"🟢 **Active Systems:** `{active_count}`\n"
                f"🔴 **Disabled Systems:** `{inactive_count}`"
            ),
            color=discord.Color.dark_embed()
        )
        embed.set_footer(text="Security Command Center v3.0")
        return embed

    def protection_enabled(self, name: str) -> bool:
        return bool(self.ANTI_SETTINGS.get(name, False))

    def is_protected_member(self, member: discord.Member | discord.User) -> bool:
        return member.id in WHITELISTED_USERS

    async def safe_delete_message(self, message: discord.Message):
        try:
            await message.delete()
            return True
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
            print(f"[ANTI] Failed to delete message: {e}")
            return False

    async def safe_warn(self, message: discord.Message, text: str):
        try:
            await message.channel.send(f"⚠️ {message.author.mention} {text}", delete_after=5)
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"[ANTI] Failed to send warning: {e}")

    def count_emojis(self, text: str) -> int:
        custom = len(re.findall(r"<a?:\w+:\d+>", text))
        unicode_emoji = len(re.findall(r"[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF]", text))
        return custom + unicode_emoji

    async def get_recent_audit_entry(self, guild: discord.Guild, action: discord.AuditLogAction, target_id: int | None = None, seconds: int = 10):
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            async for entry in guild.audit_logs(limit=8, action=action):
                if target_id is not None:
                    entry_target = getattr(entry.target, "id", None)
                    if entry_target != target_id:
                        continue
                created = entry.created_at
                if (now - created).total_seconds() <= seconds:
                    return entry
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"[ANTI] Audit log error: {e}")
        return None

    async def punish_executor(self, guild: discord.Guild, executor: discord.Member, reason: str):
        if executor.bot or self.is_protected_member(executor):
            return
        try:
            await executor.timeout(datetime.timedelta(minutes=10), reason=reason)
            print(f"[ANTI] Timeout: {executor} | {reason}")
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"[ANTI] Could not timeout {executor}: {e}")

    async def restore_role_after_delete(self, guild: discord.Guild, role_id: int):
        entry = await self.get_recent_audit_entry(guild, discord.AuditLogAction.role_delete, role_id)
        if not entry or not entry.target:
            return
        old = entry.target
        try:
            new_role = await guild.create_role(
                name=old.name, permissions=old.permissions, colour=old.colour,
                hoist=old.hoist, mentionable=old.mentionable, reason="AntiRole restore"
            )
            print(f"[ANTI] Restored deleted role: {new_role.name}")
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"[ANTI] Role restore failed: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if message.author.bot or not message.guild:
                return

            is_allowed = self.is_protected_member(message.author)

            if not is_allowed and (self.protection_enabled("antilink") or self.protection_enabled("antiinvite")):
                link_pattern = r"(https?://\S+|www\.\S+|discord\.gg/\S+|discord\.com/invite/\S+)"
                if re.search(link_pattern, message.content, re.IGNORECASE):
                    await self.safe_delete_message(message)
                    await self.safe_warn(message, "Links and Discord invites are not allowed here.")
                    return

            if not is_allowed and (self.protection_enabled("antimention") or self.protection_enabled("antiping")):
                mentions = len(message.mentions) + len(message.role_mentions)
                everyone_ping = message.mention_everyone
                if mentions > self.MAX_MENTIONS or (everyone_ping and (self.protection_enabled("antiping") or self.protection_enabled("antieveryone"))):
                    await self.safe_delete_message(message)
                    await self.safe_warn(message, "Excessive mentions/pings are blocked.")
                    return

            if not is_allowed and self.protection_enabled("antiemoji"):
                if self.count_emojis(message.content) > self.MAX_EMOJIS:
                    await self.safe_delete_message(message)
                    await self.safe_warn(message, "Too many emojis in this message.")
                    return

            if not is_allowed and self.protection_enabled("antispamfiles") and message.attachments:
                for attachment in message.attachments:
                    if attachment.size > self.MAX_FILE_SIZE_MB * 1024 * 1024:
                        await self.safe_delete_message(message)
                        await self.safe_warn(message, f"File size exceeds the allowed limit ({self.MAX_FILE_SIZE_MB}MB).")
                        return

            if not is_allowed and self.protection_enabled("anticaps"):
                letters = [c for c in message.content if c.isalpha()]
                if len(letters) >= 8:
                    upper = sum(1 for c in letters if c.isupper())
                    if upper / len(letters) >= self.CAPS_PERCENT:
                        await self.safe_delete_message(message)
                        await self.safe_warn(message, "Excessive use of uppercase letters is not allowed.")
                        return

            if not is_allowed and (self.protection_enabled("antispam") or self.protection_enabled("antiflood")):
                now = asyncio.get_running_loop().time()
                history = self.MESSAGE_TIMES[message.author.id]
                history.append(now)

                if self.protection_enabled("antispam"):
                    recent = [t for t in history if now - t <= self.SPAM_WINDOW]
                    if len(recent) >= self.SPAM_LIMIT:
                        try:
                            await message.author.timeout(datetime.timedelta(minutes=2), reason="AntiSpam")
                        except Exception:
                            pass
                        await self.safe_delete_message(message)
                        await self.safe_warn(message, "You have been timed out for spamming.")
                        history.clear()
                        return

                if self.protection_enabled("antiflood"):
                    recent = [t for t in history if now - t <= self.FLOOD_WINDOW]
                    if len(recent) >= self.FLOOD_LIMIT:
                        await self.safe_delete_message(message)
                        await self.safe_warn(message, "Please do not send messages too quickly.")
                        return

            # نظام الكلمات الممنوعة المحسّن (تحذير 1، تحذير 2، تحذير 3 مع تايم أوت يوم)
            if not is_allowed and self.protection_enabled("badwords") and self.filtered_words:
                content_lower = message.content.lower()
                matched = False
                for word in self.filtered_words:
                    if word in content_lower:
                        matched = True
                        break
                
                if matched:
                    await self.safe_delete_message(message)
                    user_id = message.author.id
                    self.word_warning_counts[user_id] = self.word_warning_counts.get(user_id, 0) + 1
                    count = self.word_warning_counts[user_id]

                    if count == 1:
                        await self.safe_warn(message, "You used a prohibited word! This is your **1st Warning**.")
                    elif count == 2:
                        await self.safe_warn(message, "You used a prohibited word again! This is your **2nd Warning**.")
                    else:
                        # وصل لـ 3 تحذيرات أو أكثر، يتم إعطاؤه تايم أوت لمدة يوم كامل (24 ساعة)
                        try:
                            await message.author.timeout(datetime.timedelta(days=1), reason="Reached 3 warnings for using bad words")
                            self.word_warning_counts[user_id] = 0 # تصفير العداد بعد العقوبة
                            await self.safe_warn(message, "You reached **3 warnings** for using prohibited words and have been muted for **1 Day**.")
                        except Exception as e:
                            print(f"[ANTI] Failed to timeout user for bad words: {e}")
                    return

        except Exception:
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            if not self.protection_enabled("antibot") or not member.bot or self.is_protected_member(member):
                return
            await member.kick(reason="AntiBot: unauthorized bot joined")
        except Exception:
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        try:
            if not self.protection_enabled("antiwebhook"):
                return
            guild = channel.guild
            entry = await self.get_recent_audit_entry(guild, discord.AuditLogAction.webhook_create)
            if entry and entry.target:
                webhook_id = getattr(entry.target, "id", None)
                if webhook_id:
                    webhook = await guild.fetch_webhook(webhook_id)
                    if webhook.user and not self.is_protected_member(webhook.user):
                        await webhook.delete(reason="AntiWebhook")
                        await self.punish_executor(guild, entry.user, "AntiWebhook: unauthorized webhook creation")
        except Exception:
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        try:
            if not (self.protection_enabled("antichannel") or self.protection_enabled("antichanneldelete")):
                return
            entry = await self.get_recent_audit_entry(channel.guild, discord.AuditLogAction.channel_delete, channel.id, seconds=15)
            if entry and entry.user and not self.is_protected_member(entry.user):
                if isinstance(entry.user, discord.Member):
                    await channel.guild.kick(entry.user, reason="AntiChannel: deleted a channel")
        except Exception:
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        try:
            if not (self.protection_enabled("antiroledelete") or self.protection_enabled("antirole")):
                return
            entry = await self.get_recent_audit_entry(role.guild, discord.AuditLogAction.role_delete, role.id)
            if entry and entry.user and not self.is_protected_member(entry.user):
                await self.restore_role_after_delete(role.guild, role.id)
                await self.punish_executor(role.guild, entry.user, "AntiRole: unauthorized role deletion")
        except Exception:
            traceback.print_exc()

    @app_commands.command(name="controlpanel", description="Open the server main security control panel")
    @is_whitelisted()
    async def controlpanel(self, interaction: discord.Interaction):
        embed = self.get_main_panel_embed()
        view = MainDashboardView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="antisettings", description="Display security settings statuses")
    @is_whitelisted()
    async def antisettings(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🛡️ Security Settings Panel", color=discord.Color.blurple())
        for k, v in self.ANTI_SETTINGS.items():
            embed.add_field(name=k, value="🟢 Enabled" if v else "🔴 Disabled", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="removeword", description="Add a word to the bad words list")
    @app_commands.describe(word="The word to ban")
    @is_whitelisted()
    async def removeword(self, interaction: discord.Interaction, word: str):
        w = word.strip().lower()
        if w in self.filtered_words:
            await interaction.response.send_message(f"⚠️ The word `{w}` is already in the ban list.", ephemeral=True)
            return
        self.filtered_words.add(w)
        self.save_words()
        await interaction.response.send_message(f"✅ Successfully added the word `{w}` to the ban list and saved.", ephemeral=True)

    @app_commands.command(name="showwords", description="Display the current bad words list")
    @is_whitelisted()
    async def showwords(self, interaction: discord.Interaction):
        if not self.filtered_words:
            await interaction.response.send_message("📂 The bad words list is currently empty.", ephemeral=True)
            return
        words_list = ", ".join([f"`{w}`" for w in self.filtered_words])
        embed = discord.Embed(title="🚫 Current Bad Words", description=words_list, color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="delword", description="Remove a word from the ban list")
    @app_commands.describe(word="The word to remove")
    @is_whitelisted()
    async def delword(self, interaction: discord.Interaction, word: str):
        w = word.strip().lower()
        if w not in self.filtered_words:
            await interaction.response.send_message(f"❌ The word `{w}` is not in the ban list.", ephemeral=True)
            return
        self.filtered_words.remove(w)
        self.save_words()
        await interaction.response.send_message(f"🗑️ Successfully removed the word `{w}` from the ban list.", ephemeral=True)


async def main():
    async with bot:
        sec_cog = Security(bot)
        await bot.add_cog(sec_cog)
        
        bot.add_view(MainDashboardView(sec_cog))
        bot.add_view(EmergencyPanelView(sec_cog))
        bot.add_view(IndividualControlView(sec_cog))
        
        @bot.event
        async def on_ready():
            try:
                synced = await bot.tree.sync()
                print(f"Synced {len(synced)} slash commands.")
            except Exception as e:
                print(e)
            print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
            print("Anti-Raid & Security System is Online!")

        TOKEN = "MTU0NDE0ODAwNDMwNTYzMzI4MQ.GvcITA.FhLwiLrxgqZa9cplEuFJ3jCx9-wO3xGZPLPbkc"
        
        if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("❌ Error: Please put your valid bot token in the code.")
            return
            
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())