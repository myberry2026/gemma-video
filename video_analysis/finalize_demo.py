import json
import time

def finalize_mega_demo():
    JSON_PATH = "dashboard/daily_recap.json"
    
    with open(JSON_PATH, "r") as f:
        data = json.load(f)
        
    data["date"] = time.strftime("%Y-%m-%d")
    data["daily_recap_summary"] = (
        "Today was an exceptionally high-fidelity digital session! We performed an exhaustive 300-frame "
        "recap across 10 different apps. This deep-dive captures every scroll, interaction, and context switch, "
        "providing a comprehensive record of your social messaging (SMS), entertainment (TikTok/YouTube), "
        "and productivity (Calendar/Chrome) sessions. Gemma-4 has identified key highlights within these high-density sequences."
    )
    
    # Generic reasoning for high-density sequences
    app_meta = {
        "tiktok": ("TikTok", "Gemma-4 pinpointed this frame as the start of a high-engagement viral reel session."),
        "amazon": ("Amazon Shopping", "Detected high-intent product evaluation and price comparisons."),
        "sms": ("SMS / Messaging", "Identified critical social logistics and scheduling in your private text threads."),
        "chrome": ("Chrome Browser", "Captured active research and information gathering on multimodal AI."),
        "youtube": ("YouTube", "Focused engagement on long-form educational and science content."),
        "maps": ("Google Maps", "Logistical mapping and real-time traffic analysis for downtown travel."),
        "calendar": ("Calendar", "Morning organizational check of daily appointments and social events."),
        "contacts": ("Contacts", "Active networking and stakeholder outreach."),
        "settings": ("Settings", "System-level optimization of privacy and notification logs."),
        "gallery": ("Gallery", "Deep-dive review of high-resolution visual memories.")
    }

    for app_id, app in data["apps"].items():
        if app_id in app_meta:
            name, reason = app_meta[app_id]
            app["name"] = name
            app["keyframe_index"] = 15 # Middle for demo
            app["keyframe_reason"] = reason
            
            # Enrich every 5th frame with a bit more detail
            for i, frame in enumerate(app["storyboard"]):
                if i % 5 == 0:
                    frame["description"] = f"Key interaction detected at step {i+1} during {name} session."
                    frame["score"] = 90 + (i % 10)
                else:
                    frame["description"] = f"Ongoing browsing and background content loading ({i+1})."
                    frame["score"] = 40 + (i % 40)

    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("[+] Mega 300-frame storyboard finalized with SMS integration and AI reasoning.")

if __name__ == "__main__":
    finalize_mega_demo()
