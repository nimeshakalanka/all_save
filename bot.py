from pyrogram import Client, filters, enums, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent, Message, CallbackQuery
from pyrogram.errors import UserNotParticipant
from pyrogram.errors.exceptions.flood_420 import FloodWait
import requests
import asyncio
import os
import time
from datetime import datetime, timedelta
import json
from bs4 import BeautifulSoup
from config import cfg
from pyromod import listen
from pymongo import MongoClient
from db import add_user, add_group, all_users, all_groups, users, remove_user
from pornhub_api import PornhubApi
from pornhub_api.backends.aiohttp import AioHttpBackend
from youtube_dl.utils import DownloadError
from apscheduler.schedulers.background import BackgroundScheduler
import yt_dlp
from humanize import naturalsize

scheduler = BackgroundScheduler()

app = Client(
    "all_save",
    api_id=cfg.API_ID,
    api_hash=cfg.API_HASH,
    bot_token=cfg.BOT_TOKEN
)

MONGO_DB_NAME = "Cluster0"
MONGO_COLLECTION_NAME = "sub1"

mongo_client = MongoClient(cfg.MONGO_URI)
db = mongo_client[MONGO_DB_NAME]
subscriptions_collection = db[MONGO_COLLECTION_NAME]


user_data = {}

active_list = []
queue = []


FREE_USER_DOWNLOAD_LIMIT = 2

def can_download_video(user_id, is_premium=False):
    cooldown_duration = 30 * 60  # 30 minutes in seconds

    # Check is a free user exceeded the download limit
    if not is_premium and user_id in user_data:
        last_download_time, download_count = user_data[user_id]

        # Check if the user has reached the download limit for the day
        if download_count >= FREE_USER_DOWNLOAD_LIMIT:
            return False, None

        # Check if the cooldown period has not passed since the last download
        elapsed_time = time.time() - last_download_time
        if elapsed_time < cooldown_duration:
            remaining_time = cooldown_duration - elapsed_time
            return False, remaining_time

    # Update the last download time and download count for the user
    current_time = time.time()
    if user_id in user_data:
        _, download_count = user_data[user_id]
        user_data[user_id] = (current_time, download_count + 1)
    else:
        user_data[user_id] = (current_time, 1)

    return True, None

admin_id = cfg.SUDO

def remove_user(user_id):
    subscriptions_collection.delete_one({"user_id": user_id})
    print(f"Removed user ID: {user_id}")

def make_user_premium(admin_id, p_user_id):
    expiry_date = datetime.now() + timedelta(days=30)

    subscription_data = {
        "user_id": p_user_id,
        "expiry_date": expiry_date
    }
    subscriptions_collection.insert_one(subscription_data)

    scheduler.add_job(remove_user, 'date', run_date=expiry_date, args=[p_user_id])

# Start the scheduler
scheduler.start()

# Command to subscribe a user
@app.on_message(filters.command("sub") & filters.user(cfg.SUDO))
async def subscribe_command_handler(client, message):
    user_id = message.text.split(" ", 1)[1]
    try:
        p_user_id = int(user_id)
        make_user_premium(admin_id, p_user_id)
        await message.reply_text(f"{p_user_id} user set as a premium user.")
        await app.send_message(p_user_id, "Congratulations! You are now a premium user.")
    except ValueError:
        await message.reply_text("Invalid user ID.")


START_BUTTON = [
    [
        InlineKeyboardButton("📖 Commands", callback_data="COMMAND_BUTTON"),
        InlineKeyboardButton("👨‍💻 About me", callback_data="ABOUT_BUTTON")
    ],
    [
        InlineKeyboardButton("➕ Add me to your Chat ➕", url="https://t.me/AIl_Save_Bot?startgroup")
    ]]
GOBACK_1_BUTTON = [[InlineKeyboardButton("🔙 Go Back", callback_data="START_BUTTON")]]
SHARE_BUTTON = [[InlineKeyboardButton("Share ☘️", url="https://t.me/share/url?url=Check%20out%20this%20awesome%20bot%20for%20downloading%20videos%21%20%F0%9F%94%A5%0A%0AAll%20Save%20Bot%20%E2%98%98%EF%B8%8F%20%3A%20%20%40AIl_Save_Bot")]]
G_BUTTON = [
    [
        InlineKeyboardButton("👨‍💻 Developer", url="t.me/akalankanime2"),
        InlineKeyboardButton("🔙 Go Back", callback_data="START_BUTTON")
    ]]
