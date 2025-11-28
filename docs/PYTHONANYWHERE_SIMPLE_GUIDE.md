# 🚀 How to Run Your Telegram Bot 24/7 on PythonAnywhere

**A simple guide for non-technical users - No IT knowledge needed!**

---

## 📖 What This Guide Does

This guide will help you:
- Put your Telegram bot on a website that runs it 24/7
- Set it up so you never have to touch your computer again
- Make sure it keeps working even when you're sleeping

**Think of it like:** You're moving your bot from your personal computer to a "robot computer" on the internet that never turns off.

---

## 🎯 Before We Start

### What You Need:

1. **A PythonAnywhere account** (we'll create this together)
   - Costs: $5 per month
   - Like Netflix, but for running bots instead of watching shows

2. **Your Telegram information** (you should already have these):
   - Your bot's special code (looks like: `123456789:ABCdef...`)
   - Your phone number (for logging in to Telegram)
   - Your Telegram channels (the ones you're copying messages from/to)

3. **30-60 minutes of your time**
   - Grab a coffee ☕, we'll do this together!

---

## Step 1: Create Your Robot Computer Account

### What We're Doing:
Creating an account on PythonAnywhere - think of it as renting a tiny computer on the internet that will run your bot for you.

### Steps:

1. **Open your web browser** (Chrome, Safari, Firefox - any works)

2. **Go to:** https://www.pythonanywhere.com

3. **Click the big "Pricing & signup" button** at the top

4. **Choose "Hacker Plan"** ($5/month)
   - Why? The free version turns off after a few hours
   - The $5 plan keeps your bot running forever

5. **Fill in the form:**
   - Username: Pick something simple (like "mybot2024")
   - Email: Your regular email
   - Password: Make it strong, save it somewhere safe!

6. **Click "Register"**

7. **Check your email** and click the confirmation link

8. **Log in** to PythonAnywhere

🎉 **Done! You now have your robot computer!**

---

## Step 2: Upload Your Bot Files

### What We're Doing:
Moving all your bot files from your computer to the robot computer.

### Option A: Using ZIP File (Easiest!)

#### On Your Computer:

1. **Find your bot folder** (probably called `telegram-addresser`)

2. **Right-click on the folder** and choose:
   - **Mac:** "Compress telegram-addresser"
   - **Windows:** "Send to" → "Compressed (zipped) folder"

3. **You'll get a file** called `telegram-addresser.zip`
   - Remember where it is! (Desktop is good)

#### On PythonAnywhere Website:

4. **Click "Files"** at the top of the page

5. **You'll see a file browser** (looks like Windows Explorer or Mac Finder)

6. **Click "Upload a file"** button

7. **Choose your** `telegram-addresser.zip` file

8. **Wait for the upload** (might take 2-5 minutes)

9. **Click "Consoles"** at the top

10. **Click "Bash"** (it's like opening a command window)

11. **Type this command** (copy and paste it):
    ```
    unzip telegram-addresser.zip -d telegram-addresser
    ```

12. **Press Enter**

13. **Type this:**
    ```
    cd telegram-addresser
    ```

14. **Press Enter**

🎉 **Done! Your files are now on the robot computer!**

---

## Step 3: Install Required Software

### What We're Doing:
Installing the "ingredients" your bot needs to work - like installing apps on your phone.

### In that same black window (Bash console):

**Copy these commands ONE AT A TIME, paste them, and press Enter after each:**

```bash
python3.10 -m venv venv
```
*(Press Enter and wait 10 seconds)*

```bash
source venv/bin/activate
```
*(Press Enter)*

```bash
pip install -r requirements.txt
```
*(Press Enter and wait 30-60 seconds - you'll see lots of text)*

**When you see your username again, you're done!**

---

## Step 4: Add Your Settings

### What We're Doing:
Telling the bot YOUR information - which channels to copy, your passwords, etc.

### Easy Way:

1. **On your computer,** open your `config.json` file
   - It has all your channels, passwords, etc.

2. **In PythonAnywhere,** click **"Files"** at the top

3. **Click on "telegram-addresser"** folder

4. **Click "Upload a file"**

5. **Choose your** `config.json` file

6. **Done!** Your settings are uploaded

### Check It Worked:

1. In **Files**, you should see `config.json` in the `telegram-addresser` folder
2. Click on it to open and check it looks correct

---

## Step 5: Connect Your Telegram Account

### What We're Doing:
Logging your bot into Telegram - like logging into Instagram on a new phone.

### Steps:

1. **Go back to "Consoles"** tab

2. **Click on your Bash console** (or open a new one)

3. **Type these commands:**
   ```bash
   cd ~/telegram-addresser
   ```
   *(Press Enter)*

   ```bash
   source venv/bin/activate
   ```
   *(Press Enter)*

   ```bash
   python3 auth_worker.py
   ```
   *(Press Enter)*

4. **You'll see:**
   ```
   Available workers:
   1. worker_1
   ```

5. **Type: 1** and press Enter

6. **Enter your phone number** with the + sign
   - Example: `+421901234567`
   - Press Enter

7. **Check your Telegram app** - you'll get a code

8. **Type the code** and press Enter

9. **If you have two-factor authentication:**
   - It will ask for your password
   - Type it and press Enter

10. **You'll see:** ✅ Authentication successful!

**🎉 Done! Your bot can now access Telegram!**

**If you have more workers:** Repeat for each one (type 2, then 3, etc.)

---

## Step 6: Make It Run Forever

### What We're Doing:
Setting up TWO "auto-start" programs:
- One for managing the bot via Telegram
- One for actually copying messages

Think of it like setting your phone to auto-start certain apps when it boots up.

### Task 1: The Management Bot

1. **Click "Tasks"** at the top

2. **Scroll down to "Always-on tasks"**

3. **Click "Create a new always-on task"**

4. **In "Description"** box, type:
   ```
   Admin Bot
   ```

5. **In "Command"** box, type this ALL ON ONE LINE:**
   ```
   cd /home/YOUR_USERNAME/telegram-addresser && source venv/bin/activate && python3 admin_bot.py
   ```
   
   ⚠️ **IMPORTANT:** Change `YOUR_USERNAME` to your actual username!
   - Your username is shown at the top of the page (like "mybot2024")
   - So if your username is "mybot2024", you'd type:
     ```
     cd /home/mybot2024/telegram-addresser && source venv/bin/activate && python3 admin_bot.py
     ```

6. **Check the "Enabled" box** ✅

7. **Click "Create"**

8. **Wait 10 seconds** - you should see it turn GREEN (Running)

### Task 2: The Message Copier

1. **Click "Create a new always-on task"** AGAIN

2. **In "Description"** box, type:
   ```
   Message Forwarder
   ```

3. **In "Command"** box, type this ALL ON ONE LINE:**
   ```
   cd /home/YOUR_USERNAME/telegram-addresser && source venv/bin/activate && python3 worker_manager.py
   ```
   
   ⚠️ **IMPORTANT:** Again, change `YOUR_USERNAME` to your username!

4. **Check the "Enabled" box** ✅

5. **Click "Create"**

6. **Wait 10 seconds** - should turn GREEN (Running)

### Check Both Are Running:

You should now see TWO green checkmarks:
- ✅ Admin Bot (Running)
- ✅ Message Forwarder (Running)

**🎉 Done! Your bot is now running 24/7!**

---

## Step 7: Test It's Working

### Test 1: Check the Management Bot

1. **Open Telegram on your phone**

2. **Search for your bot** (the name you gave it)

3. **Send:** `/start`

4. **You should see:** Menu with buttons

✅ **If you see buttons, it's working!**

❌ **If nothing happens:** Wait 2 minutes and try again (might be starting up)

### Test 2: Check Message Copying

**Option A: Quick Test**

1. **Send a message** in one of your source channels

2. **Check the target channel** within 5-10 seconds

3. **Should see:** The message copied over

✅ **If copied, it's working!**

**Option B: Check Logs (slightly technical but safe)**

1. Click **"Consoles"** → **"Bash"**

2. Type:
   ```bash
   cd ~/telegram-addresser
   tail -20 logs/forwarder.log
   ```

3. Press Enter

4. **Look for lines** with arrows like: `LIVE -> Sent message`

✅ **If you see these, it's working!**

---

## 🎉 You're Done! What Now?

### Your Bot Is Now:

✅ Running 24/7 (even when you're sleeping)
✅ Copying messages automatically
✅ Accessible from your Telegram app
✅ Managed by the robot computer (not your computer)

### You Can Now:

**Close your laptop!** The bot keeps running on PythonAnywhere

**Use Telegram** to manage it:
- Send `/menu` to your bot
- Add channels, change settings, check status
- All from your phone!

**Check it daily:**
- Just send a message in source channel
- Check if it appears in target channel
- That's it!

---

## 📱 Daily Quick Check (30 seconds)

**Every day, do this quick check:**

1. Open Telegram
2. Send a test message in source channel
3. Check target channel (should appear in 5 seconds)
4. ✅ If it appears = All good!

**If test message doesn't appear:**
- Go to PythonAnywhere website
- Click "Tasks"
- Check both tasks have GREEN checkmark
- If red, click "Restart" button

---

## 🆘 Simple Troubleshooting

### Problem: Bot Not Responding

**What to do:**

1. Go to PythonAnywhere website
2. Click **"Tasks"**
3. Find your two tasks
4. **If RED (stopped):**
   - Click the task name
   - Click "Restart" button
   - Wait 30 seconds

5. **Still not working?**
   - Stop BOTH tasks (click "Stop")
   - Wait 2 minutes
   - Start both again (click "Start")

### Problem: Messages Not Copying

**Check these:**

1. **Is your phone number still logged into Telegram?**
   - Yes? Good, continue
   - No? You need to do Step 5 again

2. **Are tasks running?**
   - Go to Tasks → Should be GREEN
   - If RED, restart them

3. **Is bot admin in channels?**
   - Open channel settings in Telegram
   - Check bot is in "Administrators" list
   - If not, add it back

### Problem: Task Turns Red Every Day

**This means:** Session expired or something wrong

**Quick fix:**

1. Click **"Consoles"** → **"Bash"**

2. Copy-paste these commands ONE AT A TIME:
   ```bash
   cd ~/telegram-addresser
   ```
   *(Press Enter)*

   ```bash
   rm -f *.session*
   ```
   *(Press Enter)*

   ```bash
   source venv/bin/activate
   ```
   *(Press Enter)*

   ```bash
   python3 auth_worker.py
   ```
   *(Press Enter)*

3. Follow the login steps again (Step 5)

4. Go to Tasks and restart both tasks

### Problem: Getting an Email About "Too Much CPU"

**This means:** Bot is using too much power

**Quick fix:**

Ask your developer to:
- Reduce workers in config
- Increase polling time

(This is slightly technical, you might need help)

---

## 💰 Monthly Bill

**You'll be charged $5 per month** by PythonAnywhere

**Payment:**
- Automatic from your credit card
- Same day each month
- You'll get email receipt

**To cancel:**
- Account → Billing → Cancel subscription
- Your bot will stop running

---

## 🔐 Keep These Safe!

**Write down and save somewhere safe:**

1. PythonAnywhere username: _______________
2. PythonAnywhere password: _______________
3. Bot token (from @BotFather): _______________
4. Your Telegram password: _______________

**Don't share these with anyone!**

---

## 📞 Getting Help

### If Something's Wrong:

**Option 1: Ask Your Developer**
- They set this up, they can fix it quickly
- Show them the error message

**Option 2: Check the Logs**
- Go to PythonAnywhere → Consoles → Bash
- Type: `cd ~/telegram-addresser`
- Type: `tail -50 logs/forwarder.log`
- Send screenshot to your developer

**Option 3: Restart Everything**
- Tasks tab → Stop both tasks
- Wait 3 minutes
- Start both tasks
- Test again

### Common Messages You Might See:

**"Database is locked"**
- **What it means:** Two things trying to use same file
- **Fix:** Stop both tasks, wait 2 minutes, start again

**"AuthKeyDuplicatedError"**
- **What it means:** You logged in from two places
- **Fix:** Do Step 5 again (re-login)

**"Cannot access channel"**
- **What it means:** Bot can't see the channel
- **Fix:** Make sure bot is admin in ALL channels

---

## ✅ Simple Checklist

**Copy this checklist, check off as you go:**

- [ ] Created PythonAnywhere account ($5/month)
- [ ] Uploaded bot files (ZIP method)
- [ ] Installed software (pip install command)
- [ ] Uploaded config.json with my settings
- [ ] Logged into Telegram (auth_worker.py)
- [ ] Created Admin Bot task (GREEN checkmark)
- [ ] Created Message Forwarder task (GREEN checkmark)
- [ ] Tested: Bot responds to /start in Telegram
- [ ] Tested: Messages copy from source to target
- [ ] Saved my passwords somewhere safe
- [ ] Set calendar reminder to check daily

**If all checked ✅, you're done! 🎉**

---

## 🎓 In Simple Terms

**What You Built:**

```
Your Old Setup:
Your Computer → Telegram Bot
(Turns off when you close laptop)

Your New Setup:
PythonAnywhere Computer → Telegram Bot
(Never turns off, always working)
```

**How It Works:**

1. **Messages arrive** in source channel
2. **Robot computer sees them** (every 5 seconds it checks)
3. **Robot copies them** to target channel
4. **You manage it** from your phone via Telegram

**It's like having a robot assistant** that:
- Never sleeps
- Never takes a break
- Always copies messages
- You can control from your phone

---

## 🌟 You Did It!

**Congratulations!** You successfully:

✅ Created a cloud account
✅ Uploaded your bot
✅ Set it up to run forever
✅ Tested it works
✅ Can manage it from your phone

**This was the hardest part!** From now on, it just runs by itself.

**Need to change settings?**
- Open Telegram
- Message your bot
- Use the menu buttons
- Easy!

**Your bot is now working 24/7!** 🚀

---

## 📞 Quick Help Phone Numbers

**If completely stuck, contact:**

Your Developer: _______________
(They set this up and know it best)

PythonAnywhere Support: support@pythonanywhere.com
(For account/billing issues only)

---

**Remember:** It's supposed to be easy now! You did the hard setup, now it just works. Check it once a day, and enjoy your automated system! 🎉

**Have a question? Ask your developer - they're here to help!** 😊

