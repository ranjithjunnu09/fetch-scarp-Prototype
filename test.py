import os

from dotenv import load_dotenv

from google import genai


# =====================================================
# LOAD ENV
# =====================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

dotenv_path = os.path.join(
    BASE_DIR,
    ".env"
)

load_dotenv(
    dotenv_path,
    override=True
)


# =====================================================
# DEBUG ENV
# =====================================================

print("\n========== GEMINI TEST ==========\n")

print("ENV PATH:")
print(dotenv_path)

print("\nENV EXISTS:")
print(os.path.exists(dotenv_path))


# =====================================================
# API KEY
# =====================================================

api_key = os.getenv(
    "GEMINI_API_KEY"
)

print("\nAPI KEY:")

if api_key:

    print(
        api_key[:40] + "..."
    )

    print("\nKEY LENGTH:")
    print(len(api_key))

else:

    print("❌ API KEY NOT FOUND")

    exit()


# =====================================================
# CREATE GEMINI CLIENT
# =====================================================

try:

    client = genai.Client(
        api_key=api_key
    )

    print("\n✅ GEMINI CLIENT CREATED")

except Exception as e:

    print("\n❌ CLIENT ERROR\n")

    print(e)

    exit()


# =====================================================
# SIMPLE CHATBOT TEST
# =====================================================

try:

    print("\n⏳ SENDING REQUEST...\n")

    response = client.models.generate_content(

        model="gemini-2.5-flash",

        contents="""
You are a helpful AI chatbot.

User:
Hello, introduce yourself in 3 lines.
"""
    )

    print("✅ GEMINI RESPONSE SUCCESS\n")

    print("LLM RESPONSE:\n")

    print(response.text)

except Exception as e:

    print("\n❌ GEMINI ERROR\n")

    print(e)


print("\n=================================\n")