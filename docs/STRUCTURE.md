# Структура проекта "Точка внимания"

## Общее описание

Telegram-бот для всероссийского дизайн-челленджа среди школьников «Точка внимания». Бот позволяет участникам подавать заявки на конкурс, а организаторам — управлять заявками через веб-панель администратора.

## Последние изменения (кратко)

- Улучшена безопасность: поддержка bcrypt-хэшей для пароля админа, предупреждения только при дефолтных значениях секрета/пароля.
- Защита админки: CSRF, rate-limiting на логин, безопасное сравнение паролей.
- Фильтры в списке заявок: поиск по ФИО/школе, фильтр по городу, диапазон дат.
- Экспорт в Excel с учётом фильтров; ограничение размера экспорта для защиты памяти.
- Резервные копии: базовые утилиты/роуты для создания и восстановления бэкапов.
- Улучшена обработка файлов: асинхронная запись `aiofiles` и проверка лимитов по размеру для рассылок.
- Оптимизированы запросы к БД (убраны N+1), улучшено управление пулами подключений для разных СУБД.


## Технологический стек

| Компонент | Технология | Версия |
|-----------|------------|--------|
| Язык | Python | 3.11+ |
| Telegram Bot | aiogram | 3.4.1 |
| Веб-фреймворк | FastAPI | 0.128.0 |
| ORM | SQLAlchemy | 2.0.23 |
| База данных | SQLite | aiosqlite |
| Шаблонизатор | Jinja2 | 3.1.2 |
| Валидация | Pydantic | 2.5.2 |
| HTTP-клиент | httpx | 0.25.2 |

---

## Структура каталогов

```
shkolatochka_bot/
├── .env                    # Конфигурация (секреты)
├── .env.example            # Пример конфигурации
├── requirements.txt        # Зависимости Python
├── run.py                  # Точка входа приложения
│
├── config/                 # Конфигурация
│   ├── __init__.py
│   └── settings.py         # Настройки приложения (Pydantic)
│
├── database/               # Слой работы с БД
│   ├── __init__.py
│   ├── database.py         # Подключение к БД, сессии
│   ├── models.py           # SQLAlchemy модели
│   └── crud.py             # CRUD операции
│
├── bot/                    # Telegram бот
│   ├── __init__.py
│   ├── main.py             # Инициализация бота
│   ├── handlers/           # Обработчики сообщений
│   │   ├── __init__.py
│   │   ├── start.py        # Команда /start
│   │   └── application.py  # FSM подачи заявки
│   ├── keyboards/          # Клавиатуры
│   │   ├── __init__.py
│   │   └── menus.py        # Меню и кнопки
│   └── utils/              # Утилиты
│       └── local_storage.py # Локальное хранение файлов
│
├── admin/                  # Админ-панель (FastAPI)
│   ├── __init__.py
│   ├── app.py              # FastAPI приложение
│   ├── routes/             # Маршруты
│   │   ├── auth.py         # Авторизация
│   │   ├── dashboard.py    # Дашборд
│   │   ├── applications.py # Заявки
│   │   ├── nominations.py  # Этапы конкурса
│   │   ├── content.py      # Контент бота
│   │   ├── broadcasts.py   # Рассылка сообщений
│   │   ├── logs.py         # Просмотр логов
│   │   └── settings_routes.py # Настройки
│   ├── templates/          # HTML шаблоны (Jinja2)
│   │   ├── base.html       # Базовый шаблон
│   │   ├── login.html      # Страница входа
│   │   ├── dashboard.html  # Дашборд
│   │   ├── applications/   # Шаблоны заявок
│   │   ├── nominations/    # Шаблоны этапов
│   │   ├── content/        # Шаблоны контента
│   │   ├── broadcasts/     # Шаблоны рассылок
│   │   ├── logs/           # Шаблоны логов
│   │   └── settings/       # Шаблоны настроек
│   ├── static/             # Статические файлы
│   │   ├── icon.png        # Иконка сайта
│   │   └── fonts/          # Шрифты FuturaPT
│   └── utils/              # Утилиты админки
│       ├── auth.py         # Авторизация
│       └── jinja_filters.py # Фильтры Jinja2
│
├── uploads/                # Загруженные файлы
│   └── broadcasts/         # Изображения для рассылок
│
├── logs/                   # Логи приложения
│   └── bot.log             # Основной лог-файл
│
└── docs/                   # Документация
    ├── STRUCTURE.md        # Этот файл
    ├── ADMIN_GUIDE.md      # Руководство менеджера
    └── DEPLOYMENT.md       # Инструкция по развёртыванию
```

---

## Модели данных (database/models.py)

### User — Участник конкурса
```python
- id: int                   # ID в базе
- telegram_id: BigInteger   # Telegram ID пользователя
- username: str             # Username в Telegram
- full_name: str            # ФИО участника
- city: str                 # Населённый пункт
- school: str               # Школа/лицей/гимназия
- grade: str                # Класс
- is_blocked: bool          # Заблокирован ли
- created_at: datetime      # Дата регистрации
- updated_at: datetime      # Дата обновления
```