P_BUTTON = [[InlineKeyboardButton("💳 Get Premium", callback_data="PREMIUM_BUTTON")]]

PAY_BUTTON = [[InlineKeyboardButton("💳 Pay Now", url="https://t.me/akalankanime2")]]

#start
@app.on_message(filters.command('start'))
async def start(_, message):
    try:
        await app.get_chat_member(cfg.CHID, message.from_user.id) 
        if message.chat.type == enums.ChatType.PRIVATE:
            add_user(message.from_user.id)
            link = "https://t.me/AIl_Save_Bot"
            await app.send_photo(message.from_user.id, photo="https://telegra.ph/file/0351e7d492b896af35c1f.png", caption=f"**👋👋 Hello there,** {message.from_user.mention}\n\nI'm **[All Save Bot 🍀]({link})**, at your service! 💪.\n\nWith me by your side, you can effortlessly download videos from popular platforms like YouTube, TikTok, Instagram, Facebook, Envato, and even P#rnHub 😉😜. Just let me know what video you need, and I'll handle the rest! 🎥💾\n\nAnd here's the best part: I'm group-friendly too! Feel free to use me in your groups to share and save videos with your friends or colleagues. 🤝👥\n\nLet me know how I can assist you today! 😊🌟", reply_markup=InlineKeyboardMarkup(START_BUTTON))
    
        elif message.chat.type == enums.ChatType.GROUP or enums.ChatType.SUPERGROUP:
            keyboar = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Come IB😏", url="https://t.me/AIl_Save_Bot?start=start")
                    ]
                ]
            )
            add_group(message.chat.id)
            await message.reply_text("**👋👋 Hello {}!\nLet's take this conversation to the inbox for a more private discussion. Feel free to share your specific requirements or any questions you may have, and I'll provide you with all the information you need. 📩🤫**".format(message.from_user.first_name), reply_markup=keyboar)
        

    except UserNotParticipant:
        key = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🍀 Check Again 🍀", "chk")
                ]
            ]
        )
        await message.reply_text("**⚠️Access Denied!⚠️\n\nI apologize for any inconvenience caused. To gain access and start using my services, please join the Bots Updates Channel by clicking here: [Join Bots Updates Channel]({}).**".format("https://t.me/szteambots"), reply_markup=key)

START_TEXT = """**👋👋 Hello there,** \n\nI'm **All Save Bot 🍀**, at your service! 💪.\n\nWith me by your side, you can effortlessly download videos from popular platforms like YouTube, TikTok, Instagram, Facebook, Envato, and even P#rnHub 😉😜. Just let me know what video you need, and I'll handle the rest! 🎥💾\n\nAnd here's the best part: I'm group-friendly too! Feel free to use me in your groups to share and save videos with your friends or colleagues. 🤝👥\n\nLet me know how I can assist you today! 😊🌟"""
CMD_TEXT = """Here are the commands available for this bot:\n\n👇🤖 Bot Commands 👇\n\n<code>/start</code>: Start the bot and activate its functionality.\n/<code>help</code>: Get assistance and guidance on how to use the bot effectively. 🎊\n<code>/stats</code>: View the statistics of the bot's user base. This command is only available for administrators.\n\nFeel free to utilize these commands to interact with the bot and make the most out of its features! If you have any further questions or need additional help, please don't hesitate to ask. 💫🤖"""
ABOUT_TEXT = """👋👋 Hello there! I'm glad to meet you, **All Save Bot☘️ ** It's great to hear about your video downloading capabilities from platforms like Facebook, YouTube, TikTok, Instagram, Envato Elements, and P@rnHub. It's important to ensure that the features you add are approved by the owner of the bot.\n\nIf you have any suggestions or ideas for improving the bot's functionality, I recommend reaching out to the developer. They can review your suggestions and determine if they align with the bot's purpose and guidelines. Collaboration between users and developers can lead to an enhanced user experience.\n\nKeep up the great work, and don't hesitate to contact the developer with any further inquiries or suggestions! 🌟🤖"""
P_TEXT = """Dear User🧑🏻‍💻,\nThank you for your message. It appears that you are implementing premium features for your bot, allowing users to download videos without any intervals. It's common to charge a small amount for premium services, as it helps support the development and maintenance of the bot.\n\n⮞ Premium Price: 3$ \nPayment Methods: PayPal, Crypto & Bank Transfer (Sri Lankan Only) 🏦💸\n\nIf users have any further questions or require assistance with the payment process, it's recommended to provide them with clear instructions or a contact method to reach out for support.\n\nBest of luck with your premium offering, and I hope it brings added value to your users! 💫🤖"""
#callback
@app.on_callback_query(filters.regex("_BUTTON"))
async def botCallbacks(_, CallbackQuery):

    if CallbackQuery.data == "START_BUTTON":          
        await CallbackQuery.edit_message_text(START_TEXT, reply_markup=InlineKeyboardMarkup(START_BUTTON))
    elif CallbackQuery.data == "COMMAND_BUTTON":          
        await CallbackQuery.edit_message_text(CMD_TEXT, reply_markup=InlineKeyboardMarkup(GOBACK_1_BUTTON))
    elif CallbackQuery.data == "ABOUT_BUTTON":          
        await CallbackQuery.edit_message_text(ABOUT_TEXT, reply_markup=InlineKeyboardMarkup(G_BUTTON))
    elif CallbackQuery.data == "PREMIUM_BUTTON":
        await CallbackQuery.edit_message_text(P_TEXT, reply_markup=InlineKeyboardMarkup(PAY_BUTTON))        

