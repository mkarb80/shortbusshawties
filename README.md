# ShortbusShawties: Instagram automation

Group-chat dark humor. Five friends (Dre, Nate, Marco, Benny, Luis) in a chat called **Short Bus Shawties**. See `data/characters.md` for voices and running bits, and `data/canon.json` for what has already happened.

## How posting works

| Piece | What it does |
|---|---|
| `queue/q01.json`, `q02.json`, ... | Posts written ahead of time. The poster always takes the lowest-numbered unused file. Add `q13.json`, `q14.json` ... to extend the runway. |
| `data/bank.json` | Reserve. Used only when the queue is empty, so the page never goes silent. |
| `data/seed.json` | The 10 launch posts. Posted once, on demand, in reverse order so post 1 lands top-left on the grid. |
| GitHub Action `Instagram post` | Runs hourly. Posts once in the 12-4pm PT window and once in the 8pm-midnight PT window, then marks the slot done in `posted/`. |
| GitHub Action `Refresh Instagram token` | Weekly. Keeps the 60-day Instagram token alive. |

Runway at launch: 12 queued + 6 reserve = 9 days at 2 posts/day, independent of anyone's computer.

## One-time setup

Repository secrets (Settings, Secrets and variables, Actions):
- `IG_ACCESS_TOKEN`: Instagram long-lived token (Instagram API with Instagram Login; scopes `instagram_business_basic`, `instagram_business_content_publish`).
- `GH_PAT`: used only by the weekly token refresh job.

Repository variable: `IG_HANDLE` = `@shortbusshawties`.

Launch: Actions, Instagram post, Run workflow, tick **seed**.

## Post format

```json
{"id": "q13", "format": "chat", "pov": "Marco", "theme": "light", "time": "Sun 12:20 PM",
 "bits": ["marco_back"], "caption": "caption text + max 5 hashtags",
 "messages": [{"from": "Dre", "text": "..."}, {"system": "Nate left the lobby."}]}
```

Rules: `pov` is whoever is texting (blue, right side). Everyone is on their own phone; never "in the same room". Nobody's wife is named. Aim for 8 messages or fewer so the text stays readable on a phone.

## Manual controls

- Post now: Actions, Instagram post, Run workflow (force on).
- Preview only: tick **dry run**; images land in `posts/`.
- Skip a slot: add `posted/YYYY-MM-DD-a.json` (or `-b`) containing `{"skipped": true}`.