### Nomination — Этап конкурса
```python
- id: int                   # ID этапа
- name: str                 # Название этапа
- description: text         # Описание
- is_active: bool           # Активен ли этап
- start_date: datetime      # Дата начала
- deadline: datetime        # Дедлайн
- created_at: datetime      # Дата создания
- updated_at: datetime      # Дата обновления
```

### Application — Заявка на конкурс
```python
- id: int                   # ID заявки
- user_id: FK -> User       # Участник
- nomination_id: FK -> Nomination  # Этап
- photos: JSON              # Telegram file_id фото
- photos_remote_paths: JSON # URL фото для просмотра
- comment_text: text        # Текстовый комментарий
- voice_file_id: str        # Telegram file_id голосового
- voice_remote_path: str    # URL голосового для просмотра
- status: Enum              # Статус заявки
- admin_comment: text       # Комментарий модератора
- created_at: datetime      # Дата подачи
- updated_at: datetime      # Дата обновления
```

### Статусы заявки (ApplicationStatus)
- `PENDING` — Ожидает рассмотрения
- `APPROVED` — Одобрена
- `REJECTED` — Отклонена
- `NEEDS_REVISION` — Требует доработки

### Broadcast — Сообщение для рассылки
```python
- id: int                   # ID сообщения
- text: text                # Текст сообщения
- image_path: str           # Путь к изображению
- status: Enum              # Статус рассылки
- sent_count: int           # Отправлено
- failed_count: int         # Ошибок
- total_count: int          # Всего получателей
- created_at: datetime      # Дата создания
- sent_at: datetime         # Дата отправки
```

### BotContent — Тексты бота
```python
- id: int
- key: str                  # Ключ (например: "greeting")
- value: text               # Текст сообщения
- description: str          # Описание для админки
```

### Settings — Настройки
```python
- id: int
- key: str                  # Ключ настройки
- value: str                # Значение
- value_type: str           # Тип (string, bool, int)
- description: str          # Описание
```

---

## Бот: FSM (Finite State Machine)

Процесс подачи заявки реализован через состояния:

```
START
  │
  ▼
entering_fio      →  Ввод ФИО
  │
  ▼
entering_city     →  Ввод города
  │
  ▼
entering_school   →  Ввод школы
  │
  ▼
entering_grade    →  Ввод класса
  │
  ▼
choosing_stage    →  Выбор этапа (InlineKeyboard)
  │
  ▼
uploading_photos  →  Загрузка 3-5 фото
  │
  ▼
entering_comment  →  Текст или голосовое сообщение
  │
  ▼
FINISH            →  Заявка сохранена
```

---

## Админ-панель: Маршруты

| Путь | Метод | Описание |
|------|-------|----------|
| `/login` | GET/POST | Авторизация |
| `/logout` | GET | Выход |
| `/dashboard` | GET | Дашборд со статистикой |
| `/applications` | GET | Список заявок |
| `/applications/{id}` | GET | Детали заявки |
| `/applications/{id}/status` | POST | Изменить статус |
| `/nominations` | GET | Список этапов |
| `/nominations/new` | GET/POST | Создать этап |
| `/nominations/{id}/edit` | GET/POST | Редактировать этап |
| `/nominations/{id}/delete` | POST | Удалить этап |
| `/content` | GET | Список текстов бота |
| `/content/{key}/edit` | GET/POST | Редактировать текст |
| `/content/{key}/reset` | GET | Сбросить к умолчанию |
| `/broadcasts` | GET | Список рассылок |
| `/broadcasts/new` | GET/POST | Создать рассылку |
| `/broadcasts/{id}/send` | POST | Отправить рассылку |
| `/logs` | GET | Просмотр логов |
| `/settings` | GET/POST | Настройки |

---

## Конфигурация (.env)

```env
# Telegram Bot
BOT_TOKEN=123456:ABC-DEF...

# Admin Panel
ADMIN_SECRET_KEY=your-secret-key-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure-password

# Database
DATABASE_URL=sqlite+aiosqlite:///./database/bot.db

# File Storage
UPLOADS_DIR=uploads  # Папка для загруженных файлов

# Debug
DEBUG=false
```

---

## Запуск приложения

```bash
# Оба сервиса (бот + админка)
python run.py

# Только бот
python run.py bot

# Только админка
python run.py admin
```

При запуске:
1. Инициализируется логирование (`logs/bot.log`)
2. Создаётся/обновляется база данных
3. Запускается Telegram бот (polling)
4. Запускается FastAPI сервер на порту 8000

---

## Дизайн-система

| Элемент | Значение |
|---------|----------|
| Фон | `#f8f8f8` |
| Основной цвет (красный) | `#eb3d24` |
| Вторичный цвет (зелёный) | `#29a64a` |
| Цвет текста | `#58595b` |
| Шрифт | FuturaPT |
| Тени | Отсутствуют (flat design) |

---

## Логирование

Логи записываются в `logs/bot.log` с ротацией:
- Максимальный размер файла: 5 MB
- Хранится до 5 резервных копий
- Формат: `YYYY-MM-DD HH:MM:SS,ms - module - LEVEL - message`

Уровни логирования:
- `DEBUG` — отладочная информация
- `INFO` — информационные сообщения
- `WARNING` — предупреждения
- `ERROR` — ошибки