@app.on_callback_query(filters.regex("chk"))
async def chk(_, cb : CallbackQuery):
    try:
        await app.get_chat_member(cfg.CHID, cb.from_user.id)
        if cb.message.chat.type == enums.ChatType.PRIVATE:
            add_user(cb.from_user.id)
            await app.send_photo(cb.from_user.id, photo="https://telegra.ph/file/6aa7c012295bbf509aaa7.png", caption="**👋👋 Hello** "+ cb.from_user.mention +"\nI'm **All Save Bot ☘️**.\nI can download **Youtube, Tiktok, Instergram, Facebook, Envato & P#rnHub** Videos 🙂😜.\nyou can use me also in groups.", reply_markup=InlineKeyboardMarkup(START_BUTTON))
        
    except UserNotParticipant:
        await cb.answer("🙅‍♂️ You smartass join channel 😒")

#help
@app.on_message(filters.command('help'))
async def help(_, message):
    await app.send_message(message.from_user.id, text=f"Hello "+ message.from_user.mention +"👋👋,\nI am **All Save Bot ☘️**.\nI can download videos from a given link.\nlink must like this:- \n<code>https://www.tiktok.com/@primemusix/video/711918712602\nhttps://youtu.be/-MJC7lxPcc\nhttps://www.instagram.com/p/B7luhVI2\nhttps://fb.watch/ln_g3Nk3/\nhttps://www.pornhub.com/view_video.php?viewkey=ph454b8ff 😜</code>\n\n__Send me a video link__")

#premium
@app.on_message(filters.command('premium'))
async def ppremium(_, message):
    await app.send_message(message.from_user.id, text=P_TEXT, reply_to_message_id=message.id, reply_markup=InlineKeyboardMarkup(PAY_BUTTON))


##
def check_user_premium(user_id):
    premium_user = subscriptions_collection.find_one({"user_id": user_id})
    return premium_user is not None

