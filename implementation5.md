# Implementation Plan: AI Emoji System

Make the AI use custom Discord emojis contextually based on mode, affection level, and conversation triggers.

---

## Available Emojis & Usage Rules

| Emoji | Name | Usage | Restrictions |
|-------|------|-------|--------------|
| `<a:tada:1466380598535782410>` | tada | When user calls femmy or yumi | All modes |
| `<:mikucinema:1466380594312249385>` | mikucinema | When user is dramatic/sarcastic/dumb | All modes |
| `<a:ban:1466380556613980265>` | ban | When banning someone | All modes |
| `<:thisisfinefrog:1466380478734008341>` | thisisfinefrog | When user bullies or is rude | All modes |
| `<:pout:1466380471134064817>` | pout | When user makes bot annoyed/angry | All modes |
| `<:inlovehearts:1466380463080865966>` | inlovehearts | High affection responses | Femboy mode, affection >= 800 |
| `<:horny:1466380460723798028>` | horny | Flirty responses | Femboy evil mode only |
| `<:aah_openingmouth_horny:1466380414309367921>` | aah_openingmouth_horny | Flirty responses | Femboy evil mode only |
| `<a:twin_spin:1467187207491031243>` | twin_spin | Excited responses | Femboy mode, affection >= 500 |
| `<a:sneakpeekcat:1467187672450728017>` | sneakpeekcat | When user mentions femmy | Femboy mode only |
| `<:what:1467187836045496591>` | what | When user says something shocking | All modes |

### General Use Emojis (No Restrictions)

```
<:smh:1466380596266799199>
<:meowsadpats:1466380592332406834>
<:meowpatshappy:1466380589912428554>
<:inloove:1466380588129980426>
<:holdingheartemoji:1466380585978040421>
<a:happyemoji:1466380582924714182>
<:handsyellowheartredyt:1466380579816865905>
<:happy_normalblush:1466380577560334474>
<:facewithbagsundereyes:1466380575358324882>
<a:eyebrowflashsmirk:1466380572011004108>
<:erm:1466380569637294093>
<a:doropatfast:1466380567560982548>
<:cutesybite:1466380565442728202>
<:cutepet:1466380563412811797>
<:browhat:1466380561412264111>
<:Annoyed:1466380554793652244>
<:Youmesittingalone:1466380484899639330>
<:uhmmmm_sweating:1466380482437578753>
<:slay_christmas_hat:1466380476200648847>
<:sendlove:1466380472933285942>
<:ohmygosh:1466380468500041784>
<:kiss:1466380465756967023>
<a:girlblowkiss:1466380457938780231>
<:ermactually_nerd:1466380453136306310>
<:devilhandshake:1466380450271330494>
<:cutecrying:1466380447671124007>
<:cuteblushinghearts:1466380445355868233>
<:crying:1466380442486968330>
<:catblush:1466380439928180788>
<:browhat_facepalm:1466380437352878111>
<a:babyhm:1466380434567856210>
<:awwwwsocuteblush:1466380430017036308>
<:adoring:1466380420395434117>
<:actingcute:1466380416910102661>
<:a_bit_shy:1466380410815643749>
<:whoknows:1467187481052057601>
```

---

## Architecture

```
+--------------------------------------------------------------+
|                          Emoji System                         |
|--------------------------------------------------------------|
|  data/emoji_config.json  ->  Emoji definitions + usage rules  |
|  utils/emoji_manager.py  ->  Validates & filters emojis       |
|  AI Prompt Builder       ->  Injects available emojis to AI   |
+--------------------------------------------------------------+
```

---

## Implementation

### 1. Emoji Config File

**File:** `discord_bot/data/emoji_config.json`

