"""Quick-start setup helper."""
import os
import sys
import subprocess
from pathlib import Path


def main():
    root = Path(__file__).parent

    print("=" * 50)
    print("  J A R V I S  —  Setup")
    print("=" * 50)

    # Create .env from example if missing
    env_file = root / ".env"
    env_example = root / ".env.example"
    if not env_file.exists():
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            print(f"\n[1/3] Created .env — please add your ANTHROPIC_API_KEY")
        else:
            print("\n[1/3] No .env found — please create one with your API keys")
    else:
        print("\n[1/3] .env already exists")

    # Create data directories
    data_dir = Path.home() / ".jarvis"
    (data_dir / "logs").mkdir(parents=True, exist_ok=True)
    print(f"[2/3] Data directory: {data_dir}")

    # Install dependencies
    print("[3/3] Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(root / "requirements.txt")], check=True)

    print("\n✓ Setup complete!")
    print("\nNext steps:")
    print("  1. Edit .env and set your ANTHROPIC_API_KEY")
    print("  2. (Optional) Set PORCUPINE_ACCESS_KEY for wake word: https://picovoice.ai")
    print("  3. Grant macOS permissions: Accessibility + Microphone + Screen Recording")
    print("  4. Run: python -m jarvis.main")
    print("     Or:   python -m jarvis.main --no-voice  (skip microphone)")


if __name__ == "__main__":
    main()
