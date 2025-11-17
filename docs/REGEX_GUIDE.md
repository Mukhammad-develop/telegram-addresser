# 🔣 Regex Replacement Rules - Simple Guide

## What is Regex?

**Regex** (Regular Expressions) lets you find and replace **patterns** instead of exact text.

### Simple Example:

**Without Regex (Exact Match):**
- Find: `https://t.me/c/2921430534/238`
- This ONLY matches that exact link with `/238` at the end

**With Regex (Pattern Match):**
- Find: `https://t\.me/c/2921430534/\d+`
- This matches ALL links from that channel: `/238`, `/248`, `/1000`, etc.

## When Should I Use Regex?

✅ **Use Regex When:**
- You want to replace links with different numbers: `/238`, `/248`, `/999`
- You want to replace similar phrases: "Good morning", "Good afternoon", "Good evening"
- You want to match variations: phone numbers, dates, usernames

❌ **Use Normal (Exact Match) When:**
- You're replacing one specific word or link
- You want simple, straightforward replacement
- You don't need pattern matching

## How to Add Regex Rules

### Option 1: Using Admin Bot

1. Open your admin bot in Telegram
2. Choose "🔄 Replacement Rules"
3. Choose "➕ Add Rule"
4. **Step 1:** Enter the pattern (see examples below)
5. **Step 2:** Enter what to replace it with
6. **Step 3:** Choose case-sensitive (usually "Yes" for links)
7. **Step 4:** Choose "✅ Yes (Regex)"

### Option 2: Edit config.json

Add this to the `replacement_rules` section:

```json
{
  "find": "https://t\\.me/c/2921430534/\\d+",
  "replace": "https://t.me/+YOUR_INVITE_LINK",
  "case_sensitive": true,
  "is_regex": true
}
```

## Common Regex Patterns

### Replace Channel Message Links

**Problem:** You want to replace ALL links like:
- `https://t.me/c/2921430534/238`
- `https://t.me/c/2921430534/248`
- `https://t.me/c/2921430534/1000`

**Solution:**
- Find: `https://t\.me/c/2921430534/\d+`
- Replace: `https://t.me/+fL1L6_W1tFtlYjE0`
- Regex: Yes

### Replace Phone Numbers

**Problem:** Replace any phone number format:
- +1-234-567-8900
- +44 20 1234 5678

**Solution:**
- Find: `\+\d{1,3}[-\s]?\d{2,4}[-\s]?\d{3,4}[-\s]?\d{4}`
- Replace: `+1-555-NEW-NUMBER`
- Regex: Yes

### Replace Times of Day

**Problem:** Replace "Good morning", "Good afternoon", "Good evening"

**Solution:**
- Find: `Good (morning|afternoon|evening)`
- Replace: `Hello`
- Regex: Yes

## Important Notes

⚠️ **Special Characters in Regex:**

If your pattern includes these characters, you MUST add a `\` before them:
- `.` becomes `\.`
- `?` becomes `\?`
- `+` becomes `\+`
- `(` becomes `\(`
- `)` becomes `\)`

**Common Regex Symbols:**
- `\d+` = one or more numbers (123, 45, 6789)
- `\d{3}` = exactly 3 numbers (123)
- `.*` = any characters
- `\s` = space
- `|` = OR (cat|dog matches "cat" or "dog")

⚠️ **Regex Will Break Formatting:**

When you use regex (or any replacement), **formatting will be lost**:
- ❌ Bold, italic, custom emojis won't work
- ✅ Plain text will work fine

If you need to keep formatting, don't use replacements on those messages.

## Testing Your Regex

### Test Before Using:

1. Add the rule in admin bot
2. Forward a test message
3. Check if it worked correctly
4. If not, remove the rule and try again

### Common Mistakes:

❌ **Wrong:** `https://t.me/c/2921430534/\d+` (missing `\` before `.`)
✅ **Right:** `https://t\\.me/c/2921430534/\\d+`

❌ **Wrong:** `\d` (in config.json - needs double backslash)
✅ **Right:** `\\d` (in config.json)

## Need Help?

If your regex isn't working:
1. Check if you escaped special characters (`.` → `\.`)
2. Check if you used double backslash in config.json (`\\d` not `\d`)
3. Test with a simple pattern first
4. Check bot logs for errors

## Summary

- **Regex** = pattern matching for flexible replacements
- Use it when you want to replace similar things with different numbers/words
- Add `\` before special characters like `.` and `+`
- In config.json, use `\\` instead of `\`
- Regex breaks formatting (bold, emojis, etc.)

That's it! You're ready to use regex. 🎉