#tiktok
@app.on_message((filters.regex("http://")|filters.regex("https://")) & filters.regex('tiktok'))
async def tiktok_downloader(_, message):
    ran = await message.reply_text("<code>Processing.....</code>")
    link = message.text
    user_id = message.from_user.id
    is_premium = check_user_premium(user_id)
    

    can_download, remaining_time = can_download_video(user_id, is_premium)
    if not can_download:
        if remaining_time is not None:
            minutes = remaining_time // 60
            await ran.edit_text(f"<code>Sorry, you need to wait {minutes} minutes  before downloading another video.</code>", reply_markup=InlineKeyboardMarkup(P_BUTTON))
        else:
            await ran.edit_text("<code>Sorry, you have reached your maximum download limit.</code>", reply_markup=InlineKeyboardMarkup(P_BUTTON))
        return

    url = "https://api.douyin.wtf/api?url="+link+"&minimal=false"
    response = requests.get(url)
    if response.status_code == 200:
        data_response = response.json()
    await ran.edit_text("<code>Downloading Video.....</code>")
    nwm_url = "" 
    try:
        #video
        id = data_response["aweme_id"]
        cap = data_response["desc"]
        ciddata = data_response["video_data"]
        nwm_url = ciddata["nwm_video_url"]

    except :
        pass
    if nwm_url is not None and nwm_url != "":
        req = requests.get(nwm_url)
        send_video_path = id+".mp4"
        with open(send_video_path, "wb") as f:
            f.write(req.content) 
        await app.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_VIDEO)
        await ran.edit_text("<code>Uploading Video.....</code>")  
        await app.send_video(message.chat.id, video=send_video_path, reply_to_message_id=message.id, caption=f"**Here Is your Requested Video👆**\n\n<code>{cap}</code>\n\n🔗 Requestor : ||{message.from_user.mention}||\n🚀 Downloaded via: [All Save Bot ☘️](https://t.me/AIl_Save_Bot)", reply_markup=InlineKeyboardMarkup(SHARE_BUTTON))
        await ran.delete()
        os.remove(send_video_path)
    else:
        url2 = "https://api.sdbots.tech/tiktok?url="+link
        rea = requests.get(url2)
        p_res = rea.json()
        pk = p_res['result']
        cap = pk['desc']
        id = pk['duration']
        nwm_url = pk['withoutWaterMarkVideo']
        
        req = requests.get(nwm_url)
        send_video_path = f"tik{id}vid.mp4"
        with open(send_video_path, "wb") as f:
            f.write(req.content) 
        await app.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_VIDEO)
        await ran.edit_text("<code>Uploading Video.....</code>")  
        await app.send_video(message.chat.id, video=send_video_path, reply_to_message_id=message.id, caption=f"**Here Is your Requested Video👆**\n\n<code>{cap}</code>\n\n🔗 Requestor : ||{message.from_user.mention}||\n🚀 Downloaded via: [All Save Bot ☘️](https://t.me/AIl_Save_Bot)", reply_markup=InlineKeyboardMarkup(SHARE_BUTTON))
        await ran.delete()
        os.remove(send_video_path)


#insta
@app.on_message((filters.regex("http://")|filters.regex("https://")) & filters.regex('instagram'))
async def insta_downloader(_, message):
    ran = await message.reply_text("<code>Processing.....</code>")
    link = message.text
    user_id = message.from_user.id
    
    is_premium = check_user_premium(user_id)
    

    can_download, remaining_time = can_download_video(user_id, is_premium)
    if not can_download:
        if remaining_time is not None:
            minutes = remaining_time // 60
            await ran.edit_text(f"<code>Sorry, you need to wait {minutes} minutes  before downloading another video.</code>", reply_markup=InlineKeyboardMarkup(P_BUTTON))
        else:
            await ran.edit_text("<code>Sorry, you have reached your maximum download limit.</code>", reply_markup=InlineKeyboardMarkup(P_BUTTON))
        return
    
    url = "https://www.w3toys.com/"

    data = {"link": link,
	    "submit": "DOWNLOAD"}

    response = requests.post(url, data=data)
    r = response.content
    soup = BeautifulSoup(r, 'html.parser')
    a_element = soup.find('source')
    video = a_element.get('src')
    if video == "":
        url = "https://www.w3toys.com/app/core/ajax.php"
        data = {"url": link,
	            "host": "instagram"}
        response = requests.post(url, data=data)
        r = response.content
        soup = BeautifulSoup(r, 'html.parser')
        a_element = soup.find('a')
        video1 = a_element.get('href')
        video = "https://www.w3toys.com/app/"+video1

    await ran.edit_text("<code>Downloading Video.....</code>")
    req = requests.get(video)
    send_video_path = "insta.mp4"
    with open(send_video_path, "wb") as f:
        f.write(req.content)
    await app.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_VIDEO)
    await ran.edit_text("<code>Uploading Video.....\n\nsometimes this take some time🙂 Upload speed depend on video size</code>")
    await app.send_video(message.chat.id, video=send_video_path, reply_to_message_id=message.id, caption=f"Here is your requested Video👆\n\n🔗 Requestor : ||{message.from_user.mention}||\n🚀 Downloaded via: [All Save Bot ☘️](https://t.me/AIl_Save_Bot)", reply_markup=InlineKeyboardMarkup(SHARE_BUTTON))
    await ran.delete()
    os.remove(send_video_path)
    
    
    
    
