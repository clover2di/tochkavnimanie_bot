from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from .database import Base


class ApplicationStatus(enum.Enum):
    PENDING = "pending"           # Ожидает рассмотрения
    APPROVED = "approved"         # Одобрена
    REJECTED = "rejected"         # Отклонена
    NEEDS_REVISION = "revision"   # Требует доработки


class AdminRole(enum.Enum):
    SUPER_ADMIN = "super_admin"   # Полный доступ
    MODERATOR = "moderator"       # Просмотр и модерация заявок


class User(Base):
    """Участник конкурса."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    full_name = Column(String(500), nullable=True)  # ФИО
    city = Column(String(255), nullable=True)       # Населенный пункт
    school = Column(String(500), nullable=True)     # Школа/лицей/гимназия
    grade = Column(String(50), nullable=True)       # Класс
    
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    applications = relationship("Application", back_populates="user", lazy="selectin")


class Nomination(Base):
    """Этап конкурса."""
    __tablename__ = "nominations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)       # Название этапа
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime, nullable=True)     # Дата начала этапа
    deadline = Column(DateTime, nullable=True)       # Дедлайн этапа
    order = Column(Integer, default=0)               # Порядок отображения
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    applications = relationship("Application", back_populates="nomination", lazy="selectin")


class Application(Base):
    """Заявка на конкурс."""
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    nomination_id = Column(Integer, ForeignKey("nominations.id"), nullable=False)
    
    # Фотографии (до 5 штук, храним пути через запятую или JSON)
    photos = Column(Text, nullable=True)             # JSON список путей к фото
    photos_remote_paths = Column(Text, nullable=True)  # Пути на R7 сервере
    
    # Комментарий (текст или голосовое)
    comment_text = Column(Text, nullable=True)       # Текстовый комментарий
    voice_file_id = Column(String(255), nullable=True)  # Telegram file_id голосового
    voice_remote_path = Column(String(500), nullable=True)  # Путь голосового на R7
    
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.PENDING)
    admin_comment = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="applications")
    nomination = relationship("Nomination", back_populates="applications")


class Admin(Base):
    """Администратор панели управления."""
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=True)  # Опционально для уведомлений
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(AdminRole), default=AdminRole.MODERATOR)
    
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())


class BotContent(Base):
    """Тексты и контент бота (редактируемые через админку)."""
    __tablename__ = "bot_content"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    description = Column(String(500), nullable=True)  # Описание для админки
    
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Settings(Base):
    """Настройки бота (редактируемые через админку)."""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(1000), nullable=False)
    value_type = Column(String(50), default="string")  # string, int, bool, json
    description = Column(String(500), nullable=True)
    
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class BroadcastStatus(enum.Enum):
    DRAFT = "draft"         # Черновик
    SENDING = "sending"     # Отправляется
    SENT = "sent"           # Отправлено
    FAILED = "failed"       # Ошибка


class Broadcast(Base):
    """Сообщения для рассылки участникам."""
    __tablename__ = "broadcasts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)                     # Текст сообщения
    image_path = Column(String(500), nullable=True)         # Путь к изображению (локальный)
    
    status = Column(SQLEnum(BroadcastStatus), default=BroadcastStatus.DRAFT)
    sent_count = Column(Integer, default=0)                 # Сколько отправлено
    failed_count = Column(Integer, default=0)               # Сколько ошибок
    total_count = Column(Integer, default=0)                # Всего получателей
    
    created_at = Column(DateTime, default=func.now())
    sent_at = Column(DateTime, nullable=True)               # Когда отправлено
