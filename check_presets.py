
import json
import requests
import sys

# Extract presets from the file content I know (avoiding imports issues if running standalone)
PRESET_CHECKPOINTS = {
    "it_IT-riccardo-x_low (Male)": {
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/it/it_IT/riccardo/x_low/epoch=4619-step=1729116.ckpt",
    },
    "it_IT-leonardo-medium (Male)": {
        "url": "https://huggingface.co/kirys79/piper_italiano/resolve/main/Leonardo/leonardo-epoch=2024-step=996300.ckpt",
    },
    "it_IT-aurora-medium (Female)": {
        "url": "https://huggingface.co/kirys79/piper_italiano/resolve/main/Aurora/epoch=2093-step=498372.ckpt",
    },
    "it_IT-giorgio-medium (Male)": {
        "url": "https://huggingface.co/kirys79/piper_italiano/resolve/main/Giorgio/giorgio-epoch=5028-step=1098436.ckpt",
    },
    "en_US-libritts-high (Multi)": {
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/libritts/high/epoch=955-step=3176588.ckpt",
    }
}

def check_urls():
    print("Checking Preset URLs...")
    for name, data in PRESET_CHECKPOINTS.items():
        url = data['url']
        try:
            r = requests.head(url, timeout=5)
            status = r.status_code
            # Some servers might return 403 or 405 for HEAD, try GET stream=True
            if status >= 400:
                 r = requests.get(url, stream=True, timeout=5)
                 status = r.status_code
                 r.close()
            
            print(f"[{status}] {name}")
        except Exception as e:
            print(f"[ERR] {name}: {e}")

if __name__ == "__main__":
    check_urls()
