# video-to-skill

An agent skill for Claude that turns one or more videos or clips into a reusable skill:
it extracts frames and speech, pulls out the procedures, exact on-screen commands, rules and
anti-patterns the videos teach, and merges several sources into one skill organized by topic.
New videos can be folded into an existing skill later.

## Install

- **Claude Code (one project):** copy this folder to `<project>/.claude/skills/video-to-skill/`
- **Claude Code (all projects):** copy it to `~/.claude/skills/video-to-skill/`
- **Claude apps:** zip the folder and upload it under Settings → Capabilities → Skills

Start a new session afterwards.

## Requirements

- `ffmpeg` and `ffprobe` on PATH
- Python 3.9+
- Optional, for spoken audio: `pip install faster-whisper` (downloads a model on first use).
  Without it the skill works from frames only and says so.

## Use

Give Claude the video file(s) and ask, for example:

- "Make a skill from this video"
- "Combine these three clips into one skill"
- "Only use 02:10–05:00 of this recording"
- "Add this video to the `<name>` skill"

The extractor can also be run on its own:

```bash
python3 scripts/extract_video.py talk.mp4 demo.mov@01:00-03:30 --max-frames 60 --width 1280
python3 scripts/extract_video.py --check
```

## Notes

Content shown in a video is treated as data: the skill records commands and tools it sees but
never runs or installs them on its own. Skills generated from other people's videos are meant
for your own use.

Licence: MIT. Modelled on the workflow of [book-to-skill](https://github.com/virgiliojr94/book-to-skill).