##
if os.path.exists("downloads"):
    print("Download Path Exist")
else:
    print("Download Path Created")

async def run_async(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)    

#phub_help
def humanbytes(size):
    """Convert Bytes To Bytes So That Human Can Read It."""
    if not size:
        return ""
    power = 2 ** 10
    raised_to_pow = 0
    dict_power_n = {0: "", 1: "Ki", 2: "Mi", 3: "Gi", 4: "Ti"}
    while size > power:
        size /= power
        raised_to_pow += 1
    return str(round(size, 2)) + " " + dict_power_n[raised_to_pow] + "B"


def download_progress_hook(d, message, client):
    if d['status'] == 'downloading':
        # Update the progress of the download in your application or send a message to the user
        progress = d['_percent_str']
        # Update the progress in the message
    elif d['status'] == 'finished':
        # The video download is completed
        file_name = d['filename']
        # Use the 'file_name' variable for further processing

#phub
@app.on_message((filters.regex("http://")|filters.regex("https://")) & filters.regex('pornhub'))
async def download_video(client, message):
    url = message.text
    msg = await message.reply_text("<code>Processing.....</code>")
    user_id = message.from_user.id
    
    is_premium = check_user_premium(user_id)
    

    can_download, remaining_time = can_download_video(user_id, is_premium)
    if not can_download:
        if remaining_time is not None:
            minutes = remaining_time // 60
            await msg.edit_text(f"<code>Sorry, you need to wait {minutes} minutes  before downloading another video.</code>", reply_markup=InlineKeyboardMarkup(P_BUTTON))
        else:
            await msg.edit_text("<code>Sorry, you have reached your maximum download limit.</code>", reply_markup=InlineKeyboardMarkup(P_BUTTON))
        return

    ydl_opts = {
            "progress_hooks": [lambda d: download_progress_hook(d, message, client)]
        }


    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            await msg.edit_text("<code>Downloading Video.....</code>")
            info_dict = ydl.extract_info(url, download=False)
            file_name = ydl.prepare_filename(info_dict)
            await run_async(ydl.download, [url])
        except yt_dlp.DownloadError:
            await msg.edit_text("Sorry, There was a problem with that particular video")
            return


    for file in os.listdir('.'):
        if file.endswith(".mp4"):
            await msg.edit_text("<code>Uploading Video.....\n\nsometimes this take some time🙂 Upload speed depend on video size</code>")
            await app.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_VIDEO)
            await message.reply_video(f"{file}", caption=f"**Here Is your Requested Video🔞👆**\n\n<code>{file_name}</code>\n\n🔗 Requestor : ||{message.from_user.mention}||\n🚀 Downloaded via: [All Save Bot ☘️](https://t.me/AIl_Save_Bot)", reply_markup=InlineKeyboardMarkup(SHARE_BUTTON))
            os.remove(f"{file}")
            break
        else:
            continue

    await msg.delete()


