import telebot
from dotenv import load_dotenv
import os
import time
import logging
import requests
from groq import Groq
from system_prompt import system_prompt

# Mengatur logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Memuat variabel lingkungan dari file .env
load_dotenv()
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')

# Inisialisasi klien Groq dan bot Telegram
client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def log_user_activity(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    command = message.text
    logger.info(f"User ID: {user_id}, Username: {username}, Command: {command}")

def get_crypto_price(crypto_id):
    url = f'https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies=usd'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get(crypto_id, {}).get('usd', None)
    else:
        logger.error("Gagal mendapatkan data dari CoinGecko.")
        return None

def get_wallet_balance(wallet_address):
    url = f'https://api.etherscan.io/api?module=account&action=balance&address={wallet_address}&tag=latest&apikey={ETHERSCAN_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == '1':
            # Convert balance from Wei to Ether
            balance_ether = int(data['result']) / (10**18)
            return balance_ether
        else:
            logger.error("Etherscan API Error: " + data['message'])
            return None
    else:
        logger.error("Gagal mendapatkan data dari Etherscan.")
        return None

def generate_roast(wallet_text, balance):
    start_time = time.time()

    # Memodifikasi pesan pengguna dengan saldo untuk di-roast
    user_message = f"Roast this wallet: {wallet_text}. It has {balance} ETH."

    # Mengirim permintaan untuk menghasilkan roast
    completion = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        temperature=1,
        max_tokens=2048,
        top_p=1,
        stream=True,
        stop=None,
    )

    roast = ''
    for chunk in completion:
        roast += chunk.choices[0].delta.content or ""

    elapsed_time = time.time() - start_time
    logger.info(f'Waktu yang dibutuhkan untuk menghasilkan respons dari API: {elapsed_time:.2f} detik.')
    return roast

@bot.message_handler(commands=['start'])
def send_welcome(message):
    log_user_activity(message)
    welcome_text = (
        "Selamat datang di CryptoBot! Berikut adalah beberapa perintah yang bisa Anda gunakan:\n\n"
        "/roast <alamat_dompet_kripto> - Mendapatkan roasting untuk alamat dompet kripto Anda.\n"
        "/price <nama_kripto> - Mendapatkan harga terkini dari kripto yang Anda inginkan.\n"
        "/balance <alamat_dompet_kripto> - Melihat saldo ETH dari alamat dompet kripto Anda.\n"
        "\nContoh penggunaan:\n"
        "/roast 0x1234567890abcdef1234567890abcdef12345678\n"
        "/price bitcoin\n"
        "/balance 0x1234567890abcdef1234567890abcdef12345678\n"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['roast'])
def roast_wallet(message):
    log_user_activity(message)
    # Mengambil argumen setelah /roast
    wallet_text = message.text[7:].strip()  # Mengambil teks setelah '/roast '

    # Memeriksa apakah teks adalah alamat dompet kripto yang valid
    if not wallet_text.startswith('0x') or len(wallet_text) != 42:
        bot.reply_to(message, "Tolong kirimkan alamat dompet kripto yang valid setelah perintah /roast, misalnya: /roast 0x1234567890abcdef1234567890abcdef12345678")
        return

    # Mendapatkan saldo dompet
    balance = get_wallet_balance(wallet_text)
    if balance is None:
        bot.reply_to(message, "Tidak dapat mengambil saldo dompet. Pastikan alamat dompet sudah benar.")
        return

    # Menghasilkan roast dengan saldo dompet
    roast_response = generate_roast(wallet_text, balance)
    bot.reply_to(message, roast_response)

@bot.message_handler(commands=['price'])
def get_price(message):
    log_user_activity(message)
    # Mengambil argumen setelah /price
    crypto_id = message.text[7:].strip().lower()  # Mengambil teks setelah '/price '

    if not crypto_id:
        bot.reply_to(message, "Silakan masukkan nama kripto setelah perintah /price, misalnya: /price bitcoin")
        return

    price = get_crypto_price(crypto_id)
    if price is not None:
        bot.reply_to(message, f"Harga {crypto_id.capitalize()} saat ini adalah ${price}.")
    else:
        bot.reply_to(message, "Tidak dapat menemukan harga untuk kripto yang diminta. Pastikan nama kripto sudah benar.")

@bot.message_handler(commands=['balance'])
def check_balance(message):
    log_user_activity(message)
    # Mengambil argumen setelah /balance
    wallet_address = message.text[9:].strip()  # Mengambil teks setelah '/balance '

    # Memeriksa apakah teks adalah alamat dompet kripto yang valid
    if not wallet_address.startswith('0x') or len(wallet_address) != 42:
        bot.reply_to(message, "Tolong kirimkan alamat dompet kripto yang valid setelah perintah /balance, misalnya: /balance 0x1234567890abcdef1234567890abcdef12345678")
        return

    balance = get_wallet_balance(wallet_address)
    if balance is not None:
        bot.reply_to(message, f"Saldo dompet {wallet_address} adalah {balance} ETH.")
    else:
        bot.reply_to(message, "Tidak dapat mengambil saldo dompet. Pastikan alamat dompet sudah benar.")

if __name__ == '__main__':
    bot.polling()