```json
{
  "emojis": {
    "tada": {
      "id": "1466380598535782410",
      "animated": true,
      "usage": "when user calls femmy or yumi by name",
      "modes": ["all"],
      "conditions": {}
    },
    "mikucinema": {
      "id": "1466380594312249385",
      "animated": false,
      "usage": "when user is being dramatic, sarcastic, or dumb",
      "modes": ["all"],
      "conditions": {}
    },
    "ban": {
      "id": "1466380556613980265",
      "animated": true,
      "usage": "when banning someone",
      "modes": ["all"],
      "conditions": {}
    },
    "thisisfinefrog": {
      "id": "1466380478734008341",
      "animated": false,
      "usage": "when user bullies or is rude to bot",
      "modes": ["all"],
      "conditions": {}
    },
    "pout": {
      "id": "1466380471134064817",
      "animated": false,
      "usage": "when user makes bot annoyed or angry",
      "modes": ["all"],
      "conditions": {}
    },
    "what": {
      "id": "1467187836045496591",
      "animated": false,
      "usage": "when user says something shocking or surprising",
      "modes": ["all"],
      "conditions": {}
    },
    "inlovehearts": {
      "id": "1466380463080865966",
      "animated": false,
      "usage": "affectionate response to beloved user",
      "modes": ["mode_femboy"],
      "conditions": {"min_affection": 800}
    },
    "twin_spin": {
      "id": "1467187207491031243",
      "animated": true,
      "usage": "excited or happy response",
      "modes": ["mode_femboy"],
      "conditions": {"min_affection": 500}
    },
    "sneakpeekcat": {
      "id": "1467187672450728017",
      "animated": true,
      "usage": "when user mentions femmy's name",
      "modes": ["mode_femboy"],
      "conditions": {}
    },
    "horny": {
      "id": "1466380460723798028",
      "animated": false,
      "usage": "flirty or suggestive response",
      "modes": ["mode_femboy"],
      "conditions": {"evil_mode": true}
    },
    "aah_openingmouth_horny": {
      "id": "1466380414309367921",
      "animated": false,
      "usage": "flirty or suggestive response",
      "modes": ["mode_femboy"],
      "conditions": {"evil_mode": true}
    }
  },
  "general_emojis": [
    "<:smh:1466380596266799199>",
    "<:meowsadpats:1466380592332406834>",
    "<:meowpatshappy:1466380589912428554>",
    "<:inloove:1466380588129980426>",
    "<:holdingheartemoji:1466380585978040421>",
    "<a:happyemoji:1466380582924714182>",
    "<:handsyellowheartredyt:1466380579816865905>",
    "<:happy_normalblush:1466380577560334474>",
    "<:facewithbagsundereyes:1466380575358324882>",
    "<a:eyebrowflashsmirk:1466380572011004108>",
    "<:erm:1466380569637294093>",
    "<a:doropatfast:1466380567560982548>",
    "<:cutesybite:1466380565442728202>",
    "<:cutepet:1466380563412811797>",
    "<:browhat:1466380561412264111>",
    "<:Annoyed:1466380554793652244>",
    "<:Youmesittingalone:1466380484899639330>",
    "<:uhmmmm_sweating:1466380482437578753>",
    "<:slay_christmas_hat:1466380476200648847>",
    "<:sendlove:1466380472933285942>",
    "<:ohmygosh:1466380468500041784>",
    "<:kiss:1466380465756967023>",
    "<a:girlblowkiss:1466380457938780231>",
    "<:ermactually_nerd:1466380453136306310>",
    "<:devilhandshake:1466380450271330494>",
    "<:cutecrying:1466380447671124007>",
    "<:cuteblushinghearts:1466380445355868233>",
    "<:crying:1466380442486968330>",
    "<:catblush:1466380439928180788>",
    "<:browhat_facepalm:1466380437352878111>",
    "<a:babyhm:1466380434567856210>",
    "<:awwwwsocuteblush:1466380430017036308>",
    "<:adoring:1466380420395434117>",
    "<:actingcute:1466380416910102661>",
    "<:a_bit_shy:1466380410815643749>",
    "<:whoknows:1467187481052057601>"
  ]
}
```

---

### 2. EmojiManager Class

**File:** `discord_bot/utils/emoji_manager.py`

