import discord
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import json
import time
import datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
UNI_USER = os.getenv('UNI_USER')
UNI_PASS = os.getenv('UNI_PASS')

channel_id_env = os.getenv('CHANNEL_ID')
CHANNEL_ID = int(channel_id_env) if channel_id_env else 0

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

def get_professor_name(course_name):
    name_lower = course_name.lower()
    if "english language" in name_lower:
        return "Dr. Rasha Saeed"
    elif "introduction to programming" in name_lower:
        return "Dr. HAFEZ M.S. ABDEL-WAHAB"
    elif "introduction to computer science" in name_lower:
        return "Dr. Mohamed M. Elgazzar"
    elif "linear algebra" in name_lower:
        return "Walid Basiony"
    elif "mathematical analysis" in name_lower:
        return "Dr. Rania Ahmed"
    elif "entrepreneur" in name_lower:
        return "Dr. El-sayed Orabi"
    return "Not Specified"

def load_sent_events():
    try:
        with open('sent_events.json', 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
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
        
        time.sleep(5)
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "event")))
        events = driver.find_elements(By.CLASS_NAME, "event")
        
        saved_events = load_sent_events()
        
        for event in events:
            try:
                title_el = event.find_element(By.CSS_SELECTOR, "a.text-truncate")
                raw_title = title_el.get_attribute("title")
                if not raw_title:
                    raw_title = title_el.get_attribute("textContent")
                raw_title = raw_title.strip()
                
                event_link = title_el.get_attribute("href")
                if not event_link:
                    event_link = "https://elearning-01.mti.edu.eg/"
                
                date_el = event.find_element(By.CSS_SELECTOR, "div.date.small")
                date_time = date_el.get_attribute("textContent").strip()
                date_time = " ".join(date_time.split())
                
                event_id = f"{raw_title}_{date_time}"
                
                if event_id not in saved_events:
                    new_events.append({
                        "raw_title": raw_title, 
                        "date": date_time, 
                        "link": event_link,
                        "id": event_id
                    })
                    save_sent_event(event_id)
            except Exception as inner_e:
                print(f"Error parsing event: {inner_e}")
                continue
                
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
            raw_title = event['raw_title']
            course_name = "Check Link For Details"
            task_name = raw_title
            
            if "-" in raw_title:
                parts = raw_title.split("-", 1)
                course_name = parts[0].replace("F26", "").strip()
                task_name = parts[1].strip()
            elif " is due" in raw_title:
                task_name = raw_title.replace(" is due", "").strip()

            professor = get_professor_name(course_name)

            embed = discord.Embed(
                title=f"📘 New {task_name}",
                description=f"A new update has been posted on the university portal.\n\n🔗 **[Access Assignment Directly]({event['link']})**",
                color=0x000080
            )
            embed.set_author(name="Automated Academic Tracker", icon_url="https://cdn-icons-png.flaticon.com/512/3135/3135715.png")
            embed.add_field(name="📚 Course", value=f"`{course_name}`", inline=True)
            embed.add_field(name="👨‍🏫 Professor", value=f"`{professor}`", inline=True)
            embed.add_field(name="⏳ Deadline", value=f"> {event['date']}", inline=False)
            embed.set_footer(text="M7md's Educational server | CS Dept.", icon_url="https://cdn-icons-png.flaticon.com/512/2948/2948062.png")
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            
            embeds.append(embed)
        
        await channel.send(content="@everyone 📢 **New Academic Updates Available!**", embeds=embeds)
        print("Message and Embeds sent successfully.")
    else:
        print("No new assignments.")
        
    await bot.close()

if __name__ == "__main__":
    print("Starting MTI Discord Scraper...")
    if TOKEN and CHANNEL_ID:
        bot.run(TOKEN)
    else:
        print("Error: Missing DISCORD_TOKEN or CHANNEL_ID in GitHub Secrets.")