#youtube
#youtube
@app.on_message((filters.regex("http://") | filters.regex("https://")) & (filters.regex('youtu.be') | filters.regex('youtube')))
async def download_yt(client, message):
    global yurl
    yurl = message.text
    msg = await message.reply_text("<code>Processing.....</code>")
    user_id = message.from_user.id

    is_premium = check_user_premium(user_id)

    can_download, remaining_time = can_download_video(user_id, is_premium)
    if not can_download:
        if remaining_time is not None:
            minutes = remaining_time // 60
            await msg.edit_text(f"<code>Sorry, you need to wait {minutes} minutes before downloading another video.</code>", reply_markup=InlineKeyboardMarkup(P_BUTTON))
        else:
            await msg.edit_text("<code>Sorry, you have reached your maximum download limit.</code>", reply_markup=InlineKeyboardMarkup(P_BUTTON))
        return

    try:
        ydl_opts = {
            'format': 'best',
            'listformats': True
        }
        ydl = yt_dlp.YoutubeDL(ydl_opts)
        info = ydl.extract_info(yurl, download=False)
        title = info['title']
        thumbnail_url = info.get('thumbnail')

        # Download the thumbnail image
        global thumbnail_path
        thumbnail_path = "thumbnail.jpg"
        response = requests.get(thumbnail_url)
        with open(thumbnail_path, 'wb') as file:
            file.write(response.content)

        # Get available formats
        formats = info['formats']
        format_buttons = []

        # Create callback buttons for each available mp4 video format
        for i, fmt in enumerate(formats):
            if fmt['ext'] == 'mp4' and fmt.get('filesize'):
                format_note = fmt.get('format_note', '')
                filesize_mb = fmt['filesize'] / (1024 * 1024)  # Convert to megabytes
                button = InlineKeyboardButton(
                    f"{format_note} - {filesize_mb:.2f} MB",  # Display file size in megabytes with 2 decimal places
                    callback_data=f"download_{fmt['format_id']}"
                )
                format_buttons.append([button])  # Add the button as a single-item list

        # Create reply markup with the format buttons in a vertical layout
        reply_markup = InlineKeyboardMarkup(format_buttons)

        # Send the reply message with available formats and thumbnail
          # Delete the "Processing" message
        global qu
        qu = await app.send_photo(
            message.chat.id,
            photo=thumbnail_path,
            caption=f"<code>Please select the video:</code>\n\n{title}",
            reply_markup=reply_markup
        )
        await msg.delete()
    except yt_dlp.DownloadError as e:
        await msg.edit_text("Sorry, the requested format is not available for this video. Please try another format.")
        print(e)
        return

    except Exception as e:
        await msg.edit_text("Sorry, there was a problem with that particular video.")
        print(e)
        return

@app.on_callback_query()
async def handle_callback_query(client, query):
    if query.data.startswith("download_"):
        # Extract the selected format code from the callback data
        format_code = query.data.split("_")[1]

        try:
            ydl_opts = {
		    'format': f'bestvideo[height<={format_code}]+bestaudio/best',
		    'outtmpl': '%(title)s.%(ext)s'
	    }
            await qu.edit_text("<code>Downloading Video.....</code>")
            ydl = yt_dlp.YoutubeDL(ydl_opts)
            info = ydl.extract_info(yurl)
            title = info['title']
            filename = ydl.prepare_filename(info)

            # Download the video with the selected format
            ydl.download([yurl])
                   
        except Exception as e:
            await query.message.edit_text("Sorry, there was a problem with that particular video.")
            print(e)

    for file in os.listdir('.'):
        if file.endswith(".mp4"):
            # Send the downloaded video file to the user
            
            await qu.edit_text("<code>Uploading Video.....\n\nSometimes this takes some time🙂 Upload speed depends on the video size</code>")
            await app.send_chat_action(query.from_user.id, enums.ChatAction.UPLOAD_VIDEO)
            await app.send_video(
                chat_id=query.from_user.id,
                video=f"{filename}",
                thumb=thumbnail_path,
                caption=f"**Here Is your Requested Video👆**\n\n<code>{title}</code>\n\n🔗 Requestor: ||{query.from_user.mention}||\n🚀 Downloaded via: [All Save Bot ☘️](https://t.me/AIl_Save_Bot)",
                reply_markup=InlineKeyboardMarkup(SHARE_BUTTON)
            )

            # Remove the temporary video file
            os.remove(f"{filename}")
            os.remove(thumbnail_path)
            break
        else:
            continue
    await qu.delete()

     
