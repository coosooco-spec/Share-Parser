import os
import csv
import asyncio
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from dotenv import load_dotenv
from io import StringIO

load_dotenv()

# Конфиг
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

client = TelegramClient('session', API_ID, API_HASH)

async def parse_group_members(group_link):
    """Парсит участников группы по ссылке"""
    try:
        # Получаем сущность группы по ссылке
        entity = await client.get_entity(group_link)
        
        # Получаем всех участников
        participants = []
        offset = 0
        limit = 200
        
        while True:
            try:
                result = await client(GetParticipantsRequest(
                    channel=entity,
                    offset=offset,
                    filter=ChannelParticipantsSearch(''),
                    limit=limit,
                    hash=0
                ))
                
                if not result.participants:
                    break
                
                participants.extend(result.participants)
                offset += limit
                
            except Exception as e:
                print(f"Ошибка при получении участников: {e}")
                break
        
        # Формируем данные
        members_data = []
        for participant in participants:
            user = participant.user
            members_data.append({
                'ID': user.id,
                'Имя': user.first_name or '',
                'Фамилия': user.last_name or '',
                'Юзернейм': user.username or 'Нет',
                'Статус': 'Бот' if user.bot else 'Пользователь',
                'Дата присоединения': 'Неизвестно'
            })
        
        return members_data, len(members_data)
    
    except Exception as e:
        print(f"Ошибка: {e}")
        return None, 0

def create_csv(members_data):
    """Создает CSV файл из данных участников"""
    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=['ID', 'Имя', 'Фамилия', 'Юзернейм', 'Статус', 'Дата присоединения'])
    writer.writeheader()
    writer.writerows(members_data)
    return csv_buffer.getvalue()

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    """Команда /start"""
    await event.reply(
        "👋 Привет! Я бот для парсинга участников Telegram групп.\n\n"
        "📝 Отправь мне ссылку на группу (например: https://t.me/groupname), "
        "и я парсю список всех участников и отправлю тебе CSV файл.\n\n"
        "⚠️ Важно: Я должен быть добавлен в группу как администратор!"
    )

@client.on(events.NewMessage)
async def handle_message(event):
    """Обработка входящих сообщений"""
    if event.message.text.startswith('/'):
        return
    
    message_text = event.message.text.strip()
    
    # Проверяем, это ли ссылка на группу
    if 't.me/' in message_text or 'telegram.me/' in message_text:
        await event.reply("⏳ Парсю участников группы... Это может занять время.")
        
        members_data, count = await parse_group_members(message_text)
        
        if members_data is None:
            await event.reply("❌ Ошибка: Не удалось получить доступ к группе.\n"
                            "Убедитесь, что:\n"
                            "1. Ссылка верна\n"
                            "2. Я добавлен в группу\n"
                            "3. У меня есть права на просмотр участников")
            return
        
        if count == 0:
            await event.reply("❌ В группе нет участников или доступ запрещен.")
            return
        
        # Создаем CSV
        csv_content = create_csv(members_data)
        
        # Сохраняем временный файл
        filename = f"group_members_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        
        # Отправляем файл
        await event.reply(f"✅ Найдено участников: {count}\n\n📥 Загружаю файл...")
        
        with open(filename, 'rb') as f:
            await client.send_file(event.chat_id, f, caption=f"📊 Участники группы ({count} человек)")
        
        # Удаляем временный файл
        os.remove(filename)
    else:
        await event.reply("📍 Пожалуйста, отправь ссылку на Telegram группу (например: https://t.me/groupname)")

async def main():
    """Основной цикл бота"""
    print("🚀 Бот запущен...")
    await client.start(bot_token=BOT_TOKEN)
    print("✅ Бот подключен к Telegram")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
