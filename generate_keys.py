"""
Generate API keys for LiveKit configuration.

This script generates secure random keys for LiveKit API authentication.
Run this before starting the services for the first time.
"""

import secrets
import base64


def generate_api_key():
    """Generate a secure random API key."""
    random_bytes = secrets.token_bytes(32)
    return base64.b64encode(random_bytes).decode('utf-8')


if __name__ == "__main__":
    print("=" * 60)
    print("LiveKit API Key Generator")
    print("=" * 60)
    print()

    api_key = generate_api_key()
    api_secret = generate_api_key()

    print("Generated API Keys:")
    print("-" * 60)
    print(f"LIVEKIT_API_KEY={api_key}")
    print(f"LIVEKIT_API_SECRET={api_secret}")
    print("-" * 60)
    print()

    print("Instructions:")
    print("1. Copy the keys above")
    print("2. Update your .env file with these values")
    print("3. Update configs/livekit.yaml with the API key")
    print("4. Update configs/sip.yaml with the API key and secret")
    print()

    # Also update the .env file automatically
    try:
        env_file = ".env"
        env_example = ".env.example"

        # Read the example file
        with open(env_example, 'r') as f:
            content = f.read()

        # Replace placeholder values
        content = content.replace('LIVEKIT_API_KEY=devkey', f'LIVEKIT_API_KEY={api_key}')
        content = content.replace('LIVEKIT_API_SECRET=secret', f'LIVEKIT_API_SECRET={api_secret}')

        # Write to .env file
        with open(env_file, 'w') as f:
            f.write(content)

        print(f"✓ Created {env_file} with generated keys")
        print()

    except FileNotFoundError:
        print("⚠ .env.example not found. Please create .env manually with the keys above.")
        print()

    # Generate config files with keys
    print("Next steps:")
    print("1. Update configs/livekit.yaml - replace 'devkey: secret' with:")
    print(f"   {api_key}: {api_secret}")
    print()
    print("2. Update configs/sip.yaml - replace api_key and api_secret with:")
    print(f"   api_key: {api_key}")
    print(f"   api_secret: {api_secret}")
    print()
    print("3. Run: docker-compose up -d")
    print("=" * 60)