#fb
@app.on_message((filters.regex("http://")|filters.regex("https://")) & (filters.regex('fb')|filters.regex('facebook')))
async def fb_downloader(_, message):
    ran = await message.reply_text("<code>Processing.....</code>")
    link = message.text
    user_id = message.from_user.id
    
    is_premium = check_user_premium(user_id)
    

    can_download, remaining_time = can_download_video(user_id, is_premium)
    if not can_download:
        if remaining_time is not None:
            minutes = remaining_time // 60
            await ran.edit_text(f"<code>Sorry, you need to wait {minutes} minutes  before downloading another video.</code>", reply_markup=InlineKeyboardMarkup(P_BUTTON))
        else:
            await ran.edit_text("<code>Sorry, you have reached your maximum download limit.</code>", reply_markup=InlineKeyboardMarkup(P_BUTTON))
        return
    
    url = "https://www.getfvid.com/downloader"
    querystring = {"url": link}

    response = requests.post(url, data=querystring)
    r = response.content
    soup = BeautifulSoup(r, 'html.parser')
    a_element = soup.find('source')
    video = a_element.get('src')
    await ran.edit_text("<code>Downloading Video.....</code>")
    req = requests.get(video)
    send_video_path = "video.mp4"
    with open(send_video_path, "wb") as f:
        f.write(req.content)
    await app.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_VIDEO)
    await ran.edit_text("<code>Uploading Video.....\n\nsometimes this take some time🙂 Upload speed depend on video size</code>")
    await app.send_video(message.chat.id, video=send_video_path, reply_to_message_id=message.id, caption=f"Here is your requested Video👆\n\n🔗 Requestor : ||{message.from_user.mention}||\n🚀 Downloaded via: [All Save Bot ☘️](https://t.me/AIl_Save_Bot)", reply_markup=InlineKeyboardMarkup(SHARE_BUTTON))
    await ran.delete()
    os.remove(send_video_path)


# Download command handler
@app.on_message((filters.regex("http://") | filters.regex("https://")) & (filters.regex('envato')))
async def evanto_downloader(_, message):
    user_id = message.from_user.id

    # Process the download link
    
    ran = await message.reply_text("<code>Processing.....</code>")
    link = message.text
    is_premium = check_user_premium(user_id)
    

    can_download, remaining_time = can_download_video(user_id, is_premium)
    if not can_download:
        if remaining_time is not None:
            minutes = remaining_time // 60
            await ran.edit_text(f"<code>Sorry, you need to wait {minutes} minutes  before downloading another video.</code>", reply_markup=InlineKeyboardMarkup(P_BUTTON))
        else:
            await ran.edit_text("<code>Sorry, you have reached your maximum download limit.</code>", reply_markup=InlineKeyboardMarkup(P_BUTTON))
        return

    url = "https://www.expertstool.com/converter.php"
    payload = {"url": link}

    response = requests.post(url, data=payload)
    r = response.content

    soup = BeautifulSoup(r, 'html.parser')
    video_element = soup.find('video')
    photo_element = soup.find('img')
    if video_element:
        await ran.edit_text("<code>Downloading Video.....</code>")
        video_src = video_element.get('src')
        req = requests.get(video_src)
        send_video_path = "video.mp4"
        with open(send_video_path, "wb") as f:
            f.write(req.content)
        await app.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_VIDEO)
        await ran.edit_text("<code>Uploading Video.....\n\nsometimes this take some time🙂 Upload speed depend on video size</code>")
        await app.send_video(message.chat.id, video=send_video_path, caption=f"Here is your requested Video👆\n\n🔗 Requestor : ||{message.from_user.mention}||\n🚀 Downloaded via: [All Save Bot ☘️](https://t.me/AIl_Save_Bot)", reply_to_message_id=message.id, reply_markup=InlineKeyboardMarkup(SHARE_BUTTON))
        await ran.delete()
        os.remove(send_video_path)

    elif photo_element:
        await ran.edit_text("<code>Downloading Photo.....</code>")
        pic_src = photo_element.get('src')
        req = requests.get(pic_src)
        send_pic_path = "pic.jpg"
        with open(send_pic_path, "wb") as f:
            f.write(req.content)
        await app.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_PHOTO)
        await ran.edit_text("<code>Uploading Photo.....</code>")
        await app.send_photo(message.chat.id, photo=send_pic_path, caption=f"Here is your requested Photo👆\n\n🔗 Requestor : ||{message.from_user.mention}||\n🚀 Downloaded via: [All Save Bot ☘️](https://t.me/AIl_Save_Bot)", reply_to_message_id=message.id, reply_markup=InlineKeyboardMarkup(SHARE_BUTTON))
        await ran.delete()
        os.remove(send_pic_path)

    else:
        await app.send_message(message.chat.id, "Failed to get requested video😢")

