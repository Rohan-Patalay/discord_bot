import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Load bot token
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Enable intents
intents = discord.Intents.default()
intents.message_content = True

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Store active sessions
sessions = {}

# Store session history for daily reports
session_history = {}

# Scheduler for daily reports
scheduler = AsyncIOScheduler()

# Set the report channel (Replace with your actual channel ID)
REPORT_CHANNEL_ID = 1352553890750533724  # Replace with your channel ID

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} and ready!")
    scheduler.start()  # Start the scheduler

# Function to format time nicely
def format_time(dt):
    return dt.strftime("%I:%M %p")  # Converts to 12-hour format with AM/PM

# Function to format duration nicely
def format_duration(duration):
    total_seconds = int(duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    if hours and minutes:
        return f"{hours} hr {minutes} min"
    elif hours:
        return f"{hours} hr"
    elif minutes:
        return f"{minutes} min"
    else:
        return "less than a minute"

# Command to start a work session
@bot.command(name="start")
async def start_session(ctx, *, session_name: str):
    user_id = ctx.author.id
    if user_id in sessions:
        await ctx.send(f"{ctx.author.mention}, you already have an active session!")
        return
    
    sessions[user_id] = {
        "name": session_name,
        "start_time": datetime.now()
    }
    
    await ctx.send(f" {ctx.author.mention}, started session: **{session_name}** at **{format_time(sessions[user_id]['start_time'])}**")

    # Reminder after 1 hour
    await asyncio.sleep(3600)  
    if user_id in sessions:
        await ctx.send(f"⏳ {ctx.author.mention}, you've been working on **{session_name}** for an hour! Take a short break. ☕")

# Command to end a session
@bot.command(name="end")
async def end_session(ctx):
    user_id = ctx.author.id
    if user_id not in sessions:
        await ctx.send(f"{ctx.author.mention}, you don't have an active session!")
        return
    
    session = sessions.pop(user_id)
    end_time = datetime.now()
    duration = end_time - session["start_time"]
    
    # Store the session in history
    if user_id not in session_history:
        session_history[user_id] = []
    session_history[user_id].append({
        "name": session["name"],
        "duration": duration,
        "start_time": format_time(session["start_time"]),
        "end_time": format_time(end_time)
    })
    
    await ctx.send(f" {ctx.author.mention}, ended session: **{session['name']}**. Duration: **{format_duration(duration)}**")

# Command to view session history
@bot.command(name="history")
async def show_history(ctx):
    user_id = ctx.author.id
    if user_id not in session_history or len(session_history[user_id]) == 0:
        await ctx.send(f"{ctx.author.mention}, you have no session history yet!")
        return
    
    history_text = f"📜 **Session History for {ctx.author.name}:**\n"
    for session in session_history[user_id]:
        history_text += f"-> **{session['name']}** - **{format_duration(session['duration'])}** | {session['start_time']} - {session['end_time']}\n"

    await ctx.send(history_text)

# Command to send daily report manually
@bot.command(name="report")
async def send_report(ctx):
    user_id = ctx.author.id
    if user_id not in session_history or len(session_history[user_id]) == 0:
        await ctx.send(f"{ctx.author.mention}, you have no recorded sessions today!")
        return

    report_text = f"📊 **Daily Report for {ctx.author.name}:**\n"
    total_duration = timedelta()
    
    for session in session_history[user_id]:
        report_text += f"🕒 **{session['name']}** - **{format_duration(session['duration'])}** | {session['start_time']} - {session['end_time']}\n"
        total_duration += session["duration"]

    report_text += f"\n⏳ **Total Work Time:** {format_duration(total_duration)}"
    
    await ctx.send(report_text)

    # Clear history after sending the report
    session_history[user_id] = []

# Scheduled daily report at 10:00 PM
async def daily_report():
    channel = bot.get_channel(REPORT_CHANNEL_ID)
    if channel:
        await channel.send("📢 **Daily Work Session Report:**")
        for user_id in session_history:
            if session_history[user_id]:  # Only send if user has history
                user = await bot.fetch_user(user_id)
                await send_report(channel)  # Send report

scheduler.add_job(daily_report, "cron", hour=22, minute=0)

# Run bot
bot.run(TOKEN)
