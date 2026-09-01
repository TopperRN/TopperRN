# Setup

Notes for keeping this profile working. GitHub only renders `README.md` on the profile — this file is just for you.

## Turn the snake on

The snake images 404 until the workflow has run once.

1. Repo → **Settings** → **Actions** → **General** → Workflow permissions → **Read and write permissions** → Save
2. Repo → **Actions** tab → **Generate snake animation** → **Run workflow**
3. Wait about a minute. It creates an `output` branch holding `snake.svg` and `snake-dark.svg`, then reruns itself every 12 hours.

## Things you may want to change

| What | Where |
|---|---|
| Skill percentages | `assets/skills.svg` — each bar has an `animate` tag; the `to=` value is `percent × 5` (70% → 350) |
| Accent colour | Search `4ec9b0` in `README.md` and `assets/skills.svg` |
| Project sections | Each one is a `<details>` block in `README.md` |

The repo name must stay `TopperRN` — that is the account login GitHub matches against for profile repos.