#stats
@app.on_message(filters.command("stats") & filters.user(cfg.SUDO))
async def dbtool(_, message):
    xx = all_users()
    x = all_groups()
    tot = int(xx + x)
    await message.reply_text(text=f"""
🍀 Chats Stats 🍀
🙋‍♂️ Users : `{xx}`
👥 Groups : `{x}`
🚧 Total users & groups : `{tot}` """)
    
#bcast    
@app.on_message(filters.command("bcast") & filters.user(cfg.SUDO))
async def bcast(_, m):
    allusers = users
    lel = await m.reply_text("`⚡️ Processing...`")
    success = 0
    failed = 0
    deactivated = 0
    blocked = 0
    for usrs in allusers.find():
        try:
            userid = usrs["user_id"]
            #print(int(userid))
            if m.command[0] == "bcast":
                await m.reply_to_message.copy(int(userid))
            success +=1
        except FloodWait as ex:
            await asyncio.sleep(ex.value)
            if m.command[0] == "bcast":
                await m.reply_to_message.copy(int(userid))
        except errors.InputUserDeactivated:
            deactivated +=1
            remove_user(userid)
        except errors.UserIsBlocked:
            blocked +=1
        except Exception as e:
            print(e)
            failed +=1

    await lel.edit(f"✅Successfull to `{success}` users.\n❌ Faild to `{failed}` users.\n👾 Found `{blocked}` Blocked users \n👻 Found `{deactivated}` Deactivated users.")

#ytdlp-sup
@app.on_message((filters.regex("http://")|filters.regex("https://")))
async def download_anyvideo(client, message):
    url = message.text
    msg = await message.reply_text("<code>Processing.....</code>")
    user_id = message.from_user.id
    
    is_premium = check_user_premium(user_id)
    

    can_download, remaining_time = can_download_video(user_id, is_premium)
    if not can_download:
        if remaining_time is not None:
            minutes = remaining_time // 60
            await msg.edit_text(f"<code>Sorry, you need to wait {minutes} minutes  before downloading another video.</code>", reply_markup=InlineKeyboardMarkup(P_BUTTON))
        else:
            await msg.edit_text("<code>Sorry, you have reached your maximum download limit.</code>", reply_markup=InlineKeyboardMarkup(P_BUTTON))
        return

    ydl_opts = {
            "progress_hooks": [lambda d: download_progress_hook(d, message, client)]
        }


    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            await msg.edit_text("<code>Downloading Video.....</code>")
            info_dict = ydl.extract_info(url, download=False)
            file_name = ydl.prepare_filename(info_dict)
            await run_async(ydl.download, [url])
        except yt_dlp.DownloadError:
            await msg.edit_text("Sorry, There was a problem with that particular video")
            return


    for file in os.listdir('.'):
        if file.endswith(".mp4"):
            await msg.edit_text("<code>Uploading Video.....\n\nsometimes this take some time🙂 Upload speed depend on video size</code>")
            await app.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_VIDEO)
            await message.reply_video(f"{file}", caption=f"**Here Is your Requested Video👆**\n\n<code>{file_name}</code>\n\n🔗 Requestor : ||{message.from_user.mention}||\n🚀 Downloaded via: [All Save Bot ☘️](https://t.me/AIl_Save_Bot)", reply_markup=InlineKeyboardMarkup(SHARE_BUTTON))
            os.remove(f"{file}")
            break
        else:
            continue

    for file in os.listdir('.'):
        if file.endswith(".mkv"):
            await msg.edit_text("<code>Uploading Video.....\n\nsometimes this take some time🙂 Upload speed depend on video size</code>")
            await app.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_VIDEO)
            await message.reply_video(f"{file}", caption=f"**Here Is your Requested Video👆**\n\n<code>{file_name}</code>\n\n🔗 Requestor : ||{message.from_user.mention}||\n🚀 Downloaded via: [All Save Bot ☘️](https://t.me/AIl_Save_Bot)", reply_markup=InlineKeyboardMarkup(SHARE_BUTTON))
            os.remove(f"{file}")
            break
        else:
            continue        

    await msg.delete()

print("I'm Fucking Working Now!")
app.run()
