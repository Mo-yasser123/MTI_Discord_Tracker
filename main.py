import discord
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
UNI_USER = os.getenv('UNI_USER')
UNI_PASS = os.getenv('UNI_PASS')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

def load_sent_events():
    try:
       with open('sent_events.json', 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_sent_event(event_id):
    events = load_sent_events()
    if event_id not in events:
        events.append(event_id)
        with open('sent_events.json', 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=4)

def scrape_moodle():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    new_events = []

    try:
        driver.get("https://elearning-01.mti.edu.eg/login/index.php?loginredirect=1")
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(UNI_USER)
        driver.find_element(By.ID, "password").send_keys(UNI_PASS)
        
        login_btn = driver.find_element(By.ID, "loginbtn")
        driver.execute_script("arguments[0].click();", login_btn)
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "event")))
        events = driver.find_elements(By.CLASS_NAME, "event")
        
        saved_events = load_sent_events()
        
        for event in events:
            title = event.find_element(By.CSS_SELECTOR, "a.text-truncate").text
            date_time = event.find_element(By.CSS_SELECTOR, "div.date.small").text.strip()
            event_id = f"{title}_{date_time}"
            
            if event_id not in saved_events:
                new_events.append({"title": title, "date": date_time, "id": event_id})
                save_sent_event(event_id)
                
    except Exception as e:
        print(f"Scraping error: {e}")
    finally:
        driver.quit()
        
    return new_events

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    channel = bot.get_channel(CHANNEL_ID)
    
    if not channel:
        print("Channel not found.")
        await bot.close()
        return

    upcoming_events = scrape_moodle()
    
    if upcoming_events:
        embeds = []
        for event in upcoming_events:
            course_name = event['title']
            task_type = "تحديث جامعي"
            
            if "-" in course_name:
                parts = course_name.split("-")
                course_name = parts[0].replace("F26", "").strip()
                task_type = parts[1].strip()

            embed = discord.Embed(
                title=f"📝 {task_type}",
                description=f"**المادة:** `{course_name}`",
                url="https://elearning-01.mti.edu.eg/",
                color=0x2ecc71
            )
            embed.set_author(name="إشعار MTI Moodle", icon_url="https://cdn-icons-png.flaticon.com/512/3135/3135715.png")
            embed.add_field(name="⏳ الموعد النهائي (Deadline)", value=f"> {event['date']}", inline=False)
            embed.set_footer(text="CS Department Tracker", icon_url="https://cdn-icons-png.flaticon.com/512/2948/2948062.png")
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            
            embeds.append(embed)
        
        await channel.send(content="@everyone 🚨 **تكليفات جديدة ظهرت على المنصة!**", embeds=embeds)
    else:
        print("No new assignments.")
        
    await bot.close() # السطر ده هو اللي بيخلي السيرفر ميعلقش

bot.run(TOKEN)