```python
import json
import re
from pathlib import Path
from typing import Dict, List
from utils.logger import get_logger

logger = get_logger(__name__)

class EmojiManager:
    def __init__(self, bot):
        self.bot = bot
        self.config = self._load_config()
        self._validated_emojis: Dict[str, str] = {}
        self._validated_general: List[str] = []
    
    def _load_config(self) -> dict:
        config_path = Path(__file__).parent.parent / "data" / "emoji_config.json"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("emoji_config.json not found, using empty config")
            return {"emojis": {}, "general_emojis": []}
    
    async def validate_emojis(self) -> None:
        """Validate that configured emojis exist and cache them."""
        for name, data in self.config.get("emojis", {}).items():
            emoji_id = int(data["id"])
            emoji = self.bot.get_emoji(emoji_id)
            if emoji:
                self._validated_emojis[name] = str(emoji)
                logger.debug(f"Validated emoji: {name}")
            else:
                logger.warning(f"Emoji not found: {name} (ID: {emoji_id})")

        # Validate general emojis by ID where possible
        self._validated_general = []
        for raw in self.config.get("general_emojis", []):
            match = re.match(r"<a?:[A-Za-z0-9_]+:(\d+)>", raw)
            if not match:
                continue
            emoji = self.bot.get_emoji(int(match.group(1)))
            if emoji:
                self._validated_general.append(str(emoji))
            else:
                logger.warning(f"General emoji not found: {raw}")
    
    def get_emoji(self, name: str) -> str:
        """Get emoji string by name."""
        return self._validated_emojis.get(name, "")
    
    def get_available_emojis(
        self,
        mode: str,
        affection: int = 0,
        evil_mode: bool = False
    ) -> Dict[str, Dict[str, str]]:
        """Get emojis available for current context with usage instructions."""
        available = {}
        
        for name, data in self.config.get("emojis", {}).items():
            # Skip if not validated
            if name not in self._validated_emojis:
                continue
            
            # Check mode restriction
            modes = data.get("modes", ["all"])
            if modes != ["all"] and mode not in modes:
                continue
            
            # Check conditions
            conditions = data.get("conditions", {})
            if conditions.get("min_affection", 0) > affection:
                continue
            if conditions.get("evil_mode") and not evil_mode:
                continue
            
            available[name] = {
                "emoji": self._validated_emojis[name],
                "usage": data.get("usage", "general use")
            }
        
        return available
    
    def build_prompt_section(
        self,
        mode: str,
        affection: int = 0,
        evil_mode: bool = False
    ) -> str:
        """Build emoji usage instructions for AI prompt."""
        available = self.get_available_emojis(mode, affection, evil_mode)
        
        if not available and not self._validated_general:
            return ""
        
        lines = [
            "# Custom Emojis",
            "You may use these custom Discord emojis in your responses:",
            ""
        ]
        
        for name, info in available.items():
            lines.append(f"- {info['emoji']} -> {info['usage']}")

        if self._validated_general:
            lines.append("")
            lines.append("General emojis (no restrictions):")
            lines.append(" ".join(self._validated_general))
        
        lines.extend([
            "",
            "Use emojis sparingly (1-2 per message max). Match emoji to emotional context."
        ])
        
        return "\n".join(lines)
```

---

### 3. Integration with AI Brain

**File:** `discord_bot/cogs/ai_brain.py`

Add emoji section to system prompt:

```python
# In the response generation method:

# Get emoji prompt section
emoji_section = self.bot.emoji_manager.build_prompt_section(
    mode=current_mode,
    affection=affection_points,
    evil_mode=is_evil_mode
)

# Append to system prompt
if emoji_section:
    full_prompt = f"{base_system_prompt}\n\n{emoji_section}"
```

---

### 4. Bot Initialization

**File:** `discord_bot/main.py`

```python
from utils.emoji_manager import EmojiManager

# In Femmy.__init__:
self.emoji_manager = EmojiManager(self)

# In Femmy.on_ready (existing):
await self.emoji_manager.validate_emojis()
logger.info(
    "Validated %s emoji rules and %s general emojis",
    len(self.emoji_manager._validated_emojis),
    len(self.emoji_manager._validated_general)
)
```

---

## Dynamic vs Hardcoded

**We use a hybrid approach:**

| What | Where | Why |
|------|-------|-----|
| Emoji IDs + usage rules | `emoji_config.json` | AI needs usage instructions |
| Emoji validation | `EmojiManager.validate_emojis()` | Ensures emojis exist via API |
| Available emoji filtering | Runtime | Depends on mode/affection/evil_mode |

**Benefit:** If an emoji is removed from Discord, the bot logs a warning and skips it rather than sending broken emoji strings.

---

## Implementation Checklist

- [ ] Create `discord_bot/data/emoji_config.json` with all emojis
- [ ] Create `discord_bot/utils/emoji_manager.py`
- [ ] Initialize `EmojiManager` in `main.py`
- [ ] Call `validate_emojis()` in `on_ready`
- [ ] Add `build_prompt_section()` call in `ai_brain.py` prompt builder
- [ ] Test emoji filtering by mode/affection/evil_mode
- [ ] Ensure general emojis are validated and included in the prompt section
